"""
万益特货品装箱计算器 - Streamlit 主程序
"""

import streamlit as st
from config import PRODUCTS, CONTAINERS
from algorithms import calculate_loading_plan
from ui import display_solution_summary, display_detailed_plan, display_visualization_simple


def main():
    st.set_page_config(
        page_title="万益特货品装箱计算器",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🚚 万益特货品装箱计算器")
    st.markdown("---")

    # 侧边栏参数输入
    with st.sidebar:
        st.header("📝 参数设置")

        # 柜型选择
        container_type = st.selectbox(
            "选择柜型",
            list(CONTAINERS.keys()),
            index=0
        )

        st.divider()

        # 货品数量输入
        st.subheader("货品数量（箱）")
        product_quantities = {}

        for product_name in PRODUCTS.keys():
            quantity = st.number_input(
                f"{product_name}",
                min_value=0,
                max_value=10000,
                value=0,
                step=10,
                help=f"规格: {PRODUCTS[product_name]['length']}×{PRODUCTS[product_name]['width']}×{PRODUCTS[product_name]['height']}cm"
            )
            product_quantities[product_name] = quantity

        st.divider()

        # 计算按钮
        calculate = st.button("🔢 计算装箱方案", type="primary", use_container_width=True)

    # 显示柜子信息
    col1, col2, col3, col4 = st.columns(4)
    container = CONTAINERS[container_type]

    with col1:
        st.metric("柜型", container_type)
    with col2:
        st.metric("内长", f"{container['length']} cm")
    with col3:
        st.metric("内宽", f"{container['width']} cm")
    with col4:
        st.metric("内高", f"{container['height']} cm")

    st.markdown("---")

    # 计算并显示结果
    if calculate:
        used_products = sum(1 for q in product_quantities.values() if q > 0)

        if used_products == 0:
            st.warning("⚠️ 请至少选择一种货品")
        elif used_products > 3:
            st.error("❌ 最多支持3种货品混装")
        else:
            with st.spinner("正在计算最优装箱方案..."):
                solution = calculate_loading_plan(container_type, product_quantities)

            if solution is None:
                st.error("❌ 无法找到合适的装箱方案")
            elif "error" in solution:
                st.error(f"❌ {solution['error']}")
            else:
                # 显示结果摘要
                display_solution_summary(solution, container_type)
                display_detailed_plan(solution)

                # 简洁版可视化
                st.divider()
                st.subheader("📐 可视化查看")
                display_visualization_simple(solution, container_type)
                st.divider()



if __name__ == "__main__":
    main()
