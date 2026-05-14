"""
UI 展示模块 - 显示装箱结果
"""

import streamlit as st
from config import CONTAINERS, POSITIONS_MAP


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
    
    col1, col2, col3 = st.columns(3)
    
    heights = []
    for segment in sorted(solution["segments"], key=lambda x: x["position"]):
        heights.append(segment["height"])
    
    with col1:
        st.metric("柜型", container_type)
        st.metric("总装载量", f"{solution['total_loaded']} 箱")

        # 显示相邻段高度差
        max_adjacent_diff = solution.get("max_adjacent_height_diff", 0)

        # 检查是否满足硬约束（≤50cm）
        if max_adjacent_diff <= 50:
            status = "✓ 满足硬约束"
        else:
            status = "✗ 超出硬约束"

        st.metric("相邻段高度差", f"{max_adjacent_diff:.1f} cm", delta=status)
    
    with col2:
        st.write("各段高度:")
        for segment in sorted(solution["segments"], key=lambda x: x["position"]):
            st.write(f"• {POSITIONS_MAP[segment['position']]}: {segment['height']:.1f}cm ({segment['layers']}层)")
    
    with col3:
        st.write("各段装载:")
        for segment in sorted(solution["segments"], key=lambda x: x["position"]):
            st.write(f"• {POSITIONS_MAP[segment['position']]}: {segment['total_boxes']}箱 {segment['name']}")
            if segment["direction"] == "混合":
                st.caption(f"  └─ 混合方向摆放，最优利用空间")
    
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
    for segment in sorted(solution["segments"], key=lambda x: x["position"]):
        data.append({
            "位置": POSITIONS_MAP[segment['position']],
            "货品": segment['name'],
            "箱数": segment['total_boxes'],
            "层数": segment['layers'],
            "高度(cm)": segment['height'],
            "长度(cm)": segment['actual_length'],
            "摆放方式": f"{segment['rows']}行 × {segment['cols']}列 ({segment['direction']})"
        })
    
    st.dataframe(data, use_container_width=True)
