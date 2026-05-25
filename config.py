"""
配置文件 - 货品规格和柜子尺寸
"""

# 货品规格（单位：cm）
# width: 沿柜宽方向
# depth: 沿柜长方向
# height: 竖高方向
PRODUCTS = {
    "5L": {"width": 32, "depth": 24, "height": 22, "weight": 11.18, "max_layers": 7, "color": "#4A90E2"},
    "2L": {"width": 37.5, "depth": 27.5, "height": 28.5, "weight": 18.54, "max_layers": 8, "color": "#F5A623"},
    "艾考": {"width": 28, "depth": 42.5, "height": 35.5, "weight": 19.86, "max_layers": 6, "color": "#7ED321"},
}

# 柜子内尺寸（单位：cm）
CONTAINERS = {
    "20尺海运柜": {"length": 589, "width": 235, "height": 239},
    "20尺铁路柜": {"length": 589, "width": 235, "height": 239},
    "40尺海运柜": {"length": 1203, "width": 235, "height": 239},
    "40尺铁路柜": {"length": 1250, "width": 240, "height": 250},
}

# 垂直混合装载配置
VERTICAL_MIXING_CONFIG = {
    "enabled": True,
    "main_product": "5L",
    "max_bottom_layers": 2,
    "min_top_layers": 3,
    "max_top_layers": 7
}
