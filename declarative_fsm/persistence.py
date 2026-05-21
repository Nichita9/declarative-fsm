from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import HistoryRecord
from .exceptions import StatePersistenceError


STATE_FILE_VERSION = 1


def history_to_dicts(history: List[HistoryRecord]) -> List[Dict[str, Any]]:
    """Convert history records to JSON-serializable dictionaries."""
    return [record.__dict__.copy() for record in history]


def history_from_dicts(items: List[Dict[str, Any]]) -> List[HistoryRecord]:
    """Restore history records from dictionaries loaded from JSON."""
    if not isinstance(items, list):
        raise StatePersistenceError(
            "Поле history в файле состояния должно быть списком.",
            details={"actual_type": type(items).__name__},
        )

    records: List[HistoryRecord] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise StatePersistenceError(
                f"Запись истории #{index} должна быть объектом.",
                details={"history_index": index, "actual_type": type(item).__name__},
            )
        try:
            records.append(
                HistoryRecord(
                    from_state=item["from_state"],
                    to_state=item["to_state"],
                    action=item["action"],
                    context_snapshot=dict(item.get("context_snapshot") or {}),
                    result=item.get("result", "success"),
                    timestamp=item.get("timestamp"),
                )
            )
        except KeyError as exc:
            raise StatePersistenceError(
                f"В записи истории #{index} отсутствует обязательное поле: {exc.args[0]}",
                details={"history_index": index, "missing_field": exc.args[0]},
            ) from exc
    return records


def save_json_state(path: str | Path, snapshot: Dict[str, Any]) -> Path:
    """Save workflow snapshot to a JSON file."""
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise StatePersistenceError(
            f"Не удалось сохранить состояние процесса в файл: {target}",
            details={"path": str(target), "error": str(exc)},
        ) from exc
    return target


def load_json_state(path: str | Path) -> Dict[str, Any]:
    """Load workflow snapshot from a JSON file."""
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StatePersistenceError(
            f"Файл состояния не найден: {source}",
            details={"path": str(source)},
            hint="Сначала сохраните процесс через workflow.save_state() или CLI --state-file.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise StatePersistenceError(
            f"Файл состояния содержит некорректный JSON: {source}",
            details={"path": str(source), "json_error": str(exc)},
        ) from exc

    if not isinstance(data, dict):
        raise StatePersistenceError(
            "Файл состояния должен содержать JSON-объект.",
            details={"path": str(source), "actual_type": type(data).__name__},
        )
    if "current_state" not in data:
        raise StatePersistenceError(
            "В файле состояния отсутствует поле current_state.",
            details={"path": str(source)},
        )
    return data
