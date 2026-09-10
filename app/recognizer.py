"""视觉模型识别：调用 OpenAI 兼容的 chat/completions 接口识别图片形象。"""
import base64
import json
import re

import requests


def recognize(image_path: str, cfg) -> dict:
    """返回 {name, species, personality, appearance} 识别结果。"""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    url = cfg.base_url.rstrip("/") + "/chat/completions"
    prompt = (
        "请识别这张图片中的形象。只返回 JSON，不要任何额外文字，字段如下：\n"
        '{"name": "形象的名字或称呼", "species": "种类(如:猫/人/机器人/卡通角色等)", '
        '"personality": "给它设定一个活泼可爱的性格(中文,20字内)", '
        '"appearance": "外形特征简述(中文,30字内)"}\n'
        "如果看不清或无法识别，也要尽量给出合理猜测，并填好所有字段。"
    )

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        "temperature": 0.7,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=120)
    except requests.RequestException as e:
        raise ValueError(f"网络请求失败：{e}")

    if r.status_code != 200:
        raise ValueError(
            f"API 返回错误（HTTP {r.status_code}）：{r.text[:200] or '无响应内容'}\n"
            f"请检查 Base URL、API Key、模型名是否正确。"
        )

    try:
        data = r.json()
    except (json.JSONDecodeError, ValueError):
        raise ValueError(
            f"API 返回的不是有效 JSON：{(r.text or '')[:200]}\n"
            f"请检查 Base URL 是否正确（如漏了 /v1）或服务是否可用。"
        )
    content = data["choices"][0]["message"]["content"]

    # 提取 JSON（容错：可能有 markdown 代码块或前后缀）
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        raise ValueError(f"识别返回无法解析: {content[:200]}")
    try:
        result = json.loads(m.group(0))
    except json.JSONDecodeError:
        raise ValueError(f"识别返回无法解析: {content[:200]}")

    return {
        "name": str(result.get("name", "")).strip() or "小宠物",
        "species": str(result.get("species", "")).strip(),
        "personality": str(result.get("personality", "")).strip(),
        "appearance": str(result.get("appearance", "")).strip(),
    }
