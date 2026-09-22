"""素材展示组件：图片缩略图卡片与视频信息卡片。"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


def _load_pixmap(path_or_bytes) -> QPixmap:
    if isinstance(path_or_bytes, (bytes, bytearray)):
        return QPixmap()
    return QPixmap(str(Path(path_or_bytes)))


class ImageCard(QFrame):
    """单张图片卡片：缩略图、尺寸、查看/下载/复制操作。"""

    view_requested = Signal(dict)
    download_requested = Signal(dict)
    copy_requested = Signal(dict)

    def __init__(self, image: dict, thumbnail_path: str = ""):
        super().__init__()
        self.image = image
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        thumb = QLabel()
        pixmap = _load_pixmap(thumbnail_path)
        if not pixmap.isNull():
            thumb.setPixmap(pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            thumb.setText("无预览")
            thumb.setAlignment(Qt.AlignCenter)
            thumb.setFixedSize(180, 120)
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
