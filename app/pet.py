"""桌面宠物主窗口：透明悬浮、程序化动画、拖拽、点击互动、右键菜单、聊天。"""
import math
import random
import sys
import threading

from PyQt5.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QIcon, QPen
from PyQt5.QtWidgets import (
    QWidget, QLabel, QApplication, QMenu, QAction, QVBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QHBoxLayout, QDialog, QInputDialog,
)

from . import chat


# 右键菜单美化样式
MENU_QSS = """
QMenu {
    background: #ffffff;
    border: 2px solid #ddd6fe;
    border-radius: 12px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 24px 8px 16px;
    border-radius: 8px;
    font-size: 14px;
    color: #374151;
}
QMenu::item:selected {
    background: #f3e8ff;
    color: #6d28d9;
    font-weight: 600;
}
QMenu::separator {
    height: 1px;
    background: #ede9fe;
    margin: 4px 8px;
}
QMenu::item:disabled {
    color: #c4b5fd;
}
"""


class BubbleLabel(QLabel):
    """不透明圆角气泡：paintEvent 手动画不透明底 + 边框。

    顶层无边框窗口 + WA_TranslucentBackground 下，QSS 的 background 不渲染，
    必须用 paintEvent 手动绘制，才能保证气泡背景不透明（不跟壁纸颜色冲突）。
    """

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # 纯白不透明底 + 紫色描边 + 圆角
        p.setBrush(QColor(255, 255, 255, 255))
        p.setPen(QPen(QColor("#8b5cf6"), 2))
        p.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 14, 14)
        p.end()
        # 再画文字（走 QLabel 默认绘制）
        super().paintEvent(e)


CHAT_QSS = """
* { font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif; }
QPushButton#WinClose {
    background: transparent;
    color: #9ca3af;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 700;
}
QPushButton#WinClose:hover {
    background: #ef4444;
    color: #ffffff;
}
QTextEdit#ChatLog {
    background: #ffffff;
    border: 2px solid #f3e8ff;
    border-radius: 14px;
    padding: 10px;
    font-size: 13px;
    color: #374151;
}
QLineEdit {
    background: #ffffff;
    border: 2px solid #e5e7eb;
    border-radius: 11px;
    padding: 9px 12px;
    font-size: 13px;
    color: #1f2937;
}
QLineEdit:focus { border: 2px solid #8b5cf6; }
QPushButton#SendBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #8b5cf6, stop:1 #ec4899);
    color: #ffffff;
    border: none;
    border-radius: 11px;
    padding: 9px 18px;
    font-weight: 700;
}
QPushButton#SendBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c3aed, stop:1 #db2777);
}
QPushButton#SendBtn:disabled { background: #d1d5db; }
"""


class ChatDialog(QDialog):
    """聊天对话框。"""

    reply_ready = pyqtSignal(str)  # 跨线程安全回传聊天结果

    def __init__(self, cfg, parent=None, action_callback=None):
        super().__init__(parent)
        self.cfg = cfg
        self.history = []
        self.action_callback = action_callback
        self.setWindowTitle(f"和 {cfg.name} 聊天")
        self.resize(400, 500)
        # 无边框窗口（去掉系统标题栏）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(CHAT_QSS)
        self.reply_ready.connect(self._on_reply)
        self._drag_pos = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        # 自定义标题栏
        titlebar = QHBoxLayout()
        header = QLabel(f"💬 和 {cfg.name} 聊天", self)
        header.setStyleSheet(
            "font-size:16px; font-weight:800; color:#6d28d9; padding:4px 2px;"
        )
        titlebar.addWidget(header)
        titlebar.addStretch(1)
        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("WinClose")
        btn_close.setFixedSize(30, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        titlebar.addWidget(btn_close)
        layout.addLayout(titlebar)

        self.log = QTextEdit(self)
        self.log.setObjectName("ChatLog")
        self.log.setReadOnly(True)
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("说点什么，或输入动作（如「挥手」「跳舞」）…")
        self.send_btn = QPushButton("发送", self)
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.act_btn = QPushButton("🎬 动作", self)
        self.act_btn.setObjectName("SendBtn")
        self.act_btn.setCursor(Qt.PointingHandCursor)

        layout.addWidget(self.log, 1)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.input, 1)
        row.addWidget(self.send_btn)
        row.addWidget(self.act_btn)
        layout.addLayout(row)

        self.input.returnPressed.connect(self._send)
        self.send_btn.clicked.connect(self._send)
        self.act_btn.clicked.connect(self._send_action)
        self._append(f"🐾 {cfg.name}：嗨！我是你的小可爱～(｡･ω･｡)\n"
                     f"提示：点「🎬 动作」或在输入框输入动作描述，可以让桌宠动起来哦！")

    # ---------- 无边框窗口拖拽 ----------
    def paintEvent(self, e):
        """手动画圆角背景（顶层窗口 QSS 背景不生效）。"""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#fdf2f8"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _append(self, text: str):
        self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    @staticmethod
    def _looks_like_action(text: str) -> bool:
        """判断输入是否像动作描述（短词 + 动作关键词）。"""
        action_words = ["挥手", "跑步", "跳舞", "鼓掌", "比心", "走路", "跳跃",
                        "转圈", "鞠躬", "敬礼", "招手", "卖萌", "生气", "开心",
                        "睡觉", "打滚", "蹲下", "举手", "飞吻", "点赞", "哭",
                        "笑", "跳", "走", "跑", "挥", "扭", "摇", "踢", "打",
                        "蹦", "蹲", "躺", "坐", "站", "招手", "蹦跳", "翻滚"]
        if len(text) > 12:
            return False
        return any(w in text for w in action_words)

    def _send_action(self):
        """🎬 动作按钮：把输入框内容当动作描述触发。"""
        text = self.input.text().strip()
        if not text:
            self._append("🐾 提示：先在输入框输入动作，如「挥手」「跑步」「比心」。")
            return
        self._trigger_action(text)

    def _trigger_action(self, action: str):
        if self.action_callback is not None:
            self._append(f"🎬 已请求动作：{action}")
            self.action_callback(action)
        else:
            self._append("🐾 提示：动作功能需要在主窗口生成的桌宠上使用。")

    def _send(self):
        text = self.input.text().strip()
        if not text:
            return
        # 若输入疑似动作关键词（短词），优先当动作触发
        if self._looks_like_action(text):
            self._trigger_action(text)
            self.input.clear()
            return
        if not (self.cfg.api_key and self.cfg.base_url):
            self._append("🐾 提示：未配置 API Key，暂时无法聊天。请在主界面的 AI 配置里填写。")
            return
        self.input.clear()
        self._append(f"你：{text}")
        self.history.append({"role": "user", "content": text})
        self.send_btn.setEnabled(False)

        def _work():
            buf = []

            def on_chunk(c):
                buf.append(c)

            try:
                chat.chat_stream(self.cfg, self.history, on_chunk)
                reply = "".join(buf).strip()
            except Exception as e:
                reply = f"（出错了：{e}）"
            self.history.append({"role": "assistant", "content": reply})
            # 跨线程安全：用信号回传主线程更新 UI
            self.reply_ready.emit(reply)

        threading.Thread(target=_work, daemon=True).start()

    def _on_reply(self, reply: str):
        """主线程更新聊天结果（避免跨线程操作 GUI 崩溃）。"""
        self._append(f"{self.cfg.name}：{reply}")
        self.send_btn.setEnabled(True)


class BehaviorProfile:
    """从性格/种类描述解析行为特征，驱动桌宠的动作偏好。"""

    def __init__(self, personality="", species=""):
        text = (personality or "") + (species or "")
        self.active = any(k in text for k in ["活泼", "好动", "爱动", "调皮", "元气", "精力", "跳脱"])
        self.sleepy = any(k in text for k in ["慵懒", "爱睡", "困", "懒", "佛系", "悠闲", "慢"])
        self.tsundere = any(k in text for k in ["傲娇", "高冷", "冷淡", "酷", "傲"])
        self.clingy = any(k in text for k in ["撒娇", "黏人", "粘人", "软", "亲昵", "依赖"])
        self.shy = any(k in text for k in ["胆小", "害羞", "怕生", "怯", "内向"])
        self.cheerful = any(k in text for k in ["乐观", "开朗", "阳光", "乐天", "元气"])

        # 活动间隔（毫秒）：越活跃间隔越短
        if self.active:
            self.activity_range = (12000, 22000)
        elif self.sleepy:
            self.activity_range = (28000, 55000)
        else:
            self.activity_range = (18000, 35000)


class PetWindow(QWidget):
    """透明悬浮桌宠，带程序化动画与性格化行为。"""

    def __init__(self, image_path: str, cfg, frames=None, action_callback=None,
                 bone_callback=None, quit_callback=None):
        super().__init__()
        self.cfg = cfg
        self.image_path = image_path
        self.profile = BehaviorProfile(cfg.personality, cfg.species)
        self.base_pixmap = QPixmap(image_path)
        self.action_callback = action_callback  # 触发动作生成的回调（连到主窗口）
        self.bone_callback = bone_callback      # 编辑骨骼的回调（连到主窗口）
        self.quit_callback = quit_callback      # 关闭桌宠的回调（连到主窗口清引用）

        # 多帧动画（四肢动作）：frames 为 QPixmap 列表，有帧时循环播放
        self._frames = [QPixmap()]  # 占位，实际在下方填充
        self._frame_idx = 0
        self._playing_frames = False
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._advance_frame)

        if frames and len(frames) > 1:
            self._frames = [QPixmap() for _ in frames]
            for i, fb in enumerate(frames):
                self._frames[i].loadFromData(fb)
        else:
            self._frames = [self.base_pixmap]

        # 骨骼动画（Live2D 式分层）：bones 为骨骼配置 dict 或 None
        self._bone_parts = []      # 像素坐标部位列表（含子图）
        self._bone_active = False
        self._bone_action = ""
        self._bone_phase = 0.0
        self._bone_elapsed = 0.0
        self._bone_dur = 0

        # 拖拽
        self._dragging = False
        self._drag_offset = QPoint()
        self._press_pos = None
        # 动画状态
        self._walking = False
        self._angle = 0.0      # 旋转角（度）
        self._sx = 1.0         # 水平缩放（负值=翻转）
        self._sy = 1.0         # 垂直缩放
        self._offset_y = 0     # 内部垂直偏移
        self._flip = False     # 朝向（True=朝左）
        self._action = "breathe"
        self._action_elapsed = 0.0
        self._action_dur = 10 ** 9
        # 气泡
        self._bubble = None

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 按图片真实宽高比确定窗口尺寸，最长边 220px
        self.display_w, self.display_h = self._fit_size(220)
        self.setFixedSize(self.display_w, self.display_h)

        # 气泡自动关闭定时器
        self._bubble_timer = QTimer(self)
        self._bubble_timer.setSingleShot(True)
        self._bubble_timer.timeout.connect(self._close_bubble)

        # 动画循环（约 30fps）
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._anim_tick)
        self.anim_timer.start(33)

        # 活动调度（随机走动/跳舞/转身/睡觉）
        self.activity_timer = QTimer(self)
        self.activity_timer.setSingleShot(True)
        self.activity_timer.timeout.connect(self._do_activity)
        self._schedule_activity()

        self.move(80, 80)

    # ---------- 图像 ----------
    def _fit_size(self, max_side: int):
        w, h = self.base_pixmap.width(), self.base_pixmap.height()
        if w <= 0 or h <= 0:
            return max_side, max_side
        if w >= h:
            return max_side, max(1, int(h * max_side / w))
        return max(1, int(w * max_side / h)), max_side

    def _current_frame_pixmap(self):
        """返回当前应显示的帧（多帧动画时按索引取）。"""
        return self._frames[self._frame_idx % len(self._frames)]

    @property
    def _flip_sign(self):
        return -1.0 if self._flip else 1.0

    def _disp_frame(self):
        """把当前帧缩放到显示尺寸。"""
        return self._current_frame_pixmap().scaled(
            self.display_w, self.display_h,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )

    def _advance_frame(self):
        self._frame_idx += 1
        self.update()

    def play_action(self, frames, fps: int = 6):
        """播放一段多帧动作动画（四肢动起来）。frames: [bytes, ...] 透明 PNG 字节。"""
        self._frames = [QPixmap() for _ in frames]
        for i, fb in enumerate(frames):
            self._frames[i].loadFromData(fb)
        self._frame_idx = 0
        self._frame_timer.start(int(1000 / fps))
        self._playing_frames = True
        self.update()

    def stop_action(self):
        """停止多帧动画，回到静态图。"""
        self._frame_timer.stop()
        self._playing_frames = False
        self._frames = [self.base_pixmap]
        self._frame_idx = 0
        self.update()

    # ---------- 骨骼动画 ----------
    def load_skeleton(self, bones: dict):
        """加载骨骼配置，把 base_pixmap 切成各部位子图。"""
        from . import skeleton as sk
        self._bone_parts = []
        if not bones or not bones.get("parts"):
            return
        parts = sk.build_skeleton(
            (self.base_pixmap.width(), self.base_pixmap.height()),
            bones["parts"],
        )
        for p in parts:
            sub = self.base_pixmap.copy(p["x"], p["y"], p["w"], p["h"])
            p["pixmap"] = sub
            self._bone_parts.append(p)

    def play_bone_action(self, action: str, duration_ms: int = 3000):
        """播放骨骼动画（纯本地，零 API）。action: walk/wave/jump/dance/idle。"""
        if not self._bone_parts:
            self.show_bubble("还没有骨骼，先在主窗口「编辑骨骼」哦～")
            return
        self._bone_action = action
        self._bone_phase = 0.0
        self._bone_elapsed = 0.0
        self._bone_dur = duration_ms
        self._bone_active = True
        self._frame_timer.stop()
        self._playing_frames = False
        self.update()

    def stop_bone_action(self):
        """停止骨骼动画，回到静态图。"""
        self._bone_active = False
        self.update()

    def _bone_tick(self):
        """骨骼动画相位推进（复用 anim_timer）。"""
        if not self._bone_active:
            return
        self._bone_elapsed += 33
        self._bone_phase += 0.15  # 相位步进，约每秒 4.5 弧度
        if self._bone_elapsed > self._bone_dur:
            self._bone_active = False

    def _paint_skeleton(self, p: QPainter, scale_x: float, scale_y: float):
        """按骨骼逐部位绘制（每个部位绕锚点旋转）。"""
        from . import skeleton as sk
        poses = sk.compute_pose(self._bone_parts, self._bone_action, self._bone_phase)
        for part, pose in zip(self._bone_parts, poses):
            angle, dx, dy = pose
            pm = part["pixmap"]
            if pm.isNull():
                continue
            # 缩放后的部位尺寸和位置
            w = part["w"] * scale_x
            h = part["h"] * scale_y
            px = part["pivot_x"] * scale_x
            py = part["pivot_y"] * scale_y
            # 部位左上角在缩放后的位置
            ox = part["x"] * scale_x + dx
            oy = part["y"] * scale_y + dy

            p.save()
            # 平移到锚点（相对整体左上角）
            p.translate(px, py)
            p.rotate(angle)
            # 画子图：子图左上角相对锚点的偏移 = (ox - px, oy - py)
            p.translate(ox - px, oy - py)
            scaled = pm.scaled(int(w), int(h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(0, 0, scaled)
            p.restore()

    def paintEvent(self, e):
        # 骨骼动画模式：逐部位绘制
        if self._bone_active and self._bone_parts:
            p = QPainter(self)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.setRenderHint(QPainter.Antialiasing)
            # 计算整体缩放（base_pixmap → 显示尺寸）
            scale_x = self.display_w / max(1, self.base_pixmap.width())
            scale_y = self.display_h / max(1, self.base_pixmap.height())
            # 居中偏移
            disp_w = self.base_pixmap.width() * scale_x
            disp_h = self.base_pixmap.height() * scale_y
            off_x = (self.display_w - disp_w) / 2
            off_y = (self.display_h - disp_h) / 2
            p.translate(off_x, off_y)
            self._paint_skeleton(p, scale_x, scale_y)
            p.end()
            return

        pm = self._disp_frame()
        if pm.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.Antialiasing)
        cx = self.width() / 2.0
        cy = self.height() / 2.0 + self._offset_y
        p.translate(cx, cy)
        p.rotate(self._angle)
        p.scale(self._sx, self._sy)
        p.translate(-pm.width() / 2.0, -pm.height() / 2.0)
        p.drawPixmap(0, 0, pm)
        p.end()

    # ---------- 动画核心 ----------
    def _set_action(self, name, dur):
        self._action = name
        self._action_dur = dur
        self._action_elapsed = 0.0

    def _anim_tick(self):
        self._action_elapsed += 33
        self._update_transform()
        self._bone_tick()
        self.update()
        # 气泡跟随桌宠运动（走路/跳跃等窗口移动时同步气泡位置）
        self._position_bubble()
        # 动作结束回到呼吸
        if self._action != "breathe" and self._action_elapsed > self._action_dur:
            self._set_action("breathe", 10 ** 9)

    def _update_transform(self):
        t = self._action_elapsed
        self._offset_y = 0
        if self._action == "breathe":
            # 呼吸：轻微缩放，周期 2.5s
            s = 1.0 + 0.05 * math.sin(t * 2 * math.pi / 2500)
            self._sx = s * self._flip_sign
            self._sy = s
            self._angle = 0.0
        elif self._action == "walk":
            # 走路：左右摇摆 ±6°，周期 400ms
            self._angle = 6.0 * math.sin(t * 2 * math.pi / 400)
            self._sx = self._flip_sign
            self._sy = 1.0
        elif self._action == "jump":
            # 跳跃：先缩后放
            prog = t / self._action_dur
            self._sy = 1.0 + 0.08 * math.sin(prog * math.pi)
            self._sx = self._flip_sign * self._sy
            self._angle = 0.0
        elif self._action == "turn":
            # 转身：水平翻转 1→-1→1（cos 一个完整周期）
            prog = t / self._action_dur
            self._sx = self._flip_sign * math.cos(prog * 2 * math.pi)
            self._sy = 1.0
            self._angle = 0.0
        elif self._action == "sleep":
            # 打瞌睡：下沉 + 缓慢呼吸
            self._offset_y = 4
            s = 0.92 + 0.03 * math.sin(t * 2 * math.pi / 3000)
            self._sx = s * self._flip_sign
            self._sy = s
            self._angle = 0.0
        elif self._action == "dance":
            # 跳舞：大幅度摇摆 + 缩放律动
            self._angle = 15.0 * math.sin(t * 2 * math.pi / 500)
            s = 1.0 + 0.08 * math.sin(t * 2 * math.pi / 250)
            self._sx = s * self._flip_sign
            self._sy = s
        elif self._action == "sway":
            # 开心晃动：快速摇摆
            self._angle = 12.0 * math.sin(t * 2 * math.pi / 300)
            self._sx = self._flip_sign
            self._sy = 1.0

    # ---------- 动作触发 ----------
    def _start_walk_anim(self, x, y):
        self._walking = True
        self._set_action("walk", 1500)
        self.anim = QPropertyAnimation(self, b"pos", self)
        self.anim.setDuration(1500)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPoint(x, y))
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim.finished.connect(lambda: setattr(self, "_walking", False))
        self.anim.start()

    def walk_to(self, x, y):
        self._flip = x < self.x()
        self._start_walk_anim(x, y)

    def jump(self):
        if self._walking:
            return
        self._set_action("jump", 600)
        self._walking = True
        start = self.pos()
        self.anim = QPropertyAnimation(self, b"pos", self)
        self.anim.setDuration(600)
        self.anim.setStartValue(start)
        self.anim.setKeyValueAt(0.5, QPoint(start.x(), start.y() - 45))
        self.anim.setEndValue(start)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.finished.connect(lambda: setattr(self, "_walking", False))
        self.anim.start()

    def sway(self):
        self._set_action("sway", 900)

    def turn_around(self):
        self._set_action("turn", 2000)

    def sleep(self):
        self._set_action("sleep", 8000)
        self.show_bubble("💤 Zzz…", 8000)

    def dance(self):
        self._set_action("dance", 4000)

    # ---------- 行为调度 ----------
    def _schedule_activity(self):
        lo, hi = self.profile.activity_range
        self.activity_timer.start(random.randint(lo, hi))

    def _do_activity(self):
        if self._dragging or self._walking:
            self._schedule_activity()
            return
        r = random.random()
        if self.profile.sleepy and r < 0.5:
            self.sleep()
        elif self.profile.active and r < 0.4:
            self.dance()
        elif self.profile.tsundere and r < 0.3:
            self.turn_around()
        else:
            self._random_walk()
        self._schedule_activity()

    def _random_walk(self):
        screen = QApplication.primaryScreen().availableGeometry()
        target_x = random.randint(0, max(0, screen.width() - self.width()))
        target_y = random.randint(
            screen.top(), max(screen.top(), screen.height() - self.height())
        )
        self.walk_to(target_x, target_y)

    def _react(self):
        """点击反应，根据性格不同。"""
        if self.profile.tsundere:
            self.turn_around()
            self.show_bubble("哼！(￣へ￣)")
        elif self.profile.shy:
            self.turn_around()
            self.show_bubble("呀！别、别看我…")
        elif self.profile.active or self.profile.cheerful:
            self.jump()
            self.show_bubble(random.choice(["耶！", "嘿嘿～", "再来一次！"]))
        elif self.profile.clingy:
            self.sway()
            self.show_bubble("最喜欢你啦！💕")
        else:
            self.jump()
            self.show_bubble(random.choice(["干嘛呀？", "抱抱～", "怎么啦？"]))

    # ---------- 气泡 ----------
    def show_bubble(self, text: str, duration_ms: int = 3000):
        self._close_bubble()
        bubble = BubbleLabel(text, None)
        bubble.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        bubble.setAttribute(Qt.WA_TranslucentBackground)
        # 文字样式（背景和边框由 BubbleLabel.paintEvent 手动画，不透明）
        bubble.setStyleSheet(
            "color:#1f2937; padding:10px 16px;"
            "font-size:16px; font-weight:700;"
            "font-family:'Microsoft YaHei UI','Microsoft YaHei',sans-serif;"
        )
        bubble.adjustSize()
        self._bubble = bubble
        self._position_bubble()
        bubble.show()
        self._bubble_timer.start(duration_ms)

    def _position_bubble(self):
        """把气泡定位到桌宠上方居中，并跟随桌宠位置。"""
        if self._bubble is None:
            return
        bx = self.x() + (self.width() - self._bubble.width()) // 2
        by = self.y() - self._bubble.height() - 8
        self._bubble.move(max(0, bx), max(0, by))

    def _close_bubble(self):
        bubble = self._bubble
        self._bubble = None
        if bubble is not None:
            try:
                bubble.close()
                bubble.deleteLater()
            except RuntimeError:
                pass

    # ---------- 鼠标交互 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = True
            self._press_pos = e.globalPos()
            self._drag_offset = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._dragging and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_offset)
            self._position_bubble()  # 拖拽时气泡跟随
            e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            was_drag = (self._press_pos is not None
                        and (e.globalPos() - self._press_pos).manhattanLength() > 6)
            self._dragging = False
            if not was_drag:
                self._react()
            self._press_pos = None

    def mouseDoubleClickEvent(self, e):
        # 已去除双击打开聊天功能（避免误触）
        e.accept()

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        # 关键：popup 窗口 + 透明背景，才能让 QMenu 的 border-radius 真正生效
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setStyleSheet(MENU_QSS)
        act_chat = QAction("💬 聊天", self)
        act_chat.triggered.connect(self.open_chat)

        # 本地骨骼动作（零 API）
        act_bone_walk = QAction("🚶 走路", self)
        act_bone_walk.triggered.connect(lambda: self.play_bone_action("walk"))
        act_bone_wave = QAction("👋 挥手", self)
        act_bone_wave.triggered.connect(lambda: self.play_bone_action("wave"))
        act_bone_dance = QAction("💃 跳舞", self)
        act_bone_dance.triggered.connect(lambda: self.play_bone_action("dance"))
        act_bone_edit = QAction("✂️ 编辑骨骼…", self)
        act_bone_edit.triggered.connect(self._edit_bones)

        act_jump = QAction("🦘 跳一下", self)
        act_jump.triggered.connect(self.jump)
        act_turn = QAction("🔄 转身", self)
        act_turn.triggered.connect(self.turn_around)
        act_walk = QAction("🚶 到处走走", self)
        act_walk.triggered.connect(self._random_walk)
        act_say = QAction("👋 打个招呼", self)
        act_say.triggered.connect(self.greet)
        act_action = QAction("🎬 做动作…", self)
        act_action.triggered.connect(self.request_action)
        act_close = QAction("🚪 关闭桌宠", self)
        act_close.triggered.connect(self._close_pet)

        menu.addAction(act_chat)
        menu.addSeparator()
        menu.addAction(act_bone_walk)
        menu.addAction(act_bone_wave)
        menu.addAction(act_bone_dance)
        menu.addAction(act_bone_edit)
        menu.addSeparator()
        for a in (act_jump, act_turn, act_walk, act_say):
            menu.addAction(a)
        menu.addSeparator()
        menu.addAction(act_action)
        menu.addSeparator()
        menu.addAction(act_close)
        menu.exec_(e.globalPos())

    def _edit_bones(self):
        """编辑骨骼：回调主窗口打开骨骼编辑器。"""
        if self.bone_callback is not None:
            self.bone_callback()
        else:
            self.show_bubble("（需要主窗口支持，重新生成桌宠试试）")

    def _close_pet(self):
        """关闭当前桌宠（不影响主程序）。"""
        self._close_bubble()
        if self.quit_callback is not None:
            self.quit_callback()
        self.close()
        self.deleteLater()

    def _quit(self):
        # 兼容旧调用：关闭当前桌宠，而不是退出整个程序
        self._close_pet()

    # ---------- 动作 ----------
    # 系统默认打招呼语
    DEFAULT_GREETINGS = [
        "你好呀～",
        "嘻嘻，抱抱！(≧▽≦)",
        "主人主人，陪我玩嘛～",
        "今天也要元气满满哦！",
        "想我了吗？",
    ]

    def greet(self):
        # 默认 + 用户自定义，随机选一条；有名字时优先用带名字的问候
        msgs = list(self.DEFAULT_GREETINGS)
        custom = getattr(self.cfg, "greet_msgs", None) or []
        msgs += [m for m in custom if m and m.strip()]
        if self.cfg.name:
            msgs.append(f"你好呀～我是{self.cfg.name}！")
        self.show_bubble(random.choice(msgs))
        self.sway()

    def open_chat(self):
        dlg = ChatDialog(self.cfg, self, action_callback=self.action_callback)
        dlg.show()

    def request_action(self, action: str = None):
        """请求做动作：优先用本地骨骼动画（零 API），无骨骼时才走 AI。"""
        if action is None:
            action, ok = QInputDialog.getText(
                self, "做动作",
                "想让桌宠做什么动作？\n（如：挥手、跑步、跳舞、鼓掌、比心…）"
            )
            if not ok or not action.strip():
                return
        action = action.strip()

        # 优先：本地骨骼动画（零 API）
        bone_action = self._match_bone_action(action)
        if bone_action and self._bone_parts:
            self.play_bone_action(bone_action)
            return

        # 有骨骼但动作不匹配，提示可用的骨骼动作
        if self._bone_parts and not bone_action:
            self.show_bubble("这个动作需要 AI 生成，或试试：走路、挥手、跳舞、跳跃")
            return

        # 无骨骼：走 AI 生成（需要 API）
        if self.action_callback is not None:
            self.action_callback(action)
        else:
            self.show_bubble("（这个功能需要主窗口支持，重新生成桌宠试试）")

    @staticmethod
    def _match_bone_action(action: str):
        """把自然语言动作映射到本地骨骼动作。"""
        a = action
        if any(k in a for k in ["走", "跑", "散步", "溜达", "踱"]):
            return "walk"
        if any(k in a for k in ["挥手", "招手", "再见", "打招呼", "挥"]):
            return "wave"
        if any(k in a for k in ["跳", "蹦", "跃"]):
            return "jump"
        if any(k in a for k in ["跳舞", "舞", "扭", "摇"]):
            return "dance"
        return None


def run_pet(image_path: str, cfg):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = PetWindow(image_path, cfg)
    pet.show()
    pet.greet()
    return app
