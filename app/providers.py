"""模型服务商识别：根据 Base URL 自动匹配服务商，推荐默认聊天模型。"""

# 服务商关键词 → (服务商名, 默认聊天模型, 支持的模型列表)
# 关键词按顺序匹配 base_url，命中即返回
PROVIDERS = [
    {
        "keywords": ["openai.com", "api.openai"],
        "name": "OpenAI",
        "default": "gpt-4o-mini",
        "models": [
            "gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini",
            "gpt-4.1-nano", "o3-mini", "o4-mini", "gpt-4-turbo", "gpt-3.5-turbo",
        ],
    },
    {
        "keywords": ["deepseek"],
        "name": "DeepSeek",
        "default": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    {
        "keywords": ["dashscope", "aliyuncs", "tongyi", "qwen"],
        "name": "通义千问",
        "default": "qwen-plus",
        "models": [
            "qwen-plus", "qwen-max", "qwen-turbo", "qwen-long",
            "qwen-vl-plus", "qwen-vl-max", "qwen3-32b", "qwen3-235b-a22b",
            "qwen2.5-72b-instruct", "qwen2.5-vl-72b-instruct",
        ],
    },
    {
        "keywords": ["bigmodel", "zhipu", "glm"],
        "name": "智谱 GLM",
        "default": "glm-4-flash",
        "models": [
            "glm-4-flash", "glm-4-plus", "glm-4-air", "glm-4", "glm-4.5",
            "glm-4v", "glm-4v-plus", "glm-zero-preview",
        ],
    },
    {
        "keywords": ["moonshot", "kimi"],
        "name": "Kimi (Moonshot)",
        "default": "moonshot-v1-8k",
        "models": [
            "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k",
            "kimi-latest", "kimi-k2-0711-preview",
        ],
    },
    {
        "keywords": ["volces", "volcengine", "doubao"],
        "name": "豆包 (火山方舟)",
        "default": "doubao-1.5-pro-32k",
        "models": [
            "doubao-1.5-pro-32k", "doubao-1.5-lite-32k", "doubao-pro-32k",
            "doubao-lite-32k", "doubao-seed-1.6",
        ],
    },
    {
        "keywords": ["siliconflow"],
        "name": "硅基流动",
        "default": "deepseek-ai/DeepSeek-V3",
        "models": [
            "deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1",
            "Qwen/Qwen2.5-72B-Instruct", "Qwen/Qwen3-32B",
            "THUDM/glm-4-9b-chat", "moonshotai/Kimi-K2-Instruct",
        ],
    },
    {
        "keywords": ["anthropic", "claude"],
        "name": "Anthropic Claude",
        "default": "claude-3-5-sonnet-20241022",
        "models": [
            "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229", "claude-3-7-sonnet-20250219",
        ],
    },
    {
        "keywords": ["gemini", "googleapis", "generativelanguage"],
        "name": "Google Gemini",
        "default": "gemini-1.5-flash",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
    },
]


def detect_provider(base_url: str) -> dict:
    """根据 base_url 识别服务商，返回 provider dict 或 None。"""
    url = (base_url or "").lower()
    if not url:
        return None
    for p in PROVIDERS:
        for kw in p["keywords"]:
            if kw in url:
                return p
    return None


def all_models() -> list:
    """返回所有服务商的所有模型（去重，用于兜底列表）。"""
    seen = []
    result = []
    for p in PROVIDERS:
        for m in p["models"]:
            if m not in seen:
                seen.append(m)
                result.append(m)
    return result
