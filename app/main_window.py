"""主窗口：URL 输入、图片/视频标签页、后台解析与下载、素材展示。"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.service import default_save_name, extract_share_links
from app.widgets import FlowLayout, ImageCard, VideoCard
from app.workers import DownloadWorker, ParseWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无印豆包")
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))
        self.thread_pool = QThreadPool.globalInstance()
        self._active_workers = []
        self._thumb_workers = []
        self._download_seq = 0
        self._last_save_dir = ""
        self._last_url = ""
        self._last_tab = 0

        self._build_ui()
        self._restore_state()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("粘贴豆包（doubao/dola）对话分享链接…")
        self.url_input.setFixedHeight(44)
        self.url_input.returnPressed.connect(self._on_parse)
        root.addWidget(self.url_input)

        controls = QVBoxLayout()
        controls.setSpacing(8)
        self.tabs = QTabWidget()
        self.tabs.addTab(QWidget(), "图片")
        self.tabs.addTab(QWidget(), "视频")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        controls.addWidget(self.tabs)

        self.parse_btn = QPushButton("解析")
        self.parse_btn.setFixedHeight(44)
        self.parse_btn.clicked.connect(self._on_parse)
        controls.addWidget(self.parse_btn)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        controls.addWidget(self.status_label)

        root.addLayout(controls)

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self._results_host = QWidget()
        self._results_layout = FlowLayout(self._results_host, spacing=8)
        self.results_scroll.setWidget(self._results_host)
        root.addWidget(self.results_scroll, stretch=1)

        self.setCentralWidget(central)
        self.url_input.setFocus()

    def _restore_state(self) -> None:
        self.url_input.setText(self._last_url)
        self.tabs.setCurrentIndex(self._last_tab)

    def _on_tab_changed(self, index: int) -> None:
        self._last_tab = index
        self._clear_results()

    def _on_parse(self) -> None:
        self._last_url = self.url_input.text().strip()
        links = extract_share_links(self._last_url)
        self._clear_results()

        if not links:
            self.status_label.setText("未识别到有效的豆包分享链接，请检查输入。")
            return

        url = links[0]
        kind = "video" if self.tabs.currentIndex() == 1 else "image"
        self.status_label.setText("正在解析，请稍候…")
        self.parse_btn.setEnabled(False)

        worker = ParseWorker(url, kind)
        worker.signals.succeeded.connect(self._on_parse_success)
        worker.signals.failed.connect(self._on_parse_failed)
        self._active_workers.append(worker)
        worker.signals.succeeded.connect(lambda _r: self._track_done(worker))
        worker.signals.failed.connect(lambda _e: self._track_done(worker))
        self.thread_pool.start(worker)

    def _track_done(self, worker) -> None:
        try:
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            worker.signals.deleteLater()
        finally:
            self.parse_btn.setEnabled(True)

    def _clear_results(self) -> None:
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _add_card(self, card: QWidget) -> None:
        self._results_layout.addWidget(card)

    def _on_parse_success(self, items: list) -> None:
        self.status_label.setText("")
        if not items:
            self.status_label.setText("解析完成，但未找到资源。")
            return
        is_video = self.tabs.currentIndex() == 1
        for item in items:
            if is_video:
                card = VideoCard(item)
                card.download_requested.connect(self._on_download)
                card.copy_requested.connect(self._on_copy_link)
                card.open_requested.connect(self._on_open)
            else:
                card = ImageCard(item)
                card.download_requested.connect(self._on_download)
                card.copy_requested.connect(self._on_copy_link)
                card.view_requested.connect(self._on_open)
                self._load_thumbnail(card, item)
            self._add_card(card)
        self.status_label.setText(f"共找到 {len(items)} 项。")

    def _load_thumbnail(self, card, item: dict) -> None:
        """后台下载缩略图，完成后刷新卡片预览。"""
        url = item.get("url")
        if not url:
            return
        thumb_dir = os.path.join(tempfile.gettempdir(), "doubao_remove_mark_thumbs")
        os.makedirs(thumb_dir, exist_ok=True)
        index = len(self._thumb_workers) + 1
        worker = DownloadWorker(str(url), thumb_dir, "image", index)
        worker.signals.succeeded.connect(lambda path, c=card: self._on_thumb_ready(c, path))
        self._thumb_workers.append(worker)
        self.thread_pool.start(worker)

    def _on_thumb_ready(self, card, path: str) -> None:
        pixmap = QPixmap(str(path))
        if not pixmap.isNull() and card.isVisible():
            card.set_thumbnail(pixmap)

    def _on_parse_failed(self, message: str) -> None:
        self._clear_results()
        self.status_label.setText(f"解析失败：{message}")

    def _on_copy_link(self, item: dict) -> None:
        url = item.get("url")
        if url:
            QGuiApplication.clipboard().setText(str(url))
            self.status_label.setText("链接已复制到剪贴板。")

    def _on_open(self, item: dict) -> None:
        url = item.get("url")
        if not url:
            return
        if sys.platform == "win32":
            os.startfile(str(url))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(url)])
        else:
            subprocess.Popen(["xdg-open", str(url)])

    def _on_download(self, item: dict) -> None:
        url = item.get("url")
        if not url:
            return

        is_video = "poster_url" in item or "definition" in item
        media_type = "video" if is_video else "image"
        default_name = default_save_name(media_type)
        default_path = str(Path(self._last_save_dir) / default_name) if self._last_save_dir else default_name
        chosen, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            default_path,
            "媒体文件 (*.jpg *.jpeg *.png *.webp *.gif *.mp4 *.mov *.webm)",
        )
        if not chosen:
            return

        target = Path(chosen)
        self._last_save_dir = str(target.parent)
        worker = DownloadWorker(str(url), str(target.parent), media_type, self._download_seq, target_path=str(target))
        worker.signals.succeeded.connect(lambda _p: self._on_downloaded(str(target)))
        worker.signals.failed.connect(self._on_download_failed)
        self._active_workers.append(worker)
        self.thread_pool.start(worker)

    def _on_downloaded(self, path: str) -> None:
        self.status_label.setText(f"下载完成：{path}")

    def _on_download_failed(self, message: str) -> None:
        QMessageBox.warning(self, "下载失败", message)
