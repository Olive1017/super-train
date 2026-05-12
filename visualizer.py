"""
可视化模块 - 使用 Plotly 绘制3D装箱方案
"""

import plotly.graph_objects as go
import numpy as np
from config import CONTAINERS, PRODUCTS, COLORS, POSITIONS_MAP


def visualize_loading_plan_3d(solution, container_type):
    """
    3D 可视化装箱方案

    参数:
        solution: 装箱方案
        container_type: 柜型

    返回:
        plotly Figure 对象
    """
    container = CONTAINERS[container_type]

    # 创建3D图形
    fig = go.Figure()

    # 绘制柜子轮廓（透明线框）
    _draw_container_wireframe(fig, container)

    # 绘制所有箱子
    current_x = 0

    for segment in sorted(solution["segments"], key=lambda x: x["position"]):
        name = segment["name"]
        length = segment["actual_length"]
        height = segment["height"]
        width = container["width"]
        rows = segment["rows"]
        cols = segment["cols"]
        layers = segment["layers"]
        boxes = segment["total_boxes"]

        # 绘制段区域的半透明背景
        segment_color = COLORS.get(name, '#DDA0DD')
        fig.add_shape(
            type="mesh3d",
            x=[current_x, current_x + length, current_x + length, current_x,
               current_x, current_x + length, current_x + length, current_x],
            y=[0, 0, width, width, 0, 0, width, width],
            z=[0, 0, 0, 0, height, height, height, height],
            i=[0, 0, 0, 0, 4, 4, 4, 4, 5, 5, 5, 5],
            j=[1, 2, 3, 4, 5, 6, 7, 0, 6, 7, 1, 4],
            k=[2, 3, 4, 7, 6, 7, 0, 3, 7, 1, 4, 0],
            opacity=0.1,
            color=segment_color,
            showlegend=False
        )

        # 绘制箱子
        _draw_boxes(fig, segment, current_x, container)

        current_x += length

    # 设置图形布局
    fig.update_layout(
        title=dict(
            text=f"{container_type} 3D 装箱方案",
            font=dict(size=16, family='Arial')
        ),
        scene=dict(
            xaxis=dict(title='长度 (cm)', range=[0, container["length"]]),
            yaxis=dict(title='宽度 (cm)', range=[0, container["width"]]),
            zaxis=dict(title='高度 (cm)', range=[0, container["height"]]),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)  # 默认视角
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


def _draw_container_wireframe(fig, container):
    """绘制柜子的线框"""
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

    # 绘制每条边
    for edge in edges:
        fig.add_trace(go.Scatter3d(
            x=[x[edge[0]], x[edge[1]]],
            y=[y[edge[0]], y[edge[1]]],
            z=[z[edge[0]], z[edge[1]]],
            mode='lines',
            line=dict(color='black', width=2),
            showlegend=False,
            hoverinfo='skip'
        ))


def _draw_boxes(fig, segment, segment_x, container):
    """绘制箱子"""
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

    # 逐层、逐行、逐列绘制箱子
    box_count = 0
    for layer in range(layers):
        z = layer * layer_height

        for i, row_dir in enumerate(row_directions):
            if i >= rows_int or box_count >= boxes_to_draw:
                break

            # 确定该行的箱子尺寸
            if row_dir == 1:
                box_l = product["length"]
                box_w = product["width"]
                box_color = 'rgba(135, 206, 250, 0.7)'  # 浅蓝色（长×宽）
                edge_color = 'rgb(0, 0, 139)'
                direction_label = "长×宽"
            else:
                box_l = product["width"]
                box_w = product["length"]
                box_color = 'rgba(144, 238, 144, 0.7)'  # 浅绿色（宽×长）
                edge_color = 'rgb(0, 100, 0)'
                direction_label = "宽×长"

            for j in range(cols_int):
                if box_count >= boxes_to_draw:
                    break

                # 计算箱子位置
                x = segment_x + i * box_l
                y = j * box_w

                # 绘制箱子
                _draw_single_box(
                    fig,
                    x=x,
                    y=y,
                    z=z,
                    l=box_l,
                    w=box_w,
                    h=layer_height,
                    color=box_color,
                    edge_color=edge_color,
                    box_num=box_count + 1,
                    direction=direction_label,
                    product_name=name
                )

                box_count += 1

    # 添加图例
    if mixed_layout is not None:
        fig.add_trace(go.Scatter3d(
            x=[None], y=[None], z=[None],
            mode='markers',
            marker=dict(
                size=10,
                color='rgba(135, 206, 250, 0.7)',
                line=dict(color='rgb(0, 0, 139)', width=2)
            ),
            name='长×宽 (浅蓝色)',
            showlegend=True
        ))

        fig.add_trace(go.Scatter3d(
            x=[None], y=[None], z=[None],
            mode='markers',
            marker=dict(
                size=10,
                color='rgba(144, 238, 144, 0.7)',
                line=dict(color='rgb(0, 100, 0)', width=2)
            ),
            name='宽×长 (浅绿色)',
            showlegend=True
        ))


def _draw_single_box(fig, x, y, z, l, w, h, color, edge_color, box_num, direction, product_name):
    """绘制单个箱子"""
    # 定义8个顶点
    box_x = [x, x + l, x + l, x, x, x + l, x + l, x]
    box_y = [y, y, y + w, y + w, y, y, y + w, y + w]
    box_z = [z, z, z, z, z + h, z + h, z + h, z + h]

    # 定义6个面的顶点索引
    faces = [
        # 底面
        dict(i=[0, 0, 0, 0], j=[1, 1, 1, 1], k=[2, 3, 2, 3], order=[0, 1, 2, 0, 2, 3]),
        # 顶面
        dict(i=[4, 4, 4, 4], j=[5, 5, 5, 5], k=[6, 7, 6, 7], order=[4, 5, 6, 4, 6, 7]),
        # 前面
        dict(i=[0, 0, 0, 0], j=[4, 4, 4, 4], k=[5, 1, 5, 1], order=[0, 4, 5, 0, 5, 1]),
        # 后面
        dict(i=[2, 2, 2, 2], j=[6, 6, 6, 6], k=[7, 3, 7, 3], order=[2, 6, 7, 2, 7, 3]),
        # 左面
        dict(i=[0, 0, 0, 0], j=[3, 3, 3, 3], k=[7, 4, 7, 4], order=[0, 3, 7, 0, 7, 4]),
        # 右面
        dict(i=[1, 1, 1, 1], j=[2, 2, 2, 2], k=[6, 5, 6, 5], order=[1, 2, 6, 1, 6, 5])
    ]

    # 绘制每个面
    for face in faces:
        fig.add_trace(go.Mesh3d(
            x=box_x,
            y=box_y,
            z=box_z,
            i=face['i'],
            j=face['j'],
            k=face['k'],
            color=color,
            opacity=0.7,
            showlegend=False,
            hoverinfo='skip'
        ))

    # 绘制边框（用线条）
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # 底面
        [4, 5], [5, 6], [6, 7], [7, 4],  # 顶面
        [0, 4], [1, 5], [2, 6], [3, 7]   # 竖边
    ]

    for edge in edges:
        fig.add_trace(go.Scatter3d(
            x=[box_x[edge[0]], box_x[edge[1]]],
            y=[box_y[edge[0]], box_y[edge[1]]],
            z=[box_z[edge[0]], box_z[edge[1]]],
            mode='lines',
            line=dict(color=edge_color, width=1),
            showlegend=False,
            hoverinfo='skip'
        ))

    # 添加中心点的标签（仅对部分箱子显示，避免过于密集）
    if box_num <= 10 or box_num % 10 == 0:
        fig.add_trace(go.Scatter3d(
            x=[x + l/2],
            y=[y + w/2],
            z=[z + h/2],
            mode='text',
            text=[str(box_num)],
            textfont=dict(size=8, color=edge_color),
            textposition='middle center',
            showlegend=False,
            hovertemplate=f'<b>#{box_num}</b><br>' +
                          f'货品: {product_name}<br>' +
                          f'方向: {direction}<br>' +
                          f'位置: ({x:.1f}, {y:.1f}, {z:.1f})<br>' +
                          f'尺寸: {l:.1f}×{w:.1f}×{h:.1f}<extra></extra>'
        ))
