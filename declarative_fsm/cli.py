from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .exceptions import WorkflowError
from .loader import load_yaml
from .workflow import Workflow
from .definition import parse_definition
from .visualization import save_dot, save_mermaid, render_png


def _load_context(raw: str | None) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Ошибка чтения context. Передайте JSON, например: --context '{{\"сумма\": 50000}}'. Детали: {exc}")
    if not isinstance(value, dict):
        raise SystemExit("Параметр --context должен быть JSON-объектом, например: {\"сумма\": 50000}")
    return value


def _print_history(history: List[Dict[str, Any]]) -> None:
    if not history:
        print("История процесса пуста: переходы ещё не выполнялись.")
        return

    print("\nИстория процесса:")
    for index, record in enumerate(history, start=1):
        print(
            f"{index}. {record['from_state']} --[{record['action']}]--> "
            f"{record['to_state']} | время: {record['timestamp']}"
        )
        context = record.get("context_snapshot") or {}
        if context:
            print(f"   context: {context}")


def _build_noop_hooks(definition):
    parsed = parse_definition(definition)
    hook_names = set(parsed.on_enter.values()) | set(parsed.on_exit.values())

    def make_hook(name: str):
        def hook(workflow: Workflow) -> None:
            print(f"Выполнен hook: {name}")
        return hook

    return {name: make_hook(name) for name in hook_names}


def _run_workflow(args: argparse.Namespace, show_history: bool) -> int:
    definition = load_yaml(args.workflow)
    hooks = _build_noop_hooks(definition)

    state_file = Path(args.state_file) if args.state_file else None

    if args.resume:
        if state_file is None:
            raise SystemExit("Для --resume нужно указать --state-file")
        if not state_file.exists():
            raise SystemExit(f"Файл состояния не найден: {state_file}")
        workflow = Workflow.from_state_file(definition, state_file, hooks=hooks)
        if args.context:
            workflow.update_context(**_load_context(args.context))
        print(f"Процесс восстановлен из файла: {state_file}")
    else:
        workflow = Workflow(definition, context=_load_context(args.context), hooks=hooks)

    print(f"Процесс: {workflow.definition.name}")
    print(f"Начальное состояние текущего запуска: {workflow.state}")

    for action in args.actions:
        previous_state = workflow.state
        try:
            new_state = workflow.trigger(action)
        except WorkflowError as exc:
            print(f"Ошибка при выполнении действия '{action}':", file=sys.stderr)
            print(exc.user_message(), file=sys.stderr)
            print(f"Текущее состояние осталось: {workflow.state}")
            if state_file is not None:
                workflow.save_state(state_file)
                print(f"Состояние сохранено: {state_file}")
            return 1
        except Exception as exc:
            print(f"Непредвиденная ошибка при выполнении действия '{action}': {exc}", file=sys.stderr)
            print(f"Текущее состояние осталось: {workflow.state}")
            if state_file is not None:
                workflow.save_state(state_file)
                print(f"Состояние сохранено: {state_file}")
            return 1
        print(f"{previous_state} --[{action}]--> {new_state}")

    print(f"Итоговое состояние: {workflow.state}")
    print(f"Процесс завершён: {'да' if workflow.is_finished else 'нет'}")

    if state_file is not None:
        workflow.save_state(state_file)
        print(f"Состояние и история сохранены: {state_file}")

    if show_history or args.show_history:
        _print_history(workflow.get_history())

    return 0

def _visualize(args: argparse.Namespace) -> int:
    definition = load_yaml(args.workflow)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    suffix = output.suffix.lower()
    if suffix == ".png":
        result = render_png(definition, output)
    elif suffix == ".dot":
        result = save_dot(definition, output)
    elif suffix == ".mmd":
        result = save_mermaid(definition, output)
    else:
        raise SystemExit("Неподдерживаемый формат. Используйте .png, .dot или .mmd")

    print(f"Схема конечного автомата сохранена: {result}")
    return 0


def _status(args: argparse.Namespace) -> int:
    definition = load_yaml(args.workflow)
    state_file = Path(args.state_file)
    if not state_file.exists():
        raise SystemExit(f"Файл состояния не найден: {state_file}")

    workflow = Workflow.from_state_file(definition, state_file, hooks=_build_noop_hooks(definition))

    print(f"Процесс: {workflow.definition.name}")
    print(f"Текущее состояние: {workflow.state}")
    print(f"Процесс завершён: {'да' if workflow.is_finished else 'нет'}")
    print(f"Доступные действия: {workflow.available_actions()}")
    _print_history(workflow.get_history())
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dfsm",
        description="CLI для декларативной FSM-библиотеки управления бизнес-процессами",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Запустить процесс и выполнить последовательность действий")
    run.add_argument("workflow", help="Путь к YAML-файлу процесса")
    run.add_argument("--actions", nargs="+", default=[], help="Действия, которые нужно выполнить по порядку")
    run.add_argument("--context", help="JSON-контекст процесса, например: '{\"сумма\": 50000}'")
    run.add_argument("--show-history", action="store_true", help="Показать историю переходов после выполнения")
    run.add_argument("--state-file", help="JSON-файл для сохранения состояния и истории процесса")
    run.add_argument("--resume", action="store_true", help="Восстановить процесс из --state-file и продолжить выполнение")
    run.set_defaults(func=lambda args: _run_workflow(args, show_history=False))

    history = subparsers.add_parser("history", help="Запустить процесс и вывести историю переходов")
    history.add_argument("workflow", help="Путь к YAML-файлу процесса")
    history.add_argument("--actions", nargs="+", default=[], help="Действия, которые нужно выполнить по порядку")
    history.add_argument("--context", help="JSON-контекст процесса, например: '{\"сумма\": 50000}'")
    history.add_argument("--show-history", action="store_true", help=argparse.SUPPRESS)
    history.add_argument("--state-file", help="JSON-файл для сохранения состояния и истории процесса")
    history.add_argument("--resume", action="store_true", help="Восстановить процесс из --state-file и показать/продолжить историю")
    history.set_defaults(func=lambda args: _run_workflow(args, show_history=True))

    visualize = subparsers.add_parser("visualize", help="Построить схему конечного автомата")
    visualize.add_argument("workflow", help="Путь к YAML-файлу процесса")
    visualize.add_argument("--output", "-o", required=True, help="Куда сохранить схему: .png, .dot или .mmd")
    visualize.set_defaults(func=_visualize)

    status = subparsers.add_parser("status", help="Показать состояние и историю из сохранённого JSON-файла")
    status.add_argument("workflow", help="Путь к YAML-файлу процесса")
    status.add_argument("--state-file", required=True, help="JSON-файл с сохранённым состоянием процесса")
    status.set_defaults(func=_status)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except WorkflowError as exc:
        print(exc.user_message(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
