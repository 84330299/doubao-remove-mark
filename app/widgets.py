"""素材展示组件：图片缩略图卡片与视频信息卡片。"""

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


def _load_pixmap(path_or_bytes) -> QPixmap:
    if isinstance(path_or_bytes, (bytes, bytearray)):
        return QPixmap()
    return QPixmap(str(Path(path_or_bytes)))


class FlowLayout(QLayout):
    """流式布局：卡片按实际宽度自动换行，每行铺满剩余宽度。"""

    def __init__(self, parent=None, spacing: int = 8):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)
        self._items = []

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Horizontal)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._arrange(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._arrange(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        margins = self.contentsMargins()
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _arrange(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        spacing = self.spacing()
        left = rect.x() + margins.left()
        right = rect.right() - margins.right()
        total_width = right - left + 1
        y = rect.y() + margins.top()

        if total_width <= 0:
            rows = [[item] for item in self._items]
        else:
            rows = []
            row = []
            row_width = 0
            for item in self._items:
                item_width = item.sizeHint().width()
                if row and row_width + spacing + item_width > total_width:
                    rows.append(row)
                    row = []
                    row_width = 0
                if row:
                    row_width += spacing
                row.append(item)
                row_width += item_width
            if row:
                rows.append(row)

        for row_index, row in enumerate(rows):
            row_height = max(item.sizeHint().height() for item in row)
            row_width = sum(item.sizeHint().width() for item in row) + spacing * (len(row) - 1)
            # 只有因放不下而换行的“满行”才拉伸铺满；最后一行保持卡片自然宽度。
            is_full_row = total_width > 0 and row_index < len(rows) - 1
            share = max(0, total_width - row_width) // len(row) if is_full_row else 0
            x = left
            for item in row:
                hint = item.sizeHint()
                width = hint.width() + share
                if not test_only:
                    item.setGeometry(QRect(QPoint(x, y), QSize(width, row_height)))
                x += width + spacing
            y += row_height + spacing

        return y + margins.bottom() - rect.y() - spacing


class ImageCard(QFrame):
    """单张图片卡片：缩略图、尺寸、查看/下载/复制操作。"""

    view_requested = Signal(dict)
    download_requested = Signal(dict)
    copy_requested = Signal(dict)

    def __init__(self, image: dict, thumbnail_path: str = ""):
        super().__init__()
        self.image = image
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        thumb = QLabel()
        pixmap = _load_pixmap(thumbnail_path)
        if not pixmap.isNull():
            thumb.setPixmap(pixmap.scaled(640, 640, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            thumb.setText("无预览")
            thumb.setAlignment(Qt.AlignCenter)
            thumb.setFixedHeight(160)
        thumb.setAlignment(Qt.AlignCenter)
        layout.addWidget(thumb)

        width = image.get("width")
        height = image.get("height")
        size_text = f"{width}×{height}" if width and height else "未知尺寸"
        info = QLabel(size_text)
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        view_btn = QPushButton("查看")
        dl_btn = QPushButton("下载")
        copy_btn = QPushButton("复制")
        view_btn.clicked.connect(lambda: self.view_requested.emit(image))
        dl_btn.clicked.connect(lambda: self.download_requested.emit(image))
        copy_btn.clicked.connect(lambda: self.copy_requested.emit(image))
        buttons.addWidget(view_btn)
        buttons.addWidget(dl_btn)
        buttons.addWidget(copy_btn)
        layout.addLayout(buttons)

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        """解析完成后回填真实缩略图。"""
        thumb = self.findChild(QLabel)
        if thumb is None:
            return
        thumb.setPixmap(
            pixmap.scaled(
                thumb.width() or 320,
                320,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )


class VideoCard(QFrame):
    """单条视频卡片：封面、宽高、清晰度、下载/复制/打开操作。"""

    download_requested = Signal(dict)
    copy_requested = Signal(dict)
    open_requested = Signal(dict)

    def __init__(self, video: dict, cover_path: str = ""):
        super().__init__()
        self.video = video
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        cover = QLabel()
        pixmap = _load_pixmap(cover_path)
        if not pixmap.isNull():
            cover.setPixmap(pixmap.scaled(160, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            cover.setText("视频封面")
            cover.setFixedSize(160, 90)
        cover.setAlignment(Qt.AlignCenter)
        layout.addWidget(cover)

        text_layout = QVBoxLayout()
        width = video.get("width")
        height = video.get("height")
        resolution = f"{width}×{height}" if width and height else "未知尺寸"
        definition = video.get("definition") or "清晰度未知"
        title = QLabel(f"{definition} · {resolution}")
        text_layout.addWidget(title)
        if video.get("poster_url"):
            text_layout.addWidget(QLabel("（含封面）"))
        text_layout.addStretch()
        layout.addLayout(text_layout)

        button_layout = QVBoxLayout()
        button_layout.setSpacing(6)
        dl_btn = QPushButton("下载")
        copy_btn = QPushButton("复制链接")
        open_btn = QPushButton("打开")
        dl_btn.clicked.connect(lambda: self.download_requested.emit(video))
        copy_btn.clicked.connect(lambda: self.copy_requested.emit(video))
        open_btn.clicked.connect(lambda: self.open_requested.emit(video))
        button_layout.addWidget(dl_btn)
        button_layout.addWidget(copy_btn)
        button_layout.addWidget(open_btn)
        layout.addLayout(button_layout)
