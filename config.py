"""
配置文件 - 货品规格和柜子尺寸
"""

# 货品规格（单位：cm）
PRODUCTS = {
    "5L": {"length": 32, "width": 24, "height": 22, "weight": 11.18},  # 重量单位：kg
    "2L": {"length": 37.5, "width": 27.5, "height": 28.5, "weight": 18.54},
    "艾考": {"length": 42.5, "width": 28, "height": 35.5, "weight": 19.86},
}

# 柜子内尺寸（单位：cm）
CONTAINERS = {
    "20尺海运柜": {"length": 589, "width": 235, "height": 239},
    "20尺铁路柜": {"length": 589, "width": 235, "height": 239},
    "40尺海运柜": {"length": 1203, "width": 235, "height": 239},
    "40尺铁路柜": {"length": 1250, "width": 240, "height": 250},
}

# 颜色映射（用于可视化）
COLORS = {
    "5L": "#FFB6C1",      # 浅粉红
    "2L": "#87CEEB",      # 浅蓝
    "艾考": "#98FB98",    # 浅绿
}

# 位置映射
POSITIONS_MAP = {0: "前段", 1: "中段", 2: "后段"}
