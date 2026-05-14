"""
可视化模块 - 使用 Plotly 绘制3D装箱方案
优化版本：减少trace数量，调整显示比例
"""

import plotly.graph_objects as go
from config import CONTAINERS, PRODUCTS, COLORS, POSITIONS_MAP


def visualize_loading_plan_3d(solution, container_type):
    """
    3D 可视化装箱方案（优化版）

    参数:
        solution: 装箱方案
        container_type: 柜型

    返回:
        plotly Figure 对象
    """
    container = CONTAINERS[container_type]

    # 创建3D图形
    fig = go.Figure()

    # 绘制柜子轮廓（合并为1个trace）
    _draw_container_wireframe_optimized(fig, container)

    # 绘制所有箱子（合并为少量trace）
    _draw_boxes_optimized(fig, solution, container)

    # 设置图形布局
    # 根据柜子的长宽比调整相机视角
    L, W, H = container["length"], container["width"], container["height"]
    aspect_ratio = L / W

    # 动态调整相机位置
    if aspect_ratio > 3:
        # 狭长柜子（如40尺柜），从侧上方观察
        eye_x = 2.5
        eye_y = 0.6
        eye_z = 0.6
        center_x = 0.4
    elif aspect_ratio > 2:
        # 中等比例（如20尺柜）
        eye_x = 2.0
        eye_y = 0.8
        eye_z = 0.8
        center_x = 0.3
    else:
        # 近似立方体
        eye_x = 1.5
        eye_y = 1.5
        eye_z = 1.5
        center_x = 0.0

    fig.update_layout(
        title=dict(
            text=f"{container_type} 3D 装箱方案",
            font=dict(size=16, family='Arial')
        ),
        scene=dict(
            xaxis=dict(title='长度 (cm)', range=[0, L]),
            yaxis=dict(title='宽度 (cm)', range=[0, W]),
            zaxis=dict(title='高度 (cm)', range=[0, H]),
            aspectmode='data',  # 保持真实比例
            camera=dict(
                eye=dict(x=eye_x, y=eye_y, z=eye_z),
                center=dict(x=center_x, y=0.1, z=0.1)
            )
        ),
        width=1000,
        height=700,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )

    return fig


def _draw_container_wireframe_optimized(fig, container):
    """绘制柜子的线框（优化版：合并为1个trace）"""
    L, W, H = container["length"], container["width"], container["height"]

    # 定义8个顶点
    x = [0, L, L, 0, 0, L, L, 0]
    y = [0, 0, W, W, 0, 0, W, W]
    z = [0, 0, 0, 0, H, H, H, H]

    # 定义12条边
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # 底面
        [4, 5], [5, 6], [6, 7], [7, 4],  # 顶面
        [0, 4], [1, 5], [2, 6], [3, 7]   # 竖边
    ]

    # 收集所有边的坐标（合并到1个trace）
    line_x = []
    line_y = []
    line_z = []

    for edge in edges:
        line_x.extend([x[edge[0]], x[edge[1]], None])
        line_y.extend([y[edge[0]], y[edge[1]], None])
        line_z.extend([z[edge[0]], z[edge[1]], None])

    # 绘制所有边（1个trace）
    fig.add_trace(go.Scatter3d(
        x=line_x,
        y=line_y,
        z=line_z,
        mode='lines',
        line=dict(color='black', width=3),
        name='柜子轮廓',
        showlegend=True,
        hoverinfo='skip'
    ))


def _draw_boxes_optimized(fig, solution, container):
    """绘制箱子（优化版：按产品类型合并trace）"""
    # 按产品类型和方向分组
    boxes_by_type = {}
    box_info_list = []  # 存储每个箱子的信息用于hover

    current_x = 0
    global_box_counter = 0  # 全局箱子计数器

    for segment in sorted(solution["segments"], key=lambda x: x["position"]):
        name = segment["name"]
        height = segment["height"]
        layers = segment["layers"]
        rows = segment["rows"]
        cols = segment["cols"]
        boxes = segment["total_boxes"]

        product = PRODUCTS[name]
        mixed_layout = segment.get("mixed_layout", None)

        rows_int = int(rows) if rows is not None and rows > 0 else 0
        cols_int = int(cols) if cols is not None and cols > 0 else 0

        # 计算每层高度
        layer_height = height / layers

        # 获取行方向列表
        if mixed_layout is not None:
            row_directions = mixed_layout.get("row_directions", [1] * rows_int)
        else:
            # 单一方向
            if segment["direction"] == "长×宽":
                row_directions = [1] * rows_int
            else:
                row_directions = [2] * rows_int

        # 计算实际需要绘制的箱子数量
        boxes_to_draw = min(boxes, rows_int * cols_int * layers)
        segment_box_counter = 0  # 段内箱子计数器

        # 逐层、逐行、逐列收集箱子数据
        for layer in range(layers):
            z = layer * layer_height

            for i, row_dir in enumerate(row_directions):
                if i >= rows_int or segment_box_counter >= boxes_to_draw:
                    break

                # 确定该行的箱子尺寸和颜色
                if row_dir == 1:
                    box_l = product["length"]
                    box_w = product["width"]
                    direction_label = "长×宽"
                else:
                    box_l = product["width"]
                    box_w = product["length"]
                    direction_label = "宽×长"

                # 根据产品类型设置颜色
                base_color = COLORS.get(name, '#DDA0DD')
                # 转换为rgba格式，添加透明度
                if base_color.startswith('#'):
                    # 十六进制转rgb
                    r = int(base_color[1:3], 16)
                    g = int(base_color[3:5], 16)
                    b = int(base_color[5:7], 16)
                    box_color = f'rgba({r}, {g}, {b}, 0.7)'
                    # 边框颜色稍微深一点
                    edge_r = max(0, r - 50)
                    edge_g = max(0, g - 50)
                    edge_b = max(0, b - 50)
                    edge_color = f'rgb({edge_r}, {edge_g}, {edge_b})'
                else:
                    box_color = base_color.replace(')', ', 0.7)').replace('rgb', 'rgba')
                    edge_color = base_color

                for j in range(cols_int):
                    if segment_box_counter >= boxes_to_draw:
                        break

                    # 计算箱子位置
                    x = current_x + i * box_l
                    y = j * box_w

                    # 确定分组键（仅按产品类型分组）
                    key = name

                    if key not in boxes_by_type:
                        boxes_by_type[key] = {
                            'x': [], 'y': [], 'z': [],
                            'color': box_color,
                            'edge_color': edge_color,
                            'name': name,
                            'direction': direction_label,
                            'product': name
                        }

                    # 收集该箱子的顶点坐标
                    box_x = [x, x + box_l, x + box_l, x, x, x + box_l, x + box_l, x]
                    box_y = [y, y, y + box_w, y + box_w, y, y, y + box_w, y + box_w]
                    box_z = [z, z, z, z, z + layer_height, z + layer_height, z + layer_height, z + layer_height]

                    # 定义12条边
                    edges = [
                        [0, 1], [1, 2], [2, 3], [3, 0],  # 底面
                        [4, 5], [5, 6], [6, 7], [7, 4],  # 顶面
                        [0, 4], [1, 5], [2, 6], [3, 7]   # 竖边
                    ]

                    # 将边坐标添加到对应分组
                    for edge in edges:
                        boxes_by_type[key]['x'].extend([box_x[edge[0]], box_x[edge[1]], None])
                        boxes_by_type[key]['y'].extend([box_y[edge[0]], box_y[edge[1]], None])
                        boxes_by_type[key]['z'].extend([box_z[edge[0]], box_z[edge[1]], None])

                    segment_box_counter += 1
                    global_box_counter += 1

        current_x += segment["actual_length"]

    # 为每种类型创建1个trace
    for key, box_data in boxes_by_type.items():
        fig.add_trace(go.Scatter3d(
            x=box_data['x'],
            y=box_data['y'],
            z=box_data['z'],
            mode='lines',
            line=dict(color=box_data['edge_color'], width=1),
            name=box_data['name'],
            showlegend=True,
            hoverinfo='skip'
        ))

