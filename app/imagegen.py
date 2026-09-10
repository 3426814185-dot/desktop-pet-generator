"""图像生成：根据角色外观 + 动作描述，生成多帧动画（四肢动起来）。"""
import base64
import io
import json
import requests


def _post_json(url, headers, payload, timeout):
    """发 POST 并解析 JSON，失败时给出可读的错误提示。"""
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as e:
        raise ValueError(f"网络请求失败：{e}")

    # HTTP 状态码错误（401/404/429/500 等）
    if r.status_code != 200:
        body = r.text[:200]
        raise ValueError(
            f"API 返回错误（HTTP {r.status_code}）：{body or '无响应内容'}\n"
            f"请检查 Base URL 是否正确、API Key 是否有效、模型名是否支持。"
        )

    # 响应不是合法 JSON（HTML 错误页 / 空内容）
    try:
        return r.json()
    except (json.JSONDecodeError, ValueError):
        body = (r.text or "").strip()
        snippet = body[:200]
        raise ValueError(
            f"API 返回的不是有效 JSON（可能是端点不支持或返回了错误页）：\n{snippet}\n"
            f"提示：图像生成需要服务商支持 OpenAI 兼容的 /images/generations 端点，"
            f"且「图像模型」名要填对该服务商支持的模型。"
        )


def generate_action_frames(cfg, action: str, n_frames: int = 4) -> list:
    """生成同一角色做某动作的 n 帧图，返回 [bytes, ...]（每帧 PNG 字节）。

    通过图像生成 API（OpenAI 兼容 /images/generations）逐帧生成。
    为尽量保持角色一致，prompt 中反复强调同一角色外观 + 全身 + 白底。
    """
    url = cfg.base_url.rstrip("/") + "/images/generations"
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    appearance = cfg.appearance or cfg.species or "可爱的卡通角色"
    frames = []
    for i in range(n_frames):
        # 帧描述：强调动作的不同阶段，让动画连贯
        phase = ["起始姿势", "动作中段", "动作高潮", "动作收尾"][
            min(i, 3) if n_frames <= 4 else i % 4
        ]
        prompt = (
            f"一个{appearance}的卡通角色，正在{action}，{phase}。"
            f"全身像，正面视角，四肢动作清晰，纯白色背景，"
            f"角色外观、颜色、服装在所有帧中保持完全一致。"
            f"风格：可爱的 Q 版卡通，简洁干净。"
        )
        payload = {
            "model": cfg.image_model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json",
        }
        data = _post_json(url, headers, payload, 180)

        b64 = None
        item = data.get("data", [{}])[0] if data.get("data") else {}
        if item.get("b64_json"):
            b64 = item["b64_json"]
        elif item.get("url"):
            # 部分服务返回 URL，需要下载
            try:
                img_resp = requests.get(item["url"], timeout=120)
                img_resp.raise_for_status()
                frames.append(img_resp.content)
                continue
            except requests.RequestException as e:
                raise ValueError(f"下载生成图片失败：{e}")
        if b64:
            frames.append(base64.b64decode(b64))

    if len(frames) < n_frames:
        raise ValueError(f"图像生成失败：仅生成 {len(frames)}/{n_frames} 帧")
    return frames


def generate_single(cfg, prompt: str) -> bytes:
    """生成单张图（备用）。返回 PNG 字节。"""
    url = cfg.base_url.rstrip("/") + "/images/generations"
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg.image_model,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "b64_json",
    }
    data = _post_json(url, headers, payload, 180)
    item = data.get("data", [{}])[0] if data.get("data") else {}
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        img_resp = requests.get(item["url"], timeout=120)
        img_resp.raise_for_status()
        return img_resp.content
    raise ValueError("图像生成失败：无返回数据")
