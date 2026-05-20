"""
UI 展示模块 - 显示装箱结果
"""

import streamlit as st
from config import CONTAINERS, get_position_name
from visualizer import display_visualization_simple
import base64


def _sort_segments(solution):
    """按位置排序 segments"""
    return sorted(solution["segments"], key=lambda x: x["position"])


def _format_direction(direction):
    """格式化方向字符串"""
    return direction


def display_solution_summary(solution, container_type):
    """
    显示装箱方案摘要
    """
    st.subheader("📊 装箱方案摘要")

    # 显示布局信息
    layout = solution.get("layout", [])
    if layout:
        layout_str = " → ".join([p if p else "空" for p in layout])
        st.info(f"🎯 布局方案: {layout_str}")

    container = CONTAINERS[container_type]

    # 计算空间利用率
    total_volume = sum(
        seg["actual_length"] * seg["width"] * seg["height"]
        for seg in solution["segments"]
    )
    container_volume = container["length"] * container["width"] * container["height"]
    volume_utilization = (total_volume / container_volume) * 100

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("柜型", container_type)
        st.metric("总装载量", f"{solution['total_loaded']} 箱")

    with col2:
        # 显示相邻段高度差（仅供参考）
        max_adjacent_diff = solution.get("max_adjacent_height_diff", 0)
        st.metric("高度差", f"{max_adjacent_diff:.1f} cm", delta="参考值")
        st.metric("空间利用率", f"{volume_utilization:.1f}%")

    with col3:
        st.write("各段高度:")
        for segment in _sort_segments(solution):
            st.write(f"• {get_position_name(segment['position'])}: {segment['height']:.1f}cm ({segment['layers']}层)")

    with col4:
        st.write("各段装载:")
        for segment in _sort_segments(solution):
            st.write(f"• {get_position_name(segment['position'])}: {segment['total_boxes']}箱 {segment['name']}")
            if "混合" in segment["direction"] or "垂直" in segment["direction"]:
                st.caption(f"  └─ {segment['direction']}")

    # 显示重量中心信息
    if "weight_center" in solution:
        weight_center = solution["weight_center"]
        weight_deviation = solution["weight_deviation"]
        container_center = container["length"] / 2

        st.divider()
        st.subheader("⚖️ 重量中心分析")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("重量中心位置", f"{weight_center:.1f} cm")
        with col2:
            st.metric("柜子中点", f"{container_center:.1f} cm")
        with col3:
            st.metric("偏差", f"{weight_deviation:.1f} cm")

    st.divider()


def display_detailed_plan(solution):
    """
    显示详细的装箱计划表格
    """
    st.subheader("📋 详细装箱计划")

    data = []
    for segment in _sort_segments(solution):
        # 处理垂直混合段的详细信息
        is_vertical_mixed = "segment_details" in segment and segment["segment_details"]

        if is_vertical_mixed:
            # 垂直混合段：显示分层布局
            layers_info = []
            layout_details = []
            for detail in segment["segment_details"]:
                if detail["total_boxes"] > 0:
                    layer_desc = f"{detail['product_name']}×{detail['layers']}层"
                    layers_info.append(layer_desc)

                    # 获取每层的方向
                    layer_dir = detail.get("direction", "无")

                    layout_details.append(
                        f"{detail['product_name']} {detail['rows']}行×{detail['cols']}列 ({layer_dir})"
                    )

            # 将信息合并显示，使用分号分隔
            if layout_details:
                placement = f"垂直混合：{', '.join(layers_info)}； {'； '.join(layout_details)}"
            else:
                placement = f"垂直混合：{', '.join(layers_info)}"
        else:
            # 非垂直混合段
            placement = f"{segment['rows']}行×{segment['cols']}列 ({segment['direction']})"

        data.append({
            "位置": get_position_name(segment['position']),
            "货品": segment['name'],
            "箱数": segment['total_boxes'],
            "层数": segment['layers'],
            "高度(cm)": segment['height'],
            "长度(cm)": segment['actual_length'],
            "摆放方式": placement
        })

    st.dataframe(data, use_container_width=True)

