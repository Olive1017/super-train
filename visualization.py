"""
装柜方案可视化
"""

import itertools

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import plotly.graph_objects as go
from packing import PackingResult
from config import CONTAINERS, PRODUCTS

COLORS = {"5L": "#4A90E2", "2L": "#7ED321", "艾考": "#F5A623"}
FONT_PATH = "fonts/SIMHEI.ttf"

# 正向/竖装：长沿柜长、宽沿柜宽（宽面朝柜门），须与 packing.py generate_ways 一致
NORMAL_ORIENTATION = "打竖装"


def dim_along_L(product, orientation):
    """箱子沿柜长方向的尺寸"""
    return product["length"] if orientation == NORMAL_ORIENTATION else product["width"]


def dim_along_W(product, orientation):
    """箱子沿柜宽方向的尺寸"""
    return product["width"] if orientation == NORMAL_ORIENTATION else product["length"]


def bump_subblock_x_starts(placement, x_seg_start, seg_length, bump_length, box_length, tail_full_rows, tail_last_cols):
    """
    返回 bump 内部 '满行块' 和 '零散行块' 的 x 起点。

    零散行永远紧邻段主体，满行永远占段外缘。

    Args:
        placement: "front" 或 "back"
        x_seg_start: 段起点 x 坐标
        seg_length: 段长度
        bump_length: bump 总长度
        box_length: 单个箱子长度
        tail_full_rows: 满行数量
        tail_last_cols: 零散列数量

    Returns:
        (x_full_start, x_partial_start): 满行块和零散块的 x 起点
    """
    full_width = tail_full_rows * box_length
    partial_width = box_length if tail_last_cols > 0 else 0

    if placement == "front":
        # bump 在段左、主体在右；零散行靠右（贴主体），满行靠左（贴段外缘）
        x_full_start = x_seg_start
        x_partial_start = x_seg_start + full_width
    elif placement == "back":
        # bump 在段右、主体在左；零散行靠左（贴主体），满行靠右（贴段外缘）
        bump_start = x_seg_start + seg_length - bump_length
        x_partial_start = bump_start
        x_full_start = bump_start + partial_width
    else:
        raise ValueError(f"Invalid placement: {placement}")

    return x_full_start, x_partial_start


def get_segment_profile(seg):
    """
    返回该段的"高度档案"。

    Returns:
        dict: {
            main_height: 主体高度（不含尾层），
            bump_length: 尾层长度，
            bump_height: 尾层高度，
            bump_full_rows: 尾层满行数，
            bump_partial_cols: 尾层零散列数，
            box_length: 沿柜长方向的箱子长度，
            box_width_along_W: 沿柜宽方向的箱子宽度，
            color: 颜色，
            orientation: 朝向
        }
    """
    if seg.type == "pure":
        per_layer = seg.per_layer
        full_layers = seg.qty // per_layer
        remainder = seg.qty - full_layers * per_layer
        tail_full_rows = remainder // seg.cols
        tail_last_cols = remainder - tail_full_rows * seg.cols
        layer_height = seg.total_height / seg.actual_layers

        product = PRODUCTS[seg.ptype]
        box_length = dim_along_L(product, seg.orientation)
        box_width_along_W = dim_along_W(product, seg.orientation)

        if remainder > 0:
            bump_length = (tail_full_rows + (1 if tail_last_cols > 0 else 0)) * box_length
            bump_height = layer_height
            main_height = full_layers * layer_height
        else:
            bump_length = 0
            bump_height = 0
            main_height = seg.total_height

        return {
            "main_height": main_height,
            "bump_length": bump_length,
            "bump_height": bump_height,
            "bump_full_rows": tail_full_rows,
            "bump_partial_cols": tail_last_cols,
            "box_length": box_length,
            "box_width_along_W": box_width_along_W,
            "color": COLORS[seg.ptype],
            "orientation": seg.orientation,
            "cols": seg.cols,
        }

    elif seg.type == "shared":
        # base 始终满 2 层，不参与决策
        base_height = 2 * seg.way_base.box_height

        # 5L 部分计算尾层
        fiveL_product = PRODUCTS["5L"]
        per_layer_5L = seg.rows_5L * seg.way_5L.cols
        full_layers_5L = seg.qty_5L // per_layer_5L
        remainder_5L = seg.qty_5L - full_layers_5L * per_layer_5L
        tail_full_rows_5L = remainder_5L // seg.way_5L.cols
        tail_last_cols_5L = remainder_5L - tail_full_rows_5L * seg.way_5L.cols

        box_length = dim_along_L(fiveL_product, seg.way_5L.orientation)
        box_width_along_W = dim_along_W(fiveL_product, seg.way_5L.orientation)

        if remainder_5L > 0:
            bump_length = (tail_full_rows_5L + (1 if tail_last_cols_5L > 0 else 0)) * box_length
            bump_height = seg.way_5L.box_height
            main_height = base_height + full_layers_5L * seg.way_5L.box_height
        else:
            bump_length = 0
            bump_height = 0
            main_height = seg.total_height

        return {
            "main_height": main_height,
            "bump_length": bump_length,
            "bump_height": bump_height,
            "bump_full_rows": tail_full_rows_5L,
            "bump_partial_cols": tail_last_cols_5L,
            "box_length": box_length,
            "box_width_along_W": box_width_along_W,
            "color": COLORS["5L"],
            "orientation": seg.way_5L.orientation,
            "cols": seg.way_5L.cols,
        }

    return {
        "main_height": seg.total_height,
        "bump_length": 0,
        "bump_height": 0,
        "bump_full_rows": 0,
        "bump_partial_cols": 0,
        "box_length": 0,
        "box_width_along_W": 0,
        "color": "gray",
        "orientation": NORMAL_ORIENTATION,
        "cols": 0,
    }


def choose_bump_placements(segments):
    """
    枚举每段 front/back 选择，选总边界跳跃最小的组合。

    Args:
        segments: 段列表，已按 total_height 降序排序

    Returns:
        list[str]: 每段的尾层位置，长度 = len(segments)
                   可能的值: "front", "back", "none"
    """
    profiles = [get_segment_profile(s) for s in segments]
    n = len(segments)

    if n == 0:
        return []

    # 为每段生成选项：无尾层时只有 "none"，否则 "front" 或 "back"
    options_per_seg = [["none"] if p["bump_length"] == 0 else ["front", "back"] for p in profiles]

    best_score = float("inf")
    best_choices = None

    # 枚举所有可能的组合 (最多 2^N 种)
    for combo in itertools.product(*options_per_seg):
        # 计算每段在前端/后端的实际可见高度
        edges = []
        for p, c in zip(profiles, combo):
            if c == "front":
                edges.append((p["main_height"] + p["bump_height"], p["main_height"]))
            elif c == "back":
                edges.append((p["main_height"], p["main_height"] + p["bump_height"]))
            else:
                edges.append((p["main_height"], p["main_height"]))

        # 计算相邻段边界跳跃之和
        if n > 1:
            score = sum(abs(edges[i][1] - edges[i + 1][0]) for i in range(n - 1))
        else:
            score = 0

        if score < best_score:
            best_score = score
            best_choices = list(combo)

    return best_choices


def setup_chinese_font():
    import matplotlib.font_manager as fm
    return fm.FontProperties(fname=FONT_PATH)


def render_side_view(result: PackingResult, container: str, placements=None):
    """侧视图

    Args:
        result: 装箱结果
        container: 柜型名称
        placements: 尾层位置列表，["front", "back", "none"]，长度与 segments 相同
    """
    if placements is None:
        placements = choose_bump_placements(result.segments)

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
        placement = placements[i - 1] if i <= len(placements) else "none"
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
            box_length = dim_along_L(product, seg.orientation)

            # 满层：逐 row 绘制
            for layer_idx in range(full_layers):
                y_pos = layer_idx * layer_height
                for row_idx in range(seg.rows):
                    ax.add_patch(Rectangle((current_x + row_idx * box_length, y_pos), box_length, layer_height,
                                           edgecolor='black', facecolor=color, alpha=0.8))
                    # 添加层数标注在最左侧箱子
                    if row_idx == 0:
                        ax.text(current_x + box_length / 2, y_pos + layer_height / 2,
                                f"{layer_idx + 1}",
                                ha='center', va='center', fontsize=8, color='black', fontweight='bold')


            # 尾层：逐 row 绘制，空 row 留白
            if remainder > 0:
                y_pos = full_layers * layer_height
                bump_length = (tail_full_rows + (1 if tail_last_cols > 0 else 0)) * box_length

                # 计算尾层子块 x 起点
                x_full_start, x_partial_start = bump_subblock_x_starts(
                    placement, current_x, seg.seg_length, bump_length,
                    box_length, tail_full_rows, tail_last_cols
                )

                # 实排（满row）
                for row_idx in range(tail_full_rows):
                    ax.add_patch(Rectangle((x_full_start + row_idx * box_length, y_pos), box_length, layer_height,
                                           edgecolor='black', facecolor=color, alpha=0.8))
                    # 添加层数标注在最左侧箱子
                    if row_idx == 0:
                        ax.text(x_full_start + box_length / 2, y_pos + layer_height / 2,
                                f"{full_layers + 1}",
                                ha='center', va='center', fontsize=8, color='black', fontweight='bold')
                # 不满排（浅色）
                if tail_last_cols > 0:
                    ax.add_patch(Rectangle((x_partial_start, y_pos), box_length, layer_height,
                                           edgecolor='black', facecolor=color, alpha=0.4, linestyle='--', linewidth=1))
                    ax.text(x_partial_start + box_length / 2, y_pos + layer_height / 2,
                            f"{tail_last_cols}/{seg.cols}",
                            ha='center', va='center', fontsize=7, color='#333')
                # 空 row 留白（不画矩形）

        elif seg.type == "shared":
            base_height = 2 * seg.way_base.box_height
            rows_base = seg.rows_base
            rows_5L = seg.rows_5L

            # 底 2 层 base：逐 row 绘制（满层，无尾）
            base_product = PRODUCTS[seg.base_ptype]
            base_box_length = dim_along_L(base_product, seg.way_base.orientation)
            for layer_idx in range(2):
                y_pos = layer_idx * seg.way_base.box_height
                for row_idx in range(rows_base):
                    ax.add_patch(Rectangle((current_x + row_idx * base_box_length, y_pos), base_box_length, seg.way_base.box_height,
                                           edgecolor='black', facecolor=COLORS[seg.base_ptype], alpha=0.8, hatch='//'))
                    # 添加层数标注在最左侧箱子
                    if row_idx == 0:
                        ax.text(current_x + base_box_length / 2, y_pos + seg.way_base.box_height / 2,
                                f"底{layer_idx + 1}",
                                ha='center', va='center', fontsize=8, color='black', fontweight='bold')

            # 5L 层：逐 row 绘制
            fiveL_product = PRODUCTS["5L"]
            fiveL_box_length = dim_along_L(fiveL_product, seg.way_5L.orientation)
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
                    # 添加层数标注在最左侧箱子
                    if row_idx == 0:
                        ax.text(current_x + fiveL_box_length / 2, y_pos + seg.way_5L.box_height / 2,
                                f"5L-{layer_idx + 1}",
                                ha='center', va='center', fontsize=8, color='black', fontweight='bold')


            # 5L 尾层
            if remainder_5L > 0:
                y_pos = base_height + full_layers_5L * seg.way_5L.box_height
                bump_length_5L = (tail_full_rows_5L + (1 if tail_last_cols_5L > 0 else 0)) * fiveL_box_length

                # 计算尾层子块 x 起点（使用 5L 本体长度）
                length_5L = rows_5L * fiveL_box_length
                x_full_start, x_partial_start = bump_subblock_x_starts(
                    placement, current_x, length_5L, bump_length_5L,
                    fiveL_box_length, tail_full_rows_5L, tail_last_cols_5L
                )

                # 实排
                for row_idx in range(tail_full_rows_5L):
                    ax.add_patch(Rectangle((x_full_start + row_idx * fiveL_box_length, y_pos), fiveL_box_length, seg.way_5L.box_height,
                                           edgecolor='black', facecolor=COLORS["5L"], alpha=0.8))
                    # 添加层数标注在最左侧箱子
                    if row_idx == 0:
                        ax.text(x_full_start + fiveL_box_length / 2, y_pos + seg.way_5L.box_height / 2,
                                f"5L-{full_layers_5L + 1}",
                                ha='center', va='center', fontsize=8, color='black', fontweight='bold')
                # 不满排（浅色）
                if tail_last_cols_5L > 0:
                    ax.add_patch(Rectangle((x_partial_start, y_pos), fiveL_box_length, seg.way_5L.box_height,
                                           edgecolor='black', facecolor=COLORS["5L"], alpha=0.4, linestyle='--', linewidth=1))
                    ax.text(x_partial_start + fiveL_box_length / 2, y_pos + seg.way_5L.box_height / 2,
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

        prev_seg_height = seg.total_height
        current_x += seg.seg_length

    # 柜门方向标识
    ax.arrow(container_L + 2, container_H / 2, 8, 0,
             head_width=3, head_length=5, fc='#666', ec='#666', lw=1.5)
    ax.text(container_L + 12, container_H / 2, '🚪柜门',
            ha='left', va='center', fontsize=10, color='#666', fontproperties=font_prop)

    ax.set_xlim(0, container_L)
    ax.set_ylim(0, container_H + 10)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel("柜长 (cm)", fontproperties=font_prop)
    ax.set_ylabel("柜高 (cm)", fontproperties=font_prop)
    ax.set_title(f"侧视图 - 长度利用率: {result.utilization:.1%}, 最大高度差: {result.height_variance:.1f}cm",
                 fontproperties=font_prop)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def render_top_view(result: PackingResult, container: str, placements=None):
    """俯视图

    Args:
        result: 装箱结果
        container: 柜型名称
        placements: 尾层位置列表，["front", "back", "none"]，长度与 segments 相同
    """
    if placements is None:
        placements = choose_bump_placements(result.segments)

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

        for i, seg in enumerate(result.segments):
            placement = placements[i] if i < len(placements) else "none"
            color = COLORS.get(seg.ptype or seg.base_ptype, "gray")

            if seg.type == "pure":
                product = PRODUCTS[seg.ptype]
                box_length = dim_along_L(product, seg.orientation)
                box_width = dim_along_W(product, seg.orientation)
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
                    bump_length = (tail_full_rows + (1 if tail_last_cols > 0 else 0)) * box_length

                    # 计算尾层子块 x 起点
                    x_full_start, x_partial_start = bump_subblock_x_starts(
                        placement, current_x, seg.seg_length, bump_length,
                        box_length, tail_full_rows, tail_last_cols
                    )

                    for row in range(tail_full_rows):
                        for col in range(seg.cols):
                            ax.add_patch(Rectangle((x_full_start + row * box_length, col * box_width),
                                                   box_length, box_width, edgecolor='black', facecolor=color, alpha=0.8))
                    if tail_last_cols > 0:
                        for col in range(tail_last_cols):
                            ax.add_patch(Rectangle((x_partial_start, col * box_width),
                                                   box_length, box_width, edgecolor='black', facecolor=color, alpha=0.6, linestyle='--'))

            elif seg.type == "shared":
                base_product = PRODUCTS[seg.base_ptype]
                fiveL_product = PRODUCTS["5L"]

                rows_base = seg.rows_base
                rows_5L = seg.rows_5L

                if layer_idx < 2:
                    base_box_length = dim_along_L(base_product, seg.way_base.orientation)
                    base_box_width = dim_along_W(base_product, seg.way_base.orientation)
                    for row in range(rows_base):
                        for col in range(seg.way_base.cols):
                            ax.add_patch(Rectangle((current_x + row * base_box_length, col * base_box_width),
                                                   base_box_length, base_box_width,
                                                   edgecolor='black', facecolor=COLORS[seg.base_ptype], alpha=0.8, hatch='//'))
                elif 2 <= layer_idx < 2 + seg.layers_5L:
                    fiveL_box_length = dim_along_L(fiveL_product, seg.way_5L.orientation)
                    fiveL_box_width = dim_along_W(fiveL_product, seg.way_5L.orientation)

                    per_layer_5L = rows_5L * seg.way_5L.cols
                    full_layers_5L = seg.qty_5L // per_layer_5L
                    remainder_5L = seg.qty_5L - full_layers_5L * per_layer_5L
                    tail_full_rows_5L = remainder_5L // seg.way_5L.cols
                    tail_last_cols_5L = remainder_5L - tail_full_rows_5L * seg.way_5L.cols

                    relative_layer = layer_idx - 2
                    if relative_layer < full_layers_5L:
                        for row in range(rows_5L):
                            for col in range(seg.way_5L.cols):
                                ax.add_patch(Rectangle((current_x + row * fiveL_box_length, col * fiveL_box_width),
                                                       fiveL_box_length, fiveL_box_width,
                                                       edgecolor='black', facecolor=COLORS["5L"], alpha=0.8))
                    elif relative_layer == full_layers_5L and remainder_5L > 0:
                        bump_length_5L = (tail_full_rows_5L + (1 if tail_last_cols_5L > 0 else 0)) * fiveL_box_length

                        # 计算尾层子块 x 起点（使用 5L 本体长度）
                        length_5L = rows_5L * fiveL_box_length
                        x_full_start, x_partial_start = bump_subblock_x_starts(
                            placement, current_x, length_5L, bump_length_5L,
                            fiveL_box_length, tail_full_rows_5L, tail_last_cols_5L
                        )

                        for row in range(tail_full_rows_5L):
                            for col in range(seg.way_5L.cols):
                                ax.add_patch(Rectangle((x_full_start + row * fiveL_box_length, col * fiveL_box_width),
                                                       fiveL_box_length, fiveL_box_width,
                                                       edgecolor='black', facecolor=COLORS["5L"], alpha=0.8))
                        if tail_last_cols_5L > 0:
                            for col in range(tail_last_cols_5L):
                                ax.add_patch(Rectangle((x_partial_start, col * fiveL_box_width),
                                                       fiveL_box_length, fiveL_box_width,
                                                       edgecolor='black', facecolor=COLORS["5L"], alpha=0.6, linestyle='--'))

            current_x += seg.seg_length

        ax.set_xlim(0, container_L)
        ax.set_ylim(0, container_W)
        ax.set_aspect('equal', adjustable='box')
        ax.set_xlabel("柜长 (cm)", fontproperties=font_prop)
        ax.set_ylabel("柜宽 (cm)", fontproperties=font_prop)
        ax.set_title(f"第 {layer_idx + 1} 层", fontproperties=font_prop)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def render_3d_view(result: PackingResult, container: str, placements=None):
    """3D视图

    Args:
        result: 装箱结果
        container: 柜型名称
        placements: 尾层位置列表，["front", "back", "none"]，长度与 segments 相同
    """
    if placements is None:
        placements = choose_bump_placements(result.segments)

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

    # 辅助函数：绘制长方体
    def add_box(x: float, y: float, z: float, dx: float, dy: float, dz: float, color: str, hovertext: str, opacity=0.85):
        fig.add_trace(go.Mesh3d(
            x=[x,    x+dx, x+dx, x,    x,    x+dx, x+dx, x   ],
            y=[y,    y,    y+dy, y+dy, y,    y,    y+dy, y+dy],
            z=[z,    z,    z,    z,    z+dz, z+dz, z+dz, z+dz],
            i=[7, 0, 0, 0, 4, 4, 2, 6, 4, 0, 3, 7],
            j=[3, 4, 1, 2, 5, 6, 5, 5, 0, 1, 2, 2],
            k=[0, 7, 2, 3, 6, 7, 1, 2, 1, 5, 7, 6],
            opacity=opacity,
            color=color,
            hovertext=hovertext,
            showlegend=False
        ))

    x_cursor = 0

    for i, seg in enumerate(result.segments, 1):
        placement = placements[i - 1] if i <= len(placements) else "none"

        if seg.type == "pure":
            # Pure段：拆分满层、尾层满行、尾层零散箱
            product = PRODUCTS[seg.ptype]
            box_length = dim_along_L(product, seg.orientation)
            box_width_along_W = dim_along_W(product, seg.orientation)
            dy = seg.cols * box_width_along_W
            layer_height = seg.total_height / seg.actual_layers
            color = COLORS[seg.ptype]
            per_layer = seg.per_layer
            full_layers = seg.qty // per_layer
            remainder = seg.qty - full_layers * per_layer
            tail_full_rows = remainder // seg.cols
            tail_last_cols = remainder - tail_full_rows * seg.cols

            # ① 满层主体
            if full_layers > 0:
                dz_full = full_layers * layer_height
                add_box(
                    x_cursor, 0, 0, seg.seg_length, dy, dz_full,
                    color,
                    f"{i} · {seg.ptype}<br>满 {full_layers} 层 · {full_layers * per_layer} 箱"
                )

            # ② 尾层满行
            if remainder > 0:
                z_tail = full_layers * layer_height
                bump_length = (tail_full_rows + (1 if tail_last_cols > 0 else 0)) * box_length

                # 计算尾层子块 x 起点
                x_full_start, x_partial_start = bump_subblock_x_starts(
                    placement, x_cursor, seg.seg_length, bump_length,
                    box_length, tail_full_rows, tail_last_cols
                )

                if tail_full_rows > 0:
                    dx_tf = tail_full_rows * box_length
                    add_box(
                        x_full_start, 0, z_tail, dx_tf, dy, layer_height,
                        color,
                        f"{i} 尾层满行 · {tail_full_rows} 排 × {seg.cols} 列"
                    )

                # ③ 尾层零散箱（低透明度）
                if tail_last_cols > 0:
                    dy_partial = tail_last_cols * box_width_along_W
                    add_box(
                        x_partial_start, 0, z_tail, box_length, dy_partial, layer_height,
                        color,
                        f"{i} 尾层零散 · {tail_last_cols}/{seg.cols} 箱",
                        opacity=0.4
                    )

        elif seg.type == "shared":
            # Shared段：base 保持单块，5L 拆分顶层
            # —— Base（2 层始终满，保持单块）——
            base_product = PRODUCTS[seg.base_ptype]
            base_box_width_along_W = dim_along_W(base_product, seg.way_base.orientation)
            base_dy = seg.way_base.cols * base_box_width_along_W
            base_dz = 2 * seg.way_base.box_height
            add_box(
                x_cursor, 0, 0, seg.seg_length, base_dy, base_dz,
                COLORS[seg.base_ptype],
                f"{i}底 · {seg.base_ptype}<br>2 层 · {seg.qty_base} 箱"
            )

            # —— 5L 部分（拆分顶层）——
            fiveL_product = PRODUCTS["5L"]
            fiveL_box_length = dim_along_L(fiveL_product, seg.way_5L.orientation)
            fiveL_box_width_along_W = dim_along_W(fiveL_product, seg.way_5L.orientation)
            fiveL_dy = seg.way_5L.cols * fiveL_box_width_along_W
            fiveL_h = seg.way_5L.box_height
            rows_5L = seg.rows_5L
            per_layer_5L = rows_5L * seg.way_5L.cols
            full_layers_5L = seg.qty_5L // per_layer_5L
            remainder_5L = seg.qty_5L - full_layers_5L * per_layer_5L
            tail_full_rows_5L = remainder_5L // seg.way_5L.cols
            tail_last_cols_5L = remainder_5L - tail_full_rows_5L * seg.way_5L.cols

            # ① 5L 满层主体
            if full_layers_5L > 0:
                dx_5L_full = rows_5L * seg.way_5L.row_length
                dz_5L_full = full_layers_5L * fiveL_h
                add_box(
                    x_cursor, 0, base_dz, dx_5L_full, fiveL_dy, dz_5L_full,
                    COLORS["5L"],
                    f"{i}顶 · 5L<br>满 {full_layers_5L} 层 · {full_layers_5L * per_layer_5L} 箱"
                )

            # ② 5L 尾层满行
            if remainder_5L > 0:
                z_tail_5L = base_dz + full_layers_5L * fiveL_h
                bump_length_5L = (tail_full_rows_5L + (1 if tail_last_cols_5L > 0 else 0)) * fiveL_box_length

                # 计算尾层子块 x 起点（使用 5L 本体长度）
                length_5L = rows_5L * fiveL_box_length
                x_full_start, x_partial_start = bump_subblock_x_starts(
                    placement, x_cursor, length_5L, bump_length_5L,
                    fiveL_box_length, tail_full_rows_5L, tail_last_cols_5L
                )

                if tail_full_rows_5L > 0:
                    dx_tf_5L = tail_full_rows_5L * fiveL_box_length
                    add_box(
                        x_full_start, 0, z_tail_5L, dx_tf_5L, fiveL_dy, fiveL_h,
                        COLORS["5L"],
                        f"{i}顶 · 5L 尾层满行 · {tail_full_rows_5L} 排 × {seg.way_5L.cols} 列"
                    )

                # ③ 5L 尾层零散箱（低透明度）
                if tail_last_cols_5L > 0:
                    dy_partial_5L = tail_last_cols_5L * fiveL_box_width_along_W
                    add_box(
                        x_partial_start, 0, z_tail_5L, fiveL_box_length, dy_partial_5L, fiveL_h,
                        COLORS["5L"],
                        f"{i}顶 · 5L 尾层零散 · {tail_last_cols_5L}/{seg.way_5L.cols} 箱",
                        opacity=0.4
                    )

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
            text=f"3D 视图 - 长度利用率: {result.utilization:.1%}, 最大高度差: {result.height_variance:.1f}cm",
            x=0.5, xanchor="center",
            font=dict(size=14)
        ),
    )
    return fig


def generate_worker_guide(result: PackingResult, container: str) -> str:
    """生成操作指南（从里到外、按连续相同层数的排分组）"""
    container_spec = CONTAINERS[container]
    lines = [
        "==== 装柜操作指南 ====",
        f"柜型：{container}（{container_spec['length']}×{container_spec['width']}×{container_spec['height']} cm）",
        f"长度利用率：{result.utilization * 100:.1f}%    最大高度差：{result.height_variance:.1f} cm",
        "装货方向：从柜子最里面（柜壁）开始，一排一排往柜门方向装；高的排靠柜壁。",
        "",
    ]

    for i, seg in enumerate(result.segments, 1):
        if seg.type == "pure":
            per_layer = seg.per_layer
            full_layers = seg.qty // per_layer
            remainder = seg.qty - full_layers * per_layer
            tail_full_rows = remainder // seg.cols
            tail_last_cols = remainder - tail_full_rows * seg.cols
            normal_rows = seg.rows - tail_full_rows - (1 if tail_last_cols > 0 else 0)
            facing = "宽面朝柜门（正向）" if seg.orientation == "normal" else "长面朝柜门（旋转）"

            lines.append(f"── 第 {i} 区：{seg.ptype}（{facing}）──")
            lines.append(f"  每排横向放 {seg.cols} 列，从最里往柜门方向：")
            step = 1
            if tail_full_rows > 0:  # 高排（顶上多一满层）放最里
                lines.append(f"  {step}）最里 {tail_full_rows} 排：每排叠 {full_layers + 1} 层"
                             f"（{tail_full_rows * seg.cols * (full_layers + 1)} 箱）")
                step += 1
            if normal_rows > 0:
                lines.append(f"  {step}）接着 {normal_rows} 排：每排叠 {full_layers} 层"
                             f"（{normal_rows * seg.cols * full_layers} 箱）")
                step += 1
            if tail_last_cols > 0:  # 不足一层的零散箱
                lines.append(f"  {step}）最后 1 排：叠 {full_layers} 层后，顶上再放 {tail_last_cols} 箱"
                             f"（不足一层，靠柜壁集中码放）")
                step += 1
            lines.append(f"  小计：{seg.rows} 排，{seg.qty} 箱")
            lines.append("")

        elif seg.type == "shared":
            facing_base = "宽面朝柜门（正向）" if seg.way_base.orientation == "normal" else "长面朝柜门（旋转）"
            facing_5L = "宽面朝柜门（正向）" if seg.way_5L.orientation == "normal" else "长面朝柜门（旋转）"
            lines.append(f"── 第 {i} 区：{seg.base_ptype} + 5L 混装 ──")
            lines.append(f"  ① 先铺底垫 {seg.base_ptype}（{facing_base}）："
                         f"{seg.rows_base} 排 × {seg.way_base.cols} 列，叠 2 层，共 {seg.qty_base} 箱")
            lines.append(f"  ② 再在底垫上叠 5L（{facing_5L}）："
                         f"{seg.rows_5L} 排 × {seg.way_5L.cols} 列，叠 {seg.layers_5L} 层，共 {seg.qty_5L} 箱")
            lines.append(f"  小计：本区 {seg.qty_base + seg.qty_5L} 箱")
            lines.append("")

    lines.extend([
        "==== 注意 ====",
        "- 不斜放、不超层数、不改变箱子竖直高度",
        "- 高的排靠柜壁（最里），矮的排靠柜门，避免前后高低错落",
        "- 不足一层的零散箱集中靠柜壁码放",
        "- 混装区：先铺满底垫，再往上叠 5L",
    ])

    return "\n".join(lines)