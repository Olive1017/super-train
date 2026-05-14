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
            for detail in seg["segment_details"]:
                if detail["total_boxes"] > 0:
                    top_layer = detail
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

            # 计算该层的最大容量（该产品在一层的最大箱子数）
            product = PRODUCTS[layer_name]
            box_l, box_w = product["length"], product["width"]
            max_rows = math.floor(seg["width"] / box_w)
            max_cols = math.floor(seg["width"] / box_l)
            max_boxes = max_rows * max_cols

            if max_boxes == 0:
                continue

            # 计算铺满度
            filled_ratio = min(1.0, (rows * cols) / max_boxes)

            # 根据铺满度给分
            if filled_ratio >= 0.9:
                score += 50
            elif filled_ratio >= 0.8:
                score += 30
        else:
            # 非垂直混合段：直接使用段的信息
            if seg["total_boxes"] == 0:
                continue

            product_name = seg["name"]
            rows = seg["rows"]
            cols = seg["cols"]

            # 计算该产品在一层的最大箱子数
            product = PRODUCTS[product_name]
            box_l, box_w = product["length"], product["width"]
            max_rows = math.floor(seg["width"] / box_w)
            max_cols = math.floor(seg["width"] / box_l)
            max_boxes = max_rows * max_cols

            if max_boxes == 0:
                continue

            # 计算铺满度
            filled_ratio = min(1.0, (rows * cols) / max_boxes)

            # 根据铺满度给分
            if filled_ratio >= 0.9:
                score += 50
            elif filled_ratio >= 0.8:
                score += 30

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
    计算最优装箱方案（按需分配，紧凑装箱）
    
    参数:
        container_type: 柜型
        product_quantities: 货品数量字典 {"5L": 100, "2L": 50, ...}
    
    返回:
        最优装箱方案
    """
    container = CONTAINERS[container_type]
    total_length = container["length"]
    container_width = container["width"]
    
    # 获取实际使用的货品种类（数量>0的）
    used_products = {k: v for k, v in product_quantities.items() if v > 0}
    product_names = list(used_products.keys())
    n_products = len(product_names)
    
    if n_products == 0:
        return None
    if n_products > 3:
        return {"error": "最多支持3种货品混装"}
    
    # 生成所有可能的排列
    if n_products == 1:
        permutations = [product_names]
    elif n_products == 2:
        # 2种货品：只分2段或同种货品分成两段（不再允许空段）
        perms = []

        # 方案1：只分2段
        for perm in itertools.permutations(product_names):
            perms.append(list(perm))

        # 方案2：同种货品分成两段（[A, B, B] 或 [A, A, B]）
        for perm in itertools.permutations(product_names):
            # [A, B, B]
            layout1 = [perm[0], perm[1], perm[1]]
            perms.append(layout1)
            # [A, A, B]
            layout2 = [perm[0], perm[0], perm[1]]
            perms.append(layout2)

        permutations = perms
    else:  # n_products == 3
        permutations = list(itertools.permutations(product_names))
    
    best_solution = None
    best_score = -float('inf')
    total_solutions_checked = 0
    total_feasible_solutions = 0
    
    # 添加调试信息
    print(f"[DEBUG] 开始搜索最优方案，总需求：{sum(product_quantities.values())} 箱")
    
    # 对每个排列计算最优方案
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
    对给定的排列（前中后三段各装什么），寻找最优的长度分配和层数
    采用按需分配策略：先计算每种货品需要的最小长度，再组合
    """
    total_length = container["length"]
    container_width = container["width"]
    total_height = container["height"]

    # 过滤掉空段，生成实际布局字符串
    actual_layout = [x for x in layout if x is not None]
    layout_str = " → ".join(actual_layout)
    print(f"[DEBUG] 正在搜索布局：{layout_str}")
    
    # 确定有货品的段
    occupied_positions = [(i, name) for i, name in enumerate(layout) if name is not None]

    best_allocation = None
    best_score = -float('inf')

    # 生成层数组合（支持垂直混合）
    all_layers_combinations = []
    for layers_config in generate_layers_combinations_v3(occupied_positions, total_height, product_quantities):
        all_layers_combinations.append(layers_config)

    for layers_config in all_layers_combinations:
        # 计算每个段的高度和层配置
        heights = {}
        segment_layer_configs = {}
        for pos, layer_list in layers_config:
            segment_height = 0
            for layer_idx, layer_name, layers in layer_list:
                segment_height += PRODUCTS[layer_name]["height"] * layers
            heights[pos] = segment_height
            segment_layer_configs[pos] = layer_list

        # 恢复高度差约束为硬约束（基于实际操作需求）
        # 计算相邻段的最大高度差
        sorted_heights = [heights[pos] for pos in sorted(heights.keys())]
        max_adjacent_diff = 0
        for i in range(len(sorted_heights) - 1):
            diff = abs(sorted_heights[i] - sorted_heights[i + 1])
            max_adjacent_diff = max(max_adjacent_diff, diff)

        # 硬约束：相邻高度差不能超过50cm（考虑实际操作和安全性）
        MAX_HEIGHT_DIFF = 50  # cm，基于实际操作需求和运输安全
        if max_adjacent_diff > MAX_HEIGHT_DIFF:
            continue  # 高度差过大，直接跳过该方案

        # 按需分配：计算每种货品需要的最小长度（支持垂直混合）
        # 支持同种货品分成多段的情况，以及垂直混合
        segments = []
        total_actual_length = 0

        # 收集每种货品在哪些位置
        product_positions = {}
        for pos, name in occupied_positions:
            if name not in product_positions:
                product_positions[name] = []
            product_positions[name].append(pos)

        # 识别哪些段启用了垂直混合
        vertical_mixed_segments = {}
        for pos, layer_list in segment_layer_configs.items():
            if len(layer_list) > 1:  # 多层配置 = 垂直混合
                vertical_mixed_segments[pos] = layer_list

        # 对每种货品进行分配
        remaining_quantities = product_quantities.copy()  # 剩余需求数量

        # 先分配纯段（非垂直混合的段）
        for name, positions in product_positions.items():
            # 过滤出纯段
            pure_positions = [pos for pos in positions if pos not in vertical_mixed_segments]

            if not pure_positions:
                continue

            total_quantity = remaining_quantities[name]
            num_segments = len(pure_positions)

            if total_quantity <= 0:
                continue

            if num_segments == 1:
                # 只有一段，全部装入
                pos = pure_positions[0]
                segment_height = heights[pos]

                boxes_info = calculate_compact_layout(
                    total_quantity, container_width, segment_height, name
                )

                if boxes_info["actual_length"] > total_length:
                    # 单段就超过柜子长度，跳过
                    break

                segments.append({
                    "position": pos,
                    "name": name,
                    "actual_length": boxes_info["actual_length"],
                    "width": container_width,
                    "height": segment_height,
                    "layers": int(segment_height / PRODUCTS[name]["height"]),
                    "rows": boxes_info["rows"],
                    "cols": boxes_info["cols"],
                    "total_boxes": boxes_info["total_boxes"],
                    "direction": boxes_info["direction"],
                    "layers_config": [(0, name, int(segment_height / PRODUCTS[name]["height"]))]
                })
                total_actual_length += boxes_info["actual_length"]
                remaining_quantities[name] = total_quantity - boxes_info["total_boxes"]
            else:
                # 多段，尝试多种分配比例
                best_multi_segment_allocation = None
                best_multi_segment_length = float('inf')

                # 尝试不同的分配比例（确保总数量不变）
                for allocation in distribute_quantity(total_quantity, num_segments):
                    feasible = True
                    temp_segments = []
                    temp_length = 0

                    for i, pos in enumerate(pure_positions):
                        segment_height = heights[pos]
                        quantity = allocation[i]

                        boxes_info = calculate_compact_layout(
                            quantity, container_width, segment_height, name
                        )

                        if boxes_info["actual_length"] > total_length:
                            feasible = False
                            break

                        temp_segments.append({
                            "position": pos,
                            "name": name,
                            "actual_length": boxes_info["actual_length"],
                            "width": container_width,
                            "height": segment_height,
                            "layers": int(segment_height / PRODUCTS[name]["height"]),
                            "rows": boxes_info["rows"],
                            "cols": boxes_info["cols"],
                            "total_boxes": boxes_info["total_boxes"],
                            "direction": boxes_info["direction"],
                            "layers_config": [(0, name, int(segment_height / PRODUCTS[name]["height"]))]
                        })
                        temp_length += boxes_info["actual_length"]

                    if feasible and temp_length < best_multi_segment_length:
                        best_multi_segment_allocation = temp_segments
                        best_multi_segment_length = temp_length

                if best_multi_segment_allocation is None:
                    break

                segments.extend(best_multi_segment_allocation)
                total_actual_length += best_multi_segment_length
                remaining_quantities[name] = 0  # 假设全部装完

        # 再分配垂直混合段
        for pos, layer_list in vertical_mixed_segments.items():
            segment_height = heights[pos]
            segment_length = 0
            segment_boxes = 0
            segment_details = []

            # 为每一层分配箱数
            for layer_idx, layer_name, layers in layer_list:
                layer_height = PRODUCTS[layer_name]["height"] * layers
                layer_quantity = remaining_quantities.get(layer_name, 0)

                if layer_quantity <= 0:
                    # 没有需求，但保留空层占位
                    segment_details.append({
                        "layer_index": layer_idx,
                        "product_name": layer_name,
                        "layers": layers,
                        "height": layer_height,
                        "rows": 0,
                        "cols": 0,
                        "total_boxes": 0,
                        "direction": "无",
                        "actual_length": 0
                    })
                    continue

                # 计算该层能装的箱数
                max_boxes_per_layer = (container_width / PRODUCTS[layer_name]["width"]) * (container_width / PRODUCTS[layer_name]["length"])  # 粗略估计
                max_boxes = max_boxes_per_layer * layers

                # 按需求分配
                boxes_to_load = min(layer_quantity, max_boxes)

                if boxes_to_load <= 0:
                    segment_details.append({
                        "layer_index": layer_idx,
                        "product_name": layer_name,
                        "layers": layers,
                        "height": layer_height,
                        "rows": 0,
                        "cols": 0,
                        "total_boxes": 0,
                        "direction": "无",
                        "actual_length": 0
                    })
                    continue

                # 计算该层的布局
                boxes_info = calculate_compact_layout(
                    boxes_to_load, container_width, layer_height, layer_name
                )

                segment_length = max(segment_length, boxes_info["actual_length"])  # 取最大长度
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
                    "actual_length": boxes_info["actual_length"]
                })

            # 创建垂直混合段
            main_product_name = layer_list[0][1]  # 取第一层的名称（应该是主产品）
            segments.append({
                "position": pos,
                "name": main_product_name,
                "actual_length": segment_length,
                "width": container_width,
                "height": segment_height,
                "layers": sum(layers for _, _, layers in layer_list),
                "rows": max((sd["rows"] for sd in segment_details), default=0),
                "cols": max((sd["cols"] for sd in segment_details), default=0),
                "total_boxes": segment_boxes,
                "direction": "垂直混合",
                "layers_config": layer_list,
                "segment_details": segment_details
            })
            total_actual_length += segment_length
        
        # 所有段都能放下，检查总长度
        if total_actual_length <= total_length:
            loaded_count = sum(seg["total_boxes"] for seg in segments)

            # 计算重量中心偏差
            weight_center, weight_deviation = calculate_weight_center(segments, total_length)

            # 计算顶层铺满度评分
            top_layer_score = calculate_top_layer_filled_score(segments)

            # 计算总分（装载数量优先，空间利用率次之）
            score = loaded_count * 1000
            score += (total_actual_length / total_length) * 50  # 奖励空间利用率

            # 检查是否装下了所有货品
            total_required = sum(product_quantities.values())
            if loaded_count < total_required:
                # 未装下所有箱子，大幅降低分数
                # 这样如果没有方案能装下800箱，至少会返回装得最多的方案
                missing = total_required - loaded_count
                score -= missing * 2000  # 大幅扣分，但仍保留参与比较的机会
                # 添加调试信息
                if best_allocation is None or loaded_count > best_allocation.get('total_loaded', 0):
                    pass  # 这是目前找到的最多箱子数量

            # 重量中心评分优化：偏差越小越好
            # 偏差≤10cm时给予额外奖励
            if weight_deviation <= 10:
                score += 200  # 重心偏差小，大幅奖励
            else:
                score -= weight_deviation * 20  # 偏差越大，扣分越多

            # 奖励5L在中间段（轻的放中间，重的放两侧）
            if layout[1] == "5L":
                score += 150  # 5L在中间段，额外奖励

            # 奖励顶层铺满（每段铺满度>=90%奖励50分，>=80%奖励30分）
            score += top_layer_score

            allocation = {
                "layout": list(layout),
                "segments": segments,
                "score": score,
                "total_loaded": loaded_count,
                "weight_center": weight_center,
                "weight_deviation": weight_deviation,
                "max_adjacent_height_diff": max_adjacent_diff
            }

            if score > best_score:
                best_allocation = allocation
                best_score = score
                # 添加调试信息
                print(f"[DEBUG] 找到更好方案：{loaded_count} 箱，得分：{score:.2f}")

    # 返回前添加调试信息
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

                    for top_layers in range(min_top_layers, max_top + 1):
                        configs.append([(0, bottom_name, 1), (1, main_product, top_layers)])

                    # 下层2层
                    if max_bottom_layers >= 2:
                        bottom_height = PRODUCTS[bottom_name]["height"] * 2
                        remaining_height = container_height - bottom_height
                        max_top = min(max_top_layers, int(remaining_height / PRODUCTS[main_product]["height"]))

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


def calculate_compact_layout_v3(layers_config, container_width, container_height, product_quantities):
    """
    计算垂直混合的紧凑布局

    参数:
        layers_config: 该段的层配置，格式 [(layer_index, product_name, layers), ...]
        container_width: 柜子宽度
        container_height: 柜子高度
        product_quantities: 各货品需求数量

    返回:
        布局信息字典
    """
    total_actual_length = 0
    total_boxes = 0
    segment_details = []

    for layer_idx, product_name, layers in layers_config:
        # 计算该层的高度
        layer_height = PRODUCTS[product_name]["height"] * layers

        # 该层需要的箱数（向上取整，确保至少1层）
        if total_boxes == 0:
            # 第一层，计算需要的箱数
            boxes_per_layer = (product_quantities[product_name] + layers - 1) // layers
        else:
            # 后续层，暂时按0箱计算（实际使用时会更精确）
            boxes_per_layer = 0

        # 计算该层的布局
        layout_info = calculate_compact_layout(
            boxes_per_layer, container_width, layer_height, product_name
        )

        total_actual_length += layout_info["actual_length"]
        total_boxes += layout_info["total_boxes"]
        segment_details.append({
            "layer_index": layer_idx,
            "product_name": product_name,
            "layers": layers,
            "height": layer_height,
            "rows": layout_info["rows"],
            "cols": layout_info["cols"],
            "total_boxes": layout_info["total_boxes"],
            "direction": layout_info["direction"],
            "actual_length": layout_info["actual_length"]
        })

    return {
        "total_actual_length": total_actual_length,
        "total_boxes": total_boxes,
        "segment_details": segment_details,
        "mixed_layout": {
            "type": "vertical_mixing",
            "layers": segment_details
        }
    }


def distribute_quantity(total_quantity, num_segments):
    """
    将总数量分配到多个段，生成合理的分配方案
    确保每段至少有1箱，且总和等于total_quantity
    
    参数:
        total_quantity: 总箱数
        num_segments: 段数
    
    返回:
        生成器，产生各种分配方案
    """
    if num_segments == 1:
        yield [total_quantity]
        return
    
    base = total_quantity // num_segments
    remainder = total_quantity % num_segments
    
    # 方案1: 等分方案（将余数均匀分配到前几段）
    allocation = [base] * num_segments
    for i in range(remainder):
        allocation[i] += 1
    yield allocation
    
    # 方案2: 基于比例的分配（考虑段间容量差异）
    # 生成2:1, 3:1, 3:2等常见比例
    ratios = []
    if num_segments == 2:
        ratios = [
            [2, 1],  # 2:1
            [3, 1],  # 3:1
            [3, 2],  # 3:2
            [4, 1],  # 4:1
            [5, 2],  # 5:2
        ]
    elif num_segments == 3:
        ratios = [
            [2, 1, 1],  # 2:1:1
            [3, 1, 1],  # 3:1:1
            [3, 2, 1],  # 3:2:1
            [2, 2, 1],  # 2:2:1
            [4, 1, 1],  # 4:1:1
        ]
    
    for ratio in ratios:
        total_ratio = sum(ratio)
        allocation = []
        remaining = total_quantity
        for i in range(num_segments - 1):
            boxes = int(total_quantity * ratio[i] / total_ratio)
            if boxes < 1:
                boxes = 1
            allocation.append(boxes)
            remaining -= boxes
        allocation.append(max(1, remaining))
        
        # 调整使总和正确
        diff = total_quantity - sum(allocation)
        if diff != 0:
            for i in range(num_segments):
                if allocation[i] + diff >= 1:
                    allocation[i] += diff
                    break
        
        if sum(allocation) == total_quantity and all(x >= 1 for x in allocation):
            equal_allocation = [base + (1 if i < remainder else 0) for i in range(num_segments)]
            if allocation != equal_allocation:
                yield allocation
    
    # 方案3: 将一些箱从第一段移到其他段（渐进式调整）
    if total_quantity >= num_segments * 2:
        for shift in range(1, min(num_segments, base)):  # 限制shift不超过base-1
            allocation = [base] * num_segments
            allocation[0] = base + remainder + shift
            allocation[shift] = base - shift
            if allocation[shift] >= 1:
                yield allocation
    
    # 方案4: 将一些箱从最后一段移到其他段
    if total_quantity >= num_segments * 2:
        for shift in range(1, min(num_segments, base)):
            allocation = [base] * num_segments
            for i in range(remainder):
                allocation[i] += 1
            allocation[-1] = base - shift
            allocation[-(shift + 1)] = base + shift
            if allocation[-1] >= 1:
                yield allocation


def calculate_compact_layout(quantity, container_width, segment_height, product_name):
    """
    计算紧凑布局（按需分配长度）
    优化后的混合方向摆放策略：
    1. 前面用方向1，后面用方向2（前后分段混合）
    2. 前面用方向2，后面用方向1（前后分段混合）
    3. 隔行混合（行级混合，支持多种不等比例）
    """
    product = PRODUCTS[product_name]
    box_l, box_w, box_h = product["length"], product["width"], product["height"]
    layers = int(segment_height / box_h)
    
    if layers == 0:
        return {"rows": 0, "cols": 0, "total_boxes": 0, "direction": "无", "actual_length": 0,
                "mixed_layout": None}
    
    # 每层能放的箱数
    boxes_per_layer = (quantity + layers - 1) // layers  # 向上取整
    boxes_per_layer = int(boxes_per_layer)  # 确保是整数
    
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
    
    # 如果只有一个方向可用，直接使用该方向（作为后备方案）
    if cols1 > 0 and cols2 == 0:
        max_rows1 = (boxes_per_layer + boxes_per_row1 - 1) // boxes_per_row1
        return {
            "rows": int(max_rows1),
            "cols": int(cols1),
            "total_boxes": int(min(quantity, max_rows1 * cols1 * layers)),
            "direction": "长×宽",
            "actual_length": max_rows1 * box_length1,
            "mixed_layout": {"type": "single", "row_directions": [1] * max_rows1}
        }
    
    if cols2 > 0 and cols1 == 0:
        max_rows2 = (boxes_per_layer + boxes_per_row2 - 1) // boxes_per_row2
        return {
            "rows": int(max_rows2),
            "cols": int(cols2),
            "total_boxes": int(min(quantity, max_rows2 * cols2 * layers)),
            "direction": "宽×长",
            "actual_length": max_rows2 * box_length2,
            "mixed_layout": {"type": "single", "row_directions": [2] * max_rows2}
        }
    
    # 两个方向都可用，使用混合策略
    best_length = float('inf')
    best_layout = None
    
    # 策略1: 前面用方向1，后面用方向2（前后分段混合）
    # 优化：优先测试黄金比例分割点
    max_rows1 = int((boxes_per_layer + boxes_per_row1 - 1) // boxes_per_row1)
    # 生成有效的黄金比例点（至少为1，且小于最大值）
    golden_ratios = []
    for r in [0.382, 0.5, 0.618]:
        rows_candidate = int(max_rows1 * r)
        if rows_candidate >= 1 and rows_candidate < max_rows1:
            golden_ratios.append(rows_candidate)
    # 如果没有有效的黄金比例点，添加默认值
    if not golden_ratios and max_rows1 > 1:
        golden_ratios = [max_rows1 // 2]

    # 先测试关键分割点
    for rows1 in golden_ratios:
        rows1 = int(rows1)  # 确保是整数
        boxes_in_rows1 = min(boxes_per_layer, rows1 * boxes_per_row1)
        boxes_remaining = boxes_per_layer - boxes_in_rows1

        if boxes_remaining > 0:
            rows2 = int((boxes_remaining + boxes_per_row2 - 1) // boxes_per_row2)
            total_length = rows1 * box_length1 + rows2 * box_length2

            if total_length < best_length:
                best_length = total_length
                row_directions = [1] * rows1 + [2] * rows2
                best_layout = {
                    "rows": int(rows1 + rows2),
                    "cols": int(max(cols1, cols2)),
                    "total_boxes": int(min(quantity, (boxes_in_rows1 + rows2 * boxes_per_row2) * layers)),
                    "direction": "混合(前1后2)",
                    "actual_length": total_length,
                    "mixed_layout": {
                        "type": "front_back",
                        "break_point": rows1,
                        "row_directions": row_directions,
                        "row_breaks": [rows1]
                    }
                }
    
    # 如果关键点没找到，再穷举其他分割点
    for rows1 in range(max_rows1 + 1):
        if rows1 in golden_ratios:
            continue
        if rows1 == 0:  # 跳过0行
            continue
        boxes_in_rows1 = min(boxes_per_layer, rows1 * boxes_per_row1)
        boxes_remaining = boxes_per_layer - boxes_in_rows1

        if boxes_remaining > 0:
            rows2 = int((boxes_remaining + boxes_per_row2 - 1) // boxes_per_row2)
            total_length = rows1 * box_length1 + rows2 * box_length2

            if total_length < best_length:
                best_length = total_length
                row_directions = [1] * rows1 + [2] * rows2
                best_layout = {
                    "rows": int(rows1 + rows2),
                    "cols": int(max(cols1, cols2)),
                    "total_boxes": int(min(quantity, (boxes_in_rows1 + rows2 * boxes_per_row2) * layers)),
                    "direction": "混合(前1后2)",
                    "actual_length": total_length,
                    "mixed_layout": {
                        "type": "front_back",
                        "break_point": rows1,
                        "row_directions": row_directions,
                        "row_breaks": [rows1]
                    }
                }
    
    # 策略2: 前面用方向2，后面用方向1（前后分段混合）
    max_rows2 = int((boxes_per_layer + boxes_per_row2 - 1) // boxes_per_row2)
    # 生成有效的黄金比例点（至少为1，且小于最大值）
    golden_ratios_2 = []
    for r in [0.382, 0.5, 0.618]:
        rows_candidate = int(max_rows2 * r)
        if rows_candidate >= 1 and rows_candidate < max_rows2:
            golden_ratios_2.append(rows_candidate)
    # 如果没有有效的黄金比例点，添加默认值
    if not golden_ratios_2 and max_rows2 > 1:
        golden_ratios_2 = [max_rows2 // 2]
    
    for rows2 in golden_ratios_2:
        rows2 = int(rows2)  # 确保是整数
        boxes_in_rows2 = min(boxes_per_layer, rows2 * boxes_per_row2)
        boxes_remaining = boxes_per_layer - boxes_in_rows2

        if boxes_remaining > 0:
            rows1 = int((boxes_remaining + boxes_per_row1 - 1) // boxes_per_row1)
            total_length = rows2 * box_length2 + rows1 * box_length1

            if total_length < best_length:
                best_length = total_length
                row_directions = [2] * rows2 + [1] * rows1
                best_layout = {
                    "rows": int(rows1 + rows2),
                    "cols": int(max(cols1, cols2)),
                    "total_boxes": int(min(quantity, (boxes_in_rows2 + rows1 * boxes_per_row1) * layers)),
                    "direction": "混合(前2后1)",
                    "actual_length": total_length,
                    "mixed_layout": {
                        "type": "front_back",
                        "break_point": rows2,
                        "row_directions": row_directions,
                        "row_breaks": [rows2]
                    }
                }

    for rows2 in range(max_rows2 + 1):
        if rows2 in golden_ratios_2:
            continue
        if rows2 == 0:  # 跳过0行
            continue
        boxes_in_rows2 = min(boxes_per_layer, rows2 * boxes_per_row2)
        boxes_remaining = boxes_per_layer - boxes_in_rows2

        if boxes_remaining > 0:
            rows1 = int((boxes_remaining + boxes_per_row1 - 1) // boxes_per_row1)
            total_length = rows2 * box_length2 + rows1 * box_length1

            if total_length < best_length:
                best_length = total_length
                row_directions = [2] * rows2 + [1] * rows1
                best_layout = {
                    "rows": int(rows1 + rows2),
                    "cols": int(max(cols1, cols2)),
                    "total_boxes": int(min(quantity, (boxes_in_rows2 + rows1 * boxes_per_row1) * layers)),
                    "direction": "混合(前2后1)",
                    "actual_length": total_length,
                    "mixed_layout": {
                        "type": "front_back",
                        "break_point": rows2,
                        "row_directions": row_directions,
                        "row_breaks": [rows2]
                    }
                }
    
    # 策略3: 隔行混合（优化版：支持多种不等比例）
    # 扩展比例范围，支持更多不等比例混合
    ratio_pairs = [
        (1, 1),  # 1行A + 1行B
        (2, 1),  # 2行A + 1行B
        (1, 2),  # 1行A + 2行B
        (2, 2),  # 2行A + 2行B
        (3, 1),  # 3行A + 1行B
        (1, 3),  # 1行A + 3行B
        (3, 2),  # 3行A + 2行B
        (2, 3),  # 2行A + 3行B
        (3, 3),  # 3行A + 3行B
        (4, 1),  # 4行A + 1行B
        (1, 4),  # 1行A + 4行B
        (4, 2),  # 4行A + 2行B
        (2, 4),  # 2行A + 4行B
        (4, 3),  # 4行A + 3行B
        (3, 4),  # 3行A + 4行B
        (4, 4),  # 4行A + 4行B
    ]
    
    for rows_dir1, rows_dir2 in ratio_pairs:
        boxes_per_pattern = rows_dir1 * boxes_per_row1 + rows_dir2 * boxes_per_row2
        if boxes_per_pattern == 0:
            continue
        
        # 计算需要多少个完整pattern
        full_patterns = int(boxes_per_layer // boxes_per_pattern)
        remaining_boxes = int(boxes_per_layer % boxes_per_pattern)
        
        # 完整pattern的总行数和长度
        full_pattern_rows = int(full_patterns * (rows_dir1 + rows_dir2))
        full_pattern_length = full_patterns * (rows_dir1 * box_length1 + rows_dir2 * box_length2)

        # 处理剩余的箱子（优化：尝试多种策略）
        if remaining_boxes > 0:
            # 策略A: 全用方向1
            extra_rows1_needed = int((remaining_boxes + boxes_per_row1 - 1) // boxes_per_row1)
            length1_only = extra_rows1_needed * box_length1
            row_directions_1 = [1] * (full_pattern_rows + extra_rows1_needed)

            if full_pattern_length + length1_only < best_length:
                best_length = full_pattern_length + length1_only
                # 构建完整的行方向列表
                row_directions = []
                for _ in range(int(full_patterns)):
                    row_directions.extend([1] * rows_dir1 + [2] * rows_dir2)
                row_directions.extend([1] * extra_rows1_needed)
                
                best_layout = {
                    "rows": int(full_pattern_rows + extra_rows1_needed),
                    "cols": int(max(cols1, cols2)),
                    "total_boxes": int(min(quantity, boxes_per_layer * layers)),
                    "direction": f"混合(隔行{rows_dir1}+{rows_dir2})",
                    "actual_length": full_pattern_length + length1_only,
                    "mixed_layout": {
                        "type": "alternating_rows",
                        "pattern": (rows_dir1, rows_dir2),
                        "full_patterns": full_patterns,
                        "remaining_strategy": "dir1_only",
                        "row_directions": row_directions
                    }
                }
            
            # 策略B: 全用方向2
            extra_rows2_needed = int((remaining_boxes + boxes_per_row2 - 1) // boxes_per_row2)
            length2_only = extra_rows2_needed * box_length2

            if full_pattern_length + length2_only < best_length:
                best_length = full_pattern_length + length2_only
                # 构建完整的行方向列表
                row_directions = []
                for _ in range(int(full_patterns)):
                    row_directions.extend([1] * rows_dir1 + [2] * rows_dir2)
                row_directions.extend([2] * extra_rows2_needed)
                
                best_layout = {
                    "rows": int(full_pattern_rows + extra_rows2_needed),
                    "cols": int(max(cols1, cols2)),
                    "total_boxes": int(min(quantity, boxes_per_layer * layers)),
                    "direction": f"混合(隔行{rows_dir1}+{rows_dir2})",
                    "actual_length": full_pattern_length + length2_only,
                    "mixed_layout": {
                        "type": "alternating_rows",
                        "pattern": (rows_dir1, rows_dir2),
                        "full_patterns": full_patterns,
                        "remaining_strategy": "dir2_only",
                        "row_directions": row_directions
                    }
                }
            
            # 策略C: 小比例隔行混合（1:1 或 1:2 或 2:1）
            micro_patterns = [(1, 1), (1, 2), (2, 1)]
            for micro_rows1, micro_rows2 in micro_patterns:
                micro_boxes_per_pattern = micro_rows1 * boxes_per_row1 + micro_rows2 * boxes_per_row2
                if micro_boxes_per_pattern == 0:
                    continue
                
                micro_full_patterns = int(remaining_boxes // micro_boxes_per_pattern)
                micro_remaining = int(remaining_boxes % micro_boxes_per_pattern)

                if micro_full_patterns > 0:
                    micro_rows = micro_full_patterns * (micro_rows1 + micro_rows2)
                    micro_length = micro_full_patterns * (micro_rows1 * box_length1 + micro_rows2 * box_length2)
                    
                    # 处理micro剩余
                    if micro_remaining > 0:
                        extra_rows1_micro = int((micro_remaining + boxes_per_row1 - 1) // boxes_per_row1)
                        extra_length_micro = extra_rows1_micro * box_length1
                    else:
                        extra_rows1_micro = 0
                        extra_length_micro = 0
                    
                    total_length = full_pattern_length + micro_length + extra_length_micro
                    total_rows = full_pattern_rows + micro_rows + extra_rows1_micro
                    
                    if total_length < best_length:
                        best_length = total_length
                        # 构建完整的行方向列表
                        row_directions = []
                        for _ in range(int(full_patterns)):
                            row_directions.extend([1] * rows_dir1 + [2] * rows_dir2)
                        for _ in range(int(micro_full_patterns)):
                            row_directions.extend([1] * micro_rows1 + [2] * micro_rows2)
                        row_directions.extend([1] * extra_rows1_micro)
                        
                        best_layout = {
                            "rows": int(total_rows),
                            "cols": int(max(cols1, cols2)),
                            "total_boxes": int(min(quantity, boxes_per_layer * layers)),
                            "direction": f"混合(隔行{rows_dir1}+{rows_dir2})",
                            "actual_length": total_length,
                            "mixed_layout": {
                                "type": "alternating_rows",
                                "pattern": (rows_dir1, rows_dir2),
                                "full_patterns": full_patterns,
                                "remaining_strategy": f"micro_{micro_rows1}+{micro_rows2}",
                                "row_directions": row_directions
                            }
                        }
        else:
            # 没有剩余箱子，完美匹配
            total_length = full_pattern_length
            total_rows = full_pattern_rows

            if total_length < best_length:
                best_length = total_length
                # 构建完整的行方向列表
                row_directions = []
                for _ in range(int(full_patterns)):
                    row_directions.extend([1] * rows_dir1 + [2] * rows_dir2)
                
                best_layout = {
                    "rows": int(total_rows),
                    "cols": int(max(cols1, cols2)),
                    "total_boxes": int(min(quantity, boxes_per_layer * layers)),
                    "direction": f"混合(隔行{rows_dir1}+{rows_dir2})",
                    "actual_length": total_length,
                    "mixed_layout": {
                        "type": "alternating_rows",
                        "pattern": (rows_dir1, rows_dir2),
                        "full_patterns": full_patterns,
                        "remaining_strategy": "none",
                        "row_directions": row_directions
                    }
                }
    
    return best_layout if best_layout else {"rows": 0, "cols": 0, "total_boxes": 0, "direction": "无", "actual_length": 0,
                                            "mixed_layout": None}


def calculate_boxes_in_segment(segment_length, segment_width, segment_height, product_name):
    """
    计算在一个段内能装多少箱货品（给定长度限制）
    """
    product = PRODUCTS[product_name]
    box_l, box_w = product["length"], product["width"]
    layers = int(segment_height / product["height"])
    
    if layers == 0:
        return {"rows": 0, "cols": 0, "total_boxes": 0, "direction": "长×宽", "actual_length": 0}
    
    # 尝试两种摆放方向
    results = []
    
    # 方向1：货品长沿柜子长，宽沿柜子宽
    rows1 = segment_length // box_l
    cols1 = segment_width // box_w
    total1 = rows1 * cols1 * layers
    actual_length1 = rows1 * box_l
    results.append({
        "rows": int(rows1),
        "cols": int(cols1),
        "total_boxes": int(total1),
        "direction": "长×宽",
        "actual_length": actual_length1
    })
    
    # 方向2：货品宽沿柜子长，长沿柜子宽
    rows2 = segment_length // box_w
    cols2 = segment_width // box_l
    total2 = rows2 * cols2 * layers
    actual_length2 = rows2 * box_w
    results.append({
        "rows": int(rows2),
        "cols": int(cols2),
        "total_boxes": int(total2),
        "direction": "宽×长",
        "actual_length": actual_length2
    })
    
    # 选择能装更多的方向
    best = max(results, key=lambda x: x["total_boxes"])
    return best


def calculate_actual_length(rows, cols, direction, product_name):
    """
    根据行列数和方向计算实际使用的长度
    """
    product = PRODUCTS[product_name]
    if direction == "长×宽":
        return rows * product["length"]
    else:
        return rows * product["width"]
