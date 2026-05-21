from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .conditions import SafeConditionEvaluator
from .context import ExecutionContext
from .definition import parse_definition
from .exceptions import HookExecutionError, StatePersistenceError, TransitionNotAllowedError
from .models import HistoryRecord, Transition, WorkflowDefinition
from .persistence import STATE_FILE_VERSION, history_from_dicts, history_to_dicts, load_json_state, save_json_state


@dataclass(frozen=True)
class TransitionEvent:
    """Событие, передаваемое пользовательским обработчикам переходов."""

    action: str
    from_state: str
    to_state: str
    condition: Optional[str] = None


Hook = Callable[..., None]


class Workflow:
    """Декларативный workflow-движок на основе конечного автомата.

    Процесс задаётся состояниями и переходами. Переходы запускаются
    действиями и могут иметь условия, зависящие от контекста процесса.
    """

    def __init__(
        self,
        definition: Dict[str, Any] | WorkflowDefinition,
        context: Optional[Dict[str, Any]] = None,
        hooks: Optional[Dict[str, Hook]] = None,
    ):
        self.definition = definition if isinstance(definition, WorkflowDefinition) else parse_definition(definition)
        self.context = ExecutionContext(context or {})
        self.current_state: str = self.definition.initial
        self.history: List[HistoryRecord] = []
        self.hooks: Dict[str, Hook] = hooks or {}

    @property
    def state(self) -> str:
        return self.current_state

    @property
    def is_finished(self) -> bool:
        return self.current_state in self.definition.final

    def available_actions(self) -> List[str]:
        """Вернуть действия, доступные из текущего состояния и разрешённые условиями."""
        actions: List[str] = []
        for transition in self._candidate_transitions():
            if self._condition_is_allowed(transition):
                actions.append(transition.action)
        return sorted(set(actions))

    def can(self, action: str) -> bool:
        """Проверить, можно ли выполнить действие из текущего состояния."""
        return any(
            transition.action == action and self._condition_is_allowed(transition)
            for transition in self._candidate_transitions()
        )

    def trigger(self, action: str, **context_updates: Any) -> str:
        """Выполнить действие и вернуть новое состояние.

        Дополнительные именованные аргументы обновляют context перед выбором перехода.
        """
        if context_updates:
            self.context.update_values(**context_updates)

        candidates = [
            transition
            for transition in self.definition.transitions
            if transition.from_state == self.current_state and transition.action == action
        ]

        if not candidates:
            raise TransitionNotAllowedError(
                f"Действие '{action}' недоступно из состояния '{self.current_state}'.",
                details={
                    "action": action,
                    "current_state": self.current_state,
                    "available_actions": self.available_actions(),
                },
                hint="Проверьте текущее состояние процесса и список доступных действий.",
            )

        for transition in candidates:
            if self._condition_is_allowed(transition):
                self._apply_transition(transition)
                return self.current_state

        raise TransitionNotAllowedError(
            f"Переход по действию '{action}' из состояния '{self.current_state}' существует, но его условия не выполнены.",
            details={"action": action, "current_state": self.current_state, "context": self.context.to_dict()},
            hint="Проверьте context и condition в YAML-описании перехода.",
        )

    def update_context(self, **values: Any) -> None:
        self.context.update_values(**values)

    def get_context(self) -> Dict[str, Any]:
        """Вернуть копию текущего контекста выполнения."""
        return self.context.to_dict()

    def get_history(self) -> List[Dict[str, Any]]:
        return [record.__dict__.copy() for record in self.history]

    def to_snapshot(self) -> Dict[str, Any]:
        """Вернуть снимок текущего состояния workflow, пригодный для сохранения в JSON.

        Снимок содержит текущее состояние, context и историю переходов.
        Его можно сохранить в файл, а затем восстановить для продолжения процесса.
        """
        return {
            "version": STATE_FILE_VERSION,
            "workflow_name": self.definition.name,
            "current_state": self.current_state,
            "context": self.context.to_dict(),
            "history": history_to_dicts(self.history),
            "is_finished": self.is_finished,
        }

    def save_state(self, path: str | Path) -> Path:
        """Сохранить текущее состояние workflow и историю переходов в JSON-файл."""
        return save_json_state(path, self.to_snapshot())

    @classmethod
    def from_state_file(
        cls,
        definition: Dict[str, Any] | WorkflowDefinition,
        path: str | Path,
        hooks: Optional[Dict[str, Hook]] = None,
    ) -> "Workflow":
        """Создать экземпляр workflow из ранее сохранённого JSON-файла состояния."""
        snapshot = load_json_state(path)
        workflow = cls(definition, context=snapshot.get("context") or {}, hooks=hooks)
        workflow.current_state = snapshot["current_state"]
        workflow.history = history_from_dicts(snapshot.get("history") or [])

        if workflow.current_state not in workflow.definition.states:
            raise StatePersistenceError(
                f"Сохранённое состояние '{workflow.current_state}' не объявлено в текущей модели процесса.",
                details={"saved_state": workflow.current_state, "declared_states": workflow.definition.states},
                hint="Проверьте, что JSON состояния соответствует этому YAML-файлу процесса.",
            )

        return workflow

    def reset(self, context: Optional[Dict[str, Any]] = None) -> None:
        self.current_state = self.definition.initial
        self.history.clear()
        if context is not None:
            self.context = ExecutionContext(context)

    def _candidate_transitions(self) -> List[Transition]:
        return [t for t in self.definition.transitions if t.from_state == self.current_state]

    def _condition_is_allowed(self, transition: Transition) -> bool:
        if not transition.condition:
            return True
        return SafeConditionEvaluator(self.context.to_dict()).evaluate(transition.condition)

    def _apply_transition(self, transition: Transition) -> None:
        old_state = self.current_state
        event = TransitionEvent(
            action=transition.action,
            from_state=old_state,
            to_state=transition.to_state,
            condition=transition.condition,
        )

        self._execute_hook(self.definition.before_transition, event)
        self._execute_hook(self.definition.on_exit.get(old_state), event)

        self.current_state = transition.to_state
        self.history.append(
            HistoryRecord(
                from_state=old_state,
                to_state=self.current_state,
                action=transition.action,
                context_snapshot=self.context.to_dict(),
                result="success",
            )
        )

        self._execute_hook(self.definition.on_enter.get(self.current_state), event)
        self._execute_hook(self.definition.after_transition, event)

    def _execute_hook(self, hook_name: Optional[str], event: Optional[TransitionEvent] = None) -> None:
        if not hook_name:
            return
        hook = self.hooks.get(hook_name)
        if hook is None:
            raise HookExecutionError(
                f"Hook '{hook_name}' объявлен в YAML, но не зарегистрирован в Workflow.",
                details={"hook": hook_name},
                hint="Передайте функцию в параметр hooks при создании Workflow.",
            )
        try:
            parameters = inspect.signature(hook).parameters
            if event is not None and len(parameters) >= 2:
                hook(self, event)
            else:
                hook(self)
        except Exception as exc:
            raise HookExecutionError(
                f"Ошибка выполнения hook '{hook_name}': {exc}",
                details={"hook": hook_name, "error": str(exc)},
            ) from exc
