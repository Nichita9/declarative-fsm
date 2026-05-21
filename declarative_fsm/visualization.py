from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import subprocess
from shutil import which

from .definition import parse_definition
from .models import WorkflowDefinition


GRAPHVIZ_DOT = which("dot") or r"C:\Program Files\Graphviz\bin\dot.exe"


def _as_definition(definition: Dict[str, Any] | WorkflowDefinition) -> WorkflowDefinition:
    return definition if isinstance(definition, WorkflowDefinition) else parse_definition(definition)


def _escape_dot(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _escape_mermaid(value: str) -> str:
    return str(value).replace('"', "'")


def _human_label(value: str) -> str:
    return str(value).replace("_", " ")


def _visible_transitions(workflow: WorkflowDefinition):
    return [t for t in workflow.transitions if t.to_state != workflow.initial]


def to_dot(definition: Dict[str, Any] | WorkflowDefinition) -> str:
    workflow = _as_definition(definition)
    final_states = set(workflow.final)

    lines = [
        f'digraph "{_escape_dot(workflow.name)}" {{',
        '  graph [rankdir=LR, splines=polyline, overlap=false, nodesep=0.8, ranksep=1.1];',
        '  node [shape=box, style="rounded,filled", fontname="Arial", fontsize=11, margin="0.18,0.12", color="#4F76A3", fillcolor="#F5FAFF"];',
        '  edge [fontname="Arial", fontsize=9, color="#3B4A5A", arrowsize=0.8];',
    ]

    for state in workflow.states:
        attrs = []

        if state == workflow.initial:
            attrs.extend([
                'fillcolor="#E8F7ED"',
                'color="#2FA36B"',
                'penwidth=2',
            ])

        if state in final_states:
            attrs.extend([
                'fillcolor="#FFF1E3"',
                'color="#D2701F"',
                'penwidth=2',
                'shape=doubleoctagon',
            ])

        attr_text = f' [{", ".join(attrs)}]' if attrs else ""
        lines.append(f'  "{_escape_dot(state)}"{attr_text};')

    for number, transition in enumerate(_visible_transitions(workflow), start=1):
        label_parts = [str(number)]

        if transition.action:
            label_parts.append(_human_label(transition.action))

        if transition.condition:
            label_parts.append(f"[{transition.condition}]")

        label = ". ".join(label_parts)

        lines.append(
            f'  "{_escape_dot(transition.from_state)}" -> '
            f'"{_escape_dot(transition.to_state)}" '
            f'[label="{_escape_dot(label)}"];'
        )

    lines.append("}")
    return "\n".join(lines) + "\n"


def to_mermaid(definition: Dict[str, Any] | WorkflowDefinition) -> str:
    workflow = _as_definition(definition)
    lines = ["stateDiagram-v2"]

    for transition in _visible_transitions(workflow):
        label = transition.action

        if transition.condition:
            label = f"{label} [{transition.condition}]"

        lines.append(
            f'  "{_escape_mermaid(transition.from_state)}" --> '
            f'"{_escape_mermaid(transition.to_state)}": {_escape_mermaid(label)}'
        )

    return "\n".join(lines) + "\n"


def save_dot(definition: Dict[str, Any] | WorkflowDefinition, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(to_dot(definition), encoding="utf-8")
    return target


def save_mermaid(definition: Dict[str, Any] | WorkflowDefinition, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(to_mermaid(definition), encoding="utf-8")
    return target


def render_png(definition: Dict[str, Any] | WorkflowDefinition, path: str | Path) -> Path:
    workflow = _as_definition(definition)
    target = Path(path)

    if target.suffix.lower() != ".png":
        target = target.with_suffix(".png")

    target.parent.mkdir(parents=True, exist_ok=True)

    dot_path = target.with_suffix(".dot")
    dot_path.write_text(to_dot(workflow), encoding="utf-8")

    try:
        subprocess.run(
            [GRAPHVIZ_DOT, "-Tpng", str(dot_path), "-o", str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Не удалось найти Graphviz. "
            "Проверьте установку программы и путь к dot.exe."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Ошибка построения PNG через Graphviz:\n"
            f"{exc.stderr or exc.stdout}"
        ) from exc

    wide_path = target.with_name(f"{target.stem}_wide{target.suffix}")
    wide_dot_path = wide_path.with_suffix(".dot")
    wide_dot_path.write_text(to_dot(workflow), encoding="utf-8")

    try:
        subprocess.run(
            [GRAPHVIZ_DOT, "-Tpng", str(wide_dot_path), "-o", str(wide_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        pass

    return target
