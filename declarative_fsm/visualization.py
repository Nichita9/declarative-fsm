from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from textwrap import wrap
from typing import Any, Dict, Iterable, List, Tuple

from .definition import parse_definition
from .models import Transition, WorkflowDefinition


Point = Tuple[int, int]
Box = Tuple[int, int, int, int]
Color = Tuple[int, int, int]


def _as_definition(definition: Dict[str, Any] | WorkflowDefinition) -> WorkflowDefinition:
    return definition if isinstance(definition, WorkflowDefinition) else parse_definition(definition)


def _escape_dot(value: str) -> str:
    return str(value).replace('\\', '\\\\').replace('"', '\\"')


def _escape_mermaid(value: str) -> str:
    return str(value).replace('"', "'")


def _human_label(value: str) -> str:
    return str(value).replace("_", " ")


def to_dot(definition: Dict[str, Any] | WorkflowDefinition) -> str:
    """Return DOT representation of workflow finite-state machine.

    The initial state is highlighted by style. A synthetic incoming start arrow is
    intentionally not rendered: in a business process the initial state is itself
    the starting point of the model.
    """
    workflow = _as_definition(definition)
    final_states = set(workflow.final)
    lines = [
        f'digraph "{_escape_dot(workflow.name)}" {{',
        '  graph [rankdir=LR, splines=ortho, overlap=false, concentrate=false, nodesep=0.65, ranksep=0.9, margin=0.25];',
        '  node [shape=box, style="rounded,filled", fontname="Arial", fontsize=11, margin="0.16,0.10", color="#4F76A3", fillcolor="#F5FAFF"];',
        '  edge [fontname="Arial", fontsize=9, color="#3B4A5A", arrowsize=0.8];',
    ]

    for state in workflow.states:
        attrs = []
        if state == workflow.initial:
            attrs.extend(['fillcolor="#E8F7ED"', 'color="#3FA36B"', 'penwidth=2'])
        if state in final_states:
            attrs.extend(['fillcolor="#FFF1E3"', 'color="#C8792B"', 'penwidth=2'])
        attr_text = f' [{", ".join(attrs)}]' if attrs else ''
        lines.append(f'  "{_escape_dot(state)}"{attr_text};')

    for transition in _visible_transitions(workflow):
        label_parts = [transition.action]
        if transition.condition:
            label_parts.append(f'[{transition.condition}]')
        label = ' '.join(label_parts)
        lines.append(
            f'  "{_escape_dot(transition.from_state)}" -> "{_escape_dot(transition.to_state)}" '
            f'[label="{_escape_dot(label)}"];'
        )

    lines.append('}')
    return "\n".join(lines) + "\n"


def to_mermaid(definition: Dict[str, Any] | WorkflowDefinition) -> str:
    """Return Mermaid stateDiagram representation.

    The initial state is not connected to [*] to avoid drawing an artificial
    arrow into the business-process start state.
    """
    workflow = _as_definition(definition)
    lines = ['stateDiagram-v2']

    for transition in _visible_transitions(workflow):
        label = transition.action
        if transition.condition:
            label = f'{label} [{transition.condition}]'
        lines.append(
            f'    "{_escape_mermaid(transition.from_state)}" --> '
            f'"{_escape_mermaid(transition.to_state)}": {_escape_mermaid(label)}'
        )

    return "\n".join(lines) + "\n"


def save_dot(definition: Dict[str, Any] | WorkflowDefinition, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(to_dot(definition), encoding='utf-8')
    return target


def save_mermaid(definition: Dict[str, Any] | WorkflowDefinition, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(to_mermaid(definition), encoding='utf-8')
    return target


def _load_font(size: int, bold: bool = False):
    try:
        from PIL import ImageFont
    except ImportError:  # не покрывается тестами
        return None

    names = (
        ["DejaVuSans-Bold.ttf", "arialbd.ttf", "LiberationSans-Bold.ttf"]
        if bold
        else ["DejaVuSans.ttf", "arial.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf"]
    )
    for font_name in names:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_label(text: str, max_chars: int = 22, max_lines: int = 4) -> List[str]:
    normalized = _human_label(str(text))
    result: List[str] = []
    for part in normalized.split("\n"):
        result.extend(wrap(part, width=max_chars, break_long_words=False, replace_whitespace=False) or [part])
    if len(result) > max_lines:
        result = result[:max_lines]
        result[-1] = result[-1].rstrip(" .") + "…"
    return result


def _text_size(draw, text: str, font) -> Tuple[int, int]:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        return (len(text) * 7, 14)


def _draw_wrapped_text(draw, xy: Point, lines: Iterable[str], font, fill: Color = (20, 25, 30), line_gap: int = 4) -> None:
    lines = list(lines)
    if not lines:
        return
    heights = [_text_size(draw, line, font)[1] for line in lines]
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    x, y = xy
    cy = y - total_h // 2
    for line, h in zip(lines, heights):
        draw.text((x, cy + h // 2), line, fill=fill, font=font, anchor="mm")
        cy += h + line_gap


def _box_center(box: Box) -> Point:
    return (box[0] + box[2]) // 2, (box[1] + box[3]) // 2


def _left(box: Box) -> Point:
    return box[0], (box[1] + box[3]) // 2


def _right(box: Box) -> Point:
    return box[2], (box[1] + box[3]) // 2


def _top(box: Box) -> Point:
    return (box[0] + box[2]) // 2, box[1]


def _bottom(box: Box) -> Point:
    return (box[0] + box[2]) // 2, box[3]


def _draw_arrow(draw, points: List[Point], fill: Color = (53, 67, 84), width: int = 2, dash: bool = False) -> None:
    """Draw an elbow line with an explicit arrow head.

    Every transition uses this method, so the rendered diagram does not contain
    plain connector lines without an arrow head.
    """
    import math

    if len(points) < 2:
        return

    def draw_segment(a: Point, b: Point) -> None:
        if not dash:
            draw.line((*a, *b), fill=fill, width=width)
            return
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length == 0:
            return
        dx = (b[0] - a[0]) / length
        dy = (b[1] - a[1]) / length
        step = 14
        gap = 8
        current = 0
        while current < length:
            end = min(current + step, length)
            p1 = (int(a[0] + dx * current), int(a[1] + dy * current))
            p2 = (int(a[0] + dx * end), int(a[1] + dy * end))
            draw.line((*p1, *p2), fill=fill, width=width)
            current += step + gap

    for start, end in zip(points, points[1:]):
        draw_segment(start, end)

    p1 = points[-2]
    p2 = points[-1]
    angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    arrow_len = 14
    arrow_angle = 0.52
    left = (
        p2[0] - arrow_len * math.cos(angle - arrow_angle),
        p2[1] - arrow_len * math.sin(angle - arrow_angle),
    )
    right = (
        p2[0] - arrow_len * math.cos(angle + arrow_angle),
        p2[1] - arrow_len * math.sin(angle + arrow_angle),
    )
    draw.polygon([p2, left, right], fill=fill)


def _draw_edge_number(draw, number: int, center: Point, font) -> None:
    text = str(number)
    w, h = _text_size(draw, text, font)
    x, y = center
    pad_x = 8
    pad_y = 5
    box = (x - w // 2 - pad_x, y - h // 2 - pad_y, x + w // 2 + pad_x, y + h // 2 + pad_y)
    draw.rounded_rectangle(box, radius=9, fill=(255, 255, 255), outline=(170, 180, 192), width=1)
    draw.text((x, y), text, fill=(42, 49, 60), font=font, anchor="mm")


def _draw_node(draw, box: Box, state: str, workflow: WorkflowDefinition, font) -> None:
    final_states = set(workflow.final)
    fill = (246, 251, 255)
    outline = (70, 112, 158)
    line_width = 2
    if state == workflow.initial:
        fill = (232, 248, 239)
        outline = (48, 157, 99)
        line_width = 3
    if state in final_states:
        fill = (255, 244, 232)
        outline = (204, 112, 32)
        line_width = 3
    draw.rounded_rectangle(box, radius=14, fill=fill, outline=outline, width=line_width)
    _draw_wrapped_text(draw, _box_center(box), _wrap_label(state, 20, 3), font)


def _draw_legend(draw, x: int, y: int, font) -> None:
    items = [
        ((232, 248, 239), (48, 157, 99), "начальное состояние"),
        ((246, 251, 255), (70, 112, 158), "обычное состояние"),
        ((255, 244, 232), (204, 112, 32), "конечное состояние"),
    ]
    for fill, outline, label in items:
        draw.rounded_rectangle((x, y, x + 18, y + 18), radius=4, fill=fill, outline=outline, width=2)
        draw.text((x + 26, y + 9), label, fill=(45, 45, 45), font=font, anchor="lm")
        x += 260


def _visible_transitions(workflow: WorkflowDefinition) -> List[Transition]:
    """Transitions shown on diagrams.

    Business-process diagrams should not draw incoming arrows into the initial
    state. If a workflow model contains such a technical/reset transition, it is
    intentionally hidden from visualization so the start state remains visually
    unambiguous.
    """
    return [t for t in workflow.transitions if t.to_state != workflow.initial]


def _transition_label(t: Transition) -> str:
    text = f"{_human_label(t.from_state)} → {_human_label(t.to_state)} — {_human_label(t.action)}"
    if t.condition:
        text += f" [{t.condition}]"
    return text


def _build_levels(workflow: WorkflowDefinition) -> Dict[str, int]:
    """Assign states to left-to-right levels.

    A longest-path style placement is used instead of pure BFS. This keeps
    states that are reachable through a longer business path farther to the
    right, so arrows like ``review -> approve`` do not collapse onto arrows
    coming from intermediate states. The number of relaxation passes is limited
    by the number of states, so cyclic workflows do not cause infinite updates.
    """
    levels: Dict[str, int] = {workflow.initial: 0}
    max_level = max(0, len(workflow.states) - 1)
    transitions = _visible_transitions(workflow)

    for _ in range(max(1, len(workflow.states))):
        changed = False
        for t in transitions:
            if t.from_state not in levels:
                continue
            if t.to_state == workflow.initial:
                continue
            new_level = min(levels[t.from_state] + 1, max_level)
            if levels.get(t.to_state, -1) < new_level:
                levels[t.to_state] = new_level
                changed = True
        if not changed:
            break

    next_level = max(levels.values(), default=0) + 1
    for state in workflow.states:
        if state not in levels:
            levels[state] = next_level
            next_level += 1
    return levels

def _compact_positions(workflow: WorkflowDefinition) -> Dict[str, Box]:
    """Layered left-to-right layout for the main numbered diagram.

    The previous grid-like layout compressed unrelated branches into the same
    rows and many connector lines visually crossed node labels. This layout
    follows BFS levels from the initial state and places every level in its own
    column. The image can become wider for large processes, but the resulting
    scheme is much easier to read and works for arbitrary YAML workflows.
    """
    levels = _build_levels(workflow)
    groups: Dict[int, List[str]] = defaultdict(list)
    for state in workflow.states:
        groups[levels[state]].append(state)

    box_w, box_h = 250, 76
    x_gap, y_gap = 155, 92
    margin_x, margin_y = 90, 110

    max_rows = max((len(states) for states in groups.values()), default=1)
    full_column_h = max_rows * box_h + max(0, max_rows - 1) * y_gap

    positions: Dict[str, Box] = {}
    for col, level in enumerate(sorted(groups)):
        states = groups[level]
        # Размещаем начальное состояние ближе к вертикальному центру первой области.
        column_h = len(states) * box_h + max(0, len(states) - 1) * y_gap
        y0 = margin_y + (full_column_h - column_h) // 2
        x = margin_x + col * (box_w + x_gap)
        for row, state in enumerate(states):
            y = y0 + row * (box_h + y_gap)
            positions[state] = (x, y, x + box_w, y + box_h)

    return positions


def _canvas_for_positions(positions: Dict[str, Box], extra_bottom: int = 360) -> Tuple[int, int]:
    max_x = max(box[2] for box in positions.values()) if positions else 1000
    max_y = max(box[3] for box in positions.values()) if positions else 700
    return max(1100, max_x + 520), max(720, max_y + extra_bottom)

def _layout_bounds(positions: Dict[str, Box]) -> Tuple[int, int, int, int]:
    min_x = min(box[0] for box in positions.values()) if positions else 0
    min_y = min(box[1] for box in positions.values()) if positions else 0
    max_x = max(box[2] for box in positions.values()) if positions else 0
    max_y = max(box[3] for box in positions.values()) if positions else 0
    return min_x, min_y, max_x, max_y


def _route_between(source: Box, target: Box, index: int, bounds: Tuple[int, int, int, int] | None = None) -> List[Point]:
    """Build an orthogonal route for a transition.

    The renderer is intentionally simple, but it must handle branching states:
    several arrows can start from the same node and go to different targets.
    To keep such arrows readable, connector ports are shifted slightly and
    long skip-links are routed through an external lane instead of being drawn
    through intermediate states.
    """
    sc = _box_center(source)
    tc = _box_center(target)
    box_w = source[2] - source[0]

    if bounds:
        min_x, min_y, max_x, max_y = bounds
    else:
        min_x = min(source[0], target[0])
        min_y = min(source[1], target[1])
        max_x = max(source[2], target[2])
        max_y = max(source[3], target[3])

    # Different transitions receive slightly different ports. This prevents
    # several transition numbers from being drawn on one shared line.
    port_shift = ((index % 5) - 2) * 11

    if source == target:
        x1, y1, x2, y2 = source
        lane = x2 + 70 + (index % 4) * 18
        return [
            (x2, sc[1] + port_shift),
            (lane, sc[1] + port_shift),
            (lane, y1 - 55),
            (sc[0], y1 - 55),
            _top(source),
        ]

    same_column = abs(sc[0] - tc[0]) < box_w * 0.75

    if same_column:
        use_right = (index % 2 == 1)
        lane_offset = 75 + (index % 5) * 24
        if use_right:
            lane_x = max(source[2], target[2]) + lane_offset
            return [(source[2], sc[1] + port_shift), (lane_x, sc[1] + port_shift), (lane_x, tc[1] - port_shift), (target[2], tc[1] - port_shift)]
        lane_x = min(source[0], target[0]) - lane_offset
        return [(source[0], sc[1] + port_shift), (lane_x, sc[1] + port_shift), (lane_x, tc[1] - port_shift), (target[0], tc[1] - port_shift)]

    # Forward transition. If it skips over one or more columns and is located on
    # the same horizontal level, route it above/below the graph so it does not
    # pass through intermediate nodes.
    if tc[0] > sc[0]:
        start = (source[2], sc[1] + port_shift)
        end = (target[0], tc[1] - port_shift)
        horizontal_distance = end[0] - start[0]
        if abs(start[1] - end[1]) < 36 and horizontal_distance > box_w + 210:
            lane_y = min_y - 70 - (index % 4) * 32 if index % 2 == 0 else max_y + 70 + (index % 4) * 32
            return [start, (start[0] + 55, start[1]), (start[0] + 55, lane_y), (end[0] - 55, lane_y), (end[0] - 55, end[1]), end]
        if abs(start[1] - end[1]) < 8:
            return [start, end]
        mid_x = (start[0] + end[0]) // 2
        return [start, (mid_x, start[1]), (mid_x, end[1]), end]

    # Backward/return transition: draw it outside the main graph area.
    start = (source[0], sc[1] + port_shift)
    end = (target[2], tc[1] - port_shift)
    use_top = index % 2 == 0
    lane_offset = 90 + (index % 6) * 28
    lane_y = min_y - lane_offset if use_top else max_y + lane_offset
    left_x = min(start[0], end[0]) - 65 - (index % 4) * 22
    right_x = max(start[0], end[0]) + 65 + (index % 4) * 22
    return [start, (left_x, start[1]), (left_x, lane_y), (right_x, lane_y), (right_x, end[1]), end]

def _edge_number_position(points: List[Point], index: int) -> Point:
    """Return a readable position for an edge number."""
    import math

    if len(points) < 2:
        return points[0] if points else (0, 0)

    segments: List[Tuple[Point, Point, float]] = []
    total = 0.0
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length > 0:
            segments.append((a, b, length))
            total += length

    if not segments:
        return points[0]

    # Use a later point on the route than before. For branching transitions this
    # places numbers after the arrows have already separated from each other.
    target_distance = min(max(85.0, total * 0.45), max(90.0, total - 45.0))
    passed = 0.0
    chosen_a, chosen_b, chosen_len = segments[0]
    local = min(target_distance, chosen_len)

    for a, b, length in segments:
        if passed + length >= target_distance:
            chosen_a, chosen_b, chosen_len = a, b, length
            local = target_distance - passed
            break
        passed += length

    ratio = 0 if chosen_len == 0 else local / chosen_len
    x = chosen_a[0] + (chosen_b[0] - chosen_a[0]) * ratio
    y = chosen_a[1] + (chosen_b[1] - chosen_a[1]) * ratio

    dx = chosen_b[0] - chosen_a[0]
    dy = chosen_b[1] - chosen_a[1]
    length = math.hypot(dx, dy) or 1.0
    nx = -dy / length
    ny = dx / length
    offset = ((index % 3) - 1) * 10
    return int(x + nx * offset), int(y + ny * offset)

def _draw_numbered_edges(draw, workflow: WorkflowDefinition, positions: Dict[str, Box], number_font) -> None:
    bounds = _layout_bounds(positions)
    for idx, t in enumerate(_visible_transitions(workflow), start=1):
        source = positions.get(t.from_state)
        target = positions.get(t.to_state)
        if not source or not target:
            continue
        points = _route_between(source, target, idx, bounds)
        _draw_arrow(draw, points)
        label_pos = _edge_number_position(points, idx)
        _draw_edge_number(draw, idx, label_pos, number_font)


def _draw_transition_legend(draw, workflow: WorkflowDefinition, x: int, y: int, width: int, font, title_font) -> int:
    draw.text((x, y), "Расшифровка переходов:", fill=(30, 35, 42), font=title_font)
    y += 30
    columns = 3 if width > 1500 else 2
    col_w = width // columns
    line_h = 20
    rows_per_col = (len(workflow.transitions) + columns - 1) // columns
    for idx, t in enumerate(_visible_transitions(workflow), start=1):
        col = (idx - 1) // rows_per_col
        row = (idx - 1) % rows_per_col
        tx = x + col * col_w
        ty = y + row * line_h
        text = f"{idx}. {_transition_label(t)}"
        # Сохраняем читаемость легенды и избегаем слишком длинных строк.
        if len(text) > 105:
            text = text[:102] + "…"
        draw.text((tx, ty), text, fill=(40, 45, 52), font=font)
    return y + rows_per_col * line_h


def _main_path(workflow: WorkflowDefinition) -> List[str]:
    outgoing: Dict[str, List[Transition]] = defaultdict(list)
    for t in _visible_transitions(workflow):
        outgoing[t.from_state].append(t)
    path = [workflow.initial]
    visited = {workflow.initial}
    current = workflow.initial
    while True:
        candidates = [t for t in outgoing.get(current, []) if t.to_state not in visited]
        if not candidates:
            break
        # Сначала предпочитаем продолжать путь в неконечные состояния; конечные завершают путь.
        all_transitions = _visible_transitions(workflow)
        candidates.sort(key=lambda t: (t.to_state in workflow.final, all_transitions.index(t)))
        chosen = candidates[0]
        path.append(chosen.to_state)
        visited.add(chosen.to_state)
        current = chosen.to_state
        if current in workflow.final:
            break
    return path


def _wide_positions(workflow: WorkflowDefinition) -> Dict[str, Box]:
    main = _main_path(workflow)
    main_set = set(main)
    box_w, box_h = 220, 66
    x_gap = 130
    y_main = 360
    x0 = 70
    positions: Dict[str, Box] = {}

    for i, state in enumerate(main):
        x = x0 + i * (box_w + x_gap)
        positions[state] = (x, y_main, x + box_w, y_main + box_h)

    # Branch states are placed in the next column relative to their source, not
    # almost above the source. This keeps branch arrows visible and prevents
    # final states from being connected by ambiguous vertical fragments.
    branch_slots: Dict[str, int] = defaultdict(int)
    incoming_from_main: Dict[str, str] = {}
    for t in _visible_transitions(workflow):
        if t.from_state in main_set and t.to_state not in main_set:
            incoming_from_main.setdefault(t.to_state, t.from_state)

    all_other = [s for s in workflow.states if s not in main_set]
    for state in all_other:
        source = incoming_from_main.get(state)
        if source and source in positions:
            sx1, sy1, sx2, sy2 = positions[source]
            slot = branch_slots[source]
            branch_slots[source] += 1
            direction = -1 if slot % 2 == 0 else 1
            depth = slot // 2 + 1
            x = sx1 + depth * (box_w + x_gap)
            y = y_main + direction * (145 + (depth - 1) * 105)
        else:
            level = _build_levels(workflow).get(state, 0)
            x = x0 + level * (box_w + x_gap)
            y = y_main + 250 + (len(positions) % 4) * 110
        positions[state] = (x, y, x + box_w, y + box_h)
    return positions

def _normalize_positions(positions: Dict[str, Box], margin: int = 70) -> Dict[str, Box]:
    min_x = min(box[0] for box in positions.values()) if positions else 0
    min_y = min(box[1] for box in positions.values()) if positions else 0
    dx = margin - min_x
    dy = margin + 40 - min_y
    return {s: (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy) for s, b in positions.items()}


def _render(workflow: WorkflowDefinition, path: Path, *, wide: bool) -> Path:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:  # не покрывается тестами
        raise RuntimeError("PNG rendering requires Pillow: pip install Pillow") from exc

    positions = _wide_positions(workflow) if wide else _compact_positions(workflow)
    positions = _normalize_positions(positions)
    _, _, _, graph_bottom = _layout_bounds(positions)

    # Легенда размещается сразу после графа, а не по фиксированной нижней координате.
    # Так она остаётся видимой даже для очень высоких диаграмм.
    visible_transition_count = len(_visible_transitions(workflow))
    legend_columns = 3
    rows_per_col = max(1, (visible_transition_count + legend_columns - 1) // legend_columns)
    legend_height = 65 + rows_per_col * 21 + 70
    width, _ = _canvas_for_positions(positions, extra_bottom=legend_height + 80)
    height = max(720, graph_bottom + legend_height + 90)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    title_font = _load_font(18, bold=True)
    font = _load_font(15)
    small_font = _load_font(11)
    number_font = _load_font(12, bold=True)
    legend_title_font = _load_font(13, bold=True)

    draw.text((70, 26), f"Конечный автомат: {_human_label(workflow.name)}", fill=(26, 33, 43), font=title_font)

    bounds = _layout_bounds(positions)
    for idx, t in enumerate(_visible_transitions(workflow), start=1):
        source = positions.get(t.from_state)
        target = positions.get(t.to_state)
        if not source or not target:
            continue
        points = _route_between(source, target, idx, bounds)
        # Альтернативные и возвратные связи в широкой схеме пунктирные; компактная схема
        # оставляет сплошные линии, чтобы основная диаграмма была понятнее в документе.
        dashed = bool(wide and (t.to_state in workflow.final or _box_center(target)[0] <= _box_center(source)[0]))
        _draw_arrow(draw, points, dash=dashed)
        _draw_edge_number(draw, idx, _edge_number_position(points, idx), number_font)

    # Узлы рисуются после рёбер, поэтому сегменты соединителей перекрываются заливкой
    # прямоугольников и визуально не проходят через подписи.
    for state, box in positions.items():
        _draw_node(draw, box, state, workflow, font)

    legend_y = graph_bottom + 45
    legend_end_y = _draw_transition_legend(draw, workflow, 70, legend_y, width - 140, small_font, legend_title_font)
    _draw_legend(draw, 70, legend_end_y + 26, small_font)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")
    return path

def render_png(definition: Dict[str, Any] | WorkflowDefinition, path: str | Path) -> Path:
    """Render workflow to PNG and also create a wide overview PNG.

    For every YAML process the renderer produces two useful views:

    1. the requested output file, for example ``contract.png`` — a compact
       numbered diagram with transition legend;
    2. an additional wide overview file, for example ``contract_wide.png`` — a
       broad process-path diagram.

    Both diagrams avoid artificial arrows into the initial state. Transition
    labels are represented by numbers on arrows, while full transition names are
    placed in the legend. This prevents text from overlapping arrows and keeps
    diagrams readable for large Russian-language workflows.
    """
    workflow = _as_definition(definition)
    target = Path(path)
    if target.suffix.lower() != ".png":
        target = target.with_suffix(".png")
    compact_path = _render(workflow, target, wide=False)
    wide_path = target.with_name(f"{target.stem}_wide{target.suffix}")
    _render(workflow, wide_path, wide=True)
    return compact_path
