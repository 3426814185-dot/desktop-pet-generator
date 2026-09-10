"""桌面宠配置：持久化 API 配置、人设、历史桌宠记录。"""
import json
import os
import time
from dataclasses import dataclass, asdict, field

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".desktop-pet")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
HISTORY_PATH = os.path.join(CONFIG_DIR, "history.json")
AVATAR_DIR = os.path.join(CONFIG_DIR, "avatars")


@dataclass
class Config:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"          # 视觉/聊天通用模型
    image_model: str = "gpt-image-1"    # 图像生成模型（生成动作帧用）
    # 识别结果（人设）
    name: str = "小宠物"
    species: str = ""
    personality: str = ""
    appearance: str = ""
    # 用户自定义的打招呼语（额外追加到默认列表）
    greet_msgs: list = field(default_factory=list)


def load_config() -> Config:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Config(**{k: data.get(k, v) for k, v in asdict(Config()).items()})
        except Exception:
            pass
    return Config()


def save_config(cfg: Config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- 历史记录
def load_history() -> list:
    """加载历史桌宠列表。文件损坏或不存在时返回空列表，绝不让程序崩溃。"""
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                # 只保留 avatar_path 仍然存在的条目，清理失效记录
                return [d for d in data if isinstance(d, dict)
                        and d.get("avatar_path") and os.path.exists(d["avatar_path"])]
        except Exception:
            return []
    return []


def save_history(entries: list):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 写失败不影响主流程


def add_history(entry: dict):
    entries = load_history()
    # 去重：同 id 覆盖
    entries = [e for e in entries if e.get("id") != entry.get("id")]
    entries.insert(0, entry)  # 最新在前
    # 最多保留 50 条，防止无限增长
    save_history(entries[:50])


def remove_history(entry_id: str):
    entries = [e for e in load_history() if e.get("id") != entry_id]
    save_history(entries)


def new_avatar_path() -> str:
    """生成唯一的头像文件路径（时间戳命名，避免覆盖已有桌宠）。"""
    os.makedirs(AVATAR_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    return os.path.join(AVATAR_DIR, f"pet_{ts}.png")


# ---------------------------------------------------------------- 骨骼配置
BONE_DIR = os.path.join(CONFIG_DIR, "bones")


def _bone_path(pet_id: str) -> str:
    return os.path.join(BONE_DIR, f"{pet_id}.json")


def load_bones(pet_id: str) -> dict:
    """加载某桌宠的骨骼配置。不存在或损坏时返回 None。"""
    p = _bone_path(pet_id)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return None


def save_bones(pet_id: str, data: dict):
    """保存骨骼配置。part 坐标按图片原始尺寸的比例（0~1）存储。"""
    os.makedirs(BONE_DIR, exist_ok=True)
    try:
        with open(_bone_path(pet_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
