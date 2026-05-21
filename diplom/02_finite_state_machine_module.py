from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def build_noop_hooks():
    return {
        "перед переходом": lambda workflow, event: None,
        "после перехода": lambda workflow, event: None,
        "уведомить специалиста": lambda workflow, event: None,
        "отправить договор клиенту": lambda workflow, event: None,
        "уведомить о завершении": lambda workflow, event: None,
    }


from declarative_fsm import Workflow, load_yaml

definition = load_yaml(DATA_DIR / "credit_process_15_states.yml")

workflow = Workflow(
    definition,
    context={
        "документы_корректны": True,
        "рейтинг": 82,
        "сумма": 250000,
    },
    hooks=build_noop_hooks()
)

actions = [
    "заполнить данные",
    "загрузить документы",
    "отправить на проверку",
    "подтвердить документы",
    "выполнить скоринг",
]

print("Начальное состояние:", workflow.state)
print()

for step, action in enumerate(actions, start=1):

    print(f"Шаг {step}")

    available_actions = workflow.available_actions()

    if available_actions:
        print(
            "Доступные действия:",
            ", ".join(available_actions)
        )

    old_state = workflow.state

    workflow.trigger(action)

    print(
        f"Выполнен переход: "
        f"{old_state} -> {workflow.state}"
    )

    print()

next_actions = workflow.available_actions()

print("Итоговое состояние:", workflow.state)

if next_actions:
    print(
        "Следующие доступные действия:",
        ", ".join(next_actions)
    )