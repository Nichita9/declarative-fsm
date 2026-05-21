from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
from declarative_fsm import load_yaml

process = load_yaml(DATA_DIR / "credit_process_15_states.yml")

print("Название процесса:", process["name"])
print("Начальное состояние:", process["initial_state"])
print("Количество состояний:", len(process["states"]))
print("Количество переходов:", len(process["transitions"]))
print("Конечные состояния:")
for state in process["final_states"]:
    print(" -", state)

print("\nПервые 5 состояний из YAML:")
for state in process["states"][:5]:
    print(" -", state)
