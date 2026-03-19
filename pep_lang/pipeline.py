from __future__ import annotations

import csv
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from pep_lang.evaluator import EvalError, eval_expr


@dataclass
class StageMetric:
    name: str
    status: str
    items: int
    elapsed_ms: float


@dataclass
class PipelineResult:
    value: Any
    metrics: List[StageMetric] = field(default_factory=list)


class PipelineError(Exception):
    pass


class PipelineEngine:
    def __init__(self, env: Dict[str, Any], base_path: str = ""):
        self.env = env
        self.parallelism = 1
        self.base_path = base_path

    def _resolve_path(self, path: str) -> str:
        if self.base_path and not os.path.isabs(path):
            return os.path.join(self.base_path, path)
        return path

    def run(self, source_expr: str, stages: List[str]) -> PipelineResult:
        metrics: List[StageMetric] = []
        current = self._eval_source(source_expr)
        metrics.append(self._metric("source", current, 0.0))

        for stage in stages:
            started = time.perf_counter()
            current = self._apply_stage(current, stage)
            elapsed = (time.perf_counter() - started) * 1000
            metrics.append(self._metric(stage, current, elapsed))

        return PipelineResult(value=current, metrics=metrics)

    def _eval_source(self, expr: str) -> Any:
        expr = expr.strip()
        if expr.startswith("file "):
            path = self._resolve_path(_strip_quotes(expr[len("file ") :].strip()))
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                raise PipelineError(f"Arquivo não encontrado: '{path}'")
        if expr.startswith("json "):
            path = self._resolve_path(_strip_quotes(expr[len("json ") :].strip()))
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except FileNotFoundError:
                raise PipelineError(f"Arquivo não encontrado: '{path}'")
        if expr.startswith("csv "):
            path = self._resolve_path(_strip_quotes(expr[len("csv ") :].strip()))
            try:
                with open(path, "r", encoding="utf-8", newline="") as f:
                    return list(csv.DictReader(f))
            except FileNotFoundError:
                raise PipelineError(f"Arquivo não encontrado: '{path}'")

        try:
            return eval_expr(expr, self.env)
        except EvalError as exc:
            raise PipelineError(str(exc)) from exc

    def _apply_stage(self, current: Any, stage: str) -> Any:
        stage = stage.strip()

        if stage == "count":
            return len(_ensure_iterable(current))

        if stage == "collect":
            return list(_ensure_iterable(current))

        if stage.startswith("take "):
            n = int(stage[len("take ") :].strip())
            iterable = _ensure_iterable(current)
            if isinstance(iterable, list):
                return iterable[:n]
            out = []
            for idx, item in enumerate(iterable):
                if idx >= n:
                    break
                out.append(item)
            return out

        if stage.startswith("parse json"):
            if isinstance(current, str):
                return json.loads(current)
            raise PipelineError("parse json expects string input")

        if stage.startswith("parallel "):
            tokens = stage.split()
            if len(tokens) >= 3 and tokens[1] == "max":
                self.parallelism = max(1, int(tokens[2]))
            return current

        if stage.startswith("filter "):
            expr = stage[len("filter ") :].strip()
            items = _materialize_items(current)

            def _keep(item: Any) -> bool:
                item_ctx = item if isinstance(item, dict) else {"item": item}
                return bool(eval_expr(expr, self.env, item_ctx=item_ctx))

            if self.parallelism > 1 and len(items) >= 256:
                with ThreadPoolExecutor(max_workers=self.parallelism) as ex:
                    flags = list(ex.map(_keep, items, chunksize=64))
                return [item for item, keep in zip(items, flags) if keep]

            out = []
            for item in items:
                if _keep(item):
                    out.append(item)
            return out

        if stage.startswith("map "):
            expr = stage[len("map ") :].strip()
            items = _materialize_items(current)

            def _map_one(item: Any) -> Any:
                item_ctx = item if isinstance(item, dict) else {"item": item}
                return eval_expr(expr, self.env, item_ctx=item_ctx)

            if self.parallelism > 1 and len(items) >= 256:
                with ThreadPoolExecutor(max_workers=self.parallelism) as ex:
                    return list(ex.map(_map_one, items, chunksize=64))

            return [_map_one(item) for item in items]

        if stage == "print":
            print(current)
            return current

        if stage.startswith("save "):
            path = _strip_quotes(stage[len("save ") :].strip())
            _save_value(path, current)
            return current

        if stage.startswith("store "):
            path = _strip_quotes(stage[len("store ") :].strip())
            _save_value(path, current)
            return current

        raise PipelineError(f"Unknown pipeline stage: {stage}")

    def run_with_rejects(self, source_expr: str, stages: List[str]):
        """Run pipeline and return source items that fail any filter stage."""
        metrics: List[StageMetric] = []
        source_data = self._eval_source(source_expr)
        metrics.append(self._metric("source", source_data, 0.0))

        try:
            source_items = _materialize_items(source_data)
        except PipelineError:
            # Non-stream source cannot produce per-item rejections; run normally.
            current = source_data
            for stage in stages:
                started = time.perf_counter()
                current = self._apply_stage(current, stage)
                elapsed = (time.perf_counter() - started) * 1000
                metrics.append(self._metric(stage, current, elapsed))
            return PipelineResult(value=current, metrics=metrics), []

        tracked = [{"source": item, "value": item} for item in source_items]
        rejected: List[Any] = []
        tracking = True
        current: Any = source_data

        for stage in stages:
            started = time.perf_counter()
            stage_name = stage.strip()

            if tracking and stage_name.startswith("filter "):
                expr = stage_name[len("filter ") :].strip()
                kept = []
                for row in tracked:
                    item = row["value"]
                    item_ctx = item if isinstance(item, dict) else {"item": item}
                    if bool(eval_expr(expr, self.env, item_ctx=item_ctx)):
                        kept.append(row)
                    else:
                        rejected.append(row["source"])
                tracked = kept
                current = [row["value"] for row in tracked]
            elif tracking and stage_name.startswith("map "):
                expr = stage_name[len("map ") :].strip()
                for row in tracked:
                    item = row["value"]
                    item_ctx = item if isinstance(item, dict) else {"item": item}
                    row["value"] = eval_expr(expr, self.env, item_ctx=item_ctx)
                current = [row["value"] for row in tracked]
            elif tracking and stage_name.startswith("take "):
                n = int(stage_name[len("take ") :].strip())
                tracked = tracked[:n]
                current = [row["value"] for row in tracked]
            elif tracking and stage_name == "collect":
                current = [row["value"] for row in tracked]
            elif tracking and stage_name == "count":
                current = len(tracked)
                tracking = False
            elif tracking:
                raw_items = [row["value"] for row in tracked]
                transformed = self._apply_stage(raw_items, stage_name)
                if isinstance(transformed, list) and len(transformed) == len(tracked):
                    for idx, value in enumerate(transformed):
                        tracked[idx]["value"] = value
                    current = transformed
                else:
                    current = transformed
                    tracking = False
            else:
                current = self._apply_stage(current, stage_name)

            elapsed = (time.perf_counter() - started) * 1000
            metrics.append(self._metric(stage_name, current, elapsed))

        if tracking:
            current = [row["value"] for row in tracked]

        seen = set()
        unique_rejected = []
        for item in rejected:
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            unique_rejected.append(item)

        return PipelineResult(value=current, metrics=metrics), unique_rejected

    def _metric(self, stage: str, value: Any, elapsed_ms: float) -> StageMetric:
        return StageMetric(
            name=stage,
            status="ok",
            items=_count_items(value),
            elapsed_ms=elapsed_ms,
        )


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def _ensure_iterable(value: Any) -> Iterable[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return value
    if isinstance(value, dict):
        return value.values()
    if isinstance(value, str):
        raise PipelineError("String is not a valid item stream without parsing")
    if isinstance(value, Iterable):
        return value
    raise PipelineError(f"Value of type {type(value).__name__} is not iterable")


def _materialize_items(value: Any) -> List[Any]:
    iterable = _ensure_iterable(value)
    if isinstance(iterable, list):
        return iterable
    return list(iterable)


def _count_items(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (str, bytes)):
        return 1
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, (list, tuple, set)):
        return len(value)
    return 1


def _save_value(path: str, value: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if path.endswith(".json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(value))
