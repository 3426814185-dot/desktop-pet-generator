"""聊天：与桌宠对话，流式返回。"""
import requests


def build_system_prompt(cfg) -> str:
    return (
        f"你是一只桌面宠物，名叫「{cfg.name}」。"
        f"种类：{cfg.species or '未知'}。外形：{cfg.appearance or '可爱的小动物'}。"
        f"性格：{cfg.personality or '活泼可爱、黏人、爱撒娇'}。\n"
        "请始终以这个角色的口吻与主人对话，语气活泼、简短、可爱，"
        "多用语气词和颜文字，回复控制在 2-3 句话以内。用中文回答。"
    )


def chat_stream(cfg, history: list, on_chunk):
    """流式聊天。history: [{"role": "user"/"assistant", "content": str}]。"""
    url = cfg.base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    messages = [{"role": "system", "content": build_system_prompt(cfg)}] + history
    payload = {
        "model": cfg.model,
        "messages": messages,
        "temperature": 0.9,
        "stream": True,
    }

    r = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
    r.raise_for_status()

    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        import json

        try:
            obj = json.loads(data)
            delta = obj["choices"][0]["delta"].get("content")
            if delta:
                on_chunk(delta)
        except Exception:
            continue
