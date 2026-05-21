from __future__ import annotations

from collections.abc import MutableMapping, Iterator
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


@dataclass
class ExecutionContext(MutableMapping[str, Any]):
    """Контекст выполнения экземпляра бизнес-процесса.

    Контекст хранит пользовательские параметры, которые используются при
    проверке условий переходов и в пользовательских обработчиках. Класс ведёт
    себя как обычный словарь, поэтому совместим с существующим кодом, где
    ожидался ``dict``.
    """

    data: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, initial: Optional[Mapping[str, Any]] = None, **values: Any) -> None:
        self.data = dict(initial or {})
        if values:
            self.data.update(values)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def __delitem__(self, key: str) -> None:
        del self.data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def update_values(self, **values: Any) -> None:
        """Обновить параметры контекста именованными значениями."""
        self.data.update(values)

    def to_dict(self) -> Dict[str, Any]:
        """Вернуть копию контекста для истории или сохранения состояния."""
        return dict(self.data)
