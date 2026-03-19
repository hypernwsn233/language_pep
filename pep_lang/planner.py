from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from pep_lang.ast_nodes import PipelineAssignStmt, PipelineStmt, Program


@dataclass
class PipelinePlan:
    name: str
    source: str
    stages: List[str]
    estimated_parallelism: int


@dataclass
class ExecutionPlan:
    mode: str
    pipelines: List[PipelinePlan]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "pipelines": [asdict(p) for p in self.pipelines],
        }


def build_plan(program: Program, mode: str = "local") -> ExecutionPlan:
    pipelines: List[PipelinePlan] = []

    for stmt in program.statements:
        if isinstance(stmt, PipelineAssignStmt):
            pipelines.append(
                PipelinePlan(
                    name=stmt.name,
                    source=stmt.pipeline.source,
                    stages=stmt.pipeline.stages,
                    estimated_parallelism=_estimate_parallelism(stmt.pipeline.stages, mode),
                )
            )
        elif isinstance(stmt, PipelineStmt):
            pipelines.append(
                PipelinePlan(
                    name="<anonymous>",
                    source=stmt.pipeline.source,
                    stages=stmt.pipeline.stages,
                    estimated_parallelism=_estimate_parallelism(stmt.pipeline.stages, mode),
                )
            )

    return ExecutionPlan(mode=mode, pipelines=pipelines)


def _estimate_parallelism(stages: List[str], mode: str) -> int:
    if mode == "cluster":
        base = 16
    else:
        base = 4

    for stage in stages:
        tokens = stage.split()
        if len(tokens) >= 3 and tokens[0] == "parallel" and tokens[1] == "max":
            try:
                return max(1, int(tokens[2]))
            except ValueError:
                return base
    return base
