from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from declarative_fsm import Workflow, load_yaml

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

CONFIG_PATH = DATA_DIR / "credit_process_15_states.yml"
STATE_PATH = OUTPUT_DIR / "credit_process_saved_state.json"

process_definition = load_yaml(CONFIG_PATH)

def hook(workflow, event):
    pass

hooks = {
    "перед переходом": hook,
    "после перехода": hook,
    "уведомить специалиста": hook,
    "отправить договор клиенту": hook,
    "уведомить о завершении": hook,
}

workflow = Workflow.from_state_file(process_definition, STATE_PATH, hooks=hooks)

print("Процесс восстановлен из файла:", STATE_PATH)
print("Восстановленное состояние:", workflow.state)
print("История переходов после восстановления:", len(workflow.get_history()))
print("Доступные действия:", workflow.available_actions())

print("\nПользователь продолжает бизнес-процесс:")
for action in [
    "выполнить скоринг",
    "сформировать договор",
    "отправить договор",
    "подписать договор",
    "начать перечисление",
    "подтвердить перечисление",
]:
    old_state = workflow.state
    new_state = workflow.trigger(action)
    print(f"  {old_state} --[{action}]--> {new_state}")

print("\nИтоговое состояние:", workflow.state)
print("Процесс завершен:", workflow.is_finished)
print("Всего переходов в истории:", len(workflow.get_history()))

print("\nИстория выполнения процесса:")
for number, record in enumerate(workflow.get_history(), start=1):
    print(f"  {number}. {record['from_state']} --[{record['action']}]--> {record['to_state']}")
