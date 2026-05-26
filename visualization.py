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

    # 柜外区域背景
    ax.axhspan(container_H, container_H + 10, color="#f0f0f0", zorder=0)

    current_x = 0
    prev_seg_height = 0

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
                box_length = product["length"]
            else:
                box_length = product["width"]

            # 满层：逐 row 绘制
            for layer_idx in range(full_layers):
                y_pos = layer_idx * layer_height
                for row_idx in range(seg.rows):
                    ax.add_patch(Rectangle((current_x + row_idx * box_length, y_pos), box_length, layer_height,
                                           edgecolor='black', facecolor=color, alpha=0.8))


            # 尾层：逐 row 绘制，空 row 留白
            if remainder > 0:
                y_pos = full_layers * layer_height
                # 实排（满row）
                for row_idx in range(tail_full_rows):
                    ax.add_patch(Rectangle((current_x + row_idx * box_length, y_pos), box_length, layer_height,
                                           edgecolor='black', facecolor=color, alpha=0.8))
                # 不满排（浅色）
                if tail_last_cols > 0:
                    x_partial = current_x + tail_full_rows * box_length
                    ax.add_patch(Rectangle((x_partial, y_pos), box_length, layer_height,
                                           edgecolor='black', facecolor=color, alpha=0.4, linestyle='--', linewidth=1))
                    ax.text(x_partial + box_length / 2, y_pos + layer_height / 2,
                            f"{tail_last_cols}/{seg.cols}",
                            ha='center', va='center', fontsize=7, color='#333')
                # 空 row 留白（不画矩形）

        elif seg.type == "shared":
            base_height = 2 * seg.way_base.box_height
            rows_base = seg.rows_base
            rows_5L = seg.rows_5L

            # 底 2 层 base：逐 row 绘制（满层，无尾）
            base_product = PRODUCTS[seg.base_ptype]
            base_box_length = base_product["length"] if seg.way_base.orientation == "normal" else base_product["width"]
            for layer_idx in range(2):
                y_pos = layer_idx * seg.way_base.box_height
                for row_idx in range(rows_base):
                    ax.add_patch(Rectangle((current_x + row_idx * base_box_length, y_pos), base_box_length, seg.way_base.box_height,
                                           edgecolor='black', facecolor=COLORS[seg.base_ptype], alpha=0.8, hatch='//'))

            # 5L 层：逐 row 绘制
            fiveL_product = PRODUCTS["5L"]
            fiveL_box_length = fiveL_product["length"] if seg.way_5L.orientation == "normal" else fiveL_product["width"]
            per_layer_5L = rows_5L * seg.way_5L.cols
            full_layers_5L = seg.qty_5L // per_layer_5L
            remainder_5L = seg.qty_5L - full_layers_5L * per_layer_5L
            tail_full_rows_5L = remainder_5L // seg.way_5L.cols
            tail_last_cols_5L = remainder_5L - tail_full_rows_5L * seg.way_5L.cols

            # 5L 满层
            for layer_idx in range(full_layers_5L):
                y_pos = base_height + layer_idx * seg.way_5L.box_height
                for row_idx in range(rows_5L):
                    ax.add_patch(Rectangle((current_x + row_idx * fiveL_box_length, y_pos), fiveL_box_length, seg.way_5L.box_height,
                                           edgecolor='black', facecolor=COLORS["5L"], alpha=0.8))


            # 5L 尾层
            if remainder_5L > 0:
                y_pos = base_height + full_layers_5L * seg.way_5L.box_height
                # 实排
                for row_idx in range(tail_full_rows_5L):
                    ax.add_patch(Rectangle((current_x + row_idx * fiveL_box_length, y_pos), fiveL_box_length, seg.way_5L.box_height,
                                           edgecolor='black', facecolor=COLORS["5L"], alpha=0.8))
                # 不满排（浅色）
                if tail_last_cols_5L > 0:
                    x_partial = current_x + tail_full_rows_5L * fiveL_box_length
                    ax.add_patch(Rectangle((x_partial, y_pos), fiveL_box_length, seg.way_5L.box_height,
                                           edgecolor='black', facecolor=COLORS["5L"], alpha=0.4, linestyle='--', linewidth=1))
                    ax.text(x_partial + fiveL_box_length / 2, y_pos + seg.way_5L.box_height / 2,
                            f"{tail_last_cols_5L}/{seg.way_5L.cols}",
                            ha='center', va='center', fontsize=7, color='#333')

        # 段分隔虚线（只画到段顶）
        if i < len(result.segments):
            max_height = max(prev_seg_height, seg.total_height)
            ax.axvline(x=current_x + seg.seg_length, ymin=0, ymax=max_height / (container_H + 10),
                      color='gray', linestyle='--', alpha=0.5)

        # 段标签
        if seg.type == "pure":
            label = f"{i} · {seg.ptype}\n{seg.actual_layers}层 · {seg.qty}箱\nH={seg.total_height:.0f}cm"
        else:
            label = f"{i} · {seg.base_ptype}+5L\n2+{seg.layers_5L}层 · {seg.qty_base}+{seg.qty_5L}箱\nH={seg.total_height:.0f}cm"
        ax.text(current_x + seg.seg_length / 2, seg.total_height + 2,
                label,
                ha='center', va='bottom', fontsize=9, color='#333', fontproperties=font_prop)

        # 剩余空间标注
        if container_H - seg.total_height > 5:
            ax.axhline(y=seg.total_height, xmin=(current_x / container_L), xmax=((current_x + seg.seg_length) / container_L),
                      color='#ccc', linestyle='--', alpha=0.5)
            ax.text(current_x + seg.seg_length / 2, seg.total_height + 1,
                    f"剩余 {container_H - seg.total_height:.0f} cm",
                    ha='center', va='bottom', fontsize=8, color='#999')

        prev_seg_height = seg.total_height
        current_x += seg.seg_length

    # 柜门方向标识
    ax.arrow(container_L + 2, container_H / 2, 8, 0,
             head_width=3, head_length=5, fc='#666', ec='#666', lw=1.5)
    ax.text(container_L + 12, container_H / 2, '柜门',
            ha='left', va='center', fontsize=10, color='#666')

    ax.set_xlim(0, container_L)
    ax.set_ylim(0, container_H + 10)
    ax.set_xlabel("柜长 (cm)", fontproperties=font_prop)
    ax.set_ylabel("柜高 (cm)", fontproperties=font_prop)
    ax.set_title(f"侧视图 - 利用率: {result.utilization:.1%}, 高差: {result.height_variance:.1f}cm",
                 fontproperties=font_prop)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


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
                box_length = product["length"] if seg.orientation == "normal" else product["width"]
                box_width = product["width"] if seg.orientation == "normal" else product["length"]
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

                rows_base = seg.rows_base
                rows_5L = seg.rows_5L

                if layer_idx < 2:
                    base_box_length = base_product["length"] if seg.way_base.orientation == "normal" else base_product["width"]
                    base_box_width = base_product["width"] if seg.way_base.orientation == "normal" else base_product["length"]
                    for row in range(rows_base):
                        for col in range(seg.way_base.cols):
                            ax.add_patch(Rectangle((current_x + row * base_box_length, col * base_box_width),
                                                   base_box_length, base_box_width,
                                                   edgecolor='black', facecolor=COLORS[seg.base_ptype], alpha=0.8, hatch='//'))
                elif 2 <= layer_idx < 2 + seg.layers_5L:
                    fiveL_box_length = fiveL_product["length"] if seg.way_5L.orientation == "normal" else fiveL_product["width"]
                    fiveL_box_width = fiveL_product["width"] if seg.way_5L.orientation == "normal" else fiveL_product["length"]
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

    L, W, H = container_spec["length"], container_spec["width"], container_spec["height"]

    # 绘制容器线框（12条棱）
    edges = [
        # 底面4条棱
        ([0, L], [0, 0], [0, 0]),
        ([L, L], [0, W], [0, 0]),
        ([L, 0], [W, W], [0, 0]),
        ([0, 0], [W, 0], [0, 0]),
        # 顶面4条棱
        ([0, L], [0, 0], [H, H]),
        ([L, L], [0, W], [H, H]),
        ([L, 0], [W, W], [H, H]),
        ([0, 0], [W, 0], [H, H]),
        # 垂直4条棱
        ([0, 0], [0, 0], [0, H]),
        ([L, L], [0, 0], [0, H]),
        ([L, L], [W, W], [0, H]),
        ([0, 0], [W, W], [0, H]),
    ]
    for edge in edges:
        fig.add_trace(go.Scatter3d(
            x=edge[0], y=edge[1], z=edge[2],
            mode="lines",
            line=dict(color="#333", width=2),
            showlegend=False,
            hoverinfo="skip"
        ))

    # 柜门方向指示
    fig.add_trace(go.Cone(
        x=[L + 30], y=[W / 2], z=[H / 2],
        u=[1], v=[0], w=[0],
        sizemode="absolute",
        sizeref=40,
        anchor="tail",
        colorscale=[[0, "#666"], [1, "#666"]],
        showscale=False,
        showlegend=False,
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter3d(
        x=[L + 80], y=[W / 2], z=[H / 2],
        mode="text",
        text=["柜门"],
        textfont=dict(size=12, color="#666"),
        showlegend=False, hoverinfo="skip",
    ))

    # 辅助函数：计算箱子在宽度方向的尺寸
    def get_box_width_along_W(ptype: str, orientation: str) -> float:
        product = PRODUCTS[ptype]
        return product["width"] if orientation == "normal" else product["length"]

    # 辅助函数：绘制长方体
    def add_box(x: float, y: float, z: float, dx: float, dy: float, dz: float, color: str, hovertext: str):
        fig.add_trace(go.Mesh3d(
            x=[x,    x+dx, x+dx, x,    x,    x+dx, x+dx, x   ],
            y=[y,    y,    y+dy, y+dy, y,    y,    y+dy, y+dy],
            z=[z,    z,    z,    z,    z+dz, z+dz, z+dz, z+dz],
            i=[7, 0, 0, 0, 4, 4, 2, 6, 4, 0, 3, 7],
            j=[3, 4, 1, 2, 5, 6, 5, 5, 0, 1, 2, 2],
            k=[0, 7, 2, 3, 6, 7, 1, 2, 1, 5, 7, 6],
            opacity=0.85,
            color=color,
            hovertext=hovertext,
            showlegend=False
        ))

    x_cursor = 0

    for i, seg in enumerate(result.segments, 1):
        if seg.type == "pure":
            # Pure段：画1个长方体
            box_width_along_W = get_box_width_along_W(seg.ptype, seg.orientation)
            dx = seg.seg_length
            dy = seg.cols * box_width_along_W
            dz = seg.total_height
            hovertext = f"{i} · {seg.ptype}<br>{seg.actual_layers}层 · {seg.qty}箱<br>{seg.seg_length:.0f}×{dy:.0f}×{seg.total_height:.0f} cm"
            add_box(x_cursor, 0, 0, dx, dy, dz, COLORS[seg.ptype], hovertext)

        elif seg.type == "shared":
            # Shared段：画2个长方体
            # 底块
            base_box_width_along_W = get_box_width_along_W(seg.base_ptype, seg.way_base.orientation)
            dx = seg.seg_length
            dy = seg.way_base.cols * base_box_width_along_W
            dz = 2 * seg.way_base.box_height
            hovertext = f"{i}底 · {seg.base_ptype}<br>2层 · {seg.qty_base}箱"
            add_box(x_cursor, 0, 0, dx, dy, dz, COLORS[seg.base_ptype], hovertext)

            # 顶块（5L）
            fiveL_box_width_along_W = get_box_width_along_W("5L", seg.way_5L.orientation)
            rows_5L = seg.rows_5L
            dx_5L = rows_5L * seg.way_5L.row_length
            dy_5L = seg.way_5L.cols * fiveL_box_width_along_W
            dz_5L = seg.layers_5L * seg.way_5L.box_height
            hovertext = f"{i}顶 · 5L<br>{seg.layers_5L}层 · {seg.qty_5L}箱"
            add_box(x_cursor, 0, dz, dx_5L, dy_5L, dz_5L, COLORS["5L"], hovertext)

        # 段标签
        if seg.type == "pure":
            label = f"{i} · {seg.ptype}"
        else:
            label = f"{i} · {seg.base_ptype}+5L"

        fig.add_trace(go.Scatter3d(
            x=[x_cursor + seg.seg_length / 2],
            y=[container_spec["width"] / 2],
            z=[seg.total_height + 5],
            mode="text",
            text=[label],
            textfont=dict(size=14, color="#333"),
            textposition="middle center",
            showlegend=False,
            hoverinfo="skip"
        ))

        x_cursor += seg.seg_length

    # 添加产品图例
    for ptype, color in COLORS.items():
        fig.add_trace(go.Scatter3d(
            x=[None], y=[None], z=[None],
            mode="markers",
            marker=dict(size=10, color=color),
            name=ptype,
            showlegend=True,
        ))

    fig.update_layout(
        scene=dict(
            xaxis_title="柜长 (cm)",
            yaxis_title="柜宽 (cm)",
            zaxis_title="柜高 (cm)",
            aspectmode="data",
            camera=dict(eye=dict(x=1.5, y=-1.8, z=1.0)),
        ),
        font=dict(family="Microsoft YaHei, SimHei, sans-serif"),
        margin=dict(l=0, r=0, t=50, b=0),
        showlegend=True,
        title=dict(
            text=f"3D 视图 - 利用率: {result.utilization:.1%}, 高差: {result.height_variance:.1f}cm",
            x=0.5, xanchor="center",
            font=dict(size=14)
        ),
    )
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
            rows_base = seg.rows_base
            rows_5L = seg.rows_5L
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
