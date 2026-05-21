from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
from declarative_fsm import Workflow, load_yaml

print("МОДУЛЬ 4. ПОЛЬЗОВАТЕЛЬСКИЕ ОБРАБОТЧИКИ")
definition = load_yaml(DATA_DIR / "credit_process_15_states.yml")

def before_transition(workflow, event):
    print(f"[before_transition] Перед переходом: {event.from_state} --[{event.action}]--> {event.to_state}")

def after_transition(workflow, event):
    print(f"[after_transition] Текущее состояние после перехода: {workflow.state}")

def notify_specialist(workflow, event):
    print("[on_enter] Специалист получил уведомление о проверке документов")

def send_contract(workflow, event):
    print("[on_enter] Клиенту отправлен договор на подписание")

hooks = {
    "перед переходом": before_transition,
    "после перехода": after_transition,
    "уведомить специалиста": notify_specialist,
    "отправить договор клиенту": send_contract,
}
workflow = Workflow(definition, context={
    "документы_корректны": True,
    "рейтинг": 85,
    "сумма": 200000,
}, hooks=hooks)

for action in ["заполнить данные", "загрузить документы", "отправить на проверку", "подтвердить документы", "выполнить скоринг", "сформировать договор", "отправить договор"]:
    workflow.trigger(action)

print("Итоговое состояние:", workflow.state)
