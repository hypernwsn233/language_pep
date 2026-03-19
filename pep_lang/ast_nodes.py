from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Node:
    line: int


@dataclass
class Program(Node):
    statements: List["Statement"] = field(default_factory=list)


class Statement(Node):
    pass


@dataclass
class UseStmt(Statement):
    module: str
    version: Optional[str] = None
    alias: Optional[str] = None


@dataclass
class AssignStmt(Statement):
    name: str
    expr: str
    mutable: bool = False


@dataclass
class SetStmt(Statement):
    name: str
    expr: str


@dataclass
class PrintStmt(Statement):
    expr: str


@dataclass
class ExprStmt(Statement):
    expr: str


@dataclass
class ReturnStmt(Statement):
    expr: str


@dataclass
class WatchStmt(Statement):
    target: str


@dataclass
class AwaitStmt(Statement):
    task_names: List[str]


@dataclass
class IfStmt(Statement):
    condition: str
    body: List[Statement]
    elif_branches: List[tuple[str, List[Statement]]] = field(default_factory=list)
    else_body: Optional[List[Statement]] = None


@dataclass
class ForStmt(Statement):
    var_name: str
    iterable_expr: str
    body: List[Statement]


@dataclass
class RepeatStmt(Statement):
    count_expr: str
    body: List[Statement]


@dataclass
class FnStmt(Statement):
    name: str
    params: List[str]
    body: List[Statement]


@dataclass
class TaskStmt(Statement):
    name: Optional[str]
    body: List[Statement]


@dataclass
class RouteStmt(Statement):
    path: str
    body: List[Statement]


@dataclass
class ServerStmt(Statement):
    port_expr: str
    routes: List[RouteStmt]


@dataclass
class PipelineExpr:
    source: str
    stages: List[str]


@dataclass
class PipelineAssignStmt(Statement):
    name: str
    pipeline: PipelineExpr
    mutable: bool = False


@dataclass
class VerifyStmt(Statement):
    """Pipeline assignment with an else block executed for each rejected item."""
    name: str
    pipeline: PipelineExpr
    else_body: List[Statement]


@dataclass
class PipelineStmt(Statement):
    pipeline: PipelineExpr
