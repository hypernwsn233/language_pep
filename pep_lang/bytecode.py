from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from pep_lang.ast_nodes import (
    AssignStmt,
    ExprStmt,
    FnStmt,
    PipelineAssignStmt,
    PipelineStmt,
    PrintStmt,
    Program,
    ReturnStmt,
)


@dataclass
class Instruction:
    op: str
    arg: str = ""


@dataclass
class BytecodeArtifact:
    version: str = "0.1"
    instructions: List[Instruction] = field(default_factory=list)
    expressions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "instructions": [asdict(inst) for inst in self.instructions],
            "expressions": self.expressions,
            "fingerprint": self.fingerprint(),
        }

    def fingerprint(self) -> str:
        blob = "\n".join(f"{i.op}:{i.arg}" for i in self.instructions)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def compile_program(program: Program) -> BytecodeArtifact:
    artifact = BytecodeArtifact()
    for stmt in program.statements:
        _compile_stmt(stmt, artifact)
    return artifact


def save_artifact(path: str, artifact: BytecodeArtifact) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(artifact.to_dict(), f, indent=2, ensure_ascii=False)


def _compile_stmt(stmt: Any, artifact: BytecodeArtifact) -> None:
    if isinstance(stmt, AssignStmt):
        artifact.instructions.append(Instruction("EVAL", stmt.expr))
        artifact.instructions.append(Instruction("STORE", stmt.name))
        artifact.expressions.append(stmt.expr)
        return

    if isinstance(stmt, PrintStmt):
        artifact.instructions.append(Instruction("EVAL", stmt.expr))
        artifact.instructions.append(Instruction("PRINT"))
        artifact.expressions.append(stmt.expr)
        return

    if isinstance(stmt, ExprStmt):
        artifact.instructions.append(Instruction("EVAL", stmt.expr))
        artifact.expressions.append(stmt.expr)
        return

    if isinstance(stmt, ReturnStmt):
        artifact.instructions.append(Instruction("EVAL", stmt.expr))
        artifact.instructions.append(Instruction("RET"))
        artifact.expressions.append(stmt.expr)
        return

    if isinstance(stmt, FnStmt):
        artifact.instructions.append(Instruction("FN_BEGIN", stmt.name))
        for nested in stmt.body:
            _compile_stmt(nested, artifact)
        artifact.instructions.append(Instruction("FN_END", stmt.name))
        return

    if isinstance(stmt, PipelineAssignStmt):
        artifact.instructions.append(Instruction("PIPE_SOURCE", stmt.pipeline.source))
        for stage in stmt.pipeline.stages:
            artifact.instructions.append(Instruction("PIPE_STAGE", stage))
        artifact.instructions.append(Instruction("PIPE_STORE", stmt.name))
        return

    if isinstance(stmt, PipelineStmt):
        artifact.instructions.append(Instruction("PIPE_SOURCE", stmt.pipeline.source))
        for stage in stmt.pipeline.stages:
            artifact.instructions.append(Instruction("PIPE_STAGE", stage))
        artifact.instructions.append(Instruction("PIPE_RUN"))
        return

    artifact.instructions.append(Instruction("NOP", type(stmt).__name__))
