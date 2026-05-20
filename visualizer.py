"""
简洁版装箱可视化
基于算法数据结构，提供最直观的展示
"""

import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import base64
from io import BytesIO
from config import CONTAINERS, PRODUCTS, COLORS, get_position_name

# 配置字体 - 支持中文显示（兼容 Windows 和 Linux）
# Windows: SimHei, Microsoft YaHei
# Linux: WenQuanYi Micro Hei, WenQuanYi Zen Hei, Noto Sans CJK
plt.rcParams['font.sans-serif'] = [
    'WenQuanYi Micro Hei',  # Linux 常用中文字体
    'WenQuanYi Zen Hei',    # Linux 常用中文字体
    'Noto Sans CJK SC',     # Google 开源中文字体
    'Droid Sans Fallback',  # Android/Linux 备选字体
    'SimHei',               # Windows 黑体
    'Microsoft YaHei',      # Windows 微软雅黑
    'DejaVu Sans',
    'Arial'
]
plt.rcParams['axes.unicode_minus'] = False


def generate_top_view_overall(solution, container_type):
    """
    生成整体俯视图（长度×宽度）
    显示所有段在柜子中的实际位置和箱子布局
    """
    import matplotlib
    matplotlib.use('Agg')

    container = CONTAINERS[container_type]
    segments = sorted(solution["segments"], key=lambda x: x["position"])

    fig, ax = plt.subplots(figsize=(14, 6))

    # 绘制柜子轮廓
    ax.add_patch(Rectangle(
        (0, 0), container["length"], container["width"],
        linewidth=3, edgecolor='black', facecolor='none'
    ))

    current_x = 0
    for seg in segments:
        if seg["total_boxes"] == 0:
            current_x += seg["actual_length"]
            continue

        product_name = seg["name"]
        color = COLORS.get(product_name, "#DDA0DD")
        product = PRODUCTS[product_name]

        # 获取段信息
        is_vertical_mixed = "segment_details" in seg and seg["segment_details"]
        top_product_name = None  # 初始化

        if is_vertical_mixed:
            # 垂直混合段：使用最上层信息进行绘制
            top_layer = None
            for detail in reversed(seg["segment_details"]):
                if detail["total_boxes"] > 0:
                    top_layer = detail
                    break
            if top_layer is None:
                top_layer = seg["segment_details"][-1]

            # 使用最上层的产品尺寸和颜色
            top_product_name = top_layer["product_name"]
            product = PRODUCTS[top_product_name]
            color = COLORS.get(top_product_name, "#DDA0DD")

            rows = top_layer["rows"]
            cols = top_layer["cols"]
            direction = top_layer["direction"]
            boxes_to_draw = top_layer["total_boxes"]
            mixed_layout = top_layer.get("mixed_layout")
        else:
            rows = seg["rows"]
            cols = seg["cols"]
            direction = seg["direction"]
            boxes_to_draw = seg["total_boxes"]
            mixed_layout = seg.get("mixed_layout")

        box_l = product["length"]
        box_w = product["width"]

        # 判断是否为混合方向
        is_mixed_direction = "混合" in direction and mixed_layout is not None

        # 计算该段的实际占用空间
        if is_mixed_direction and "row_directions" in mixed_layout:
            row_directions = mixed_layout["row_directions"]
            max_y_width = 0
            for row_dir in row_directions:
                if row_dir == 1:  # 长×宽：Y轴是宽
                    max_y_width = max(max_y_width, cols * box_w)
                else:  # 宽×长：Y轴是长
                    max_y_width = max(max_y_width, cols * box_l)
            actual_y_width = max_y_width
        else:
            box_length_y = box_w if "长×宽" in direction else box_l
            actual_y_width = cols * box_length_y

        # 绘制段的背景区域
        seg_y_start = (container["width"] - actual_y_width) / 2
        seg_rect = Rectangle(
            (current_x, seg_y_start),
            seg["actual_length"],
            actual_y_width,
            linewidth=2,
            edgecolor='gray',
            facecolor=color,
            alpha=0.3
        )
        ax.add_patch(seg_rect)

        # 绘制箱子
        drawn_boxes = 0
        current_y = seg_y_start

        for i in range(int(rows)):
            if drawn_boxes >= boxes_to_draw:
                break

            # 确定当前行的方向
            if is_mixed_direction and "row_directions" in mixed_layout:
                row_dir = mixed_layout["row_directions"][i] if i < len(mixed_layout["row_directions"]) else 1
                box_length_x = box_l if row_dir == 1 else box_w  # 1=长×宽（X轴是长）, 2=宽×长（X轴是宽）
                box_length_y = box_w if row_dir == 1 else box_l
                # 根据方向使用对应的列数
                if "cols_per_direction" in mixed_layout and row_dir in mixed_layout["cols_per_direction"]:
                    current_cols = mixed_layout["cols_per_direction"][row_dir]
                else:
                    current_cols = cols
            else:
                box_length_x = box_l if "长×宽" in direction else box_w
                box_length_y = box_w if "长×宽" in direction else box_l
                row_dir = 1 if "长×宽" in direction else 2
                # 非混合方向：根据方向计算列数
                if "长×宽" in direction:
                    current_cols = int(container["width"] / box_w)  # 宽沿柜子宽方向
                else:
                    current_cols = int(container["width"] / box_l)  # 长沿柜子宽方向

            # 绘制当前行的箱子
            for j in range(int(current_cols)):
                if drawn_boxes >= boxes_to_draw:
                    break

                box_idx = drawn_boxes + 1
                x = current_x + j * box_length_x
                y = current_y

                # 边界检查：确保箱子在柜子范围内
                if x < 0 or y < 0 or x + box_length_x > container["length"] or y + box_length_y > container["width"]:
                    print(f"警告: 箱子{box_idx}越界 - x:{x}, y:{y}, 长:{box_length_x}, 宽:{box_length_y}")
                    continue

                rect = Rectangle(
                    (x, y), box_length_x, box_length_y,
                    linewidth=1.5, edgecolor='black', facecolor=color, alpha=0.8
                )
                ax.add_patch(rect)

                # 箱子编号（小字体）
                font_size = max(6, min(8, min(box_length_x, box_length_y) / 4))
                if font_size >= 6:
                    ax.text(x + box_length_x/2, y + box_length_y/2,
                           str(box_idx),
                           ha='center', va='center',
                           fontsize=font_size,
                           color='white' if color in ['#0000FF', '#800080', '#008000'] else 'black')

                # 箱子朝向指示（小箭头）
                arrow_size = min(box_length_x, box_length_y) * 0.3
                arrow_x = x + box_length_x - arrow_size
                arrow_y = y + box_length_y - arrow_size

                if row_dir == 1:  # 长×宽（红色）
                    ax.arrow(arrow_x - arrow_size * 0.3, arrow_y,
                            arrow_size * 0.6, 0,
                            head_width=arrow_size * 0.2, head_length=arrow_size * 0.2,
                            fc='red', ec='darkred', linewidth=1.5, alpha=0.7)
                else:  # 宽×长（蓝色）
                    ax.arrow(arrow_x, arrow_y - arrow_size * 0.3,
                            0, arrow_size * 0.6,
                            head_width=arrow_size * 0.2, head_length=arrow_size * 0.2,
                            fc='blue', ec='darkblue', linewidth=1.5, alpha=0.7)

                drawn_boxes += 1

            current_y += box_length_y

        # 段内信息
        center_x = current_x + seg["actual_length"] / 2
        center_y = seg_y_start + actual_y_width / 2

        # 货品名称（对于垂直混合段，显示最上层的产品名称）
        display_product_name = top_product_name if is_vertical_mixed else product_name
        ax.text(center_x, center_y + actual_y_width * 0.25,
               display_product_name,
               ha='center', va='center',
               fontsize=11, fontweight='bold')

        # 箱数和方向（优化显示）
        display_direction = direction
        if "前1后2" in direction:
            display_direction = "长×宽→宽×长"
        elif "前2后1" in direction:
            display_direction = "宽×长→长×宽"
        elif "隔行" in direction:
            display_direction = direction.replace("混合(隔行", "隔行(")

        # 对于垂直混合段，显示总箱数和最上层箱数
        if is_vertical_mixed:
            box_text = f"{seg['total_boxes']}箱 (上层{boxes_to_draw}箱)"
        else:
            box_text = f"{seg['total_boxes']}箱"

        ax.text(center_x, center_y,
               f"{box_text}\n{display_direction}",
               ha='center', va='center',
               fontsize=9)

        # 尺寸标注
        ax.text(center_x, center_y - actual_y_width * 0.25,
               f"{seg['actual_length']:.1f}cm",
               ha='center', va='center',
               fontsize=8)

        current_x += seg["actual_length"]

    # 设置坐标轴
    ax.set_xlim(-30, container["length"] + 30)
    ax.set_ylim(-30, container["width"] + 30)
    ax.set_xlabel('Length (cm)', fontsize=12)
    ax.set_ylabel('Width (cm)', fontsize=12)
    ax.set_title(f'{container_type} - Top View', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')

    # 转换为 BytesIO 对象
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)

    return buf



def generate_side_view(solution, container_type):
    """
    生成侧视图（最简洁：长度×高度）
    清楚展示每段的位置、高度、货品，以及每个箱子的轮廓
    """
    import matplotlib
    matplotlib.use('Agg')

    container = CONTAINERS[container_type]
    segments = sorted(solution["segments"], key=lambda x: x["position"])

    fig, ax = plt.subplots(figsize=(14, 4))

    current_x = 0
    for seg in segments:
        if seg["total_boxes"] == 0:
            current_x += seg["actual_length"]
            continue

        product_name = seg["name"]
        color = COLORS.get(product_name, "#DDA0DD")
        product = PRODUCTS[product_name]
        box_l = product["length"]
        box_w = product["width"]
        box_h = product["height"]

        # 获取段的布局信息
        is_vertical_mixed = "segment_details" in seg and seg["segment_details"]

        if is_vertical_mixed:
            # 垂直混合段：使用最上层信息
            top_layer = None
            for detail in reversed(seg["segment_details"]):
                if detail["total_boxes"] > 0:
                    top_layer = detail
                    break
            if top_layer is None:
                top_layer = seg["segment_details"][-1]

            rows = top_layer["rows"]
            cols = top_layer["cols"]
            direction = top_layer["direction"]
            boxes_to_draw = top_layer["total_boxes"]
            mixed_layout = top_layer.get("mixed_layout")
            layers = top_layer.get("layers", 1)
        else:
            rows = seg["rows"]
            cols = seg["cols"]
            direction = seg["direction"]
            boxes_to_draw = seg["total_boxes"]
            mixed_layout = seg.get("mixed_layout")
            layers = seg["layers"]

        # 判断是否为混合方向
        is_mixed_direction = "混合" in direction and mixed_layout is not None

        # 绘制箱子的轮廓（侧视图：只显示前面一列箱子）
        drawn_boxes = 0

        for i in range(int(rows)):
            if drawn_boxes >= boxes_to_draw:
                break

            # 确定当前行的方向
            if is_mixed_direction and "row_directions" in mixed_layout:
                row_dir = mixed_layout["row_directions"][i] if i < len(mixed_layout["row_directions"]) else 1
                box_length_x = box_l if row_dir == 1 else box_w  # 1=长×宽, 2=宽×长
            else:
                box_length_x = box_l if "长×宽" in direction else box_w

            # 侧视图：每行只绘制一个箱子（从侧面看）
            box_x = current_x + i * box_length_x

            # 计算箱子的垂直位置（分层堆叠）
            for k in range(int(layers)):
                if drawn_boxes >= boxes_to_draw:
                    break

                box_y = k * box_h

                # 边界检查：确保箱子在柜子范围内
                if box_x < 0 or box_y < 0 or box_x + box_length_x > container["length"] or box_y + box_h > container["height"]:
                    print(f"警告: 侧视图箱子越界 - x:{box_x}, y:{box_y}, 长:{box_length_x}, 高:{box_h}")
                    continue

                # 绘制单个箱子的轮廓
                rect = Rectangle(
                    (box_x, box_y),
                    box_length_x,
                    box_h,
                    linewidth=1.5,
                    edgecolor='black',
                    facecolor=color,
                    alpha=0.7
                )
                ax.add_patch(rect)

                drawn_boxes += 1

        # 段内信息（绘制在段中间）
        center_x = current_x + seg["actual_length"] / 2
        center_y = seg["height"] / 2

        # 货品名称
        ax.text(center_x, center_y + seg["height"] * 0.15,
               product_name,
               ha='center', va='center',
               fontsize=12, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8, edgecolor='black'))

        # 箱数
        ax.text(center_x, center_y,
               f"{seg['total_boxes']}箱",
               ha='center', va='center',
               fontsize=10,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='black'))

        # 尺寸标注
        ax.text(center_x, center_y - seg["height"] * 0.15,
               f"{seg['actual_length']:.1f}×{seg['height']:.1f}cm",
               ha='center', va='center',
               fontsize=9,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='black'))

        current_x += seg["actual_length"]

    # 柜子轮廓
    ax.add_patch(Rectangle(
        (0, 0), container["length"], container["height"],
        linewidth=3, edgecolor='black', facecolor='none'
    ))

    # 设置坐标轴
    ax.set_xlim(-50, container["length"] + 50)
    ax.set_ylim(-50, container["height"] + 50)
    ax.set_xlabel('Length (cm)', fontsize=12)
    ax.set_ylabel('Height (cm)', fontsize=12)
    ax.set_title(f'{container_type} - Side View', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')

    # 转换为Base64
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)

    return buf


def generate_top_view_segment(seg, container_width):
    """
    生成单个段的俯视图
    只展示箱子布局，简洁明了
    支持混合方向的展示
    """
    import matplotlib
    matplotlib.use('Agg')

    # 检查是否为垂直混合段
    is_vertical_mixed = "segment_details" in seg and seg["segment_details"]

    if is_vertical_mixed:
        # 垂直混合段：显示最上层
        top_layer = None
        for detail in reversed(seg["segment_details"]):
            if detail["total_boxes"] > 0:
                top_layer = detail
                break
        if top_layer is None:
            top_layer = seg["segment_details"][-1]

        product_name = top_layer["product_name"]
        rows = top_layer["rows"]
        cols = top_layer["cols"]
        direction = top_layer["direction"]
        boxes_to_draw = top_layer["total_boxes"]
        mixed_layout = top_layer.get("mixed_layout")
    else:
        product_name = seg["name"]
        rows = seg["rows"]
        cols = seg["cols"]
        direction = seg["direction"]
        boxes_to_draw = seg["total_boxes"]
        mixed_layout = seg.get("mixed_layout")

    product = PRODUCTS[product_name]
    box_l = product["length"]
    box_w = product["width"]
    color = COLORS.get(product_name, "#DDA0DD")

    # 判断是否为混合方向
    is_mixed_direction = "混合" in direction and mixed_layout is not None

    # 计算最大宽度（确保图能够容纳）- 横向显示
    if is_mixed_direction and "row_directions" in mixed_layout:
        # 混合方向：需要计算实际占用的最大宽度
        row_directions = mixed_layout["row_directions"]
        max_x_width = 0
        max_y_width = 0
        for row_dir in row_directions:
            if row_dir == 1:  # 长×宽：X轴是长，Y轴是宽
                max_x_width = max(max_x_width, cols * box_l)
                max_y_width = max(max_y_width, cols * box_w)
            else:  # 宽×长：X轴是宽，Y轴是长
                max_x_width = max(max_x_width, cols * box_w)
                max_y_width = max(max_y_width, cols * box_l)
        actual_width = max_x_width
        actual_height = rows * max(box_l, box_w)
    else:
        # 单一方向
        box_length_x = box_l if "长×宽" in direction else box_w
        box_length_y = box_w if "长×宽" in direction else box_l
        actual_width = cols * box_length_x
        actual_height = rows * box_length_y

    # 交换宽度和高度，使图横向显示
    actual_width, actual_height = actual_height, actual_width

    # 计算边距（确保标注和箭头不超出边界）
    box_length_max = max(box_l, box_w)
    margin_left = box_length_max * 2
    margin_right = box_length_max * 1
    margin_bottom = box_length_max * 4
    margin_top = box_length_max * 1

    # 绘图 - 横向显示
    fig_width = max(6, (actual_width + margin_left + margin_right) / 30)
    fig_height = max(4, (actual_height + margin_bottom + margin_top) / 30)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # 绘制箱子（只绘制实际摆放的箱子）- 横向布局
    drawn_boxes = 0
    current_x = 0

    for i in range(int(rows)):
        if drawn_boxes >= boxes_to_draw:
            break

        # 确定当前行的方向
        if is_mixed_direction and "row_directions" in mixed_layout:
            row_dir = mixed_layout["row_directions"][i] if i < len(mixed_layout["row_directions"]) else 1
            box_length_x = box_w if row_dir == 2 else box_l  # 2=宽×长, 1=长×宽
            box_length_y = box_l if row_dir == 2 else box_w
        else:
            box_length_x = box_l if "长×宽" in direction else box_w
            box_length_y = box_w if "长×宽" in direction else box_l
            row_dir = 1 if "长×宽" in direction else 2

        # 绘制当前行的箱子 - 横向排列
        for j in range(int(cols)):
            if drawn_boxes >= boxes_to_draw:
                break

            box_idx = drawn_boxes + 1
            # 横向布局：x方向是原来的y，y方向是原来的x
            y = j * box_length_y
            x = current_x

            # 边界检查：确保箱子在绘制范围内
            if x < 0 or y < 0 or x + box_length_x > actual_width or y + box_length_y > actual_height:
                print(f"警告: 段视图箱子{box_idx}超出绘制范围 - x:{x}, y:{y}")
                continue

            rect = Rectangle(
                (x, y), box_length_x, box_length_y,
                linewidth=1.5, edgecolor='black', facecolor=color, alpha=0.85
            )
            ax.add_patch(rect)

            # 箱子编号（自适应字体大小）
            font_size = max(8, min(14, min(box_length_x, box_length_y) / 3))
            ax.text(x + box_length_x/2, y + box_length_y/2,
                   str(box_idx),
                   ha='center', va='center',
                   fontsize=font_size, fontweight='bold',
                   color='white' if color in ['#0000FF', '#800080', '#008000'] else 'black')

            # 箱子朝向指示（在箱子右上角画一个大箭头）- 横向布局
            arrow_size = min(box_length_x, box_length_y) * 0.35
            arrow_x = x + box_length_x - arrow_size
            arrow_y = y + box_length_y - arrow_size

            # 使用不同颜色区分两种方向
            if row_dir == 1:  # 长×宽：长边沿X轴（用红色）
                ax.arrow(arrow_x - arrow_size * 0.3, arrow_y,
                        arrow_size * 0.6, 0,
                        head_width=arrow_size * 0.25, head_length=arrow_size * 0.25,
                        fc='red', ec='darkred', linewidth=2.5, alpha=0.8)
            else:  # 宽×长：长边沿Y轴（用蓝色）
                ax.arrow(arrow_x, arrow_y - arrow_size * 0.3,
                        0, arrow_size * 0.6,
                        head_width=arrow_size * 0.25, head_length=arrow_size * 0.25,
                        fc='blue', ec='darkblue', linewidth=2.5, alpha=0.8)

            drawn_boxes += 1

        # 移动到下一行 - 横向布局
        current_x += box_length_x

    # 绘制柜子边界 - 横向显示
    container_rect = Rectangle(
        (0, 0), actual_width, actual_height,
        linewidth=2, edgecolor='gray', facecolor='none', linestyle='--', alpha=0.5
    )
    ax.add_patch(container_rect)

    # 起始位置标注（带边框）
    start_x = box_length_max / 2
    start_y = -box_length_max * 1.5
    ax.annotate("▶️ Start Position",
                xy=(start_x, start_y),
                xytext=(start_x, start_y),
                fontsize=11, fontweight='bold', color='black',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.9, edgecolor='green'),
                ha='left', va='top')

    # 方向标注
    if is_mixed_direction:
        # 混合方向：显示标注说明（优化显示）
        display_direction = direction
        if "前1后2" in direction:
            display_direction = "混合：长×宽 → 宽×长"
        elif "前2后1" in direction:
            display_direction = "混合：宽×长 → 长×宽"
        elif "隔行" in direction:
            display_direction = direction.replace("混合(隔行", "混合：隔行(")

        ax.text(
            actual_width / 2, -box_length_max * 0.8,
            display_direction,
            ha='center', va='top', fontsize=10, fontweight='bold', color='red',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='red')
        )
    elif "长×宽" in direction or "宽×长" in direction:
        arrow_start_x = 0
        arrow_y = -box_length_max * 0.8
        arrow_length = min(actual_width * 0.5, box_length_max * 3)

        ax.arrow(arrow_start_x, arrow_y, arrow_length, 0,
                head_width=box_length_max*0.4, head_length=box_length_max*0.4,
                fc='red', ec='red', linewidth=2)
        ax.text(arrow_length/2, arrow_y + box_length_max*0.6,
               f"→ {direction}",
               ha='center', va='bottom', fontsize=10, fontweight='bold', color='red',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='red'))

    # 设置图形范围 - 横向显示
    ax.set_xlim(-margin_left, actual_width + margin_right)
    ax.set_ylim(-margin_bottom, actual_height + margin_top)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlabel('Length Direction (cm)', fontsize=10)
    ax.set_ylabel('Width Direction (cm)', fontsize=10)
    ax.set_title(f"{product_name} - Layout (Actual: {boxes_to_draw} boxes, {direction})", fontsize=12, fontweight='bold')

    # 添加朝向图例说明
    legend_text = "🔴 Red: Long edge along length (L×W)\n🔵 Blue: Long edge along width (W×L)"
    ax.text(
        actual_width - box_length_max * 3, -box_length_max * 3,
        legend_text,
        fontsize=10, fontweight='bold',
        ha='right', va='top',
        bbox=dict(boxstyle='round,pad=0.8', facecolor='lightyellow', alpha=0.95, edgecolor='orange', linewidth=2)
    )

    # 转换为 BytesIO 对象
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)

    return buf


def generate_summary_table(solution):
    """
    生成简洁的汇总表
    直接返回HTML，无需绘图
    """
    segments = sorted(solution["segments"], key=lambda x: x["position"])

    html = """
    <table style="width:100%; border-collapse: collapse; font-size: 14px;">
        <thead>
            <tr style="background-color: #4CAF50; color: white;">
                <th style="border: 1px solid #ddd; padding: 8px;">位置</th>
                <th style="border: 1px solid #ddd; padding: 8px;">货品</th>
                <th style="border: 1px solid #ddd; padding: 8px;">箱数</th>
                <th style="border: 1px solid #ddd; padding: 8px;">层数</th>
                <th style="border: 1px solid #ddd; padding: 8px;">长度(cm)</th>
                <th style="border: 1px solid #ddd; padding: 8px;">高度(cm)</th>
                <th style="border: 1px solid #ddd; padding: 8px;">摆放</th>
            </tr>
        </thead>
        <tbody>
    """

    current_pos = 0
    for seg in segments:
        position_name = get_position_name(seg["position"])

        # 摆放信息
        if "segment_details" in seg and seg["segment_details"]:
            # 垂直混合
            layers_info = ", ".join([
                f"{d['product_name']}×{d['layers']}"
                for d in seg["segment_details"]
                if d["total_boxes"] > 0
            ])
            placement = f"垂直混合（{layers_info}）"
        else:
            display_direction = seg['direction']
            if "混合：长×宽→宽×长" in display_direction:
                display_direction = "混合"
            elif "混合：宽×长→长×宽" in display_direction:
                display_direction = "混合"
            elif "混合：隔行" in display_direction:
                display_direction = "混合"
            placement = f"{seg['rows']}行×{seg['cols']}列（{display_direction}）"

        html += f"""
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{position_name}</td>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{seg['name']}</td>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{seg['total_boxes']}</td>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{seg['layers']}</td>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{seg['actual_length']:.1f}</td>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{seg['height']:.1f}</td>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{placement}</td>
            </tr>
        """
        current_pos += seg["actual_length"]

    html += """
        </tbody>
    </table>
    """

    return html





def display_visualization_simple(solution, container_type):
    """
    简洁版可视化主函数
    在Streamlit中展示所有信息
    """
    st.subheader("📊 方案总览")

    container = CONTAINERS[container_type]

    # 1. 两个视图
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 侧视图（长度×高度）")
        side_img = generate_side_view(solution, container_type)
        st.image(side_img, use_container_width=True)

    with col2:
        st.markdown("### 关键指标")

        total_length = sum(seg["actual_length"] for seg in solution["segments"])
        length_util = (total_length / container["length"]) * 100

        st.metric("总装载箱数", solution["total_loaded"])
        st.metric("长度利用率", f"{length_util:.1f}%")
        st.metric("高度差", f"{solution.get('max_adjacent_height_diff', 0):.1f} cm")
        if "weight_deviation" in solution:
            st.metric("重量中心偏差", f"{solution['weight_deviation']:.1f} cm")

    st.divider()

    # 2. 整体俯视图
    st.markdown("### 整体俯视图（长度×宽度）")
    top_overall_img = generate_top_view_overall(solution, container_type)
    st.image(top_overall_img, use_container_width=True)

    st.divider()





