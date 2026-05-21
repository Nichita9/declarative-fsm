from __future__ import annotations

from typing import Any, Dict, Optional


class WorkflowError(Exception):
    """Базовое исключение библиотеки declarative_fsm с данными для понятного вывода пользователю."""

    default_code = "WORKFLOW_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details = details or {}
        self.hint = hint

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "hint": self.hint,
        }

    def user_message(self) -> str:
        lines = [f"[{self.code}] {self.message}"]
        if self.details:
            lines.append("Детали:")
            for key, value in self.details.items():
                lines.append(f"  - {key}: {value}")
        if self.hint:
            lines.append(f"Подсказка: {self.hint}")
        return "\n".join(lines)


class WorkflowLoadError(WorkflowError):
    """Возникает, когда YAML-файл процесса не удалось загрузить."""

    default_code = "WORKFLOW_LOAD_ERROR"


class WorkflowValidationError(WorkflowError):
    """Возникает, когда описание процесса содержит ошибку."""

    default_code = "WORKFLOW_VALIDATION_ERROR"


class TransitionNotAllowedError(WorkflowError):
    """Возникает, когда переход между состояниями выполнить нельзя."""

    default_code = "TRANSITION_NOT_ALLOWED"


class ConditionEvaluationError(WorkflowError):
    """Возникает, когда условие перехода невозможно вычислить."""

    default_code = "CONDITION_EVALUATION_ERROR"


class HookExecutionError(WorkflowError):
    """Возникает при ошибке выполнения пользовательского hook-обработчика."""

    default_code = "HOOK_EXECUTION_ERROR"


class StatePersistenceError(WorkflowError):
    """Возникает при ошибке сохранения или восстановления состояния процесса."""

    default_code = "STATE_PERSISTENCE_ERROR"
