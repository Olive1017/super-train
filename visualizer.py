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
from config import CONTAINERS, PRODUCTS, COLORS, POSITIONS_MAP

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def generate_side_view(solution, container_type):
    """
    生成侧视图（最简洁：长度×高度）
    清楚展示每段的位置、高度、货品
    """
    import matplotlib
    matplotlib.use('Agg')

    container = CONTAINERS[container_type]
    segments = sorted(solution["segments"], key=lambda x: x["position"])

    fig, ax = plt.subplots(figsize=(14, 4))

    current_x = 0
    for seg in segments:
        product_name = seg["name"]
        color = COLORS.get(product_name, "#DDA0DD")

        # 绘制段
        rect = Rectangle(
            (current_x, 0),
            seg["actual_length"],
            seg["height"],
            linewidth=2,
            edgecolor='black',
            facecolor=color,
            alpha=0.8
        )
        ax.add_patch(rect)

        # 段内信息
        center_x = current_x + seg["actual_length"] / 2
        center_y = seg["height"] / 2

        # 货品名称
        ax.text(center_x, center_y + seg["height"] * 0.15,
               product_name,
               ha='center', va='center',
               fontsize=12, fontweight='bold')

        # 箱数
        ax.text(center_x, center_y,
               f"{seg['total_boxes']}箱",
               ha='center', va='center',
               fontsize=10)

        # 尺寸标注
        ax.text(center_x, center_y - seg["height"] * 0.15,
               f"{seg['actual_length']:.1f}×{seg['height']:.1f}cm",
               ha='center', va='center',
               fontsize=9)

        current_x += seg["actual_length"]

    # 柜子轮廓
    ax.add_patch(Rectangle(
        (0, 0), container["length"], container["height"],
        linewidth=2, edgecolor='black', facecolor='none'
    ))

    # 设置坐标轴
    ax.set_xlim(-50, container["length"] + 50)
    ax.set_ylim(-50, container["height"] + 50)
    ax.set_xlabel('长度 (cm)', fontsize=12)
    ax.set_ylabel('高度 (cm)', fontsize=12)
    ax.set_title(f'{container_type} 侧视图', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')

    # 转换为Base64
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    return f"data:image/png;base64,{img_base64}"


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

    # 计算最大宽度（确保图能够容纳）
    if is_mixed_direction and "row_directions" in mixed_layout:
        # 混合方向：需要计算实际占用的最大宽度
        row_directions = mixed_layout["row_directions"]
        max_x_width = 0
        max_y_width = 0
        for row_dir in row_directions:
            if row_dir == 1:  # 长×宽
                max_x_width = max(max_x_width, cols * box_w)
                max_y_width = max(max_y_width, cols * box_l)
            else:  # 宽×长
                max_x_width = max(max_x_width, cols * box_l)
                max_y_width = max(max_y_width, cols * box_w)
        actual_width = max_x_width
        actual_height = rows * max(box_l, box_w)
    else:
        # 单一方向
        box_length_x = box_w if "宽×长" in direction else box_l
        box_length_y = box_l if "宽×长" in direction else box_w
        actual_width = cols * box_length_x
        actual_height = rows * box_length_y

    # 计算边距（确保标注和箭头不超出边界）
    box_length_max = max(box_l, box_w)
    margin_left = box_length_max * 2
    margin_right = box_length_max * 1
    margin_bottom = box_length_max * 4
    margin_top = box_length_max * 1

    # 绘图
    fig_width = max(8, (actual_width + margin_left + margin_right) / 25)
    fig_height = max(6, (actual_height + margin_bottom + margin_top) / 25)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # 绘制箱子（只绘制实际摆放的箱子）
    drawn_boxes = 0
    current_y = 0

    for i in range(int(rows)):
        if drawn_boxes >= boxes_to_draw:
            break

        # 确定当前行的方向
        if is_mixed_direction and "row_directions" in mixed_layout:
            row_dir = mixed_layout["row_directions"][i] if i < len(mixed_layout["row_directions"]) else 1
            box_length_x = box_w if row_dir == 2 else box_l  # 2=宽×长, 1=长×宽
            box_length_y = box_l if row_dir == 2 else box_w
        else:
            box_length_x = box_w if "宽×长" in direction else box_l
            box_length_y = box_l if "宽×长" in direction else box_w
            row_dir = 1 if "长×宽" in direction else 2

        # 绘制当前行的箱子
        for j in range(int(cols)):
            if drawn_boxes >= boxes_to_draw:
                break

            box_idx = drawn_boxes + 1
            x = j * box_length_x
            y = current_y

            rect = Rectangle(
                (x, y), box_length_x, box_length_y,
                linewidth=1.5, edgecolor='black', facecolor=color, alpha=0.8
            )
            ax.add_patch(rect)

            # 箱子编号（自适应字体大小）
            font_size = max(8, min(14, min(box_length_x, box_length_y) / 3))
            ax.text(x + box_length_x/2, y + box_length_y/2,
                   str(box_idx),
                   ha='center', va='center',
                   fontsize=font_size, fontweight='bold',
                   color='white' if color in ['#0000FF', '#800080', '#008000'] else 'black')

            # 箱子朝向指示（在箱子右上角画一个小箭头或符号）
            arrow_size = min(box_length_x, box_length_y) * 0.25
            arrow_x = x + box_length_x - arrow_size
            arrow_y = y + box_length_y - arrow_size

            if row_dir == 1:  # 长×宽：长边沿X轴
                ax.arrow(arrow_x - arrow_size * 0.3, arrow_y,
                        arrow_size * 0.6, 0,
                        head_width=arrow_size * 0.2, head_length=arrow_size * 0.2,
                        fc='black', ec='black', linewidth=1, alpha=0.5)
            else:  # 宽×长：长边沿Y轴
                ax.arrow(arrow_x, arrow_y - arrow_size * 0.3,
                        0, arrow_size * 0.6,
                        head_width=arrow_size * 0.2, head_length=arrow_size * 0.2,
                        fc='black', ec='black', linewidth=1, alpha=0.5)

            drawn_boxes += 1

        # 移动到下一行
        current_y += box_length_y

    # 绘制柜子边界
    container_rect = Rectangle(
        (0, 0), container_width, actual_height,
        linewidth=2, edgecolor='gray', facecolor='none', linestyle='--', alpha=0.5
    )
    ax.add_patch(container_rect)

    # 起始位置标注（带边框）
    start_x = box_length_max / 2
    start_y = -box_length_max * 1.5
    ax.annotate("▶️ 起始位置",
                xy=(start_x, start_y),
                xytext=(start_x, start_y),
                fontsize=11, fontweight='bold', color='black',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.9, edgecolor='green'),
                ha='left', va='top')

    # 方向标注
    if is_mixed_direction:
        # 混合方向：显示标注说明
        direction_text = f"混合方向：{direction}"
        ax.text(
            actual_width / 2, -box_length_max * 0.8,
            direction_text,
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

    # 设置图形范围
    ax.set_xlim(-margin_left, max(actual_width + margin_right, container_width))
    ax.set_ylim(-margin_bottom, actual_height + margin_top)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlabel('宽度 (cm)', fontsize=10)
    ax.set_ylabel('深度 (cm)', fontsize=10)
    ax.set_title(f"{product_name} - 俯视图 (实际摆放{boxes_to_draw}箱, {direction})", fontsize=12, fontweight='bold')

    # 添加朝向图例说明
    legend_text = "箱子右上角箭头：\n→ 长边沿宽度方向 (长×宽)\n↑ 长边沿深度方向 (宽×长)"
    ax.text(
        actual_width - box_length_max * 2, -box_length_max * 2.5,
        legend_text,
        fontsize=8,
        ha='right', va='top',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.9, edgecolor='orange')
    )

    # 转换为Base64
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    return f"data:image/png;base64,{img_base64}"


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
        position_name = POSITIONS_MAP.get(seg["position"], f"段{seg['position']}")

        # 摆放信息
        if "segment_details" in seg and seg["segment_details"]:
            # 垂直混合
            layers_info = ", ".join([
                f"{d['product_name']}×{d['layers']}"
                for d in seg["segment_details"]
                if d["total_boxes"] > 0
            ])
            placement = f"垂直混合({layers_info})"
        else:
            placement = f"{seg['rows']}行×{seg['cols']}列"

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


def generate_worker_steps(solution, container_type):
    """
    生成简洁的工人操作步骤
    按段分步骤，每步包含关键信息
    """
    container = CONTAINERS[container_type]
    segments = sorted(solution["segments"], key=lambda x: x["position"])

    steps = []
    current_pos = 0

    for i, seg in enumerate(segments):
        position_name = POSITIONS_MAP.get(seg["position"], f"段{seg['position']}")

        step = {
            "step_num": i + 1,
            "position": position_name,
            "product": seg["name"],
            "boxes": seg["total_boxes"],
            "start_pos": current_pos,
            "end_pos": current_pos + seg["actual_length"],
            "length": seg["actual_length"],
            "height": seg["height"],
            "layers": seg["layers"],
            "direction": seg["direction"],
            "rows": seg["rows"],
            "cols": seg["cols"],
            "mixed_layout": seg.get("mixed_layout"),
            "is_vertical_mixed": "segment_details" in seg and seg["segment_details"],
            "segment_details": seg.get("segment_details", [])
        }

        steps.append(step)
        current_pos += seg["actual_length"]

    return steps


def display_visualization_simple(solution, container_type):
    """
    简洁版可视化主函数
    在Streamlit中展示所有信息
    """
    st.subheader("📊 方案总览")

    container = CONTAINERS[container_type]

    # 1. 侧视图
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

    # 2. 逐段操作指南
    st.markdown("### 👷 装箱操作步骤")

    steps = generate_worker_steps(solution, container_type)

    for step in steps:
        with st.expander(
            f"步骤 {step['step_num']}: {step['position']} - {step['product']} "
            f"({step['boxes']}箱)",
            expanded=True
        ):
            # 基本信息
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"**起始**: {step['start_pos']:.1f} cm")
                st.markdown(f"**结束**: {step['end_pos']:.1f} cm")

            with col2:
                st.markdown(f"**长度**: {step['length']:.1f} cm")
                st.markdown(f"**高度**: {step['height']:.1f} cm")

            with col3:
                st.markdown(f"**摆放**: {step['rows']}×{step['cols']}")
                st.markdown(f"**层数**: {step['layers']}")

            # 俯视图
            st.markdown("#### 平面图")

            # 垂直混合段：添加层级选择
            if step["is_vertical_mixed"]:
                layers_with_boxes = [d for d in step["segment_details"] if d["total_boxes"] > 0]

                if len(layers_with_boxes) > 1:
                    # 多层：显示选择器
                    layer_options = [
                        f"第 {d['layer_index'] + 1} 层 - {d['product_name']} ({d['total_boxes']}箱)"
                        for d in layers_with_boxes
                    ]
                    selected_layer = st.selectbox(
                        "选择要查看的层：",
                        range(len(layer_options)),
                        format_func=lambda i: layer_options[i],
                        key=f"step_{step['step_num']}_layer_selector"
                    )

                    # 显示选中的层级详情
                    selected_detail = layers_with_boxes[selected_layer]
                    st.info(f"📌 当前查看：{layer_options[selected_layer]}")

                    # 生成该层的俯视图
                    top_img = generate_top_view_segment({
                        "name": selected_detail["product_name"],
                        "rows": selected_detail["rows"],
                        "cols": selected_detail["cols"],
                        "direction": selected_detail["direction"],
                        "total_boxes": selected_detail["total_boxes"],
                        "mixed_layout": selected_detail.get("mixed_layout"),
                        "segment_details": [selected_detail]
                    }, container["width"])
                    st.image(top_img, use_container_width=True)

                    # 显示该层信息
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**摆放方向**: {selected_detail['direction']}")
                        st.markdown(f"**每层箱数**: {selected_detail['total_boxes']}")
                    with col_b:
                        st.markdown(f"**堆叠层数**: {selected_detail['layers']}")
                        st.markdown(f"**该层总箱数**: {selected_detail['total_boxes'] * selected_detail['layers']}")

                    # 显示其他层概览
                    with st.expander("查看其他层级详情", expanded=False):
                        for i, detail in enumerate(step["segment_details"]):
                            if i != selected_layer and detail["total_boxes"] > 0:
                                st.markdown(f"""
                                **第 {detail['layer_index'] + 1} 层（{detail['product_name']}）**:
                                - 摆放方向：{detail['direction']}
                                - 每层 {detail['total_boxes']} 箱，共 {detail['layers']} 层
                                - 该层总箱数：{detail['total_boxes'] * detail['layers']}
                                """)
                else:
                    # 单层：直接显示
                    top_img = generate_top_view_segment({
                        "name": step["product"],
                        "rows": step["rows"],
                        "cols": step["cols"],
                        "direction": step["direction"],
                        "mixed_layout": step["mixed_layout"],
                        "segment_details": step["segment_details"]
                    }, container["width"])
                    st.image(top_img, use_container_width=True)

                    st.info("📌 此段只有一种货品，直接按最上层布局装载")
            else:
                # 普通段：检查是否铺满
                capacity = int(step["rows"]) * int(step["cols"]) * int(step["layers"])
                if step["boxes"] < capacity:
                    st.warning(f"⚠️ 注意：该段容量为 {capacity} 箱，实际只装 {step['boxes']} 箱，最上层未铺满")

                top_img = generate_top_view_segment({
                    "name": step["product"],
                    "rows": step["rows"],
                    "cols": step["cols"],
                    "direction": step["direction"],
                    "total_boxes": step["boxes"],
                    "mixed_layout": step["mixed_layout"]
                }, container["width"])
                st.image(top_img, use_container_width=True)

            # 操作提示
            st.markdown("#### 操作要点")
            st.markdown(f"""
            - ✅ 从 **{step['start_pos']:.1f} cm** 位置开始
            - ✅ 按平面图编号顺序摆放
            - ✅ 逐层堆叠，共 **{step['layers']}** 层
            - ✅ 确保每层平整后再堆叠下一层
            """)

            # 垂直混合段特殊说明
            if step["is_vertical_mixed"]:
                st.warning("⚠️ 此段为垂直混合段，按以下顺序分层装载：")
                for detail in step["segment_details"]:
                    if detail["total_boxes"] > 0:
                        layer_name = detail["product_name"]
                        layer_count = detail["layers"]
                        layer_boxes = detail["total_boxes"]
                        st.markdown(f"""
                        **第 {detail['layer_index'] + 1} 层（{layer_name}）**:
                        - 堆叠 {layer_count} 层
                        - 装 {layer_boxes} 箱
                        - 方向：{detail['direction']}
                        """)

    st.divider()

    # 4. 下载文本指南
    st.markdown("### 📥 下载指南")

    text_guide = generate_text_guide(solution, container_type)
    b64 = base64.b64encode(text_guide.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="装箱指南.txt" ' \
           f'style="color: #4CAF50; text-decoration: none; font-weight: bold; font-size: 16px;">' \
           f'📄 点击下载文本版装箱指南</a>'
    st.markdown(href, unsafe_allow_html=True)


def generate_text_guide(solution, container_type):
    """生成文本版指南"""
    container = CONTAINERS[container_type]
    steps = generate_worker_steps(solution, container_type)

    text = f"""
{'='*60}
装箱操作指南 - {container_type}
{'='*60}

总装载箱数: {solution['total_loaded']}
{'='*60}

"""
    for step in steps:
        text += f"""
步骤 {step['step_num']}: {step['position']} - {step['product']}
{'-'*60}
起始位置: {step['start_pos']:.1f} cm
结束位置: {step['end_pos']:.1f} cm
占用长度: {step['length']:.1f} cm
堆叠高度: {step['height']:.1f} cm ({step['layers']}层)
摆放方式: {step['rows']}行 × {step['cols']}列
总箱数: {step['boxes']}箱

操作要点:
1. 从 {step['start_pos']:.1f} cm 位置开始
2. 按平面图编号顺序摆放
3. 逐层堆叠，共 {step['layers']} 层
4. 确保每层平整后再堆叠下一层
"""
        if step["is_vertical_mixed"]:
            text += "\n垂直混合段装载顺序:\n"
            for detail in step["segment_details"]:
                if detail["total_boxes"] > 0:
                    text += f"  第{detail['layer_index']+1}层: {detail['product_name']}, " \
                           f"{detail['layers']}层, {detail['total_boxes']}箱\n"

    text += f"\n{'='*60}\n安全提示:\n1. 装载前检查柜子内部\n2. 确保货品包装完好\n3. 保持重量平衡\n4. 每层检查平整度\n5. 最后检查顶部空隙\n{'='*60}\n"

    return text
