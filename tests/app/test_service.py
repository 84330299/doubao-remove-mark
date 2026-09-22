import httpx
import pytest
from httpx import MockTransport, Response

from app.service import build_filename, download_resource, extract_share_links, map_error


class TestExtractShareLinks:
    def test_extracts_doubao_thread_urls_from_text(self):
        text = (
            "看看这个 https://www.doubao.com/thread/aef4c7a4c78c2 很不错，"
            "还有 https://www.doubao.com/thread/w3de509c584a4e3da?from=x 另一个。"
        )
        assert extract_share_links(text) == [
            "https://www.doubao.com/thread/aef4c7a4c78c2",
            "https://www.doubao.com/thread/w3de509c584a4e3da?from=x",
        ]

    def test_accepts_dola_and_subdomain_with_query(self):
        text = "https://www.dola.com/thread/xWX8HqqSPfJoKRcbg 和 https://ailab.doubao.com/thread/xyz?a=1&b=2"
        result = extract_share_links(text)
        assert "https://www.dola.com/thread/xWX8HqqSPfJoKRcbg" in result
        assert "https://ailab.doubao.com/thread/xyz?a=1&b=2" in result

    def test_deduplicates_and_preserves_order(self):
        url = "https://www.doubao.com/thread/abc123"
        assert extract_share_links(f"{url} {url} {url}") == [url]

    def test_ignores_unsupported_links_and_returns_empty_when_none(self):
        text = "https://www.qianwen.com/thread/abc 和 https://example.com/thread/def 和普通文字"
        assert extract_share_links(text) == []


class TestBuildFilename:
    def test_image_naming_with_zero_padded_index(self):
        assert build_filename("image", 1, "jpg") == "图片_001.jpg"
        assert build_filename("image", 23, "png") == "图片_023.png"

    def test_video_naming(self):
        assert build_filename("video", 2, "mp4") == "视频_002.mp4"


class TestMapError:
    def test_maps_value_error_to_readable(self):
        assert map_error(ValueError("链接格式不正确，请使用豆包对话链接（包含 /thread/）")) == (
            "链接格式不正确，请使用豆包对话链接（包含 /thread/）"
        )

    def test_maps_key_error_page_parse(self):
        assert map_error(KeyError("无法解析页面数据，请确认链接是否有效")) == "无法解析页面数据，请确认链接是否有效"

    def test_maps_network_error(self):
        assert "网络请求失败" in map_error(ValueError("网络请求失败，请检查网络连接: timeout"))

    def test_maps_unknown_to_generic(self):
        assert map_error(RuntimeError("boom")) == "解析失败，请检查链接是否正确"


class TestDownloadResource:
    def _client(self):
        def handler(request):
            assert str(request.url) == "https://cdn.example.com/img.jpg"
            return Response(200, content=b"\x89PNG-data", headers={"Content-Type": "image/jpeg"})

        return httpx.Client(transport=MockTransport(handler))

    def test_downloads_and_writes_to_dest_dir(self, tmp_path):
        client = self._client()
        dest = download_resource("https://cdn.example.com/img.jpg", tmp_path, "image", 1, "jpg", client=client)
        assert dest == tmp_path / "图片_001.jpg"
        assert dest.read_bytes() == b"\x89PNG-data"

    def test_uses_extension_from_content_type_when_not_given(self, tmp_path):
        def handler(request):
            return Response(200, content=b"abc", headers={"Content-Type": "video/mp4"})

        client = httpx.Client(transport=MockTransport(handler))
        dest = download_resource("https://cdn.example.com/v", tmp_path, "video", 2, client=client)
        assert dest.name == "视频_002.mp4"

    def test_raises_on_non_ok_response(self, tmp_path):
        def handler(request):
            return Response(404)

        client = httpx.Client(transport=MockTransport(handler))
        with pytest.raises(httpx.HTTPStatusError):
            download_resource("https://cdn.example.com/missing", tmp_path, "image", 1, "jpg", client=client)
