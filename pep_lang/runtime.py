from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from concurrent.futures import Future, ThreadPoolExecutor

from pep_lang.ast_nodes import (
    AssignStmt,
    AwaitStmt,
    ExprStmt,
    FnStmt,
    ForStmt,
    IfStmt,
    PipelineAssignStmt,
    PipelineStmt,
    PrintStmt,
    Program,
    RepeatStmt,
    RouteStmt,
    ReturnStmt,
    ServerStmt,
    SetStmt,
    Statement,
    TaskStmt,
    UseStmt,
    VerifyStmt,
    WatchStmt,
)
from pep_lang.evaluator import ErrorValue, EvalError, eval_expr
from pep_lang.module_loader import ModuleLoadError, load_module
from pep_lang.parser import parse_program
from pep_lang.pipeline import PipelineEngine, PipelineError, PipelineResult
from pep_lang.server import EmbeddedServer


class RuntimeErrorPep(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value: Any):
        super().__init__("return")
        self.value = value


@dataclass
class UserFunction:
    name: str
    params: List[str]
    body: List[Statement]


class Runtime:
    def __init__(self, base_path: str = "") -> None:
        self.base_path = base_path
        self.globals: Dict[str, Any] = {}
        self.functions: Dict[str, UserFunction] = {}
        self.function_callables: Dict[str, Any] = {}
        self.modules: Dict[str, Any] = {}
        self.pipeline_results: Dict[str, PipelineResult] = {}
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.named_tasks: Dict[str, Future] = {}
        self._anonymous_tasks: List[Future] = []
        self.servers: List[EmbeddedServer] = []

    def shutdown(self) -> None:
        for server in self.servers:
            server.stop()
        self.executor.shutdown(wait=True)

    def run_script(self, source: str) -> None:
        program = parse_program(source)
        self.execute_program(program)

    def execute_program(self, program: Program) -> None:
        self._execute_block(program.statements, self.globals)

    def _execute_block(self, statements: List[Statement], env: Dict[str, Any]) -> None:
        for stmt in statements:
            self._execute_statement(stmt, env)

    def _execute_statement(self, stmt: Statement, env: Dict[str, Any]) -> None:
        if isinstance(stmt, UseStmt):
            try:
                loaded = load_module(stmt.module, stmt.version)
            except ModuleLoadError as exc:
                raise RuntimeErrorPep(str(exc)) from exc
            binding_name = stmt.alias or stmt.module
            self.modules[binding_name] = loaded
            env[binding_name] = loaded
            return

        if isinstance(stmt, AssignStmt):
            env[stmt.name] = self._eval(stmt.expr, env)
            return

        if isinstance(stmt, SetStmt):
            if stmt.name not in env:
                raise RuntimeErrorPep(f"Variable not found: {stmt.name}")
            env[stmt.name] = self._eval(stmt.expr, env)
            return

        if isinstance(stmt, PrintStmt):
            value = self._eval(stmt.expr, env)
            print(value)
            return

        if isinstance(stmt, ExprStmt):
            self._eval(stmt.expr, env)
            return

        if isinstance(stmt, ReturnStmt):
            raise ReturnSignal(self._eval(stmt.expr, env))

        if isinstance(stmt, IfStmt):
            if self._truthy(self._eval(stmt.condition, env)):
                self._execute_block(stmt.body, env)
                return
            for cond, body in stmt.elif_branches:
                if self._truthy(self._eval(cond, env)):
                    self._execute_block(body, env)
                    return
            if stmt.else_body is not None:
                self._execute_block(stmt.else_body, env)
            return

        if isinstance(stmt, ForStmt):
            iterable = self._eval(stmt.iterable_expr, env)
            for item in iterable:
                local = dict(env)
                local[stmt.var_name] = item
                self._execute_block(stmt.body, local)
                env.update({k: v for k, v in local.items() if k in env or k == stmt.var_name})
            return

        if isinstance(stmt, RepeatStmt):
            count = int(self._eval(stmt.count_expr, env))
            for _ in range(count):
                self._execute_block(stmt.body, env)
            return

        if isinstance(stmt, TaskStmt):
            future = self.executor.submit(self._run_task_body, stmt.body, env)
            if stmt.name:
                self.named_tasks[stmt.name] = future
            else:
                self._anonymous_tasks.append(future)
            return

        if isinstance(stmt, AwaitStmt):
            for task_name in stmt.task_names:
                fut = self.named_tasks.get(task_name)
                if fut is None:
                    raise RuntimeErrorPep(f"Task not found: {task_name}")
                fut.result()
            return

        if isinstance(stmt, FnStmt):
            self.functions[stmt.name] = UserFunction(
                name=stmt.name,
                params=stmt.params,
                body=stmt.body,
            )
            wrapped = self._wrap_function(stmt.name)
            self.function_callables[stmt.name] = wrapped
            env[stmt.name] = wrapped
            return

        if isinstance(stmt, ServerStmt):
            self._start_server(stmt, env)
            return

        if isinstance(stmt, VerifyStmt):
            engine = PipelineEngine(self._eval_env(env), base_path=self.base_path)
            try:
                result, rejected = engine.run_with_rejects(
                    stmt.pipeline.source, stmt.pipeline.stages
                )
            except (PipelineError, OSError) as exc:
                raise RuntimeErrorPep(str(exc)) from exc
            env[stmt.name] = result.value
            self.pipeline_results[stmt.name] = result
            for item in rejected:
                item_env = dict(env)
                if isinstance(item, dict):
                    item_env.update(item)
                else:
                    item_env["item"] = item
                self._execute_block(stmt.else_body, item_env)
            return

        if isinstance(stmt, PipelineAssignStmt):
            engine = PipelineEngine(self._eval_env(env), base_path=self.base_path)
            try:
                result = engine.run(stmt.pipeline.source, stmt.pipeline.stages)
            except (PipelineError, OSError) as exc:
                raise RuntimeErrorPep(str(exc)) from exc
            env[stmt.name] = result.value
            self.pipeline_results[stmt.name] = result
            return

        if isinstance(stmt, PipelineStmt):
            engine = PipelineEngine(self._eval_env(env), base_path=self.base_path)
            try:
                engine.run(stmt.pipeline.source, stmt.pipeline.stages)
            except (PipelineError, OSError) as exc:
                raise RuntimeErrorPep(str(exc)) from exc
            return

        if isinstance(stmt, WatchStmt):
            self._watch(stmt.target, env)
            return

        raise RuntimeErrorPep(f"Unsupported statement: {type(stmt).__name__}")

    def _eval(self, expr: str, env: Dict[str, Any]) -> Any:
        local_env = self._eval_env(env)
        try:
            return eval_expr(expr, local_env)
        except EvalError as exc:
            raise RuntimeErrorPep(str(exc)) from exc

    def _eval_env(self, env: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(self.globals)
        merged.update(env)
        merged.update(self.function_callables)
        merged.update(self.modules)
        return merged

    def _wrap_function(self, fn_name: str):
        def _callable(*args):
            fn = self.functions[fn_name]
            if len(args) != len(fn.params):
                raise RuntimeErrorPep(
                    f"Function '{fn_name}' expects {len(fn.params)} args, got {len(args)}"
                )
            local_env = dict(self.globals)
            local_env.update(zip(fn.params, args))
            local_env.update(self.function_callables)
            try:
                self._execute_block(fn.body, local_env)
            except ReturnSignal as signal:
                return signal.value
            return None

        return _callable

    def _watch(self, target: str, env: Dict[str, Any]) -> None:
        result = self.pipeline_results.get(target)
        if result is None:
            value = env.get(target, self.globals.get(target))
            if value is None:
                raise RuntimeErrorPep(f"No pipeline or value named '{target}'")
            print(f"{target:20} value 1 item")
            return

        for metric in result.metrics:
            print(
                f"{metric.name:20} {metric.status:7} "
                f"{metric.items:6} items {metric.elapsed_ms:8.2f} ms"
            )

    def _start_server(self, stmt: ServerStmt, env: Dict[str, Any]) -> None:
        port = int(self._eval(stmt.port_expr, env))
        routes: Dict[str, Any] = {}
        for route in stmt.routes:
            routes[route.path] = self._build_route_handler(route, env)

        server = EmbeddedServer(port=port, routes=routes)
        server.start()
        self.servers.append(server)
        print(f"server started on port {port}")

    def _build_route_handler(self, route: RouteStmt, env: Dict[str, Any]):
        def _handler() -> Any:
            local_env = dict(env)
            try:
                self._execute_block(route.body, local_env)
            except ReturnSignal as signal:
                return signal.value
            return {"ok": True}

        return _handler

    def _run_task_body(self, body: List[Statement], env: Dict[str, Any]) -> None:
        local_env = dict(env)
        self._execute_block(body, local_env)

    @staticmethod
    def _truthy(value: Any) -> bool:
        if isinstance(value, ErrorValue):
            return False
        return bool(value)


def run_source(source: str) -> Runtime:
    runtime = Runtime()
    runtime.run_script(source)
    return runtime
