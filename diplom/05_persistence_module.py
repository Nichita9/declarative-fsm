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

print("МОДУЛЬ 5. СОХРАНЕНИЕ И ВОССТАНОВЛЕНИЕ СОСТОЯНИЯ")
definition = load_yaml(DATA_DIR / "credit_process_15_states.yml")
state_file = OUTPUT_DIR / "saved_credit_process_state.json"

workflow = Workflow(definition, context={
    "документы_корректны": True,
    "рейтинг": 88,
    "сумма": 240000,
}, hooks=build_noop_hooks())

for action in ["заполнить данные", "загрузить документы", "отправить на проверку", "подтвердить документы", "выполнить скоринг"]:
    workflow.trigger(action)

print("Состояние перед сохранением:", workflow.state)
print("Количество записей истории:", len(workflow.get_history()))
workflow.save_state(state_file)
print("Файл состояния сохранён:", state_file)

restored = Workflow.from_state_file(definition, state_file, hooks=build_noop_hooks())
print("\nПроцесс восстановлен из файла")
print("Восстановленное состояние:", restored.state)
print("Восстановленный context:", restored.get_context())
print("Восстановленная история:", len(restored.get_history()), "записей")

restored.trigger("сформировать договор")
print("Состояние после продолжения процесса:", restored.state)
