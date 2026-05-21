from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from declarative_fsm import Workflow, load_yaml

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

CONFIG_PATH = DATA_DIR / "credit_process_15_states.yml"
STATE_PATH = OUTPUT_DIR / "credit_process_saved_state.json"

process_definition = load_yaml(CONFIG_PATH)

# В YAML могут быть объявлены пользовательские обработчики.
# В этом примере они не выполняют дополнительную бизнес-логику,
# но регистрируются, чтобы показать корректную работу процесса.
def hook(workflow, event):
    pass

hooks = {
    "перед переходом": hook,
    "после перехода": hook,
    "уведомить специалиста": hook,
    "отправить договор клиенту": hook,
    "уведомить о завершении": hook,
}

workflow = Workflow(
    process_definition,
    context={
        "документы_корректны": True,
        "рейтинг": 82,
        "сумма": 250000,
        "клиент_подписал": True,
        "деньги_перечислены": True,
    },
    hooks=hooks,
)

print("Загружен процесс:", process_definition["name"])
print("Количество состояний в YAML:", len(process_definition["states"]))
print("Начальное состояние:", workflow.state)

print("\nПользователь выполняет первые действия:")
for action in ["заполнить данные", "загрузить документы", "отправить на проверку", "подтвердить документы"]:
    old_state = workflow.state
    new_state = workflow.trigger(action)
    print(f"  {old_state} --[{action}]--> {new_state}")

print("\nТекущее состояние перед остановкой программы:", workflow.state)
print("Доступные действия для продолжения:", workflow.available_actions())

saved_file = workflow.save_state(STATE_PATH)
print("\nСостояние процесса сохранено в JSON-файл:")
print(saved_file)

print("\nСодержимое сохраненного JSON:")
print(json.dumps(workflow.to_snapshot(), ensure_ascii=False, indent=2))
