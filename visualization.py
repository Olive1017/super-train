"""
装柜方案可视化
"""

import math
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import plotly.graph_objects as go
from packing import PackingResult
from config import CONTAINERS, PRODUCTS

COLORS = {"5L": "#4A90E2", "2L": "#7ED321", "艾考": "#F5A623"}
FONT_PATH = "fonts/SIMHEI.ttf"


def setup_chinese_font():
    import matplotlib.font_manager as fm
    return fm.FontProperties(fname=FONT_PATH)


def render_side_view(result: PackingResult, container: str):
    """侧视图"""
    container_spec = CONTAINERS[container]
    font_prop = setup_chinese_font()
    fig, ax = plt.subplots(figsize=(12, 6))
    container_L, container_H = container_spec["length"], container_spec["height"]
    ax.add_patch(Rectangle((0, 0), container_L, container_H, edgecolor='black', facecolor='none', linewidth=2))
    current_x = 0

    for i, seg in enumerate(result.segments, 1):
        color = COLORS.get(seg.ptype or seg.base_ptype, "gray")

        if seg.type == "pure":
            per_layer = seg.per_layer
            full_layers = seg.qty // per_layer
            remainder = seg.qty - full_layers * per_layer
            tail_full_rows = remainder // seg.cols
            tail_last_cols = remainder - tail_full_rows * seg.cols
            layer_height = seg.total_height / seg.actual_layers

            # 计算箱子的长度（沿柜长方向）
            product = PRODUCTS[seg.ptype]
            if seg.orientation == "normal":
                box_length = product["depth"]
            else:
                box_length = product["width"]

            for layer_idx in range(full_layers):
                ax.add_patch(Rectangle((current_x, layer_idx * layer_height), seg.seg_length, layer_height,
                                       edgecolor='black', facecolor=color, alpha=0.8))

            if remainder > 0:
                y_pos = full_layers * layer_height
                if tail_full_rows > 0:
                    ax.add_patch(Rectangle((current_x, y_pos), tail_full_rows * box_length, layer_height,
                                           edgecolor='black', facecolor=color, alpha=0.8))
                if tail_last_cols > 0:
                    ax.add_patch(Rectangle((current_x + tail_full_rows * box_length, y_pos),
                                           tail_last_cols * box_length, layer_height,
                                           edgecolor='black', facecolor=color, alpha=0.6, linestyle='--'))

        elif seg.type == "shared":
            base_height = 2 * seg.way_base.box_height
            rows_base = math.ceil(seg.seg_length / seg.way_base.row_depth)
            rows_5L = math.ceil(seg.seg_length / seg.way_5L.row_depth)
            ax.add_patch(Rectangle((current_x, 0), rows_base * seg.way_base.row_depth, base_height,
                                   edgecolor='black', facecolor=COLORS[seg.base_ptype], alpha=0.8, hatch='//'))
            layer_height = seg.way_5L.box_height
            for layer_idx in range(seg.layers_5L):
                ax.add_patch(Rectangle((current_x, base_height + layer_idx * layer_height),
                                       rows_5L * seg.way_5L.row_depth, layer_height,
                                       edgecolor='black', facecolor=COLORS["5L"], alpha=0.8))

        if i < len(result.segments):
            ax.axvline(x=current_x + seg.seg_length, color='gray', linestyle='--', alpha=0.5)

        ax.text(current_x + seg.seg_length / 2, seg.total_height + 5,
                f"{i}/{seg.type}\n{seg.actual_layers or seg.layers_5L}层\n{seg.total_height:.1f}cm",
                ha='center', va='bottom', fontsize=8, fontproperties=font_prop)
        current_x += seg.seg_length

    ax.set_xlim(0, container_L)
    ax.set_ylim(0, container_H + 30)
    ax.set_xlabel("柜长 (cm)", fontproperties=font_prop)
    ax.set_ylabel("柜高 (cm)", fontproperties=font_prop)
    ax.set_title(f"侧视图 - 利用率: {result.utilization:.1%}, 高差: {result.height_variance:.1f}cm",
                 fontproperties=font_prop)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def render_3d_view(result: PackingResult, container: str):
    """3D视图"""
    container_spec = CONTAINERS[container]
    fig = go.Figure()
    boxes = []
    current_x = 0

    for seg_idx, seg in enumerate(result.segments, 1):
        if seg.type == "pure":
            product = PRODUCTS[seg.ptype]
            box_length = product["depth"] if seg.orientation == "normal" else product["width"]
            box_width = product["width"] if seg.orientation == "normal" else product["depth"]
            color = COLORS[seg.ptype]
            per_layer = seg.per_layer
            full_layers = seg.qty // per_layer
            remainder = seg.qty - full_layers * per_layer
            tail_full_rows = remainder // seg.cols
            tail_last_cols = remainder - tail_full_rows * seg.cols
            box_height = seg.total_height / seg.actual_layers

            for layer_idx in range(full_layers):
                for row in range(seg.rows):
                    for col in range(seg.cols):
                        boxes.append({'x': current_x + row * box_length, 'y': col * box_width, 'z': layer_idx * box_height,
                                     'dx': box_length, 'dy': box_width, 'dz': box_height, 'color': color, 'type': seg.ptype, 'seg': seg_idx, 'layer': layer_idx + 1})

            if remainder > 0:
                for row in range(tail_full_rows):
                    for col in range(seg.cols):
                        boxes.append({'x': current_x + row * box_length, 'y': col * box_width, 'z': full_layers * box_height,
                                     'dx': box_length, 'dy': box_width, 'dz': box_height, 'color': color, 'type': seg.ptype, 'seg': seg_idx, 'layer': full_layers + 1})
                if tail_last_cols > 0:
                    for col in range(tail_last_cols):
                        boxes.append({'x': current_x + tail_full_rows * box_length, 'y': col * box_width, 'z': full_layers * box_height,
                                     'dx': box_length, 'dy': box_width, 'dz': box_height, 'color': color, 'type': seg.ptype, 'seg': seg_idx, 'layer': full_layers + 1})

        elif seg.type == "shared":
            base_product = PRODUCTS[seg.base_ptype]
            fiveL_product = PRODUCTS["5L"]
            base_box_length = base_product["depth"] if seg.way_base.orientation == "normal" else base_product["width"]
            base_box_width = base_product["width"] if seg.way_base.orientation == "normal" else base_product["depth"]
            fiveL_box_length = fiveL_product["depth"] if seg.way_5L.orientation == "normal" else fiveL_product["width"]
            fiveL_box_width = fiveL_product["width"] if seg.way_5L.orientation == "normal" else fiveL_product["depth"]

            rows_base = math.ceil(seg.seg_length / seg.way_base.row_depth)
            rows_5L = math.ceil(seg.seg_length / seg.way_5L.row_depth)

            for layer_idx in range(2):
                for row in range(rows_base):
                    for col in range(seg.way_base.cols):
                        boxes.append({'x': current_x + row * base_box_length, 'y': col * base_box_width, 'z': layer_idx * seg.way_base.box_height,
                                     'dx': base_box_length, 'dy': base_box_width, 'dz': seg.way_base.box_height, 'color': COLORS[seg.base_ptype], 'type': seg.base_ptype, 'seg': seg_idx, 'layer': layer_idx + 1})

            base_height = 2 * seg.way_base.box_height
            for layer_idx in range(seg.layers_5L):
                for row in range(rows_5L):
                    for col in range(seg.way_5L.cols):
                        boxes.append({'x': current_x + row * fiveL_box_length, 'y': col * fiveL_box_width, 'z': base_height + layer_idx * seg.way_5L.box_height,
                                     'dx': fiveL_box_length, 'dy': fiveL_box_width, 'dz': seg.way_5L.box_height, 'color': COLORS["5L"], 'type': "5L", 'seg': seg_idx, 'layer': layer_idx + 1})

        current_x += seg.seg_length

    # 绘制所有箱子
    for box in boxes:
        x0, y0, z0 = box['x'], box['y'], box['z']
        x1, y1, z1 = x0 + box['dx'], y0 + box['dy'], z0 + box['dz']
        fig.add_trace(go.Mesh3d(
            x=[x0, x1, x1, x0, x0, x0, x1, x1, x0, x0, x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0, y0, y0, y1, y1, y0, y0, y0, y1, y1, y0],
            z=[z0, z0, z0, z0, z0, z1, z1, z1, z1, z1, z1, z1, z1, z1, z1],
            i=[0, 1, 2, 0, 3, 2, 4, 5, 6, 4, 7, 6],
            j=[1, 5, 6, 2, 0, 4, 5, 9, 10, 6, 8, 11],
            k=[4, 8, 9, 6, 7, 5, 6, 10, 11, 7, 11, 10],
            opacity=0.8, color=box['color'],
            name=f"{box['type']} 段{box['seg']} 层{box['layer']}",
            hovertext=f"品类: {box['type']}<br>段号: {box['seg']}<br>层号: {box['layer']}"
        ))

    fig.update_layout(scene=dict(aspectmode='data',
                                  xaxis_title='柜长(cm)', yaxis_title='柜宽(cm)', zaxis_title='柜高(cm)'),
                     title='3D 装柜视图')
    return fig


def generate_worker_guide(result: PackingResult, container: str) -> str:
    """生成操作指南"""
    container_spec = CONTAINERS[container]
    lines = [
        "=== 装柜操作指南 ===",
        f"柜型：{container}（{container_spec['length']}×{container_spec['width']}×{container_spec['height']} cm）",
        f"长度利用率：{result.utilization * 100:.1f}%",
        f"高度差：{result.height_variance:.1f} cm",
        f"总段数：{len(result.segments)}",
        ""
    ]

    for i, seg in enumerate(result.segments, 1):
        lines.append(f"【第 {i} 段】(段长 {seg.seg_length:.1f} cm, 段高 {seg.total_height:.1f} cm)")

        if seg.type == "pure":
            per_layer = seg.per_layer
            full_layers = seg.qty // per_layer
            remainder = seg.qty - full_layers * per_layer
            tail_full_rows = remainder // seg.cols
            tail_last_cols = remainder - tail_full_rows * seg.cols
            orientation_desc = "箱子长沿柜长" if seg.orientation == "normal" else "箱子长沿柜宽（旋转）"

            lines.append(f"  品类：{seg.ptype}")
            lines.append(f"  朝向：{orientation_desc}")
            lines.append(f"  底排：{seg.rows} 排 × {seg.cols} 列")
            lines.append(f"  叠 {full_layers} 满层（{full_layers * per_layer} 箱）")

            if remainder > 0:
                tail_desc = f"  顶层尾排：{tail_full_rows} 整排"
                if tail_last_cols > 0:
                    tail_desc += f" + {tail_last_cols} 个零散，靠后/靠边"
                lines.append(tail_desc)

        elif seg.type == "shared":
            lines.append("  ⚠ 共享段：先铺底再叠 5L")
            rows_base = math.ceil(seg.seg_length / seg.way_base.row_depth)
            rows_5L = math.ceil(seg.seg_length / seg.way_5L.row_depth)
            lines.append(f"  ① 底层 {seg.base_ptype}：2 层，{rows_base} 排 × {seg.way_base.cols} 列，共 {seg.qty_base} 箱")
            lines.append(f"  ② 上层 5L：{seg.layers_5L} 层，{rows_5L} 排 × {seg.way_5L.cols} 列，共 {seg.qty_5L} 箱")

        lines.append("")

    lines.extend([
        "=== 注意 ===",
        "- 严禁斜放、不可超层数",
        "- 尾排零散箱靠柜门方向集中放置",
        "- 共享段：先铺完底层 base，再叠 5L"
    ])

    return "\n".join(lines)



def render_top_view(result: PackingResult, container: str):
    """俯视图"""
    container_spec = CONTAINERS[container]
    font_prop = setup_chinese_font()
    max_layers = max((seg.actual_layers if seg.type == "pure" else 2 + seg.layers_5L)
                     for seg in result.segments)

    fig, axes = plt.subplots(max_layers, 1, figsize=(14, 3 * max_layers))
    if max_layers == 1:
        axes = [axes]

    container_L, container_W = container_spec["length"], container_spec["width"]

    for layer_idx in range(max_layers):
        ax = axes[layer_idx]
        ax.add_patch(Rectangle((0, 0), container_L, container_W, edgecolor='black', facecolor='none', linewidth=2))
        current_x = 0

        for seg in result.segments:
            color = COLORS.get(seg.ptype or seg.base_ptype, "gray")

            if seg.type == "pure":
                product = PRODUCTS[seg.ptype]
                box_length = product["depth"] if seg.orientation == "normal" else product["width"]
                box_width = product["width"] if seg.orientation == "normal" else product["depth"]
                per_layer = seg.per_layer
                full_layers = seg.qty // per_layer
                remainder = seg.qty - full_layers * per_layer
                tail_full_rows = remainder // seg.cols
                tail_last_cols = remainder - tail_full_rows * seg.cols

                if layer_idx < full_layers:
                    for row in range(seg.rows):
                        for col in range(seg.cols):
                            ax.add_patch(Rectangle((current_x + row * box_length, col * box_width),
                                                   box_length, box_width, edgecolor='black', facecolor=color, alpha=0.8))
                elif layer_idx == full_layers and remainder > 0:
                    for row in range(tail_full_rows):
                        for col in range(seg.cols):
                            ax.add_patch(Rectangle((current_x + row * box_length, col * box_width),
                                                   box_length, box_width, edgecolor='black', facecolor=color, alpha=0.8))
                    if tail_last_cols > 0:
                        for col in range(tail_last_cols):
                            ax.add_patch(Rectangle((current_x + tail_full_rows * box_length, col * box_width),
                                                   box_length, box_width, edgecolor='black', facecolor=color, alpha=0.6, linestyle='--'))

            elif seg.type == "shared":
                base_product = PRODUCTS[seg.base_ptype]
                fiveL_product = PRODUCTS["5L"]

                rows_base = math.ceil(seg.seg_length / seg.way_base.row_depth)
                rows_5L = math.ceil(seg.seg_length / seg.way_5L.row_depth)

                if layer_idx < 2:
                    base_box_length = base_product["depth"] if seg.way_base.orientation == "normal" else base_product["width"]
                    base_box_width = base_product["width"] if seg.way_base.orientation == "normal" else base_product["depth"]
                    for row in range(rows_base):
                        for col in range(seg.way_base.cols):
                            ax.add_patch(Rectangle((current_x + row * base_box_length, col * base_box_width),
                                                   base_box_length, base_box_width,
                                                   edgecolor='black', facecolor=COLORS[seg.base_ptype], alpha=0.8, hatch='//'))
                elif 2 <= layer_idx < 2 + seg.layers_5L:
                    fiveL_box_length = fiveL_product["depth"] if seg.way_5L.orientation == "normal" else fiveL_product["width"]
                    fiveL_box_width = fiveL_product["width"] if seg.way_5L.orientation == "normal" else fiveL_product["depth"]
                    for row in range(rows_5L):
                        for col in range(seg.way_5L.cols):
                            ax.add_patch(Rectangle((current_x + row * fiveL_box_length, col * fiveL_box_width),
                                                   fiveL_box_length, fiveL_box_width,
                                                   edgecolor='black', facecolor=COLORS["5L"], alpha=0.8))

            current_x += seg.seg_length

        ax.set_xlim(0, container_L)
        ax.set_ylim(0, container_W)
        ax.set_xlabel("柜长 (cm)", fontproperties=font_prop)
        ax.set_ylabel("柜宽 (cm)", fontproperties=font_prop)
        ax.set_title(f"第 {layer_idx + 1} 层", fontproperties=font_prop)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def render_3d_view(result: PackingResult, container: str):
    """3D视图"""
    container_spec = CONTAINERS[container]
    fig = go.Figure()
    boxes = []
    current_x = 0

    for seg_idx, seg in enumerate(result.segments, 1):
        if seg.type == "pure":
            product = PRODUCTS[seg.ptype]
            box_length = product["depth"] if seg.orientation == "normal" else product["width"]
            box_width = product["width"] if seg.orientation == "normal" else product["depth"]
            color = COLORS[seg.ptype]
            per_layer = seg.per_layer
            full_layers = seg.qty // per_layer
            remainder = seg.qty - full_layers * per_layer
            tail_full_rows = remainder // seg.cols
            tail_last_cols = remainder - tail_full_rows * seg.cols
            box_height = seg.total_height / seg.actual_layers

            for layer_idx in range(full_layers):
                for row in range(seg.rows):
                    for col in range(seg.cols):
                        boxes.append({'x': current_x + row * box_length, 'y': col * box_width, 'z': layer_idx * box_height,
                                     'dx': box_length, 'dy': box_width, 'dz': box_height, 'color': color, 'type': seg.ptype, 'seg': seg_idx, 'layer': layer_idx + 1})

            if remainder > 0:
                for row in range(tail_full_rows):
                    for col in range(seg.cols):
                        boxes.append({'x': current_x + row * box_length, 'y': col * box_width, 'z': full_layers * box_height,
                                     'dx': box_length, 'dy': box_width, 'dz': box_height, 'color': color, 'type': seg.ptype, 'seg': seg_idx, 'layer': full_layers + 1})
                if tail_last_cols > 0:
                    for col in range(tail_last_cols):
                        boxes.append({'x': current_x + tail_full_rows * box_length, 'y': col * box_width, 'z': full_layers * box_height,
                                     'dx': box_length, 'dy': box_width, 'dz': box_height, 'color': color, 'type': seg.ptype, 'seg': seg_idx, 'layer': full_layers + 1})

        elif seg.type == "shared":
            base_product = PRODUCTS[seg.base_ptype]
            fiveL_product = PRODUCTS["5L"]
            base_box_length = base_product["depth"] if seg.way_base.orientation == "normal" else base_product["width"]
            base_box_width = base_product["width"] if seg.way_base.orientation == "normal" else base_product["depth"]
            fiveL_box_length = fiveL_product["depth"] if seg.way_5L.orientation == "normal" else fiveL_product["width"]
            fiveL_box_width = fiveL_product["width"] if seg.way_5L.orientation == "normal" else fiveL_product["depth"]

            rows_base = math.ceil(seg.seg_length / seg.way_base.row_depth)
            rows_5L = math.ceil(seg.seg_length / seg.way_5L.row_depth)

            for layer_idx in range(2):
                for row in range(rows_base):
                    for col in range(seg.way_base.cols):
                        boxes.append({'x': current_x + row * base_box_length, 'y': col * base_box_width, 'z': layer_idx * seg.way_base.box_height,
                                     'dx': base_box_length, 'dy': base_box_width, 'dz': seg.way_base.box_height, 'color': COLORS[seg.base_ptype], 'type': seg.base_ptype, 'seg': seg_idx, 'layer': layer_idx + 1})

            base_height = 2 * seg.way_base.box_height
            for layer_idx in range(seg.layers_5L):
                for row in range(rows_5L):
                    for col in range(seg.way_5L.cols):
                        boxes.append({'x': current_x + row * fiveL_box_length, 'y': col * fiveL_box_width, 'z': base_height + layer_idx * seg.way_5L.box_height,
                                     'dx': fiveL_box_length, 'dy': fiveL_box_width, 'dz': seg.way_5L.box_height, 'color': COLORS["5L"], 'type': "5L", 'seg': seg_idx, 'layer': layer_idx + 1})

        current_x += seg.seg_length

    # 绘制所有箱子
    for box in boxes:
        x0, y0, z0 = box['x'], box['y'], box['z']
        x1, y1, z1 = x0 + box['dx'], y0 + box['dy'], z0 + box['dz']
        fig.add_trace(go.Mesh3d(
            x=[x0, x1, x1, x0, x0, x0, x1, x1, x0, x0, x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0, y0, y0, y1, y1, y0, y0, y0, y1, y1, y0],
            z=[z0, z0, z0, z0, z0, z1, z1, z1, z1, z1, z1, z1, z1, z1, z1],
            i=[0, 1, 2, 0, 3, 2, 4, 5, 6, 4, 7, 6],
            j=[1, 5, 6, 2, 0, 4, 5, 9, 10, 6, 8, 11],
            k=[4, 8, 9, 6, 7, 5, 6, 10, 11, 7, 11, 10],
            opacity=0.8, color=box['color'],
            name=f"{box['type']} 段{box['seg']} 层{box['layer']}",
            hovertext=f"品类: {box['type']}<br>段号: {box['seg']}<br>层号: {box['layer']}"
        ))

    fig.update_layout(scene=dict(aspectmode='data',
                                  xaxis_title='柜长(cm)', yaxis_title='柜宽(cm)', zaxis_title='柜高(cm)'),
                     title='3D 装柜视图')
    return fig


def generate_worker_guide(result: PackingResult, container: str) -> str:
    """生成操作指南"""
    container_spec = CONTAINERS[container]
    lines = [
        "=== 装柜操作指南 ===",
        f"柜型：{container}（{container_spec['length']}×{container_spec['width']}×{container_spec['height']} cm）",
        f"长度利用率：{result.utilization * 100:.1f}%",
        f"高度差：{result.height_variance:.1f} cm",
        f"总段数：{len(result.segments)}",
        ""
    ]

    for i, seg in enumerate(result.segments, 1):
        lines.append(f"【第 {i} 段】(段长 {seg.seg_length:.1f} cm, 段高 {seg.total_height:.1f} cm)")

        if seg.type == "pure":
            per_layer = seg.per_layer
            full_layers = seg.qty // per_layer
            remainder = seg.qty - full_layers * per_layer
            tail_full_rows = remainder // seg.cols
            tail_last_cols = remainder - tail_full_rows * seg.cols
            orientation_desc = "箱子长沿柜长" if seg.orientation == "normal" else "箱子长沿柜宽（旋转）"

            lines.append(f"  品类：{seg.ptype}")
            lines.append(f"  朝向：{orientation_desc}")
            lines.append(f"  底排：{seg.rows} 排 × {seg.cols} 列")
            lines.append(f"  叠 {full_layers} 满层（{full_layers * per_layer} 箱）")

            if remainder > 0:
                tail_desc = f"  顶层尾排：{tail_full_rows} 整排"
                if tail_last_cols > 0:
                    tail_desc += f" + {tail_last_cols} 个零散，靠后/靠边"
                lines.append(tail_desc)

        elif seg.type == "shared":
            lines.append("  ⚠ 共享段：先铺底再叠 5L")
            rows_base = math.ceil(seg.seg_length / seg.way_base.row_depth)
            rows_5L = math.ceil(seg.seg_length / seg.way_5L.row_depth)
            lines.append(f"  ① 底层 {seg.base_ptype}：2 层，{rows_base} 排 × {seg.way_base.cols} 列，共 {seg.qty_base} 箱")
            lines.append(f"  ② 上层 5L：{seg.layers_5L} 层，{rows_5L} 排 × {seg.way_5L.cols} 列，共 {seg.qty_5L} 箱")

        lines.append("")

    lines.extend([
        "=== 注意 ===",
        "- 严禁斜放、不可超层数",
        "- 尾排零散箱靠柜门方向集中放置",
        "- 共享段：先铺完底层 base，再叠 5L"
    ])

    return "\n".join(lines)

