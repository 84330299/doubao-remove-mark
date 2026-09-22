"""后台 worker 层：在 Qt 线程池中运行解析/下载，通过信号回传主线程。

核心逻辑在 app.service 与 parser 包中；本模块仅做薄薄的线程封装。
"""

from PySide6.QtCore import QObject, QRunnable, Signal

from app.service import download_resource, map_error
from parser.image import doubao_image_parse
from parser.video import doubao_video_parse


class _WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)


class ParseWorker(QRunnable):
    """在后台线程解析一个豆包分享链接的图片或视频。"""

    def __init__(self, url: str, parse_kind: str = "image"):
        super().__init__()
        # 禁止 Qt 在线程结束后自动销毁 QRunnable，避免待投递的信号因对象被
        # 提前释放而丢失（表现为首次点击“解析”无反应，需多次点击）。
        self.setAutoDelete(False)
        self._url = url
        self._kind = parse_kind
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            if self._kind == "video":
                result = doubao_video_parse(self._url)
            else:
                result = doubao_image_parse(self._url)
            self.signals.succeeded.emit(result)
        except Exception as exc:  # 边界处统一切换为用户可读信息
            self.signals.failed.emit(map_error(exc))


class DownloadWorker(QRunnable):
    """在后台线程下载单个资源文件。"""

    def __init__(self, url: str, dest_dir: str, media_type: str, index: int, target_path: str = ""):
        super().__init__()
        self.setAutoDelete(False)
        self._url = url
        self._dest_dir = dest_dir
        self._media_type = media_type
        self._index = index
        self._target_path = target_path
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            path = download_resource(
                self._url, self._dest_dir, self._media_type, self._index, target_path=self._target_path
            )
            self.signals.succeeded.emit(str(path))
        except Exception as exc:  # 边界处统一切换为用户可读信息
            self.signals.failed.emit(map_error(exc))
