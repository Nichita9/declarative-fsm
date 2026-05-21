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


def print_context(context):
    for key, value in context.items():
        print(f"- {key}: {value}")


from declarative_fsm import Workflow, load_yaml

definition = load_yaml(DATA_DIR / "credit_process_15_states.yml")

workflow = Workflow(
    definition,
    context={
        "документы_корректны": True,
        "рейтинг": 84,
        "сумма": 500000,
        "менеджер_одобрил": False,
    },
    hooks=build_noop_hooks()
)

print("Начальные параметры процесса:")
print_context(workflow.get_context())
print()

for action in [
    "заполнить данные",
    "загрузить документы",
    "отправить на проверку",
    "подтвердить документы",
]:
    workflow.trigger(action)

print("Состояние перед скорингом:", workflow.state)
print()
print(
    "Так как сумма кредита больше 300000, "
    "процесс переходит на ручное решение менеджера."
)

workflow.trigger("выполнить скоринг")

print("Состояние после скоринга:", workflow.state)
print()

print("Пользователь обновляет context:")
print("менеджер_одобрил = True")

workflow.update_context(менеджер_одобрил=True)
workflow.trigger("одобрить вручную")

print()
print("Состояние после решения менеджера:", workflow.state)
print()

print("Текущие параметры процесса:")
print_context(workflow.get_context())