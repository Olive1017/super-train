"""
万益特混箱装柜 - Streamlit 主程序
"""

import streamlit as st
import traceback
from config import CONTAINERS
from packing import pack
from visualization import (
    render_side_view,
    render_top_view,
    render_3d_view,
    generate_worker_guide,
)
from ui import (
    render_header,
    render_sidebar,
    render_empty_state,
    render_container_info,
    render_summary,
    render_segment_table,
)


def main():
    render_header()

    # 初始化 session_state
    if "result" not in st.session_state:
        st.session_state["result"] = None
    if "container_name" not in st.session_state:
        st.session_state["container_name"] = None
    if "should_calculate" not in st.session_state:
        st.session_state["should_calculate"] = False

    # 渲染侧边栏
    container_name, orders, error_msg = render_sidebar()

    # 🚚 标题 + 副标题
    st.markdown("---")

    # 检查是否需要计算
    if st.session_state["should_calculate"] and not error_msg:
        # 执行计算
        container = CONTAINERS[container_name]

        # 默认权重
        w1, w2, w3 = 1.0, 0.5, 0.2

        try:
            result = pack("", orders, container_name, w1, w2, w3)
            st.session_state["result"] = result
            st.session_state["container_name"] = container_name
        except ValueError as e:
            st.session_state["error_message"] = f"❌ 无可行方案: {e}"
            st.session_state["result"] = None
        except Exception as e:
            st.session_state["error_message"] = f"❌ 算法异常: {e}"
            st.session_state["result"] = None

        st.session_state["should_calculate"] = False
        st.rerun()

    # 判断是否已计算
    has_result = st.session_state["result"] is not None

    if not has_result:
        # 未计算时：显示友好空状态
        render_empty_state()
    else:
        # 已计算时：显示完整结果
        result = st.session_state["result"]
        current_container_name = st.session_state["container_name"]
        container = CONTAINERS[current_container_name]

        # 柜型信息卡片
        st.markdown("---")
        render_container_info(current_container_name)

        # ✅ 找到最优方案 提示条
        st.markdown("---")
        st.success("✅ 找到最优方案")

        # 4 个指标卡
        render_summary(result)

        # 📦 段方案明细 表格
        st.subheader("📊 段方案明细")
        render_segment_table(result)

        # 4 个 tab (侧视图 / 俯视图 / 3D / 工人指南)
        st.divider()
        tab_side, tab_top, tab_3d, tab_guide = st.tabs([
            "📐 侧视图", "🗺️ 俯视图（按层）", "🎮 3D 视图", "📋 工人指南"
        ])

        with tab_side:
            fig = render_side_view(result, current_container_name)
            st.pyplot(fig, use_container_width=True)

        with tab_top:
            fig = render_top_view(result, current_container_name)
            st.pyplot(fig, use_container_width=True)

        with tab_3d:
            fig = render_3d_view(result, current_container_name)
            st.plotly_chart(fig, use_container_width=True)

        with tab_guide:
            guide_text = generate_worker_guide(result, current_container_name)
            st.text(guide_text)
            st.download_button(
                "💾 下载操作指南 (.txt)",
                guide_text,
                file_name=f"装柜指南_{current_container_name}.txt",
                mime="text/plain",
            )


if __name__ == "__main__":
    main()
