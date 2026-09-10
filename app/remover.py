"""抠图：使用 rembg 去除背景，输出透明 PNG，并裁剪到主体边界。可选像素化。"""
import os
import io
import threading
import concurrent.futures

from PIL import Image

# onnxruntime 的 session.run() 跨线程调用会 C++ segfault（进程直接挂，Python
# try/except 抓不住）。锁只能串行化、不能解决"session 在 A 线程创建、B 线程调用"
# 的跨线程问题。彻底方案：用一个专用的单线程 executor，所有抠图都提交到这个
# 唯一 worker 线程执行 —— session 永远在同一线程创建和使用。
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="rembg"
)
_SESSION = None


def _get_session():
    """复用同一个 rembg session，避免每次抠图都重新加载模型。"""
    global _SESSION
    if _SESSION is None:
        from rembg.session_factory import new_session
        _SESSION = new_session("u2net")
    return _SESSION


def _remove_impl(data: bytes) -> bytes:
    """在专属 worker 线程内执行抠图（session 只在此线程创建/使用）。"""
    from rembg import remove
    return remove(data, session=_get_session())


def _remove_locked(data: bytes) -> bytes:
    """把抠图提交到专用单线程 executor，阻塞等待结果。

    这样无论从哪个 Qt 线程调用，实际抠图都落在同一个 rembg worker 线程，
    彻底避免 onnxruntime 跨线程 segfault。
    """
    return _EXECUTOR.submit(_remove_impl, data).result()


def remove_background(image_path: str, out_path: str, pixelate: bool = False,
                      pixel_size: int = 12, retro: bool = False) -> str:
    """去背景并保存透明 PNG。返回输出路径。首次调用会下载模型(~170MB)。

    pixelate=True 且 retro=True 时输出经典 8bit 复古风（颜色量化 + 粗像素块）。
    """
    with open(image_path, "rb") as f:
        data = f.read()

    out = _remove_locked(data)

    img = Image.open(io.BytesIO(out)).convert("RGBA")

    # 裁剪到非透明区域，去掉多余留白
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    if pixelate:
        img = _pixelate_retro(img, pixel_size) if retro else _pixelate(img, pixel_size)

    img.save(out_path, "PNG")
    return out_path


def process_frame_bytes(frame_bytes: bytes, pixelate: bool = False,
                        pixel_size: int = 12, retro: bool = False) -> bytes:
    """处理单帧图片字节：抠图 + 可选像素化。返回透明 PNG 字节。

    用于图像生成的多帧动画，每帧单独抠图。
    """
    out = _remove_locked(frame_bytes)
    img = Image.open(io.BytesIO(out)).convert("RGBA")

    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    if pixelate:
        img = _pixelate_retro(img, pixel_size) if retro else _pixelate(img, pixel_size)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _pixelate(img: Image.Image, pixel_size: int) -> Image.Image:
    """普通像素化：缩小到 pixel_size 倍块状，再最近邻放大回原尺寸。"""
    w, h = img.size
    small_w = max(1, w // pixel_size)
    small_h = max(1, h // pixel_size)
    small = img.resize((small_w, small_h), Image.NEAREST)
    return small.resize((w, h), Image.NEAREST)


def _pixelate_retro(img: Image.Image, pixel_size: int,
                    colors: int = 32) -> Image.Image:
    """8bit 复古像素化：颜色量化到有限调色板 + 粗像素块，红白机游戏质感。

    先量化颜色（减少到 colors 色），再块状化，边缘锐利。
    """
    # 1. 颜色量化（保留 alpha 通道）
    rgba = img.convert("RGBA")
    # 分离 alpha，对 RGB 部分量化
    rgb = rgba.convert("RGB")
    quantized = rgb.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    quantized = quantized.convert("RGB")
    # 把 alpha 通道盖回去
    quantized.putalpha(rgba.getchannel("A"))

    # 2. 粗像素块化
    w, h = quantized.size
    small_w = max(1, w // pixel_size)
    small_h = max(1, h // pixel_size)
    small = quantized.resize((small_w, small_h), Image.NEAREST)
    return small.resize((w, h), Image.NEAREST)


def is_image(path: str) -> bool:
    return path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))
