"""
装箱算法核心逻辑
- 计算最优装箱方案
- 按需分配，紧凑装箱
"""

import numpy as np
import itertools
import math
from config import PRODUCTS, CONTAINERS, LAYER_LIMITS, VERTICAL_MIXING_CONFIG


def calculate_top_layer_filled_score(segments):
    """
    计算顶层铺满度评分

    参数:
        segments: 段信息列表

    返回:
        score: 顶层铺满度评分
    """
    score = 0

    for seg in segments:
        # 判断是否为垂直混合段
        if "segment_details" in seg and seg["segment_details"]:
            # 垂直混合段：找到最上层有箱子的层
            top_layer = None
            # 找最顶层的非空层（layer_index最大）
            for detail in reversed(seg["segment_details"]):
                if detail["total_boxes"] > 0:
                    top_layer = detail
                    break

            if top_layer is None or top_layer["total_boxes"] == 0:
                continue

            # 计算该层的铺满度
            layer_name = top_layer["product_name"]
            rows = top_layer["rows"]
            cols = top_layer["cols"]
            direction = top_layer.get("direction", "长×宽")

            # 计算该层的最大容量（该产品在一层的最大箱子数）
            product = PRODUCTS[layer_name]
            box_l, box_w = product["length"], product["width"]

            # 根据实际摆放方向计算最大容量
            # 直接基于空间计算最大容量，不使用反推方式
            if direction == "长×宽":
                # 长沿柜子长，宽沿柜子宽
                max_rows = math.floor(seg["actual_length"] / box_l)  # 沿长度方向能放的行数
                max_cols = math.floor(seg["width"] / box_w)          # 沿宽度方向能放的列数
                max_boxes = max_rows * max_cols
            elif direction == "宽×长":
                # 宽沿柜子长，长沿柜子宽
                max_rows = math.floor(seg["actual_length"] / box_w)  # 沿长度方向能放的行数
                max_cols = math.floor(seg["width"] / box_l)          # 沿宽度方向能放的列数
                max_boxes = max_rows * max_cols
            else:
                # 混合方向，按保守方式计算
                max_rows = math.floor(seg["actual_length"] / box_w)
                max_cols = math.floor(seg["width"] / box_l)
                max_boxes = max_rows * max_cols

            if max_boxes == 0:
                continue

            # 计算铺满度
            filled_ratio = min(1.0, (rows * cols) / max_boxes)

            # 根据铺满度给分
            if filled_ratio >= 0.9:
                score += 150
            elif filled_ratio >= 0.8:
                score += 100
        else:
            # 非垂直混合段：直接使用段的信息
            if seg["total_boxes"] == 0:
                continue

            product_name = seg["name"]
            rows = seg["rows"]
            cols = seg["cols"]
            direction = seg.get("direction", "长×宽")

            # 计算该产品在一层的最大箱子数
            product = PRODUCTS[product_name]
            box_l, box_w = product["length"], product["width"]

            # 根据实际摆放方向计算最大容量
            # max_rows: 沿长度方向能放的行数 = 段实际长度 / 箱子长度方向
            # max_cols: 沿宽度方向能放的列数 = 柜子宽度 / 箱子宽度方向
            if direction == "长×宽":
                max_rows = math.floor(seg["actual_length"] / box_l)
                max_cols = math.floor(seg["width"] / box_w)
            elif direction == "宽×长":
                max_rows = math.floor(seg["actual_length"] / box_w)
                max_cols = math.floor(seg["width"] / box_l)
            else:
                # 混合方向，按宽×长计算（更保守）
                max_rows = math.floor(seg["actual_length"] / box_w)
                max_cols = math.floor(seg["width"] / box_l)

            max_boxes = max_rows * max_cols

            if max_boxes == 0:
                continue

            # 计算铺满度
            filled_ratio = min(1.0, (rows * cols) / max_boxes)

            # 根据铺满度给分
            if filled_ratio >= 0.9:
                score += 150
            elif filled_ratio >= 0.8:
                score += 100

    return score


def calculate_weight_center(segments, container_length):
    """
    计算重量中心位置（支持垂直混合）

    参数:
        segments: 段信息列表
        container_length: 柜子总长度

    返回:
        weight_center: 重量中心距前端的距离
        deviation: 与柜子中点的偏差（越小越好）
    """
    total_weight = 0
    total_moment = 0

    for seg in segments:
        segment_length = seg["actual_length"]

        # 段的起始位置
        start_pos = 0
        for other in segments:
            if other["position"] < seg["position"]:
                start_pos += other["actual_length"]

        # 段的重心位置（段中心）
        segment_center = start_pos + segment_length / 2

        # 判断是否为垂直混合段
        if "layers_config" in seg and len(seg["layers_config"]) > 1:
            # 垂直混合段：计算每层的重量
            segment_weight = 0
            for layer_idx, layer_name, layers in seg["layers_config"]:
                # 找到对应的segment_details
                layer_details = None
                if "segment_details" in seg:
                    for sd in seg["segment_details"]:
                        if sd["layer_index"] == layer_idx:
                            layer_details = sd
                            break

                if layer_details:
                    boxes = layer_details["total_boxes"]
                    weight_per_box = PRODUCTS[layer_name]["weight"]
                    segment_weight += boxes * weight_per_box
                else:
                    # 如果没有details，按seg["total_boxes"]分配
                    # 这是一个简化处理
                    weight_per_box = PRODUCTS[layer_name]["weight"]
                    # 按层数比例分配箱子
                    total_layers = sum(l for _, _, l in seg["layers_config"])
                    proportion = layers / total_layers if total_layers > 0 else 0
                    boxes = int(seg["total_boxes"] * proportion)
                    segment_weight += boxes * weight_per_box
        else:
            # 非垂直混合段：直接计算
            name = seg["name"]
            boxes = seg["total_boxes"]
            weight_per_box = PRODUCTS[name]["weight"]
            segment_weight = boxes * weight_per_box

        total_weight += segment_weight
        total_moment += segment_weight * segment_center

    if total_weight == 0:
        return 0, container_length / 2

    weight_center = total_moment / total_weight
    container_center = container_length / 2
    deviation = abs(weight_center - container_center)

    return weight_center, deviation


def calculate_loading_plan(container_type, product_quantities):
    """
    计算最优装箱方案（智能分段，按需分配）

    参数:
        container_type: 柜型
        product_quantities: 货品数量字典 {"5L": 100, "2L": 50, ...}

    返回:
        最优装箱方案
    """
    container = CONTAINERS[container_type]

    # 获取实际使用的货品种类（数量>0的）
    used_products = {k: v for k, v in product_quantities.items() if v > 0}
    product_names = list(used_products.keys())
    n_products = len(product_names)

    if n_products == 0:
        return None
    if n_products > 3:
        return {"error": "最多支持3种货品混装"}

    # 只生成货品排列（不再预设段数）
    permutations = list(itertools.permutations(product_names))

    best_solution = None
    best_score = -float('inf')
    total_solutions_checked = 0
    total_feasible_solutions = 0

    # 添加调试信息
    print(f"[DEBUG] 开始搜索最优方案，总需求：{sum(product_quantities.values())} 箱")

    # 对每个排列计算最优方案（算法自动决定段数）
    for layout in permutations:
        solution = find_optimal_allocation(layout, used_products, container)
        total_solutions_checked += 1
        if solution and solution["score"] > best_score:
            if best_solution is None:
                # 第一次找到可行方案
                total_feasible_solutions += 1
                print(f"[DEBUG] 找到第{total_feasible_solutions}个可行方案：{solution['total_loaded']} 箱")
            best_solution = solution
            best_score = solution["score"]

    # 调试信息
    if best_solution is None:
        print(f"[DEBUG] 总共检查了 {total_solutions_checked} 种排列，但未找到可行方案")
    else:
        print(f"[DEBUG] 检查了 {total_solutions_checked} 种排列，找到 {total_feasible_solutions} 个可行方案")
        print(f"[DEBUG] 最优方案装载：{best_solution['total_loaded']} 箱 / 总需求：{sum(product_quantities.values())} 箱")

    return best_solution


def find_optimal_allocation(layout, product_quantities, container):
    """
    智能分段：根据货品排列，自动决定最优分段方案

    核心策略：
    1. 按排列顺序计算每种货品需要的长度
    2. 智能判断是否需要将同种货品分段（基于重量平衡和长度利用率）
    3. 支持垂直混合
    """
    total_length = container["length"]
    container_width = container["width"]
    total_height = container["height"]

    layout_str = " → ".join(layout)
    print(f"[DEBUG] 正在搜索布局：{layout_str}")

    best_allocation = None
    best_score = -float('inf')

    # 生成层数组合（支持垂直混合）
    all_layers_combinations = []
    for layers_config in generate_layers_combinations_v3(
        [(i, name) for i, name in enumerate(layout)], total_height, product_quantities
    ):
        all_layers_combinations.append(layers_config)

    for layers_config in all_layers_combinations:
        # 计算每个位置的高度和层配置
        heights = {}
        segment_layer_configs = {}
        for pos, layer_list in layers_config:
            segment_height = 0
            for layer_idx, layer_name, layers in layer_list:
                segment_height += PRODUCTS[layer_name]["height"] * layers
            heights[pos] = segment_height
            segment_layer_configs[pos] = layer_list

        # 计算高度差（仅用于显示，不影响评分）
        sorted_heights = [heights[pos] for pos in sorted(heights.keys())]
        max_adjacent_diff = 0
        for i in range(len(sorted_heights) - 1):
            diff = abs(sorted_heights[i] - sorted_heights[i + 1])
            max_adjacent_diff = max(max_adjacent_diff, diff)

        # 识别垂直混合段
        vertical_mixed_segments = {}
        for pos, layer_list in segment_layer_configs.items():
            if len(layer_list) > 1:
                vertical_mixed_segments[pos] = layer_list

        # 计算每段需要的长度
        segments = []
        total_actual_length = 0
        remaining_quantities = product_quantities.copy()

        # 为每个位置分配货品
        for pos, product_name in enumerate(layout):
            if pos in vertical_mixed_segments:
                # 垂直混合段
                segment_height = heights[pos]
                segment_length = 0
                segment_boxes = 0
                segment_details = []

                for layer_idx, layer_name, layers in segment_layer_configs[pos]:
                    layer_height = PRODUCTS[layer_name]["height"] * layers
                    layer_quantity = remaining_quantities.get(layer_name, 0)

                    if layer_quantity <= 0:
                        segment_details.append({
                            "layer_index": layer_idx,
                            "product_name": layer_name,
                            "layers": layers,
                            "height": layer_height,
                            "rows": 0, "cols": 0, "total_boxes": 0,
                            "direction": "无", "mixed_layout": None,
                            "actual_length": 0
                        })
                        continue

                    # 修复：正确计算该层容量
                    box_l, box_w = PRODUCTS[layer_name]["length"], PRODUCTS[layer_name]["width"]

                    # 计算该层能装的最大箱数（基于实际段长度）
                    # 先估算需要的段长度，然后再精确计算
                    boxes_per_layer = math.ceil(layer_quantity / layers)

                    # 调用 calculate_compact_layout 计算实际布局
                    # 注意：这里传入的是 layer_height（单层高度），而不是整个段的高度
                    # 这样 calculate_compact_layout 会正确计算每层的布局
                    boxes_info = calculate_compact_layout(
                        layer_quantity, container_width, layer_height, layer_name
                    )

                    # 检查是否成功装载
                    if boxes_info["total_boxes"] > 0:
                        segment_length = max(segment_length, boxes_info["actual_length"])
                        segment_boxes += boxes_info["total_boxes"]
                        remaining_quantities[layer_name] = layer_quantity - boxes_info["total_boxes"]
                        segment_details.append({
                            "layer_index": layer_idx,
                            "product_name": layer_name,
                            "layers": layers,
                            "height": layer_height,
                            "rows": boxes_info["rows"],
                            "cols": boxes_info["cols"],
                            "total_boxes": boxes_info["total_boxes"],
                            "direction": boxes_info["direction"],
                            "mixed_layout": boxes_info.get("mixed_layout"),
                            "actual_length": boxes_info["actual_length"]
                        })
                    else:
                        segment_details.append({
                            "layer_index": layer_idx,
                            "product_name": layer_name,
                            "layers": layers,
                            "height": layer_height,
                            "rows": 0, "cols": 0, "total_boxes": 0,
                            "direction": "无", "mixed_layout": None,
                            "actual_length": 0
                        })

                # 确定主产品名称
                main_product_name = None
                for detail in reversed(segment_details):
                    if detail["total_boxes"] > 0:
                        main_product_name = detail["product_name"]
                        break
                if main_product_name is None:
                    main_product_name = segment_layer_configs[pos][-1][1]

                segments.append({
                    "position": pos,
                    "name": main_product_name,
                    "actual_length": segment_length,
                    "width": container_width,
                    "height": segment_height,
                    "layers": sum(layers for _, _, layers in segment_layer_configs[pos]),
                    "rows": max((sd["rows"] for sd in segment_details), default=0),
                    "cols": max((sd["cols"] for sd in segment_details), default=0),
                    "total_boxes": segment_boxes,
                    "direction": "垂直混合",
                    "layers_config": segment_layer_configs[pos],
                    "segment_details": segment_details
                })
                total_actual_length += segment_length
            else:
                # 纯段：检查是否需要分段（智能判断）
                quantity = remaining_quantities.get(product_name, 0)
                if quantity <= 0:
                    continue

                segment_height = heights[pos]

                # 计算整段需要的长度
                boxes_info = calculate_compact_layout(
                    quantity, container_width, segment_height, product_name
                )

                if boxes_info["total_boxes"] == 0:
                    continue

                if boxes_info["actual_length"] <= total_length:
                    # 装入整段
                    segments.append({
                        "position": pos,
                        "name": product_name,
                        "actual_length": boxes_info["actual_length"],
                        "width": container_width,
                        "height": segment_height,
                        "layers": int(segment_height / PRODUCTS[product_name]["height"]),
                        "rows": boxes_info["rows"],
                        "cols": boxes_info["cols"],
                        "total_boxes": boxes_info["total_boxes"],
                        "direction": boxes_info["direction"],
                        "mixed_layout": boxes_info.get("mixed_layout"),
                        "layers_config": [(0, product_name, int(segment_height / PRODUCTS[product_name]["height"]))]
                    })
                    total_actual_length += boxes_info["actual_length"]
                    remaining_quantities[product_name] = quantity - boxes_info["total_boxes"]
                else:
                    # 单段超过柜子长度，智能分段
                    # 使用新的calculate_optimal_layout函数，尝试所有层数和方向组合
                    boxes_info = calculate_optimal_layout(
                        quantity, container_width, segment_height, product_name, max_length_limit=total_length
                    )

                    if boxes_info["total_boxes"] == 0:
                        continue

                    boxes_to_load = boxes_info["total_boxes"]
                    actual_length = boxes_info["actual_length"]
                    direction = boxes_info["direction"]
                    rows = boxes_info["rows"]
                    cols = boxes_info["cols"]

                    # 计算实际使用的层数
                    layers = int(segment_height / PRODUCTS[product_name]["height"])

                    if boxes_to_load > 0:
                        segments.append({
                            "position": pos,
                            "name": product_name,
                            "actual_length": actual_length,
                            "width": container_width,
                            "height": segment_height,
                            "layers": layers,
                            "rows": rows,
                            "cols": cols,
                            "total_boxes": boxes_to_load,
                            "direction": direction,
                            "mixed_layout": boxes_info.get("mixed_layout"),
                            "layers_config": [(0, product_name, layers)]
                        })
                        total_actual_length += actual_length
                        remaining_quantities[product_name] = quantity - boxes_to_load

        # 处理剩余箱子：如果还有未装载的货品，在柜子剩余长度内继续装载
        remaining_length = total_length - total_actual_length
        for product_name, quantity in list(remaining_quantities.items()):
            if quantity > 0 and remaining_length > 0:
                # 使用新的calculate_optimal_layout函数，动态尝试所有层数和方向组合
                boxes_info = calculate_optimal_layout(
                    quantity, container_width, total_height, product_name, max_length_limit=remaining_length
                )

                if boxes_info["total_boxes"] == 0:
                    continue

                boxes_to_load = boxes_info["total_boxes"]
                actual_length = boxes_info["actual_length"]
                direction = boxes_info["direction"]
                rows = boxes_info["rows"]
                cols = boxes_info["cols"]

                # 计算实际使用的层数
                layers = int(actual_length / PRODUCTS[product_name]["height"]) if direction == "长×宽" else int(actual_length / PRODUCTS[product_name]["width"])
                # 重新计算层数：基于实际长度和箱子高度
                layers = int(boxes_info["actual_length"] / (PRODUCTS[product_name]["length"] if direction == "长×宽" else PRODUCTS[product_name]["width"])) if boxes_info["actual_length"] > 0 else 1
                # 更正：层数应该由算法内部决定，这里从计算结果中推断
                # 实际上，我们应该根据实际装载的箱子数和层数关系来计算
                # 但为了简化，我们使用容器高度来计算最大可能层数
                box_h = PRODUCTS[product_name]["height"]
                estimated_layers = int(total_height / box_h)
                # 更精确的计算：根据total_boxes、rows、cols反推层数
                estimated_layers = max(1, boxes_to_load // (rows * cols)) if rows > 0 and cols > 0 else 1
                layers = estimated_layers
                segment_height = layers * box_h

                if boxes_to_load > 0:
                    new_pos = len(segments)
                    segments.append({
                        "position": new_pos,
                        "name": product_name,
                        "actual_length": actual_length,
                        "width": container_width,
                        "height": segment_height,
                        "layers": layers,
                        "rows": rows,
                        "cols": cols,
                        "total_boxes": boxes_to_load,
                        "direction": direction,
                        "mixed_layout": boxes_info.get("mixed_layout"),
                        "layers_config": [(0, product_name, layers)]
                    })
                    total_actual_length += actual_length
                    remaining_length -= actual_length
                    remaining_quantities[product_name] = quantity - boxes_to_load

        # 检查是否所有货品都已装载
        total_required = sum(product_quantities.values())
        loaded_count = sum(seg["total_boxes"] for seg in segments)

        if total_actual_length <= total_length and loaded_count >= total_required:
            # 计算评分
            length_utilization = total_actual_length / total_length
            length_utilization_score = int(length_utilization * 2000)

            weight_center, weight_deviation = calculate_weight_center(segments, total_length)
            top_layer_score = calculate_top_layer_filled_score(segments)

            score = length_utilization_score

            if weight_deviation <= 5:
                score += 800
            elif weight_deviation <= 10:
                score += 600
            elif weight_deviation <= 15:
                score += 300
            elif weight_deviation <= 20:
                score += 100
            elif weight_deviation <= 30:
                score -= weight_deviation * 3
            else:
                score -= weight_deviation * 5

            # 奖励5L在中间位置
            if len(layout) >= 2:
                mid_pos = len(layout) // 2
                if layout[mid_pos] == "5L":
                    score += 150

            score += top_layer_score

            allocation = {
                "layout": list(layout),
                "segments": segments,
                "score": score,
                "total_loaded": loaded_count,
                "weight_center": weight_center,
                "weight_deviation": weight_deviation,
                "max_adjacent_height_diff": max_adjacent_diff,
                "length_utilization": length_utilization
            }

            if score > best_score:
                best_allocation = allocation
                best_score = score
                print(f"[DEBUG] 找到更好方案：{loaded_count} 箱，长度利用率：{length_utilization:.2%}，得分：{score:.2f}")

    if best_allocation:
        print(f"[DEBUG] 布局 {layout_str} 的最优方案：{best_allocation['total_loaded']} 箱，{len(best_allocation['segments'])} 段")
    else:
        print(f"[DEBUG] 布局 {layout_str} 未找到可行方案")

    return best_allocation


def generate_layers_combinations_v3(occupied_positions, container_height, product_quantities):
    """
    生成垂直混合的层数组合
    支持每段有多层不同货品的垂直堆叠

    参数:
        occupied_positions: [(position, product_name), ...]
        container_height: 柜子内高
        product_quantities: 各货品需求数量

    返回:
        生成器，产生各种层数组合
        每个组合格式：[(position, [(layer_index, product_name, layers), ...]), ...]
    """
    from config import LAYER_LIMITS, VERTICAL_MIXING_CONFIG

    # 如果没有启用垂直混合，使用原有逻辑
    if not VERTICAL_MIXING_CONFIG["enabled"]:
        for combo in itertools.product(
            *[
                range(1, int(container_height / PRODUCTS[name]["height"]) + 1)
                for _, name in occupied_positions
            ]
        ):
            yield [(pos, [(0, name, combo[i])]) for i, (pos, name) in enumerate(occupied_positions)]
        return

    # 启用垂直混合：支持5L段下层放其他货品
    main_product = VERTICAL_MIXING_CONFIG["main_product"]  # 通常是"5L"
    max_bottom_layers = VERTICAL_MIXING_CONFIG["max_bottom_layers"]  # 最多2层
    min_top_layers = VERTICAL_MIXING_CONFIG["min_top_layers"]  # 至少3层
    max_top_layers = VERTICAL_MIXING_CONFIG["max_top_layers"]  # 最多7层

    # 确定哪些产品可以作为下层垫底
    bottom_candidates = [name for name in product_quantities.keys() if name != main_product]

    # 为每个位置生成可能的垂直堆叠配置
    position_configs = []

    for pos, name in occupied_positions:
        configs = []

        if name == main_product and bottom_candidates:
            # 主产品段，可以尝试垂直混合
            # 方案1：纯主产品（独立装整段）
            max_independent = LAYER_LIMITS[main_product]["independent"]
            for layers in range(min_top_layers, min(max_independent + 1, int(container_height / PRODUCTS[main_product]["height"]) + 1)):
                configs.append([(0, main_product, layers)])

            # 方案2：垂直混合（下层放其他货品，上层放主产品）
            for bottom_name in bottom_candidates:
                if product_quantities[bottom_name] > 0:
                    # 下层1层
                    bottom_height = PRODUCTS[bottom_name]["height"]
                    remaining_height = container_height - bottom_height
                    max_top = min(max_top_layers, int(remaining_height / PRODUCTS[main_product]["height"]))

                    if max_top >= min_top_layers:  # 确保上层至少能放min_top_layers
                        for top_layers in range(min_top_layers, max_top + 1):
                            configs.append([(0, bottom_name, 1), (1, main_product, top_layers)])

                    # 下层2层
                    if max_bottom_layers >= 2:
                        bottom_height = PRODUCTS[bottom_name]["height"] * 2
                        remaining_height = container_height - bottom_height
                        max_top = min(max_top_layers, int(remaining_height / PRODUCTS[main_product]["height"]))

                        if max_top >= min_top_layers:  # 确保上层至少能放min_top_layers
                            for top_layers in range(min_top_layers, max_top + 1):
                                configs.append([(0, bottom_name, 2), (1, main_product, top_layers)])
        else:
            # 非主产品段，或没有其他货品可用，使用常规逻辑
            max_layers = int(container_height / PRODUCTS[name]["height"])
            for layers in range(1, max_layers + 1):
                configs.append([(0, name, layers)])

        position_configs.append((pos, configs))

    # 生成所有组合的笛卡尔积
    if not position_configs:
        return

    positions = [pc[0] for pc in position_configs]
    configs_lists = [pc[1] for pc in position_configs]

    for combo in itertools.product(*configs_lists):
        yield [(pos, config) for pos, config in zip(positions, combo)]








def calculate_optimal_layout(quantity, container_width, container_height, product_name, max_length_limit=None):
    """
    计算最优布局（尝试所有层数组合和两个方向）

    参数:
        quantity: 需要装载的箱子数量
        container_width: 柜子宽度
        container_height: 柜子高度（或可用高度）
        product_name: 货品名称
        max_length_limit: 最大长度限制（可选，用于超长段处理）

    返回:
        最优布局信息
    """
    product = PRODUCTS[product_name]
    box_l, box_w, box_h = product["length"], product["width"], product["height"]

    # 计算最大可能层数
    max_layers = int(container_height / box_h)

    if max_layers == 0:
        return {"rows": 0, "cols": 0, "total_boxes": 0, "direction": "无", "actual_length": 0,
                "mixed_layout": None}

    best_layout = None
    best_score = -float('inf')

    # 尝试所有可能的层数（从1到max_layers）
    for layers in range(1, max_layers + 1):
        # 每层需要装载的箱子数
        boxes_per_layer = math.ceil(quantity / layers)

        # 计算两种方向的参数
        # 方向1：货品长沿柜子长，宽沿柜子宽
        cols1 = math.floor(container_width / box_w)
        boxes_per_row1 = int(cols1)
        box_length1 = box_l

        # 方向2：货品宽沿柜子长，长沿柜子宽
        cols2 = math.floor(container_width / box_l)
        boxes_per_row2 = int(cols2)
        box_length2 = box_w

        # 尝试方向1（长×宽）
        if cols1 > 0:
            max_rows1 = (boxes_per_layer + boxes_per_row1 - 1) // boxes_per_row1
            actual_length1 = max_rows1 * box_length1
            total_boxes1 = min(quantity, max_rows1 * cols1 * layers)

            # 检查长度限制
            if max_length_limit is None or actual_length1 <= max_length_limit:
                # 计算评分：优先考虑装得更多，其次考虑长度更短
                score1 = total_boxes1 * 10000 - actual_length1

                if score1 > best_score:
                    best_layout = {
                        "rows": int(max_rows1),
                        "cols": int(cols1),
                        "total_boxes": int(total_boxes1),
                        "direction": "长×宽",
                        "actual_length": actual_length1,
                        "mixed_layout": {"type": "single", "row_directions": [1] * max_rows1},
                        "layers": layers
                    }
                    best_score = score1

        # 尝试方向2（宽×长）
        if cols2 > 0:
            max_rows2 = (boxes_per_layer + boxes_per_row2 - 1) // boxes_per_row2
            actual_length2 = max_rows2 * box_length2
            total_boxes2 = min(quantity, max_rows2 * cols2 * layers)

            # 检查长度限制
            if max_length_limit is None or actual_length2 <= max_length_limit:
                # 计算评分
                score2 = total_boxes2 * 10000 - actual_length2

                if score2 > best_score:
                    best_layout = {
                        "rows": int(max_rows2),
                        "cols": int(cols2),
                        "total_boxes": int(total_boxes2),
                        "direction": "宽×长",
                        "actual_length": actual_length2,
                        "mixed_layout": {"type": "single", "row_directions": [2] * max_rows2},
                        "layers": layers
                    }
                    best_score = score2

    if best_layout is None:
        return {"rows": 0, "cols": 0, "total_boxes": 0, "direction": "无", "actual_length": 0,
                "mixed_layout": None}

    # 移除layers字段（调用方不需要）
    if "layers" in best_layout:
        best_layout.pop("layers")

    return best_layout


def calculate_compact_layout(quantity, container_width, segment_height, product_name):
    """
    计算紧凑布局（按需分配长度）
    简化策略：优先单一方向，专注于长度利用率接近100%
    """
    product = PRODUCTS[product_name]
    box_l, box_w, box_h = product["length"], product["width"], product["height"]
    layers = int(segment_height / box_h)

    if layers == 0:
        return {"rows": 0, "cols": 0, "total_boxes": 0, "direction": "无", "actual_length": 0,
                "mixed_layout": None}

    # 每层能放的箱数（向上取整，确保能装下所有箱子）
    boxes_per_layer = math.ceil(quantity / layers)

    # 计算两种方向的参数
    # 方向1：货品长沿柜子长，宽沿柜子宽
    cols1 = math.floor(container_width / box_w)
    boxes_per_row1 = int(cols1)
    box_length1 = box_l

    # 方向2：货品宽沿柜子长，长沿柜子宽
    cols2 = math.floor(container_width / box_l)
    boxes_per_row2 = int(cols2)
    box_length2 = box_w

    # 检查是否至少有一个方向可用
    if cols1 == 0 and cols2 == 0:
        return {"rows": 0, "cols": 0, "total_boxes": 0, "direction": "无", "actual_length": 0,
                "mixed_layout": None}

    # 策略1：优先使用方向1（长×宽）
    if cols1 > 0:
        max_rows1 = (boxes_per_layer + boxes_per_row1 - 1) // boxes_per_row1
        layout1 = {
            "rows": int(max_rows1),
            "cols": int(cols1),
            "total_boxes": int(min(quantity, max_rows1 * cols1 * layers)),
            "direction": "长×宽",
            "actual_length": max_rows1 * box_length1,
            "mixed_layout": {"type": "single", "row_directions": [1] * max_rows1}
        }

        # 如果只有一个方向可用，直接返回
        if cols2 == 0:
            return layout1

        # 计算方向2的布局
        max_rows2 = (boxes_per_layer + boxes_per_row2 - 1) // boxes_per_row2
        layout2 = {
            "rows": int(max_rows2),
            "cols": int(cols2),
            "total_boxes": int(min(quantity, max_rows2 * cols2 * layers)),
            "direction": "宽×长",
            "actual_length": max_rows2 * box_length2,
            "mixed_layout": {"type": "single", "row_directions": [2] * max_rows2}
        }

        # 优先选择能装下所有箱子且长度较短的方向
        if layout1["total_boxes"] >= quantity and layout2["total_boxes"] >= quantity:
            # 都能装下，选长度短的
            return layout1 if layout1["actual_length"] <= layout2["actual_length"] else layout2
        elif layout1["total_boxes"] >= quantity:
            return layout1
        elif layout2["total_boxes"] >= quantity:
            return layout2
        else:
            # 都装不下，选装得多的
            return layout1 if layout1["total_boxes"] >= layout2["total_boxes"] else layout2

    # 策略2：如果方向1不可用，使用方向2
    if cols2 > 0:
        max_rows2 = (boxes_per_layer + boxes_per_row2 - 1) // boxes_per_row2
        return {
            "rows": int(max_rows2),
            "cols": int(cols2),
            "total_boxes": int(min(quantity, max_rows2 * cols2 * layers)),
            "direction": "宽×长",
            "actual_length": max_rows2 * box_length2,
            "mixed_layout": {"type": "single", "row_directions": [2] * max_rows2}
        }

    # 都不可用
    return {"rows": 0, "cols": 0, "total_boxes": 0, "direction": "无", "actual_length": 0,
            "mixed_layout": None}






