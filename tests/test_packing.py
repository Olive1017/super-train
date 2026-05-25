"""
装柜算法测试
"""

import pytest
from packing import pack


def test_order_51057547():
    """测试订单 51057547: 艾考=210, 2L=1125, 5L=150, 40尺海运柜"""
    result = pack(
        "51057547",
        {"艾考": 210, "2L": 1125, "5L": 150},
        "40尺海运柜"
    )

    assert result is not None, "应该找到装箱方案"

    # 验证长度利用率接近 1.000
    assert abs(result.utilization - 1.000) < 0.001, \
        f"长度利用率应为1.000，实际为{result.utilization}"

    # 验证高度差接近 103
    assert abs(result.height_variance - 103) < 10.3, \
        f"高度差应为103，实际为{result.height_variance}"

    # 验证所有产品数量精确匹配
    assert result.get_total_qty("艾考") == 210, f"艾考数量应为210，实际为{result.get_total_qty('艾考')}"
    assert result.get_total_qty("2L") == 1125, f"2L数量应为1125，实际为{result.get_total_qty('2L')}"
    assert result.get_total_qty("5L") == 150, f"5L数量应为150，实际为{result.get_total_qty('5L')}"

    # 验证所有段的层数不超过 max_layers
    for seg in result.segments:
        if seg.type == "pure":
            assert seg.actual_layers <= 7 if seg.ptype == "5L" else True, \
                f"5L纯装段层数{seg.actual_layers}不应超过7"
            assert seg.actual_layers <= 8 if seg.ptype == "2L" else True, \
                f"2L纯装段层数{seg.actual_layers}不应超过8"
            assert seg.actual_layers <= 6 if seg.ptype == "艾考" else True, \
                f"艾考纯装段层数{seg.actual_layers}不应超过6"
        elif seg.type == "shared":
            assert seg.layers_5L <= 7, f"5L在混合段中的层数{seg.layers_5L}不应超过7"


def test_order_51279325():
    """测试订单 51279325: 2L=850, 5L=500, 40尺海运柜"""
    result = pack(
        "51279325",
        {"2L": 850, "5L": 500},
        "40尺海运柜"
    )

    assert result is not None, "应该找到装箱方案"

    # 验证长度利用率接近 0.992
    assert abs(result.utilization - 0.992) < 0.001, \
        f"长度利用率应为0.992，实际为{result.utilization}"

    # 验证高度差接近 11.5
    assert abs(result.height_variance - 11.5) < 1.15, \
        f"高度差应为11.5，实际为{result.height_variance}"

    # 验证所有产品数量精确匹配
    assert result.get_total_qty("2L") == 850, f"2L数量应为850，实际为{result.get_total_qty('2L')}"
    assert result.get_total_qty("5L") == 500, f"5L数量应为500，实际为{result.get_total_qty('5L')}"

    # 验证所有段的层数不超过 max_layers
    for seg in result.segments:
        if seg.type == "pure":
            assert seg.actual_layers <= 8 if seg.ptype == "2L" else True, \
                f"2L纯装段层数{seg.actual_layers}不应超过8"
            assert seg.actual_layers <= 7 if seg.ptype == "5L" else True, \
                f"5L纯装段层数{seg.actual_layers}不应超过7"
        elif seg.type == "shared":
            assert seg.layers_5L <= 7, f"5L在混合段中的层数{seg.layers_5L}不应超过7"


def test_order_51279341():
    """测试订单 51279341: 艾考=500, 5L=1350, 40尺海运柜"""
    result = pack(
        "51279341",
        {"艾考": 500, "5L": 1350},
        "40尺海运柜"
    )

    assert result is not None, "应该找到装箱方案"

    # 验证长度利用率接近 0.989
    assert abs(result.utilization - 0.989) < 0.001, \
        f"长度利用率应为0.989，实际为{result.utilization}"

    # 验证高度差接近 3.5
    assert abs(result.height_variance - 3.5) < 0.35, \
        f"高度差应为3.5，实际为{result.height_variance}"

    # 验证所有产品数量精确匹配
    assert result.get_total_qty("艾考") == 500, f"艾考数量应为500，实际为{result.get_total_qty('艾考')}"
    assert result.get_total_qty("5L") == 1350, f"5L数量应为1350，实际为{result.get_total_qty('5L')}"

    # 额外断言：必须有 type=="shared" 的段，且至少一段的 orientation=="rotated"
    shared_segments = [seg for seg in result.segments if seg.type == "shared"]
    assert len(shared_segments) > 0, "必须有 type=='shared' 的段"

    rotated_shared = [seg for seg in shared_segments if seg.orientation == "rotated"]
    assert len(rotated_shared) > 0, "至少有一段shared段的orientation=='rotated'"

    # 验证所有段的层数不超过 max_layers
    for seg in result.segments:
        if seg.type == "pure":
            assert seg.actual_layers <= 6 if seg.ptype == "艾考" else True, \
                f"艾考纯装段层数{seg.actual_layers}不应超过6"
            assert seg.actual_layers <= 7 if seg.ptype == "5L" else True, \
                f"5L纯装段层数{seg.actual_layers}不应超过7"
        elif seg.type == "shared":
            assert seg.layers_5L <= 7, f"5L在混合段中的层数{seg.layers_5L}不应超过7"


def test_order_51203986():
    """测试订单 51203986: 5L=100, 2L=1250, 40尺海运柜"""
    result = pack(
        "51203986",
        {"5L": 100, "2L": 1250},
        "40尺海运柜"
    )

    assert result is not None, "应该找到装箱方案"

    # 验证长度利用率接近 0.9975
    assert abs(result.utilization - 0.9975) < 0.001, \
        f"长度利用率应为0.9975，实际为{result.utilization}"

    # 验证高度差接近 18
    assert abs(result.height_variance - 18) < 1.8, \
        f"高度差应为18，实际为{result.height_variance}"

    # 验证所有产品数量精确匹配
    assert result.get_total_qty("5L") == 100, f"5L数量应为100，实际为{result.get_total_qty('5L')}"
    assert result.get_total_qty("2L") == 1250, f"2L数量应为1250，实际为{result.get_total_qty('2L')}"

    # 额外断言：必须有 type=="shared" 的段
    shared_segments = [seg for seg in result.segments if seg.type == "shared"]
    assert len(shared_segments) > 0, "必须有 type=='shared' 的段"

    # 验证所有段的层数不超过 max_layers
    for seg in result.segments:
        if seg.type == "pure":
            assert seg.actual_layers <= 7 if seg.ptype == "5L" else True, \
                f"5L纯装段层数{seg.actual_layers}不应超过7"
            assert seg.actual_layers <= 8 if seg.ptype == "2L" else True, \
                f"2L纯装段层数{seg.actual_layers}不应超过8"
        elif seg.type == "shared":
            assert seg.layers_5L <= 7, f"5L在混合段中的层数{seg.layers_5L}不应超过7"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
