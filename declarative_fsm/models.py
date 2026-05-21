from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Transition:
    """Переход между состояниями бизнес-процесса."""

    from_state: str
    to_state: str
    action: str
    condition: Optional[str] = None
    description: Optional[str] = None


@dataclass
class HistoryRecord:
    """Запись истории о выполненном переходе."""

    from_state: str
    to_state: str
    action: str
    context_snapshot: Dict[str, Any]
    result: str = "success"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class WorkflowDefinition:
    """Разобранное декларативное описание workflow-процесса."""

    name: str
    states: List[str]
    initial: str
    transitions: List[Transition]
    final: List[str] = field(default_factory=list)
    on_enter: Dict[str, str] = field(default_factory=dict)
    on_exit: Dict[str, str] = field(default_factory=dict)
    before_transition: Optional[str] = None
    after_transition: Optional[str] = None
