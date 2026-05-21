from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

from declarative_fsm import load_yaml, render_png, to_mermaid

print("ВИЗУАЛИЗАЦИЯ ПРОЦЕССА ОБРАБОТКИ ЗАЯВКИ НА ДОСТУП")

definition = load_yaml(DATA_DIR / "access_request_5_states.yml")
output_png = OUTPUT_DIR / "access_request_visualization.png"

result_path = render_png(definition, output_png)

print("Название процесса:", definition["name"])
print("Количество состояний:", len(definition["states"]))
print("Количество переходов:", len(definition["transitions"]))
print("PNG-файл создан:", result_path)

print("\nФрагмент Mermaid-описания:")
print("-" * 60)

mermaid_lines = to_mermaid(definition).splitlines()

print(mermaid_lines[0])

for line in mermaid_lines[1:5]:
    print(line)

print("...")
