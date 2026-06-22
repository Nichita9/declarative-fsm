from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which
from typing import Any, Dict

from PIL import Image, ImageDraw, ImageFont

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
        elif state in final_states:
            attrs.extend([
                'fillcolor="#FFE6E6"',
                'color="#C82828"',
                'penwidth=2',
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


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_paths = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            pass

    return ImageFont.load_default()


def _draw_legend_box(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    draw.rounded_rectangle(
        (x, y, x + 70, y + 34),
        radius=8,
        fill=fill,
        outline=outline,
        width=3,
    )

    draw.text(
        (x + 90, y + 17),
        text,
        fill=(35, 35, 35),
        font=font,
        anchor="lm",
    )


def _draw_legend_arrow(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    draw.line(
        (x, y + 17, x + 75, y + 17),
        fill=(59, 74, 90),
        width=3,
    )

    draw.polygon(
        [
            (x + 75, y + 17),
            (x + 58, y + 8),
            (x + 58, y + 26),
        ],
        fill=(59, 74, 90),
    )

    draw.text(
        (x + 100, y + 17),
        "переход между состояниями",
        fill=(35, 35, 35),
        font=font,
        anchor="lm",
    )


def _append_legend_to_png(path: Path) -> None:
    image = Image.open(path).convert("RGB")

    width, height = image.size
    legend_height = 180
    padding = 35

    result = Image.new(
        "RGB",
        (width, height + legend_height),
        "white",
    )

    result.paste(image, (0, 0))

    draw = ImageDraw.Draw(result)

    title_font = _load_font(22)
    text_font = _load_font(17)

    legend_top = height + 20
    legend_left = padding
    legend_right = width - padding
    legend_bottom = height + legend_height - 20

    draw.rounded_rectangle(
        (legend_left, legend_top, legend_right, legend_bottom),
        radius=12,
        outline=(160, 160, 160),
        width=2,
    )

    draw.text(
        (legend_left + 25, legend_top + 28),
        "Легенда:",
        fill=(20, 20, 20),
        font=title_font,
        anchor="lm",
    )

    first_row_y = legend_top + 62
    second_row_y = legend_top + 98

    _draw_legend_box(
        draw,
        legend_left + 25,
        first_row_y,
        fill=(232, 247, 237),
        outline=(47, 163, 107),
        text="начальное состояние",
        font=text_font,
    )

    _draw_legend_box(
        draw,
        legend_left + 360,
        first_row_y,
        fill=(245, 250, 255),
        outline=(79, 118, 163),
        text="промежуточное состояние",
        font=text_font,
    )

    _draw_legend_box(
        draw,
        legend_left + 760,
        first_row_y,
        fill=(255, 230, 230),
        outline=(200, 40, 40),
        text="конечное состояние",
        font=text_font,
    )

    _draw_legend_arrow(
        draw,
        legend_left + 25,
        second_row_y,
        font=text_font,
    )

    result.save(path)


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

    _append_legend_to_png(target)

    return target
