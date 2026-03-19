from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pep_lang.ast_nodes import (
    AssignStmt,
    AwaitStmt,
    ExprStmt,
    FnStmt,
    ForStmt,
    IfStmt,
    PipelineAssignStmt,
    PipelineExpr,
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


class ParseError(Exception):
    pass


@dataclass
class Line:
    number: int
    indent: int
    text: str


class Parser:
    def __init__(self, source: str):
        self.lines = self._to_lines(source)
        self.index = 0

    def parse(self) -> Program:
        statements = self._parse_block(expected_indent=0)
        return Program(line=1, statements=statements)

    def _to_lines(self, source: str) -> List[Line]:
        out: List[Line] = []
        raw_lines = source.splitlines()
        for i, raw in enumerate(raw_lines, start=1):
            if not raw.strip():
                continue
            stripped = raw.lstrip(" ")
            if stripped.startswith("#"):
                continue
            indent = len(raw) - len(stripped)
            out.append(Line(number=i, indent=indent, text=stripped.rstrip()))
        return out

    def _peek(self) -> Optional[Line]:
        if self.index >= len(self.lines):
            return None
        return self.lines[self.index]

    def _consume(self) -> Line:
        line = self._peek()
        if line is None:
            raise ParseError("Unexpected EOF")
        self.index += 1
        return line

    def _parse_block(self, expected_indent: int) -> List[Statement]:
        statements: List[Statement] = []
        while True:
            line = self._peek()
            if line is None:
                break
            if line.indent < expected_indent:
                break
            if line.indent > expected_indent:
                raise ParseError(
                    f"Unexpected indentation at line {line.number}: {line.text}"
                )
            stmt = self._parse_statement(expected_indent)
            statements.append(stmt)
        return statements

    def _parse_statement(self, current_indent: int) -> Statement:
        line = self._consume()
        text = line.text

        if text.startswith("use "):
            return self._parse_use(line)
        if text.startswith("fn "):
            return self._parse_fn(line, current_indent)
        if text.startswith("task") and text.endswith(":"):
            return self._parse_task(line, current_indent)
        if text.startswith("server ") and text.endswith(":"):
            return self._parse_server(line, current_indent)
        if text.startswith("if ") and text.endswith(":"):
            return self._parse_if(line, current_indent)
        if text.startswith("for ") and text.endswith(":"):
            return self._parse_for(line, current_indent)
        if text.startswith("repeat ") and text.endswith(":"):
            return self._parse_repeat(line, current_indent)
        if text.startswith("set "):
            payload = text[len("set ") :]
            if "=" not in payload:
                raise ParseError(f"Invalid set statement at line {line.number}")
            name, expr = payload.split("=", 1)
            return SetStmt(line=line.number, name=name.strip(), expr=expr.strip())
        if text.startswith("print "):
            return PrintStmt(line=line.number, expr=text[len("print ") :].strip())
        if text.startswith("return "):
            return ReturnStmt(line=line.number, expr=text[len("return ") :].strip())
        if text.startswith("watch "):
            return WatchStmt(line=line.number, target=text[len("watch ") :].strip())
        if text.startswith("await "):
            payload = text[len("await ") :].strip()
            names = [n.strip() for n in payload.split(",") if n.strip()]
            if not names:
                raise ParseError(f"Invalid await statement at line {line.number}")
            return AwaitStmt(line=line.number, task_names=names)

        if ":=" in text:
            return self._parse_assignment(line, current_indent)

        if "->" in text:
            pipeline = self._parse_pipeline_inline(text, line.number)
            return PipelineStmt(line=line.number, pipeline=pipeline)

        return ExprStmt(line=line.number, expr=text)

    def _parse_use(self, line: Line) -> UseStmt:
        payload = line.text[len("use ") :].strip()
        alias = None
        if " as " in payload:
            payload, alias = payload.split(" as ", 1)
            payload = payload.strip()
            alias = alias.strip()
        version = None
        module = payload
        if "@" in payload:
            module, version = payload.split("@", 1)
            module = module.strip()
            version = version.strip()
        return UseStmt(line=line.number, module=module, version=version, alias=alias)

    def _parse_assignment(self, line: Line, current_indent: int) -> Statement:
        text = line.text
        mutable = False
        if text.startswith("mut "):
            mutable = True
            text = text[len("mut ") :].strip()

        name, expr = text.split(":=", 1)
        name = name.strip()
        expr = expr.strip()

        if expr:
            expr = self._collect_multiline_expression(expr, current_indent)

        if not expr:
            pipeline = self._parse_pipeline_block(line.number, current_indent)
            return PipelineAssignStmt(
                line=line.number,
                name=name,
                pipeline=pipeline,
                mutable=mutable,
            )

        if "->" in expr:
            has_else = expr.endswith(" else:")
            if has_else:
                expr = expr[: -len(" else:")].strip()
            pipeline = self._parse_pipeline_inline(expr, line.number)
            if has_else:
                else_body = self._parse_block(expected_indent=current_indent + 4)
                return VerifyStmt(
                    line=line.number,
                    name=name,
                    pipeline=pipeline,
                    else_body=else_body,
                )
            return PipelineAssignStmt(
                line=line.number,
                name=name,
                pipeline=pipeline,
                mutable=mutable,
            )

        return AssignStmt(line=line.number, name=name, expr=expr, mutable=mutable)

    def _parse_fn(self, line: Line, current_indent: int) -> FnStmt:
        header = line.text
        if not header.endswith(":"):
            raise ParseError(f"Function must end with ':' at line {line.number}")

        payload = header[len("fn ") : -1].strip()
        if "(" not in payload or ")" not in payload:
            raise ParseError(f"Invalid function header at line {line.number}")

        name, rest = payload.split("(", 1)
        params_part, _ = rest.split(")", 1)

        name = name.strip()
        params = [p.strip() for p in params_part.split(",") if p.strip()]

        body_indent = current_indent + 4
        body = self._parse_block(expected_indent=body_indent)
        if not body:
            raise ParseError(f"Function body cannot be empty at line {line.number}")
        return FnStmt(line=line.number, name=name, params=params, body=body)

    def _parse_task(self, line: Line, current_indent: int) -> TaskStmt:
        payload = line.text[:-1].strip()
        name = None
        if payload != "task":
            if not payload.startswith("task "):
                raise ParseError(f"Invalid task header at line {line.number}")
            name = payload[len("task ") :].strip()
            if not name:
                raise ParseError(f"Invalid task name at line {line.number}")

        body = self._parse_block(expected_indent=current_indent + 4)
        if not body:
            raise ParseError(f"Task body cannot be empty at line {line.number}")
        return TaskStmt(line=line.number, name=name, body=body)

    def _parse_server(self, line: Line, current_indent: int) -> ServerStmt:
        payload = line.text[len("server ") : -1].strip()
        if not payload:
            raise ParseError(f"Missing port in server statement at line {line.number}")

        routes: List[RouteStmt] = []
        body_indent = current_indent + 4

        while True:
            nxt = self._peek()
            if nxt is None or nxt.indent < body_indent:
                break
            if nxt.indent > body_indent:
                raise ParseError(
                    f"Unexpected indentation inside server block at line {nxt.number}"
                )

            header = self._consume()
            if not header.text.startswith("route ") or not header.text.endswith(":"):
                raise ParseError(
                    f"Only route declarations are allowed inside server at line {header.number}"
                )

            route_expr = header.text[len("route ") : -1].strip()
            route_path = route_expr
            if (
                (route_path.startswith('"') and route_path.endswith('"'))
                or (route_path.startswith("'") and route_path.endswith("'"))
            ):
                route_path = route_path[1:-1]

            route_body = self._parse_block(expected_indent=body_indent + 4)
            if not route_body:
                raise ParseError(f"Empty route body at line {header.number}")
            routes.append(RouteStmt(line=header.number, path=route_path, body=route_body))

        if not routes:
            raise ParseError(f"Server block requires at least one route at line {line.number}")
        return ServerStmt(line=line.number, port_expr=payload, routes=routes)

    def _parse_if(self, line: Line, current_indent: int) -> IfStmt:
        condition = line.text[len("if ") : -1].strip()
        body_indent = current_indent + 4
        body = self._parse_block(expected_indent=body_indent)

        elif_branches: List[tuple[str, List[Statement]]] = []
        else_body: Optional[List[Statement]] = None

        while True:
            nxt = self._peek()
            if nxt is None or nxt.indent != current_indent:
                break
            if nxt.text.startswith("elif ") and nxt.text.endswith(":"):
                self._consume()
                cond = nxt.text[len("elif ") : -1].strip()
                branch_body = self._parse_block(expected_indent=body_indent)
                elif_branches.append((cond, branch_body))
                continue
            if nxt.text == "else:":
                self._consume()
                else_body = self._parse_block(expected_indent=body_indent)
                break
            break

        return IfStmt(
            line=line.number,
            condition=condition,
            body=body,
            elif_branches=elif_branches,
            else_body=else_body,
        )

    def _parse_for(self, line: Line, current_indent: int) -> ForStmt:
        payload = line.text[len("for ") : -1].strip()
        if " in " not in payload:
            raise ParseError(f"Invalid for statement at line {line.number}")
        var_name, iterable_expr = payload.split(" in ", 1)
        body = self._parse_block(expected_indent=current_indent + 4)
        return ForStmt(
            line=line.number,
            var_name=var_name.strip(),
            iterable_expr=iterable_expr.strip(),
            body=body,
        )

    def _parse_repeat(self, line: Line, current_indent: int) -> RepeatStmt:
        count_expr = line.text[len("repeat ") : -1].strip()
        body = self._parse_block(expected_indent=current_indent + 4)
        return RepeatStmt(line=line.number, count_expr=count_expr, body=body)

    def _parse_pipeline_inline(self, expr: str, line_number: int) -> PipelineExpr:
        parts = [p.strip() for p in expr.split("->")]
        if not parts or not parts[0]:
            raise ParseError(f"Invalid pipeline at line {line_number}")
        source = parts[0]
        stages = [p for p in parts[1:] if p]
        return PipelineExpr(source=source, stages=stages)

    def _parse_pipeline_block(self, line_number: int, current_indent: int) -> PipelineExpr:
        expected_indent = current_indent + 4
        first = self._peek()
        if first is None:
            raise ParseError(f"Expected pipeline after ':=' at line {line_number}")
        if first.indent != expected_indent:
            raise ParseError(
                f"Pipeline block must be indented at line {line_number}"
            )

        source_line = self._consume()
        source = self._collect_multiline_expression(source_line.text, expected_indent)
        stages: List[str] = []

        while True:
            nxt = self._peek()
            if nxt is None or nxt.indent != expected_indent:
                break
            if not nxt.text.startswith("->"):
                break
            consumed = self._consume()
            stage = consumed.text[2:].strip()
            if not stage:
                raise ParseError(f"Empty pipeline stage at line {consumed.number}")
            stages.append(stage)

        return PipelineExpr(source=source, stages=stages)

    def _collect_multiline_expression(self, expr: str, base_indent: int) -> str:
        if self._bracket_balance(expr) <= 0:
            return expr

        parts = [expr]
        balance = self._bracket_balance(expr)

        while balance > 0:
            nxt = self._peek()
            if nxt is None:
                break
            continuation = self._consume()
            parts.append(continuation.text)
            balance += self._bracket_balance(continuation.text)

        return " ".join(parts)

    @staticmethod
    def _bracket_balance(expr: str) -> int:
        opened = expr.count("(") + expr.count("[") + expr.count("{")
        closed = expr.count(")") + expr.count("]") + expr.count("}")
        return opened - closed


def parse_program(source: str) -> Program:
    parser = Parser(source)
    return parser.parse()
