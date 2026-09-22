"""应用服务层：纯逻辑（网址识别、下载命名、错误映射、资源下载），与 GUI 解耦。"""

import re
from pathlib import Path

import httpx

SHARE_URL_RE = re.compile(
    r"https://(?:[a-z0-9-]+\.)*(?:doubao|dola)\.com/thread/[A-Za-z0-9_\-?&=./]+",
    re.IGNORECASE,
)

_MEDIA_TYPE_LABELS = {"image": "图片", "video": "视频"}
_EXTENSION_BY_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/webm": "webm",
}


def extract_share_links(text: str) -> list[str]:
    """从任意文本中提取豆包/豆乐对话分享链接，去重并保持顺序。"""
    seen: set[str] = set()
    links: list[str] = []
    for match in SHARE_URL_RE.finditer(text or ""):
        url = match.group(0).rstrip(".,;，。；、")
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


def build_filename(media_type: str, index: int, extension: str = "") -> str:
    """基于资源类型与序号生成文件名，如 图片_001.jpg。"""
    label = _MEDIA_TYPE_LABELS.get(media_type, media_type)
    ext = extension.lstrip(".").lower()
    return f"{label}_{index:03d}.{ext}" if ext else f"{label}_{index:03d}"


def _extension_from_url(url: str) -> str:
    path = httpx.URL(url).path
    suffix = Path(path).suffix.lstrip(".").lower()
    return suffix if len(suffix) <= 5 else ""


def _extension_from_headers(headers: httpx.Headers) -> str:
    content_type = (headers.get("content-type") or "").split(";")[0].strip().lower()
    return _EXTENSION_BY_MIME.get(content_type, "")


def download_resource(
    url: str,
    dest_dir,
    media_type: str,
    index: int,
    extension: str = "",
    client: httpx.Client | None = None,
) -> Path:
    """下载资源到 dest_dir，返回保存路径。extension 缺省时从 Content-Type 推断。"""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    close_client = client is None
    client = client or httpx.Client(follow_redirects=True, timeout=30)

    try:
        response = client.get(url)
        response.raise_for_status()
        ext = extension or _extension_from_headers(response.headers) or _extension_from_url(url)
        filename = build_filename(media_type, index, ext)
        target = dest_dir / filename
        target.write_bytes(response.content)
        return target
    finally:
        if close_client:
            client.close()


def map_error(exc: Exception) -> str:
    """将解析异常映射为用户可读的错误信息。"""
    if isinstance(exc, (ValueError, KeyError)) and getattr(exc, "args", ()):
        return str(exc.args[0])
    return "解析失败，请检查链接是否正确"
