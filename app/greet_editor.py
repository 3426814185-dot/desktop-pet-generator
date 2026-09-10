"""打招呼语编辑器：用户自定义打招呼内容，附系统默认语预览。"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget,
    QLineEdit, QMessageBox, QWidget,
)

from . import pet as pet_mod


class GreetEditor(QDialog):
    """编辑打招呼语对话框（无边框）。"""

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("编辑打招呼语")
        self.resize(460, 520)
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

        # 标题栏
        titlebar = QHBoxLayout()
        title = QLabel("💬 编辑打招呼语", self)
        title.setStyleSheet("font-size:16px; font-weight:800; color:#6d28d9;")
        titlebar.addWidget(title)
        titlebar.addStretch(1)
        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("WinClose")
        btn_close.setFixedSize(30, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        titlebar.addWidget(btn_close)
        layout.addLayout(titlebar)

        tip = QLabel("自定义桌宠打招呼时会说的话（会随机选一条）。\n"
                     "下方「系统默认」不可删，供参考；你可以在「自定义」里增删。")
        tip.setStyleSheet("color:#6b7280; font-size:13px;")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        # 自定义列表
        lbl_custom = QLabel("我的自定义", self)
        lbl_custom.setStyleSheet("font-size:14px; font-weight:700; color:#6d28d9;")
        layout.addWidget(lbl_custom)

        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet(
            "QListWidget { background: #ffffff; border:2px solid #f3e8ff;"
            "border-radius:10px; padding:6px; font-size:14px; }"
        )
        for m in (cfg.greet_msgs or []):
            if m and m.strip():
                self.list_widget.addItem(m.strip())
        layout.addWidget(self.list_widget, 1)

        # 输入行
        input_row = QHBoxLayout()
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("输入一句新的打招呼语…")
        self.input.setStyleSheet(
            "padding:9px 12px; font-size:14px; border:2px solid #e5e7eb; border-radius:10px;"
        )
        self.input.returnPressed.connect(self._add)
        btn_add = QPushButton("➕ 添加", self)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(
            "background:#8b5cf6; color:white; border:none; border-radius:10px;"
            "padding:9px 16px; font-weight:700;"
        )
        btn_add.clicked.connect(self._add)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(btn_add)
        layout.addLayout(input_row)

        btn_del = QPushButton("🗑 删除选中", self)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet(
            "background:#ffffff; color:#ef4444; border:2px solid #fecaca;"
            "border-radius:10px; padding:8px; font-weight:600;"
        )
        btn_del.clicked.connect(self._delete)
        layout.addWidget(btn_del)

        # 系统默认预览
        lbl_default = QLabel("系统默认（不可编辑）", self)
        lbl_default.setStyleSheet("font-size:14px; font-weight:700; color:#8b8ba7;")
        layout.addWidget(lbl_default)

        default_box = QListWidget(self)
        default_box.setStyleSheet(
            "QListWidget { background:#faf5ff; border:2px solid #f3e8ff;"
            "border-radius:10px; padding:6px; font-size:14px; color:#8b8ba7; }"
        )
        for m in pet_mod.PetWindow.DEFAULT_GREETINGS:
            default_box.addItem(m)
        default_box.setMaximumHeight(110)
        layout.addWidget(default_box)

        # 保存/取消
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("取消", self)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("保存", self)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8b5cf6,stop:1 #ec4899);"
            "color:white;border:none;border-radius:10px;padding:10px 24px;font-weight:700;"
        )
        btn_save.clicked.connect(self._save)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _add(self):
        text = self.input.text().strip()
        if not text:
            return
        self.list_widget.addItem(text)
        self.input.clear()

    def _delete(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def _save(self):
        msgs = [self.list_widget.item(i).text()
                for i in range(self.list_widget.count())]
        self.result = [m for m in msgs if m and m.strip()]
        self.accept()

    # ---------- 无边框拖拽 ----------
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


def open_greet_editor(cfg, parent=None):
    """打开打招呼语编辑器，返回用户自定义列表或 None（取消）。"""
    dlg = GreetEditor(cfg, parent)
    if dlg.exec_() == QDialog.Accepted:
        return dlg.result
    return None
