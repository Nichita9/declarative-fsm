from __future__ import annotations

from typing import Any, Dict, List

from .exceptions import WorkflowValidationError
from .models import Transition, WorkflowDefinition


def parse_definition(raw: Dict[str, Any]) -> WorkflowDefinition:
    """Разобрать и проверить исходное декларативное описание процесса."""
    if not isinstance(raw, dict):
        raise WorkflowValidationError("Описание процесса должно быть словарём.", details={"actual_type": type(raw).__name__})

    name = raw.get("name", "workflow")
    states = raw.get("states")
    # Поддерживаются оба варианта: initial (короткая форма) и initial_state
    # (название, используемое в тексте диплома и YAML-примерах).
    initial = raw.get("initial")
    if initial is None:
        initial = raw.get("initial_state")

    transitions_raw = raw.get("transitions", [])
    # Поддерживаются оба варианта: final (короткая форма) и final_states
    # (название, используемое в тексте диплома и YAML-примерах).
    final = raw.get("final")
    if final is None:
        final = raw.get("final_states", [])
    final = final or []
    on_enter = raw.get("on_enter", {}) or {}
    on_exit = raw.get("on_exit", {}) or {}
    hooks = raw.get("hooks", {}) or {}
    before_transition = raw.get("before_transition") or hooks.get("before_transition")
    after_transition = raw.get("after_transition") or hooks.get("after_transition")

    if not isinstance(states, list) or not states:
        raise WorkflowValidationError("Поле 'states' должно быть непустым списком состояний.", details={"field": "states"}, hint="Добавьте states: [created, review, done].")

    if len(states) != len(set(states)):
        raise WorkflowValidationError("Поле 'states' содержит повторяющиеся состояния.", details={"states": states}, hint="Удалите дубликаты из списка states.")

    if initial not in states:
        raise WorkflowValidationError("Начальное состояние должно быть объявлено в states.", details={"initial": initial, "states": states}, hint="Добавьте initial или initial_state в states либо исправьте значение начального состояния.")

    if not isinstance(final, list):
        raise WorkflowValidationError("Поле 'final' должно быть списком.", details={"field": "final", "actual_type": type(final).__name__})

    for state in final:
        if state not in states:
            raise WorkflowValidationError(f"Конечное состояние '{state}' не объявлено в states.", details={"final_state": state, "states": states})

    if not isinstance(transitions_raw, list):
        raise WorkflowValidationError("Поле 'transitions' должно быть списком переходов.", details={"field": "transitions", "actual_type": type(transitions_raw).__name__})

    transitions: List[Transition] = []
    for idx, item in enumerate(transitions_raw):
        if not isinstance(item, dict):
            raise WorkflowValidationError(f"Переход #{idx + 1} должен быть словарём.", details={"transition_index": idx + 1})

        for key in ("from", "to", "action"):
            if key not in item:
                raise WorkflowValidationError(f"Переход #{idx + 1} не содержит обязательное поле '{key}'.", details={"transition_index": idx + 1, "missing_field": key}, hint="Каждый переход должен содержать from, to и action.")

        from_state = item["from"]
        to_state = item["to"]
        action = item["action"]

        if from_state not in states:
            raise WorkflowValidationError(f"Переход #{idx + 1} ссылается на неизвестное начальное состояние '{from_state}'.", details={"transition_index": idx + 1, "from": from_state, "states": states})
        if to_state not in states:
            raise WorkflowValidationError(f"Переход #{idx + 1} ссылается на неизвестное целевое состояние '{to_state}'.", details={"transition_index": idx + 1, "to": to_state, "states": states})
        if not isinstance(action, str) or not action:
            raise WorkflowValidationError(f"В переходе #{idx + 1} поле action должно быть непустой строкой.", details={"transition_index": idx + 1, "action": action})

        transitions.append(
            Transition(
                from_state=from_state,
                to_state=to_state,
                action=action,
                condition=item.get("condition"),
                description=item.get("description"),
            )
        )

    if not isinstance(hooks, dict):
        raise WorkflowValidationError("Поле 'hooks' должно быть словарём.", details={"field": "hooks"})

    for hook_name, value in (("before_transition", before_transition), ("after_transition", after_transition)):
        if value is not None and not isinstance(value, str):
            raise WorkflowValidationError(
                f"Hook '{hook_name}' должен быть строкой с именем зарегистрированного обработчика.",
                details={"hook": hook_name, "actual_type": type(value).__name__},
            )

    for hook_map_name, hook_map in (("on_enter", on_enter), ("on_exit", on_exit)):
        if not isinstance(hook_map, dict):
            raise WorkflowValidationError(f"Поле '{hook_map_name}' должно быть словарём.", details={"field": hook_map_name})
        for state in hook_map.keys():
            if state not in states:
                raise WorkflowValidationError(f"Hook '{hook_map_name}' ссылается на неизвестное состояние '{state}'.", details={"hook": hook_map_name, "state": state, "states": states})

    return WorkflowDefinition(
        name=name,
        states=states,
        initial=initial,
        final=final,
        transitions=transitions,
        on_enter=on_enter,
        on_exit=on_exit,
        before_transition=before_transition,
        after_transition=after_transition,
    )
