"""骨骼动画：Live2D 式分层骨骼，让四肢独立动起来（纯本地，零 API）。

原理：把抠出的图按用户框选的部位（头/躯干/左右手/左右腿）切成若干子图，
每个部位围绕自己的关节锚点做周期性旋转/平移，叠加出走路、挥手等动作。

坐标约定：骨骼配置里的部位矩形用相对比例（0~1），锚点用相对矩形的比例。
"""
import math


# 每个部位锚点在矩形内的相对位置（默认值，可按部位类型覆盖）
DEFAULT_PIVOT = {"x": 0.5, "y": 0.5}


def build_skeleton(source_size, parts: list) -> list:
    """把比例坐标转成像素坐标的骨骼部位。

    parts: [{"name", "x", "y", "w", "h", "pivot_x", "pivot_y"}, ...]
    返回像素坐标的列表，每项含 (x, y, w, h, px, py) 和 name。
    """
    W, H = source_size
    result = []
    for p in parts:
        x = int(p["x"] * W)
        y = int(p["y"] * H)
        w = max(1, int(p["w"] * W))
        h = max(1, int(p["h"] * H))
        px = x + int(p.get("pivot_x", 0.5) * w)
        py = y + int(p.get("pivot_y", 0.5) * h)
        result.append({
            "name": p.get("name", ""),
            "x": x, "y": y, "w": w, "h": h,
            "pivot_x": px, "pivot_y": py,
        })
    return result


def compute_pose(parts, action: str, phase: float) -> list:
    """根据动作和相位，计算每个部位的 (angle_deg, dx, dy)。

    phase 用弧度，随时间递增。返回与 parts 同长度的 pose 列表。
    """
    poses = []
    t = phase
    # 各动作的摆动幅度（度）
    if action == "walk":
        # 走路：左右手/左右腿交替摆动，身体轻微上下颠簸
        amp = 25.0
        for p in parts:
            name = p["name"]
            ang = 0.0
            dy = 0.0
            if name in ("left_arm", "left_leg"):
                ang = amp * math.sin(t)
            elif name in ("right_arm", "right_leg"):
                ang = -amp * math.sin(t)
            elif name == "body":
                dy = 2.0 * abs(math.sin(t))
                ang = 3.0 * math.sin(t)
            elif name == "head":
                ang = 5.0 * math.sin(t)
            poses.append((ang, 0.0, dy))
    elif action == "wave":
        # 挥手：右臂大幅上下摆动，其他轻微
        for p in parts:
            name = p["name"]
            ang = 0.0
            dy = 0.0
            if name == "right_arm":
                ang = 50.0 * math.sin(t)
            elif name == "left_arm":
                ang = -8.0 * math.sin(t)
            elif name == "head":
                ang = 4.0 * math.sin(t)
            poses.append((ang, 0.0, dy))
    elif action == "jump":
        # 跳跃：手脚上抬
        for p in parts:
            name = p["name"]
            ang = 0.0
            dy = 0.0
            if name in ("left_arm", "right_arm"):
                ang = -30.0 * abs(math.sin(t))
            elif name in ("left_leg", "right_leg"):
                ang = 20.0 * abs(math.sin(t))
            poses.append((ang, 0.0, dy))
    elif action == "dance":
        # 跳舞：全身大幅扭动
        for p in parts:
            name = p["name"]
            ang = 0.0
            dy = 0.0
            if name in ("left_arm", "right_leg"):
                ang = 40.0 * math.sin(t)
            elif name in ("right_arm", "left_leg"):
                ang = -40.0 * math.sin(t)
            elif name == "body":
                ang = 12.0 * math.sin(t * 0.7)
            elif name == "head":
                ang = 15.0 * math.sin(t * 1.3)
            poses.append((ang, 0.0, dy))
    elif action == "idle":
        # 呼吸/待机：轻微晃动
        for p in parts:
            ang = 0.0
            dy = 1.5 * math.sin(t)
            poses.append((ang, 0.0, dy))
    else:
        # 默认：轻微摆动所有"肢体"部位
        for p in parts:
            name = p["name"]
            if name in ("left_arm", "right_arm", "left_leg", "right_leg"):
                ang = 15.0 * math.sin(t)
            else:
                ang = 0.0
            poses.append((ang, 0.0, 0.0))
    return poses


# 部位名称 → 中文标签（编辑器和 UI 显示用）
PART_LABELS = {
    "head": "头部",
    "body": "躯干",
    "left_arm": "左手臂",
    "right_arm": "右手臂",
    "left_leg": "左腿",
    "right_leg": "右腿",
}

# 部位默认锚点（相对矩形）：手/腿锚在顶部（连接身体），头锚在底部，躯干锚在中心
PART_PIVOTS = {
    "head": {"x": 0.5, "y": 1.0},
    "body": {"x": 0.5, "y": 0.5},
    "left_arm": {"x": 0.5, "y": 0.1},
    "right_arm": {"x": 0.5, "y": 0.1},
    "left_leg": {"x": 0.5, "y": 0.1},
    "right_leg": {"x": 0.5, "y": 0.1},
}
