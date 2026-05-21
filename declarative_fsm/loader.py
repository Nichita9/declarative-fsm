from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .exceptions import WorkflowLoadError


def load_yaml(path: str | Path) -> Dict[str, Any]:
    """Загрузить описание workflow из YAML-файла с понятными ошибками."""
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except FileNotFoundError as exc:
        raise WorkflowLoadError(
            f"YAML-файл процесса не найден: {source}",
            details={"path": str(source)},
            hint="Проверьте путь к файлу или запускайте команду из корня проекта.",
        ) from exc
    except PermissionError as exc:
        raise WorkflowLoadError(
            f"Нет прав на чтение YAML-файла: {source}",
            details={"path": str(source)},
            hint="Проверьте права доступа к файлу.",
        ) from exc
    except yaml.YAMLError as exc:
        raise WorkflowLoadError(
            f"Ошибка разбора YAML-файла: {source}",
            details={"path": str(source), "yaml_error": str(exc)},
            hint="Проверьте отступы, двоеточия и структуру YAML.",
        ) from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise WorkflowLoadError(
            "YAML-файл должен содержать объект с описанием процесса.",
            details={"path": str(source), "actual_type": type(data).__name__},
            hint="В корне YAML должны быть поля name, states, initial, transitions.",
        )
    return data


def load_yaml_string(content: str) -> Dict[str, Any]:
    """Загрузить описание workflow из YAML-строки."""
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise WorkflowLoadError(
            "Ошибка разбора YAML-строки.",
            details={"yaml_error": str(exc)},
            hint="Проверьте синтаксис YAML.",
        ) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise WorkflowLoadError(
            "YAML-строка должна содержать объект с описанием процесса.",
            details={"actual_type": type(data).__name__},
        )
    return data
