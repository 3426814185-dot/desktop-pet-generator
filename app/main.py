"""主界面：上传图片 -> 配置API -> 识别形象(可选) -> 抠图 -> 生成桌宠。"""
import os
import sys
import threading

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QRect, QPoint
from PyQt5.QtGui import QPixmap, QIcon, QFont, QColor, QPainter, QLinearGradient
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QApplication, QTextEdit, QGroupBox, QFormLayout, QMessageBox,
    QFrame, QCheckBox, QComboBox, QScrollArea, QSlider,
)

from . import config as cfgmod
from . import recognizer, remover, pet


# ---------------------------------------------------------------- 全局样式
QSS = """
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
}

/* 标题 */
QLabel#Title {
    font-size: 30px;
    font-weight: 800;
    color: #4c1d95;
}

/* 窗口控制按钮（最小化/关闭） */
QPushButton#WinBtn {
    background: transparent;
    color: #6d28d9;
    border: none;
    border-radius: 8px;
    font-size: 18px;
    font-weight: 700;
}
QPushButton#WinBtn:hover {
    background: #ede9fe;
}
QPushButton#WinClose {
    background: transparent;
    color: #9ca3af;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#WinClose:hover {
    background: #ef4444;
    color: #ffffff;
}
QLabel#Subtitle {
    font-size: 15px;
    color: #8b8ba7;
}

/* 卡片 */
QFrame#Card {
    background: rgba(255, 255, 255, 0.92);
    border-radius: 18px;
    border: 1px solid rgba(255, 255, 255, 0.9);
}
QLabel#CardTitle {
    font-size: 17px;
    font-weight: 700;
    color: #6d28d9;
}

/* 图片预览区 */
QLabel#ImageBox {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #fdf4ff, stop:1 #ede9fe);
    border: 2px dashed #d8b4fe;
    border-radius: 16px;
    color: #a78bfa;
    font-size: 16px;
}

/* 输入框 */
QLineEdit {
    background: #ffffff;
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 15px;
    color: #1f2937;
    selection-background-color: #8b5cf6;
}
QLineEdit:focus {
    border: 2px solid #8b5cf6;
    background: #ffffff;
}
QLineEdit:hover {
    border: 2px solid #c4b5fd;
}

/* 复选框 */
QCheckBox {
    font-size: 15px;
    color: #4b5563;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #c4b5fd;
    background: #ffffff;
}
QCheckBox::indicator:hover {
    border: 2px solid #8b5cf6;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #8b5cf6, stop:1 #ec4899);
    border: 2px solid #8b5cf6;
}

/* 下拉框（与输入框统一风格） */
QComboBox {
    background: #ffffff;
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 15px;
    font-weight: 600;
    color: #1f2937;
    min-height: 20px;
}
QComboBox:hover {
    border: 2px solid #c4b5fd;
}
QComboBox:focus {
    border: 2px solid #8b5cf6;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #8b5cf6;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 2px solid #ddd6fe;
    border-radius: 10px;
    padding: 6px;
    font-size: 15px;
    color: #1f2937;
    selection-background-color: #f3e8ff;
    selection-color: #6d28d9;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    padding: 8px 10px;
    min-height: 30px;
}
QComboBox QAbstractItemView::item:selected {
    background: #f3e8ff;
    color: #6d28d9;
    font-weight: 700;
}

/* 提示文字 */
QLabel#Hint {
    font-size: 14px;
    color: #a78bfa;
}

/* 滑条（像素大小调节） */
QSlider::groove:horizontal {
    height: 6px;
    background: #ede9fe;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #8b5cf6, stop:1 #ec4899);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    background: #ffffff;
    border: 2px solid #8b5cf6;
}
QSlider::handle:horizontal:hover {
    border: 2px solid #ec4899;
}

/* 滚动区透明背景 */
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* 滚动条美化 */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #ddd6fe;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #c4b5fd;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #ddd6fe;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #c4b5fd;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

/* 普通按钮 */
QPushButton#GhostBtn {
    background: #ffffff;
    color: #6d28d9;
    border: 2px solid #ddd6fe;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 15px;
    font-weight: 600;
}
QPushButton#GhostBtn:hover {
    border: 2px solid #8b5cf6;
    background: #faf5ff;
}
QPushButton#GhostBtn:pressed {
    background: #f3e8ff;
}

/* 主按钮（渐变） */
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #8b5cf6, stop:1 #ec4899);
    color: #ffffff;
    border: none;
    border-radius: 14px;
    padding: 14px 24px;
    font-size: 17px;
    font-weight: 700;
}
QPushButton#PrimaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c3aed, stop:1 #db2777);
}
QPushButton#PrimaryBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6d28d9, stop:1 #be185d);
}
QPushButton#PrimaryBtn:disabled {
    background: #d1d5db;
    color: #f3f4f6;
}

/* 结果文本 */
QTextEdit#ResultBox {
    background: #faf5ff;
    border: 2px solid #f3e8ff;
    border-radius: 14px;
    padding: 12px;
    font-size: 15px;
    color: #4b5563;
    line-height: 1.5;
}

/* 状态标签 */
QLabel#Status {
    font-size: 14px;
    color: #8b8ba7;
}
QLabel#Status[running="true"] {
    color: #8b5cf6;
    font-weight: 600;
}
QLabel#Status[done="true"] {
    color: #16a34a;
    font-weight: 600;
}
"""


def _card(parent) -> QFrame:
    f = QFrame(parent)
    f.setObjectName("Card")
    return f


def _card_title(text: str, parent) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setObjectName("CardTitle")
    return lbl


def _field_label(text: str, parent) -> QLabel:
    lb = QLabel(text, parent)
    lb.setStyleSheet("color:#6b7280; font-size:15px; font-weight:600;")
    return lb


class Worker(QThread):
    """后台执行（可选识别）+ 抠图。"""
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)
    stage = pyqtSignal(str)

    def __init__(self, image_path, cfg, do_recognize, manual_info=None,
                 pixelate=False, pixel_size=12, retro=False):
        super().__init__()
        self.image_path = image_path
        self.cfg = cfg
        self.do_recognize = do_recognize
        self.manual_info = manual_info or {}
        self.pixelate = pixelate
        self.pixel_size = pixel_size
        self.retro = retro

    def run(self):
        try:
            os.makedirs(cfgmod.CONFIG_DIR, exist_ok=True)
            if self.do_recognize:
                self.stage.emit("正在识别形象…")
                info = recognizer.recognize(self.image_path, self.cfg)
            else:
                info = dict(self.manual_info)

            stage = "正在生成像素风抠图…" if self.pixelate else "正在抠图…"
            self.stage.emit(stage)
            out_path = cfgmod.new_avatar_path()
            remover.remove_background(self.image_path, out_path,
                                      pixelate=self.pixelate,
                                      pixel_size=self.pixel_size,
                                      retro=self.retro)
            info["avatar_path"] = out_path
            info["pixel"] = self.pixelate
            info["pixel_size"] = self.pixel_size
            self.finished_ok.emit(info)
        except Exception as e:
            self.failed.emit(str(e))


class ActionWorker(QThread):
    """后台执行动作帧生成：图像生成 API → 逐帧抠图 → 返回帧字节列表。"""
    finished_ok = pyqtSignal(list)
    failed = pyqtSignal(str)
    stage = pyqtSignal(str)

    def __init__(self, cfg, action, n_frames=4, pixelate=False, pixel_size=12,
                 retro=False):
        super().__init__()
        self.cfg = cfg
        self.action = action
        self.n_frames = n_frames
        self.pixelate = pixelate
        self.pixel_size = pixel_size
        self.retro = retro

    def run(self):
        from . import imagegen, remover
        try:
            self.stage.emit(f"正在生成「{self.action}」动作帧…")
            raw_frames = imagegen.generate_action_frames(self.cfg, self.action, self.n_frames)

            self.stage.emit("正在抠图处理动作帧…")
            frames = []
            for i, fb in enumerate(raw_frames):
                self.stage.emit(f"正在处理第 {i + 1}/{len(raw_frames)} 帧…")
                frame = remover.process_frame_bytes(
                    fb, pixelate=self.pixelate,
                    pixel_size=self.pixel_size, retro=self.retro,
                )
                frames.append(frame)
            self.finished_ok.emit(frames)
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("桌宠生成器")
        self.resize(1100, 760)
        self.setMinimumSize(980, 680)
        self.setObjectName("Root")
        # 无边框窗口（去掉系统标题栏）
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 关键：透明背景，让 QSS 的 border-radius 圆角真正生效
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None
        self._resize_margin = 8
        self._resize_edge = None
        self._resize_start = None
        self._resize_geo = None
        self.setMouseTracking(True)
        self.image_path = None
        self.cfg = cfgmod.load_config()
        self._pet = None
        self._current_pet_id = None
        self._build_ui()
        self.setStyleSheet(QSS)

    # ---------- 无边框窗口：拖拽移动 + 手动边缘调整大小 ----------
    def paintEvent(self, e):
        """手动画圆角渐变背景（顶层窗口 QSS 背景不生效，需 paintEvent）。"""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#fdf2f8"))
        grad.setColorAt(0.5, QColor("#f5f3ff"))
        grad.setColorAt(1.0, QColor("#eef2ff"))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        p.end()

    def _hit_edge(self, pos):
        """判断鼠标位置在窗口哪个边缘（返回 Qt.Edges）。"""
        edges = Qt.Edges()
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = self._resize_margin
        if x <= m:
            edges |= Qt.LeftEdge
        if x >= w - m:
            edges |= Qt.RightEdge
        if y <= m:
            edges |= Qt.TopEdge
        if y >= h - m:
            edges |= Qt.BottomEdge
        return edges

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            edge = self._hit_edge(e.pos())
            if edge:
                # 边缘 → 记录起始状态，手动调整大小
                self._resize_edge = edge
                self._resize_start = e.globalPos()
                self._resize_geo = self.geometry()
            else:
                # 非边缘 → 拖拽移动窗口
                self._resize_edge = None
                self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        # 正在手动调整大小
        if self._resize_edge is not None and e.buttons() & Qt.LeftButton:
            self._do_resize(e.globalPos())
            e.accept()
            return
        # 正在拖拽移动
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
            e.accept()
            return
        # 悬停时更新光标形状
        if not e.buttons():
            edge = self._hit_edge(e.pos())
            if edge & (Qt.LeftEdge | Qt.RightEdge) and edge & (Qt.TopEdge | Qt.BottomEdge):
                if edge & Qt.LeftEdge and edge & Qt.TopEdge:
                    self.setCursor(Qt.SizeFDiagCursor)
                elif edge & Qt.RightEdge and edge & Qt.BottomEdge:
                    self.setCursor(Qt.SizeFDiagCursor)
                else:
                    self.setCursor(Qt.SizeBDiagCursor)
            elif edge & (Qt.LeftEdge | Qt.RightEdge):
                self.setCursor(Qt.SizeHorCursor)
            elif edge & (Qt.TopEdge | Qt.BottomEdge):
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.unsetCursor()

    def _do_resize(self, global_pos):
        """手动调整窗口大小，保证不小于最小尺寸（页面完整度）。"""
        delta = global_pos - self._resize_start
        edge = self._resize_edge
        geo = QRect(self._resize_geo)
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()

        if edge & Qt.LeftEdge:
            new_left = geo.left() + delta.x()
            # 左边缘不能超过右边缘 - 最小宽度
            new_left = min(new_left, geo.right() - min_w)
            geo.setLeft(new_left)
        if edge & Qt.RightEdge:
            new_right = geo.right() + delta.x()
            new_right = max(new_right, geo.left() + min_w)
            geo.setRight(new_right)
        if edge & Qt.TopEdge:
            new_top = geo.top() + delta.y()
            new_top = min(new_top, geo.bottom() - min_h)
            geo.setTop(new_top)
        if edge & Qt.BottomEdge:
            new_bottom = geo.bottom() + delta.y()
            new_bottom = max(new_bottom, geo.top() + min_h)
            geo.setBottom(new_bottom)

        self.setGeometry(geo)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        self._resize_edge = None

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(10)

        # ---- 自定义标题栏（无系统边框）----
        titlebar = QHBoxLayout()
        title = QLabel("🐾 桌宠生成器", self)
        title.setObjectName("Title")
        titlebar.addWidget(title)
        titlebar.addStretch(1)

        btn_min = QPushButton("—", self)
        btn_min.setObjectName("WinBtn")
        btn_min.setFixedSize(36, 32)
        btn_min.setCursor(Qt.PointingHandCursor)
        btn_min.clicked.connect(self.showMinimized)
        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("WinClose")
        btn_close.setFixedSize(36, 32)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        titlebar.addWidget(btn_min)
        titlebar.addWidget(btn_close)
        root.addLayout(titlebar)

        # ---- 副标题 ----
        subtitle = QLabel("上传一张图片，把它变成一只会陪你聊天的小宠物", self)
        subtitle.setObjectName("Subtitle")
        root.addWidget(subtitle)
        root.addSpacing(2)

        # ---- 主体：左右两栏 ----
        body = QHBoxLayout()
        body.setSpacing(16)

        # ===== 左栏：图片选择 =====
        img_card = _card(self)
        ic = QVBoxLayout(img_card)
        ic.setContentsMargins(18, 16, 18, 16)
        ic.setSpacing(12)
        ic.addWidget(_card_title("① 选择图片", img_card))

        self.img_label = QLabel("点击下方按钮选择图片\n支持 PNG / JPG / WEBP / BMP", self)
        self.img_label.setObjectName("ImageBox")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setMinimumSize(320, 280)
        ic.addWidget(self.img_label, 1)

        # 像素风格选项
        self.chk_pixel = QCheckBox("🎮 像素风格", self)
        self.chk_pixel.setCursor(Qt.PointingHandCursor)
        self.chk_pixel.toggled.connect(self._toggle_pixel)
        ic.addWidget(self.chk_pixel)

        # 像素大小调节（勾选像素风格时显示）
        self.pixel_box = QFrame(self)
        pb = QVBoxLayout(self.pixel_box)
        pb.setContentsMargins(0, 0, 0, 0)
        pb.setSpacing(6)

        pix_row = QHBoxLayout()
        pix_row.setSpacing(8)
        pix_lbl = QLabel("像素大小", self)
        pix_lbl.setStyleSheet("color:#6b7280; font-size:15px; font-weight:600;")
        self.pixel_slider = QSlider(Qt.Horizontal, self)
        self.pixel_slider.setRange(4, 40)
        self.pixel_slider.setValue(12)
        self.pixel_slider.setCursor(Qt.PointingHandCursor)
        self.pixel_slider.valueChanged.connect(self._on_pixel_change)
        self.pixel_val = QLabel("12px", self)
        self.pixel_val.setStyleSheet("color:#6d28d9; font-size:15px; font-weight:700;")
        self.pixel_val.setMinimumWidth(42)
        self.pixel_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pix_row.addWidget(pix_lbl)
        pix_row.addWidget(self.pixel_slider, 1)
        pix_row.addWidget(self.pixel_val)
        pb.addLayout(pix_row)

        self.pixel_box.setVisible(False)
        ic.addWidget(self.pixel_box)

        self.btn_pick = QPushButton("📁 选择图片", self)
        self.btn_pick.setObjectName("GhostBtn")
        self.btn_pick.setCursor(Qt.PointingHandCursor)
        self.btn_pick.clicked.connect(self._pick_image)
        ic.addWidget(self.btn_pick, alignment=Qt.AlignHCenter)
        body.addWidget(img_card, 2)

        # ===== 右栏：设定 + 配置 + 结果 + 按钮（可滚动，避免小窗口裁切） =====
        right_widget = QWidget(self)
        right_widget.setObjectName("RightCol")
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 6, 0)
        right.setSpacing(8)

        # 角色设定
        persona_card = _card(self)
        pc = QVBoxLayout(persona_card)
        pc.setContentsMargins(18, 16, 18, 16)
        pc.setSpacing(10)
        pc.addWidget(_card_title("② 角色设定", persona_card))

        self.chk_recognize = QCheckBox("使用 AI 自动识别形象", self)
        self.chk_recognize.setChecked(True)
        self.chk_recognize.setCursor(Qt.PointingHandCursor)
        self.chk_recognize.toggled.connect(self._toggle_manual)
        pc.addWidget(self.chk_recognize)

        hint = QLabel(
            "若模型不支持图片输入，可取消勾选，手动填写角色设定。", self
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        pc.addWidget(hint)

        self.manual_form = QFrame(self)
        mf = QFormLayout(self.manual_form)
        mf.setContentsMargins(0, 0, 0, 0)
        mf.setSpacing(8)
        mf.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.ed_name = QLineEdit(self)
        self.ed_name.setPlaceholderText("如：小白、皮卡丘、我的猫")
        self.ed_species = QLineEdit(self)
        self.ed_species.setPlaceholderText("如：猫、机器人、卡通角色")
        self.ed_personality = QLineEdit(self)
        self.ed_personality.setPlaceholderText("如：活泼黏人、爱撒娇、傲娇")

        mf.addRow(_field_label("名字", self), self.ed_name)
        mf.addRow(_field_label("种类", self), self.ed_species)
        mf.addRow(_field_label("性格", self), self.ed_personality)
        self.manual_form.setVisible(False)
        pc.addWidget(self.manual_form)

        # 编辑打招呼语
        self.btn_greet = QPushButton("💬 编辑打招呼语…", self)
        self.btn_greet.setObjectName("GhostBtn")
        self.btn_greet.setCursor(Qt.PointingHandCursor)
        self.btn_greet.clicked.connect(self._edit_greetings)
        pc.addWidget(self.btn_greet)
        right.addWidget(persona_card)

        # API 配置
        api_card = _card(self)
        ac = QVBoxLayout(api_card)
        ac.setContentsMargins(18, 16, 18, 16)
        ac.setSpacing(10)
        ac.addWidget(_card_title("③ AI 配置（聊天/动作生成）", api_card))

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.ed_base = QLineEdit(self.cfg.base_url, self)
        self.ed_base.setPlaceholderText("https://api.openai.com/v1")
        self.ed_key = QLineEdit(self.cfg.api_key, self)
        self.ed_key.setEchoMode(QLineEdit.Password)
        self.ed_key.setPlaceholderText("sk-...")

        # 模型用可编辑下拉框：预置所有服务商的最新模型，也能手动输入
        from . import providers
        self.ed_model = QComboBox(self)
        self.ed_model.setEditable(True)
        for m in providers.all_models():
            self.ed_model.addItem(m)
        self.ed_model.setCurrentText(self.cfg.model)
        self.ed_model.setCursor(Qt.PointingHandCursor)

        # Base URL 变化时自动识别服务商并推荐默认模型
        self.ed_base.editingFinished.connect(self._auto_pick_model)

        form.addRow(_field_label("Base URL", self), self.ed_base)
        form.addRow(_field_label("API Key", self), self.ed_key)
        form.addRow(_field_label("聊天模型", self), self.ed_model)
        ac.addLayout(form)
        right.addWidget(api_card)

        # 生成结果
        self.result_card = _card(self)
        rc = QVBoxLayout(self.result_card)
        rc.setContentsMargins(18, 16, 18, 16)
        rc.setSpacing(8)
        rc.addWidget(_card_title("④ 生成结果", self.result_card))
        self.result_text = QTextEdit(self)
        self.result_text.setObjectName("ResultBox")
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(90)
        self.result_text.setPlaceholderText("生成后这里会显示名字、种类、性格…")
        rc.addWidget(self.result_text)
        right.addWidget(self.result_card)

        # 生成按钮 + 状态
        self.btn_gen = QPushButton("✨ 生成桌宠", self)
        self.btn_gen.setObjectName("PrimaryBtn")
        self.btn_gen.setCursor(Qt.PointingHandCursor)
        self.btn_gen.clicked.connect(self._generate)
        self.btn_gen.setEnabled(False)
        right.addWidget(self.btn_gen)

        self.status = QLabel("", self)
        self.status.setObjectName("Status")
        self.status.setAlignment(Qt.AlignCenter)
        right.addWidget(self.status)

        # 历史桌宠
        hist_card = _card(self)
        hc = QVBoxLayout(hist_card)
        hc.setContentsMargins(18, 14, 18, 14)
        hc.setSpacing(8)
        hc.addWidget(_card_title("⑤ 历史桌宠", hist_card))

        self.cb_history = QComboBox(self)
        self.cb_history.setCursor(Qt.PointingHandCursor)
        self.cb_history.setMinimumHeight(34)
        hc.addWidget(self.cb_history)

        hrow = QHBoxLayout()
        hrow.setSpacing(8)
        self.btn_load = QPushButton("▶ 启动", self)
        self.btn_load.setObjectName("GhostBtn")
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.clicked.connect(self._load_history_pet)
        hrow.addWidget(self.btn_load, 1)

        self.btn_del = QPushButton("🗑 删除", self)
        self.btn_del.setObjectName("GhostBtn")
        self.btn_del.setCursor(Qt.PointingHandCursor)
        self.btn_del.clicked.connect(self._delete_history_pet)
        hrow.addWidget(self.btn_del, 1)
        hc.addLayout(hrow)

        self.btn_bone = QPushButton("✂️ 编辑骨骼（让四肢动起来）", self)
        self.btn_bone.setObjectName("GhostBtn")
        self.btn_bone.setCursor(Qt.PointingHandCursor)
        self.btn_bone.clicked.connect(self._edit_bones_from_main)
        hc.addWidget(self.btn_bone)
        right.addWidget(hist_card)

        right.addStretch(1)

        # 右栏用滚动区域包裹，避免窗口小时底部按钮被裁切
        scroll = QScrollArea(self)
        scroll.setWidget(right_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        body.addWidget(scroll, 3)

        root.addLayout(body, 1)

        # 刷新历史列表
        self._refresh_history()

    # ---------------------------------------------------------------- 逻辑
    def _toggle_manual(self, checked):
        self.manual_form.setVisible(not checked)

    def _toggle_pixel(self, checked):
        self.pixel_box.setVisible(checked)
        self._update_pixel_preview()

    def _on_pixel_change(self, val):
        self.pixel_val.setText(f"{val}px")
        self._update_pixel_preview()

    def _update_pixel_preview(self):
        """勾选像素风格且有图片时，实时预览像素化效果（仅显示，不抠图）。"""
        if not (self.chk_pixel.isChecked() and self.image_path):
            return
        try:
            from PIL import Image
            img = Image.open(self.image_path).convert("RGBA")
            # 复用 remover 的 8bit 复古像素化逻辑
            size = self.pixel_slider.value()
            pix = remover._pixelate_retro(img, size)
            # 转成 QPixmap 显示
            import tempfile
            tmp = os.path.join(tempfile.gettempdir(), "_pixel_preview.png")
            pix.save(tmp, "PNG")
            pm = QPixmap(tmp)
            self.img_label.setPixmap(
                pm.scaled(self.img_label.width() - 24, self.img_label.height() - 24,
                          Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        except Exception:
            pass  # 预览失败不阻塞主流程

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            self.image_path = path
            pm = QPixmap(path)
            self.img_label.setPixmap(
                pm.scaled(self.img_label.width() - 24, self.img_label.height() - 24,
                          Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.btn_gen.setEnabled(True)
            # 若已勾选像素风格，立即刷新预览
            if self.chk_pixel.isChecked():
                self._update_pixel_preview()

    def _auto_pick_model(self):
        """Base URL 变化时，自动识别服务商并推荐默认聊天模型。"""
        from . import providers
        base = self.ed_base.text().strip()
        prov = providers.detect_provider(base)
        if prov:
            # 把该服务商的模型加到下拉框顶部（如果还没有）
            cur = self.ed_model.currentText().strip()
            for m in prov["models"]:
                if self.ed_model.findText(m) < 0:
                    self.ed_model.addItem(m)
            self.ed_model.setCurrentText(prov["default"])
            self._set_status(f"已识别服务商：{prov['name']}，推荐模型 {prov['default']}", "done")
        else:
            self._set_status("未识别出服务商，请手动选择模型", "")

    def _current_cfg(self):
        self.cfg.base_url = self.ed_base.text().strip()
        self.cfg.api_key = self.ed_key.text().strip()
        self.cfg.model = self.ed_model.currentText().strip()
        return self.cfg

    def _set_status(self, text, kind=""):
        self.status.setText(text)
        self.status.setProperty("running", kind == "running")
        self.status.setProperty("done", kind == "done")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _generate(self):
        if not self.image_path:
            QMessageBox.warning(self, "提示", "请先选择图片")
            return
        cfg = self._current_cfg()
        do_recognize = self.chk_recognize.isChecked()

        if do_recognize:
            if not cfg.api_key:
                QMessageBox.warning(
                    self, "提示",
                    "自动识别形象需要填写 API Key。\n"
                    "如果你的模型不支持图片，请取消勾选「AI 自动识别」后手动填写角色设定。",
                )
                return
            manual_info = None
        else:
            manual_info = {
                "name": self.ed_name.text().strip() or "小宠物",
                "species": self.ed_species.text().strip(),
                "personality": self.ed_personality.text().strip(),
                "appearance": "",
            }

        cfgmod.save_config(cfg)

        self.btn_gen.setEnabled(False)
        self.btn_pick.setEnabled(False)
        self._set_status("处理中…", "running")

        pixelate = self.chk_pixel.isChecked()
        pixel_size = self.pixel_slider.value()
        self.worker = Worker(self.image_path, cfg, do_recognize, manual_info,
                             pixelate=pixelate, pixel_size=pixel_size, retro=True)
        self.worker.stage.connect(lambda s: self._set_status(s, "running"))
        self.worker.finished_ok.connect(self._on_done)
        self.worker.failed.connect(self._on_fail)
        self.worker.start()

    def _on_done(self, info):
        self.btn_gen.setEnabled(True)
        self.btn_pick.setEnabled(True)
        self._set_status("✅ 完成！桌宠已启动", "done")

        cfg = self._current_cfg()
        cfg.name = info.get("name", "小宠物")
        cfg.species = info.get("species", "")
        cfg.personality = info.get("personality", "")
        cfg.appearance = info.get("appearance", "")
        cfgmod.save_config(cfg)

        # 保存历史记录（头像文件已用唯一时间戳命名，不会覆盖）
        entry = {
            "id": os.path.splitext(os.path.basename(info["avatar_path"]))[0],
            "name": cfg.name,
            "species": cfg.species,
            "personality": cfg.personality,
            "appearance": cfg.appearance,
            "avatar_path": info["avatar_path"],
            "pixel": bool(info.get("pixel", False)),
        }
        cfgmod.add_history(entry)
        self._refresh_history()

        self.result_text.setPlainText(
            f"名字：{cfg.name}\n种类：{cfg.species or '未设置'}\n"
            f"性格：{cfg.personality or '未设置'}\n外观：{cfg.appearance or '未设置'}\n"
            f"风格：{'🎮 像素' if entry['pixel'] else '普通'}"
        )

        app = QApplication.instance()
        app.setQuitOnLastWindowClosed(False)
        pet_id = os.path.splitext(os.path.basename(info["avatar_path"]))[0]
        self._current_pet_id = pet_id
        pw = self._create_pet(info["avatar_path"], cfg, pet_id)
        pw.show()
        pw.greet()
        self._pet = pw

    def _create_pet(self, avatar_path, cfg, pet_id):
        """创建桌宠并加载已保存的骨骼配置。"""
        pw = pet.PetWindow(
            avatar_path, cfg,
            action_callback=self._do_action,
            bone_callback=lambda: self._edit_bones(pet_id),
            quit_callback=self._on_pet_closed,
        )
        bones = cfgmod.load_bones(pet_id)
        if bones:
            pw.load_skeleton(bones)
        return pw

    def _on_pet_closed(self):
        """桌宠被关闭时，清空主窗口引用。"""
        self._pet = None
        self._set_status("桌宠已关闭", "")

    def _edit_bones(self, pet_id):
        """打开骨骼编辑器，保存后立即应用到当前桌宠。"""
        from . import bone_editor
        if self._pet is None:
            return
        result = bone_editor.open_bone_editor(self._pet.image_path, self)
        if result:
            cfgmod.save_bones(pet_id, result)
            self._pet.load_skeleton(result)
            self._pet.show_bubble("骨骼已保存！试试右键「走路/挥手/跳舞」～")
            self._set_status("✅ 骨骼已保存", "done")

    def _edit_bones_from_main(self):
        """主界面「编辑骨骼」按钮：对当前桌宠编辑骨骼。"""
        if self._pet is None:
            QMessageBox.information(
                self, "提示",
                "请先生成一只桌宠，或用「▶ 启动」加载历史桌宠，\n"
                "然后再编辑它的骨骼。"
            )
            return
        pet_id = getattr(self, "_current_pet_id", None) or "default"
        self._edit_bones(pet_id)

    def _edit_greetings(self):
        """编辑打招呼语：用户自定义 + 系统默认预览。"""
        from . import greet_editor
        result = greet_editor.open_greet_editor(self.cfg, self)
        if result is not None:
            self.cfg.greet_msgs = result
            cfgmod.save_config(self.cfg)
            self._set_status("✅ 打招呼语已保存", "done")
            # 如果当前有桌宠，让它立刻用新语打招呼
            if self._pet is not None:
                self._pet.greet()

    def _on_fail(self, msg):
        self.btn_gen.setEnabled(True)
        self.btn_pick.setEnabled(True)
        self._set_status("❌ 失败", "")
        QMessageBox.critical(self, "生成失败", msg)

    # ---------------------------------------------------------------- 动作
    def _do_action(self, action: str):
        """触发动作生成：无 API 时明确提示；有 API 走图像生成。"""
        if self._pet is None:
            return
        cfg = self._current_cfg()
        if not cfg.api_key:
            self._pet.show_bubble(
                "未配置 API Key，无法用 AI 生成动作哦～\n"
                "可以右键选「走路/挥手/跳舞」体验本地动画。"
            )
            return

        # 防止重复启动 worker
        if getattr(self, "_action_worker_running", False):
            self._pet.show_bubble("正在生成动作，稍等一下哦～")
            return

        self._pet.show_bubble(f"让我{action}一下…")
        self._set_status(f"正在生成「{action}」动作…", "running")

        pixelate = self.chk_pixel.isChecked()
        pixel_size = self.pixel_slider.value()
        self.action_worker = ActionWorker(
            cfg, action, n_frames=4, pixelate=pixelate,
            pixel_size=pixel_size, retro=True,
        )
        self._action_worker_running = True
        self.action_worker.stage.connect(lambda s: self._set_status(s, "running"))
        self.action_worker.finished_ok.connect(self._on_action_done)
        self.action_worker.failed.connect(self._on_action_fail)
        self.action_worker.start()

    def _on_action_done(self, frames):
        self._action_worker_running = False
        self._set_status("✅ 动作完成！", "done")
        if self._pet is not None and frames:
            self._pet.play_action(frames, fps=6)

    def _on_action_fail(self, msg):
        self._action_worker_running = False
        self._set_status("❌ 动作生成失败", "")
        # 用桌宠气泡提示，不用弹窗（无边框窗口下弹窗易崩溃）
        if self._pet is not None:
            self._pet.show_bubble(
                f"这个动作做不了：{msg[:40]}\n"
                "试试右键「走路/挥手/跳舞」本地动画吧～",
                6000,
            )

    # ---------------------------------------------------------------- 历史
    def _refresh_history(self):
        entries = cfgmod.load_history()
        self.cb_history.clear()
        self._history_entries = entries
        if not entries:
            self.cb_history.addItem("（暂无历史桌宠）")
            self.btn_load.setEnabled(False)
            self.btn_del.setEnabled(False)
            return
        for e in entries:
            tag = "🎮" if e.get("pixel") else "🐾"
            self.cb_history.addItem(f"{tag} {e.get('name', '未命名')} - {e.get('species', '')}")
        self.btn_load.setEnabled(True)
        self.btn_del.setEnabled(True)

    def _current_history_entry(self):
        idx = self.cb_history.currentIndex()
        if not self._history_entries or idx < 0:
            return None
        return self._history_entries[idx]

    def _load_history_pet(self):
        entry = self._current_history_entry()
        if not entry:
            return
        path = entry.get("avatar_path")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "提示", "该桌宠的头像文件已丢失，无法启动。")
            self._refresh_history()
            return
        cfg = self._current_cfg()
        cfg.name = entry.get("name", "小宠物")
        cfg.species = entry.get("species", "")
        cfg.personality = entry.get("personality", "")
        cfg.appearance = entry.get("appearance", "")

        app = QApplication.instance()
        app.setQuitOnLastWindowClosed(False)
        pet_id = entry.get("id") or os.path.splitext(os.path.basename(path))[0]
        self._current_pet_id = pet_id
        pw = self._create_pet(path, cfg, pet_id)
        pw.show()
        pw.greet()
        self._pet = pw
        self._set_status(f"✅ 已启动「{cfg.name}」", "done")

    def _delete_history_pet(self):
        entry = self._current_history_entry()
        if not entry:
            return
        name = entry.get("name", "未命名")
        ret = QMessageBox.question(
            self, "确认删除", f"确定删除历史桌宠「{name}」吗？\n头像文件也会一并删除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        # 删除头像文件（容错，失败不阻塞）
        try:
            path = entry.get("avatar_path")
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        cfgmod.remove_history(entry.get("id"))
        self._refresh_history()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("桌宠生成器")
    app.setStyle("Fusion")  # 保证 QSS 一致渲染
    # 应用图标（打包进 exe 的 cat_paw.ico；源码运行时在项目根目录）
    try:
        import os
        if hasattr(sys, "_MEIPASS"):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ico = os.path.join(base, "cat_paw.ico")
        if os.path.exists(ico):
            app.setWindowIcon(QIcon(ico))
    except Exception:
        pass
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
