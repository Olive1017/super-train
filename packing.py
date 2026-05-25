"""
装柜算法核心实现
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math
import itertools
from config import PRODUCTS, CONTAINERS


@dataclass
class Way:
    """装载方式：某种产品在某种朝向下的排列参数"""
    cols: int               # 柜宽方向能放的列数
    row_depth: float        # 每行占用柜长方向深度
    side_gap: float         # 宽度方向剩余空隙
    box_height: float       # 单箱高度
    max_layers: int         # 最大层数
    orientation: str        # "normal" 或 "rotated"
    ptype: str              # 产品类型

    def __repr__(self):
        return f"Way({self.ptype}, {self.orientation}, cols={self.cols}, gap={self.side_gap})"


@dataclass
class Segment:
    """段：一段连续的柜长区域，包含纯装或混合装方案"""
    type: str               # "pure" 或 "shared"
    ptype: Optional[str]    # 纯装时的产品类型
    base_ptype: Optional[str]  # 混合时的底部产品类型
    qty: int                # 纯装：产品数量；混合：5L数量
    qty_5L: Optional[int]   # 混合：5L数量（与qty重复但语义清晰）
    qty_base: Optional[int] # 混合：底部产品数量
    seg_length: float       # 段长（沿柜长方向）
    total_height: float     # 段总高度
    side_gap: float         # 宽度方向剩余空隙
    cols: int               # 宽度方向列数
    rows: int               # 长度方向行数
    orientation: str        # 朝向
    way_5L: Optional[Way]   # 混合：5L的装载方式
    way_base: Optional[Way] # 混合：底部产品的装载方式
    layers_5L: Optional[int] = None       # 混合：5L层数
    actual_layers: Optional[int] = None   # 纯装：实际层数
    per_layer: Optional[int] = None       # 纯装：每层数量

    def __repr__(self):
        if self.type == "pure":
            return f"Pure({self.ptype}, qty={self.qty}, L={self.seg_length}, H={self.total_height}, {self.orientation})"
        else:
            return f"Shared(5L={self.qty_5L}, {self.base_ptype}={self.qty_base}, L={self.seg_length}, H={self.total_height})"


@dataclass
class PackingResult:
    """装箱结果"""
    segments: List[Segment]
    utilization: float
    height_variance: float
    side_gap_avg: float
    score: float
    container: str

    def get_total_qty(self, ptype: str) -> int:
        """获取某种产品的总装箱量"""
        total = 0
        for seg in self.segments:
            if seg.type == "pure" and seg.ptype == ptype:
                total += seg.qty
            elif seg.type == "shared":
                if ptype == "5L":
                    total += seg.qty_5L
                elif ptype == seg.base_ptype:
                    total += seg.qty_base
        return total


def generate_ways(ptype: str, container: Dict) -> List[Way]:
    """
    Phase 0: 生成某种产品的所有装载方式

    Args:
        ptype: 产品类型
        container: 柜子规格字典，包含 L, W, H

    Returns:
        Way 列表
    """
    ways = []
    product = PRODUCTS[ptype]
    container_W = container["width"]

    for orientation in ["normal", "rotated"]:
        if orientation == "normal":
            along_W = product["width"]
            along_L = product["depth"]
        else:  # rotated
            along_W = product["depth"]
            along_L = product["width"]

        cols = math.floor(container_W / along_W)
        if cols == 0:
            continue

        side_gap = container_W - cols * along_W
        way = Way(
            cols=cols,
            row_depth=along_L,
            side_gap=side_gap,
            box_height=product["height"],
            max_layers=product["max_layers"],
            orientation=orientation,
            ptype=ptype
        )
        ways.append(way)

    return ways


def generate_pure_segment(ptype: str, qty: int, way: Way, rows: int,
                         container: Dict) -> Optional[Segment]:
    """
    给定一个固定的 qty 和 (way, rows)，返回唯一的 pure 段，不可行则 None

    Args:
        ptype: 产品类型
        qty: 要装箱的数量
        way: 装载方式
        rows: 长度方向行数
        container: 柜子规格

    Returns:
        Segment 或 None
    """
    per_layer = rows * way.cols
    if per_layer == 0:
        return None

    full_layers = qty // per_layer
    remainder = qty - full_layers * per_layer
    tail_full_rows = remainder // way.cols
    tail_last_cols = remainder - tail_full_rows * way.cols
    actual_layers = full_layers + (1 if remainder > 0 else 0)

    if actual_layers == 0:
        return None
    if actual_layers > way.max_layers:
        return None

    total_height = actual_layers * way.box_height
    if total_height > container["height"]:
        return None

    seg_length = rows * way.row_depth
    if seg_length > container["length"]:
        return None

    return Segment(
        type="pure",
        ptype=ptype,
        base_ptype=None,
        qty=qty,
        qty_5L=None,
        qty_base=None,
        seg_length=seg_length,
        total_height=total_height,
        side_gap=way.side_gap,
        cols=way.cols,
        rows=rows,
        orientation=way.orientation,
        way_5L=None,
        way_base=None,
        actual_layers=actual_layers,
        per_layer=per_layer,
        layers_5L=None
    )


def enumerate_pure_options(ptype: str, qty: int, container: Dict) -> List[Segment]:
    """
    给定 ptype 和要装的 qty，枚举所有 (way, rows) 组合返回所有可行 pure 段

    Args:
        ptype: 产品类型
        qty: 要装箱的数量
        container: 柜子规格

    Returns:
        Segment 列表（已去重和 Pareto 剪枝）
    """
    if qty == 0:
        return []

    options = []
    ways = generate_ways(ptype, container)

    for way in ways:
        max_rows = math.floor(container["length"] / way.row_depth)
        for rows in range(1, max_rows + 1):
            seg = generate_pure_segment(ptype, qty, way, rows, container)
            if seg is not None:
                options.append(seg)

    # 剪枝 1: 对相同 (qty, seg_length, total_height) 的段去重，只保留 side_gap 最小的一个
    unique_dict = {}
    for seg in options:
        key = (seg.qty, seg.seg_length, seg.total_height)
        if key not in unique_dict or seg.side_gap < unique_dict[key].side_gap:
            unique_dict[key] = seg
    options = list(unique_dict.values())

    # 剪枝 2: 按 seg_length 排序后，对每个 seg_length 只保留 side_gap 最小的
    options.sort(key=lambda s: s.seg_length)
    pareto = []
    for seg in options:
        # 查找是否有相同 seg_length 的段（允许小误差）
        existing = next((p for p in pareto if abs(p.seg_length - seg.seg_length) < 0.1), None)
        if existing is None or seg.side_gap < existing.side_gap:
            if existing is not None:
                pareto.remove(existing)
            pareto.append(seg)
    options = pareto

    # 剪枝 3: 如果选项太多，只保留前 30 个最短的
    if len(options) > 30:
        options = options[:30]

    return options


def enumerate_shared_options(qty_5L: int, base_ptype: str, qty_base_available: int,
                            container: Dict) -> List[Segment]:
    """
    枚举 5L+底垫的共享段，每个段消耗 qty_5L 全部 5L + 部分 base

    Args:
        qty_5L: 5L 数量
        base_ptype: 底部产品类型（2L 或 艾考）
        qty_base_available: 底部产品可用数量
        container: 柜子规格

    Returns:
        Segment 列表（已去重和 Pareto 剪枝）
    """
    if qty_5L == 0:
        return []

    options = []
    ways_5L = generate_ways("5L", container)
    ways_base = generate_ways(base_ptype, container)

    for way_5L in ways_5L:
        max_rows_5L = math.floor(container["length"] / way_5L.row_depth)

        for rows_5L in range(1, max_rows_5L + 1):
            per_layer_5L = rows_5L * way_5L.cols
            layers_5L = math.ceil(qty_5L / per_layer_5L)

            if layers_5L > way_5L.max_layers:
                continue

            for way_base in ways_base:
                max_rows_base = math.floor(container["length"] / way_base.row_depth)

                for rows_base in range(1, max_rows_base + 1):
                    qty_base = rows_base * way_base.cols * 2
                    if qty_base > qty_base_available:
                        continue

                    seg_length = max(
                        rows_5L * way_5L.row_depth,
                        rows_base * way_base.row_depth
                    )

                    if seg_length > container["length"]:
                        continue

                    total_height = 2 * way_base.box_height + layers_5L * way_5L.box_height
                    if total_height > container["height"]:
                        continue

                    segment = Segment(
                        type="shared",
                        ptype=None,
                        base_ptype=base_ptype,
                        qty=qty_5L,
                        qty_5L=qty_5L,
                        qty_base=qty_base,
                        seg_length=seg_length,
                        total_height=total_height,
                        side_gap=min(way_5L.side_gap, way_base.side_gap),
                        cols=min(way_5L.cols, way_base.cols),
                        rows=max(rows_5L, rows_base),
                        orientation=way_5L.orientation,
                        way_5L=way_5L,
                        way_base=way_base,
                        layers_5L=layers_5L,
                        actual_layers=None,
                        per_layer=None
                    )
                    options.append(segment)

    # 剪枝 1: 对相同 (qty_5L, qty_base, seg_length, total_height) 的段去重
    unique_dict = {}
    for seg in options:
        key = (seg.qty_5L, seg.qty_base, seg.seg_length, seg.total_height)
        if key not in unique_dict or seg.side_gap < unique_dict[key].side_gap:
            unique_dict[key] = seg
    options = list(unique_dict.values())

    # 剪枝 2: 按 seg_length 排序，对相同 seg_length 只保留 side_gap 最小的
    options.sort(key=lambda s: s.seg_length)
    pareto = []
    for seg in options:
        existing = next((p for p in pareto if abs(p.seg_length - seg.seg_length) < 0.1), None)
        if existing is None or seg.side_gap < existing.side_gap:
            if existing is not None:
                pareto.remove(existing)
            pareto.append(seg)
    options = pareto

    # 剪枝 3: 如果选项太多，只保留前 50 个最短的
    if len(options) > 50:
        options = options[:50]

    return options


def evaluate_combo(combo: List[Segment], container: Dict,
                  w1: float, w2: float, w3: float) -> Optional[Tuple[float, float, float, float]]:
    """
    评估一个组合，返回 (score, utilization, height_variance, side_gap_avg) 或 None

    Args:
        combo: 段组合
        container: 柜子规格
        w1, w2, w3: 权重

    Returns:
        元组或 None（如果不可行）
    """
    total_len = sum(s.seg_length for s in combo)
    if total_len > container["length"]:
        return None

    utilization = total_len / container["length"]
    if utilization < 0.95:
        return None

    sorted_combo = sorted(combo, key=lambda s: s.total_height)
    heights = [s.total_height for s in sorted_combo]
    height_variance = sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))

    side_gaps = [s.side_gap for s in combo]
    side_gap_avg = sum(side_gaps) / len(side_gaps)

    score = (w1 * utilization -
             w2 * height_variance / container["height"] -
             w3 * side_gap_avg / container["width"])

    return (score, utilization, height_variance, side_gap_avg)


def search_best(orders: Dict[str, int], container: str,
               w1: float = 1.0, w2: float = 0.5, w3: float = 0.2) -> PackingResult:
    """
    Phase 2: 搜索最优装箱方案

    Args:
        orders: 订单字典
        container: 柜型名称
        w1, w2, w3: 权重

    Returns:
        PackingResult
    """
    container_spec = CONTAINERS[container]

    print(f"[search_best] 开始搜索最优方案...")
    print(f"[search_best] 订单: {orders}")

    best = None

    # 选项 A: 完全不用共享段，每个品类一个 pure 段
    print(f"[search_best] 选项 A: 纯 pure 段方案")
    ptypes = list(orders.keys())
    pure_options_per_ptype = []

    for ptype in ptypes:
        opts = enumerate_pure_options(ptype, orders[ptype], container_spec)
        if not opts:
            print(f"[search_best] 品类 {ptype} 无可行 pure 段，跳过选项 A")
            break
        pure_options_per_ptype.append(opts)
    else:
        # 所有品类都有可行方案，计算笛卡尔积大小
        cartesian_size = 1
        for opts in pure_options_per_ptype:
            cartesian_size *= len(opts)
        print(f"[search_best] 选项 A 笛卡尔积大小: {cartesian_size}")

        # 剪枝：检查最小长度和是否超过柜长
        min_total_len = sum(min(o.seg_length for o in opts) for opts in pure_options_per_ptype)
        if min_total_len <= container_spec["length"]:
            print(f"[search_best] 最小长度和 {min_total_len:.2f} <= 柜长 {container_spec['length']}，开始枚举")
            combo_count = 0
            for combo in itertools.product(*pure_options_per_ptype):
                combo_count += 1
                result = evaluate_combo(list(combo), container_spec, w1, w2, w3)
                if result is not None:
                    score, util, h_var, sg_avg = result
                    if best is None or score > best.score:
                        sorted_combo = sorted(list(combo), key=lambda s: s.total_height)
                        best = PackingResult(
                            segments=sorted_combo,
                            utilization=util,
                            height_variance=h_var,
                            side_gap_avg=sg_avg,
                            score=score,
                            container=container
                        )
                        print(f"[search_best] 更新 best: score={score:.4f}, util={util:.4f}, h_var={h_var:.2f}")
            print(f"[search_best] 选项 A 评估了 {combo_count} 个组合")
        else:
            print(f"[search_best] 最小长度和 {min_total_len:.2f} > 柜长 {container_spec['length']}，跳过选项 A")

    # 选项 B: 用一个共享段 (5L + base)
    if orders.get("5L", 0) > 0:
        print(f"[search_best] 选项 B: 使用共享段方案")
        for base_ptype in ["2L", "艾考"]:
            if orders.get(base_ptype, 0) == 0:
                continue

            shared_segs = enumerate_shared_options(
                orders["5L"], base_ptype, orders[base_ptype], container_spec
            )
            print(f"[search_best] {base_ptype} 共享段候选数: {len(shared_segs)}")

            for shared in shared_segs:
                # 共享段消耗 orders["5L"] 全部 + shared.qty_base 的 base
                remaining = {p: orders[p] for p in orders}
                remaining["5L"] = 0
                remaining[base_ptype] -= shared.qty_base
                if remaining[base_ptype] < 0:
                    continue

                # 其余品类各一个 pure 段
                pure_options_per_ptype = []
                for ptype, qty in remaining.items():
                    if qty == 0:
                        pure_options_per_ptype.append([None])  # 占位
                    else:
                        opts = enumerate_pure_options(ptype, qty, container_spec)
                        if not opts:
                            break
                        pure_options_per_ptype.append(opts)
                else:
                    # 计算笛卡尔积大小
                    cartesian_size = 1
                    for opts in pure_options_per_ptype:
                        cartesian_size *= len(opts)
                    if cartesian_size > 0:
                        # 剪枝：检查最小长度和
                        min_total_len = shared.seg_length + sum(
                            min(o.seg_length for o in opts) if opts and opts[0] is not None else 0
                            for opts in pure_options_per_ptype
                        )
                        if min_total_len <= container_spec["length"]:
                            for pures in itertools.product(*pure_options_per_ptype):
                                combo = [shared] + [p for p in pures if p is not None]
                                result = evaluate_combo(combo, container_spec, w1, w2, w3)
                                if result is not None:
                                    score, util, h_var, sg_avg = result
                                    if best is None or score > best.score:
                                        sorted_combo = sorted(combo, key=lambda s: s.total_height)
                                        best = PackingResult(
                                            segments=sorted_combo,
                                            utilization=util,
                                            height_variance=h_var,
                                            side_gap_avg=sg_avg,
                                            score=score,
                                            container=container
                                        )
                                        print(f"[search_best] 更新 best (shared): score={score:.4f}, util={util:.4f}, h_var={h_var:.2f}")

    if best is None:
        raise ValueError("No feasible packing")

    print(f"[search_best] 最终 best: score={best.score:.4f}, util={best.utilization:.4f}, h_var={best.height_variance:.2f}")
    print(f"[search_best] 组合: {[f'{s.type}({s.ptype or s.base_ptype}) L={s.seg_length:.2f} H={s.total_height:.2f}' for s in best.segments]}")

    return best


def pack(order_id: str, orders: Dict[str, int], container: str,
        w1: float = 1.0, w2: float = 0.5, w3: float = 0.2) -> Optional[PackingResult]:
    """
    计算装箱方案的主函数

    Args:
        order_id: 订单号
        orders: 订单字典，key为产品类型，value为数量
        container: 柜型名称
        w1, w2, w3: 评分权重

    Returns:
        PackingResult 或 None
    """
    # 过滤掉数量为0的产品
    orders = {k: v for k, v in orders.items() if v > 0}

    if not orders:
        return None

    result = search_best(orders, container, w1, w2, w3)

    return result
