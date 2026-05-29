"""
UI 组件函数 - 无副作用，只返回用户输入
"""

import io
from datetime import datetime
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import streamlit as st
import pandas as pd
from config import PRODUCTS, CONTAINERS


def build_pdf_bytes(result, container_name):
    """
    生成包含侧视图和俯视图的 PDF

    Args:
        result: PackingResult 装箱结果
        container_name: 柜型名称

    Returns:
        bytes: PDF 文件的字节内容
    """
    from visualization import render_side_view, render_top_view

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        # 第1页：侧视图
        fig_side = render_side_view(result, container_name)
        pdf.savefig(fig_side, bbox_inches="tight")
        plt.close(fig_side)

        # 第2页：俯视图
        fig_top = render_top_view(result, container_name)
        pdf.savefig(fig_top, bbox_inches="tight")
        plt.close(fig_top)

    buf.seek(0)
    return buf.getvalue()


def render_header() -> None:
    """渲染页面标题和简介"""
    st.set_page_config(
        page_title="万益特混箱装柜",
        page_icon="📦",
        layout="wide"
    )
    st.title("🚚 万益特集装箱装柜算法")
    st.caption("多产品混装拼柜方案优化")


def render_sidebar() -> tuple[str, dict[str, int], str]:
    """
    渲染侧边栏，返回 (柜型名, 订单输入, 错误信息)
    """
    # 初始化 session_state
    if "error_message" not in st.session_state:
        st.session_state["error_message"] = ""

    # 📦 参数设置
    st.sidebar.header("📦 参数设置")
    container_name = st.sidebar.selectbox(
        "选择柜型",
        list(CONTAINERS.keys()),
        index=2  # 默认 40尺海运
    )

    # 📋 订单输入
    st.sidebar.subheader("📋 输入产品数量")

    # 使用 session_state 保存输入值
    if "orders_input" not in st.session_state:
        st.session_state["orders_input"] = {"5L": 0, "2L": 0, "艾考": 0}

    orders = {}
    for ptype in PRODUCTS.keys():
        qty = st.sidebar.number_input(
            f"{ptype}",
            min_value=0,
            max_value=10000,
            value=st.session_state["orders_input"][ptype],
            step=10,
            key=f"order_{ptype}"
        )
        orders[ptype] = qty

    # 更新 session_state 中的输入值
    st.session_state["orders_input"] = orders

    st.sidebar.divider()

    # 🚀 计算装柜方案 按钮
    if st.sidebar.button("🚀 计算装柜方案", type="primary"):
        st.session_state["error_message"] = ""

        # 验证订单
        if all(qty == 0 for qty in orders.values()):
            st.session_state["error_message"] = "❌ 请至少输入一个品类的箱数"
            return container_name, orders, st.session_state["error_message"]

        # 触发计算
        st.session_state["should_calculate"] = True
        st.rerun()

    # 🔄 重置 按钮
    if st.sidebar.button("🔄 重置", type="secondary"):
        st.session_state["result"] = None
        st.session_state["container_name"] = None
        st.session_state["should_calculate"] = False
        st.session_state["error_message"] = ""
        st.session_state["orders_input"] = {"5L": 0, "2L": 0, "艾考": 0}
        st.rerun()

    st.sidebar.divider()

    # 📥 下载 PDF 按钮
    st.sidebar.subheader("📥 导出方案")
    if st.session_state.get("result") is not None:
        result = st.session_state["result"]
        container_name = st.session_state.get("container_name", "")

        if container_name:
            # 生成 PDF 字节数据
            pdf_bytes = build_pdf_bytes(result, container_name)

            # 生成文件名：装柜方案_{container}_{今天日期YYYYMMDD}.pdf
            today_str = datetime.now().strftime("%Y%m%d")
            file_name = f"装柜方案_{container_name}_{today_str}.pdf"

            st.sidebar.download_button(
                label="📥 下载装柜方案 PDF",
                data=pdf_bytes,
                file_name=file_name,
                mime="application/pdf",
            )
    else:
        st.sidebar.info("💡 请先生成装柜方案")

    # 显示错误信息（如果有）
    if st.session_state["error_message"]:
        st.sidebar.error(st.session_state["error_message"])

    return container_name, orders, st.session_state["error_message"]


def render_empty_state() -> None:
    """渲染友好空状态"""
    st.markdown(
        """
        <div style="text-align: center; padding: 80px 20px;">
            <h1 style="color: #888; font-size: 48px;">👈</h1>
            <p style="color: #666; font-size: 20px; margin-top: 20px;">
                请在左侧输入订单箱数，点击「计算装柜方案」
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_container_info(container_name: str) -> None:
    """渲染柜型信息卡片"""
    container = CONTAINERS[container_name]
    volume = container['length'] * container['width'] * container['height'] / 1000000

    st.info(
        f"**柜型**: {container_name}  |  "
        f"**内尺寸**: {container['length']}×{container['width']}×{container['height']} cm  |  "
        f"**内体积**: {volume:.2f} m³"
    )


def render_summary(result) -> None:
    """渲染顶部 4 个指标卡片"""
    col1, col2, col3, col4 = st.columns(4)

    with col2:
        st.metric(
            "长度利用率",
            f"{result.utilization * 100:.1f}%"
        )

    with col3:
        st.metric(
            "段数",
            len(result.segments)
        )

    with col4:
        st.metric(
            "最大高度差",
            f"{result.height_variance:.1f} cm"
        )

    with col1:
        space_utilization = result.get_space_utilization()
        st.metric(
            "空间利用率",
            f"{space_utilization * 100:.1f}%"
        )


def render_segment_table(result) -> None:
    """渲染段汇总表格"""
    rows = []

    for i, seg in enumerate(result.segments, 1):
        if seg.type == "pure":
            rows.append({
                "段号": i,
                "类型": "纯段",
                "品类": seg.ptype,
                "朝向": "打横装" if seg.orientation == "打横装" else "打竖装",
                "排×列×层": f"{seg.rows}×{seg.cols}×{seg.actual_layers}",
                "箱数": seg.qty,
                "段长(cm)": round(seg.seg_length, 1),
                "段高(cm)": round(seg.total_height, 1),
            })
        else:  # shared
            rows.append({
                "段号": i,
                "类型": "共享段",
                "品类": f"{seg.base_ptype}+5L",
                "朝向": "—",
                "排×列×层": (
                    f"底{seg.rows_base}×{seg.way_base.cols}×2 / "
                    f"上{seg.rows_5L}×{seg.way_5L.cols}×{seg.layers_5L}"
                ),
                "箱数": f"{seg.qty_base}+{seg.qty_5L}",
                "段长(cm)": round(seg.seg_length, 1),
                "段高(cm)": round(seg.total_height, 1),
            })

    # 在第 177 行之前插入：
    st.caption(
        "💡 **朝向说明**："
        "「打竖装」表示长沿柜长、宽沿柜宽；"
        "「打横装」表示长沿柜宽、宽沿柜长"
    )

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True
    )
