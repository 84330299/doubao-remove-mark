"""GUI 构建级的离屏冒烟测试：验证窗口与卡片可无头实例化（CI 可用）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.widgets import ImageCard, VideoCard


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_main_window_constructs(qapp):
    window = MainWindow()
    assert window.windowTitle() == "无印豆包"
    assert window.tabs.count() == 2
    window.close()


def test_image_card_constructs(qapp):
    card = ImageCard({"url": "https://x.com/a.jpg", "width": 1024, "height": 768})
    assert card.image["url"] == "https://x.com/a.jpg"


def test_video_card_constructs(qapp):
    card = VideoCard({"url": "https://x.com/v.mp4", "width": 1920, "height": 1080, "definition": "2k"})
    assert card.video["definition"] == "2k"


def test_video_card_set_thumbnail(qapp):
    from PySide6.QtGui import QPixmap

    card = VideoCard({"url": "https://x.com/v.mp4", "poster_url": "https://x.com/poster.jpg"})
    pixmap = QPixmap(160, 90)
    pixmap.fill()
    card.set_thumbnail(pixmap)
    assert not card._cover.pixmap().isNull()
