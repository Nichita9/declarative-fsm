from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
from declarative_fsm import load_yaml, render_png, to_mermaid

print("МОДУЛЬ 6. ВИЗУАЛИЗАЦИЯ БИЗНЕС-ПРОЦЕССА")
definition = load_yaml(DATA_DIR / "vacation_process_8_states.yml")
output_png = OUTPUT_DIR / "vacation_process_visualization.png"

result_path = render_png(definition, output_png)

print("Для визуализации используется отдельный компактный YAML на 8 состояний")
print("Название процесса:", definition["name"])
print("Количество состояний:", len(definition["states"]))
print("Количество переходов:", len(definition["transitions"]))
print("PNG-файл создан:", result_path)
print("Также создана широкая версия:", result_path.with_name(result_path.stem + "_wide" + result_path.suffix))

print("\nФрагмент Mermaid-описания, которое формирует библиотека:")
print("-" * 60)
print(to_mermaid(definition).splitlines()[0])
for line in to_mermaid(definition).splitlines()[1:5]:
    print(line)
print("...")
