"""骨骼编辑器：用户在抠出的图上框选身体部位，用于 Live2D 式骨骼动画。"""
import sys

from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox,
    QMessageBox, QWidget,
)

from . import skeleton


class BoneCanvas(QWidget):
    """可框选部位的画布：显示抠图，用户拖拽框出矩形部位。"""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.parts = []  # [{"name", "rect": QRect}]
        self._dragging = False
        self._start = QPoint()
        self._current = QRect()
        self.current_part = "head"
        self.setMouseTracking(True)
        self.setMinimumSize(400, 400)

    def set_current_part(self, name: str):
        self.current_part = name

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = True
            self._start = e.pos()
            self._current = QRect(e.pos(), e.pos())
            e.accept()

    def mouseMoveEvent(self, e):
        if self._dragging:
            self._current = QRect(self._start, e.pos()).normalized()
            self.update()
        e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = False
            r = QRect(self._start, e.pos()).normalized()
            if r.width() > 10 and r.height() > 10:
                # 移除同名的旧部位，避免重复
                self.parts = [p for p in self.parts if p["name"] != self.current_part]
                self.parts.append({"name": self.current_part, "rect": r})
            self.update()
            e.accept()

    def clear(self):
        self.parts = []
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        if not self.pixmap.isNull():
            # 缩放图片填满画布
            scaled = self.pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ox = (self.width() - scaled.width()) // 2
            oy = (self.height() - scaled.height()) // 2
            p.drawPixmap(ox, oy, scaled)

            # 画已框选的部位
            colors = {
                "head": QColor("#ef4444"),
                "body": QColor("#3b82f6"),
                "left_arm": QColor("#22c55e"),
                "right_arm": QColor("#eab308"),
                "left_leg": QColor("#8b5cf6"),
                "right_leg": QColor("#ec4899"),
            }
            for part in self.parts:
                r = part["rect"]
                c = colors.get(part["name"], QColor("#888"))
                pen = QPen(c, 2)
                p.setPen(pen)
                p.drawRect(r)
                p.drawText(r.x() + 3, r.y() - 4, skeleton.PART_LABELS.get(part["name"], part["name"]))

            # 画正在拖拽的框
            if self._dragging:
                p.setPen(QPen(QColor("#6d28d9"), 2, Qt.DashLine))
                p.drawRect(self._current)

        # 提示文字
        p.setPen(QColor("#6d28d9"))
        f = QFont()
        f.setPointSize(10)
        p.setFont(f)
        p.drawText(10, self.height() - 10,
                   "拖拽框选部位；先在上方选择部位，再框选对应区域")
        p.end()


class BoneEditor(QDialog):
    """骨骼编辑对话框：框选各部位并保存。"""

    def __init__(self, avatar_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("骨骼编辑 - 框选身体部位")
        self.resize(580, 680)
        self.avatar_path = avatar_path
        self.pixmap = QPixmap(avatar_path)
        # 无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None
        self.setStyleSheet(
            "QPushButton#WinClose { background: transparent; color:#9ca3af;"
            "border:none; border-radius:6px; font-size:14px; font-weight:700; }"
            "QPushButton#WinClose:hover { background:#ef4444; color:#ffffff; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        # 自定义标题栏
        titlebar = QHBoxLayout()
        title_label = QLabel("✂️ 骨骼编辑 - 框选身体部位", self)
        title_label.setStyleSheet(
            "font-size:16px; font-weight:800; color:#6d28d9; padding:4px 2px;"
        )
        titlebar.addWidget(title_label)
        titlebar.addStretch(1)
        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("WinClose")
        btn_close.setFixedSize(30, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        titlebar.addWidget(btn_close)
        layout.addLayout(titlebar)

        tip = QLabel("框选身体各部位，用于让四肢独立动起来（走路、挥手等）。\n"
                     "建议至少框选：头部、躯干、左右手臂、左右腿。")
        tip.setStyleSheet("color:#6b7280; font-size:14px;")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        # 部位选择
        sel_row = QHBoxLayout()
        sel_label = QLabel("当前部位：")
        sel_label.setStyleSheet("font-size:14px; font-weight:600; color:#6d28d9;")
        self.part_combo = QComboBox()
        for name, label in skeleton.PART_LABELS.items():
            self.part_combo.addItem(label, name)
        self.part_combo.setStyleSheet(
            "padding:8px 12px; font-size:14px; border:2px solid #ddd6fe; border-radius:8px;"
        )
        self.part_combo.currentIndexChanged.connect(self._on_part_change)
        sel_row.addWidget(sel_label)
        sel_row.addWidget(self.part_combo, 1)
        layout.addLayout(sel_row)

        # 画布
        self.canvas = BoneCanvas(self.pixmap, self)
        layout.addWidget(self.canvas, 1)

        # 按钮
        btn_row = QHBoxLayout()
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self.canvas.clear)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("保存骨骼")
        btn_save.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8b5cf6,stop:1 #ec4899);"
            "color:white;border:none;border-radius:10px;padding:10px 20px;font-weight:700;"
        )
        btn_save.clicked.connect(self._save)
        for b in (btn_clear, btn_cancel, btn_save):
            b.setCursor(Qt.PointingHandCursor)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _on_part_change(self, idx):
        name = self.part_combo.itemData(idx)
        self.canvas.set_current_part(name)

    # ---------- 无边框窗口拖拽 ----------
    def paintEvent(self, e):
        """手动画圆角背景。"""
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

    def _save(self):
        if len(self.canvas.parts) < 2:
            QMessageBox.warning(self, "提示", "请至少框选 2 个部位（如头部和躯干）。")
            return
        # 把画布坐标转成图片坐标（画布按 KeepAspectRatio 缩放）
        scaled = self.pixmap.scaled(self.canvas.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        ox = (self.canvas.width() - scaled.width()) // 2
        oy = (self.canvas.height() - scaled.height()) // 2
        sx = self.pixmap.width() / scaled.width()
        sy = self.pixmap.height() / scaled.height()

        W, H = self.pixmap.width(), self.pixmap.height()
        parts = []
        for p in self.canvas.parts:
            r = p["rect"]
            name = p["name"]
            # 转成图片像素坐标
            x = max(0, int((r.x() - ox) * sx))
            y = max(0, int((r.y() - oy) * sy))
            w = min(W - x, int(r.width() * sx))
            h = min(H - y, int(r.height() * sy))
            # 存成比例坐标
            pivot = skeleton.PART_PIVOTS.get(name, {"x": 0.5, "y": 0.5})
            parts.append({
                "name": name,
                "x": x / W, "y": y / H,
                "w": w / W, "h": h / H,
                "pivot_x": pivot["x"], "pivot_y": pivot["y"],
            })
        self.result = {"parts": parts, "img_w": W, "img_h": H}
        self.accept()


def open_bone_editor(avatar_path: str, parent=None):
    """打开骨骼编辑器，返回骨骼配置 dict 或 None（取消）。"""
    dlg = BoneEditor(avatar_path, parent)
    if dlg.exec_() == QDialog.Accepted:
        return dlg.result
    return None
