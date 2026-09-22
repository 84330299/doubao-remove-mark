import html as html_mod
import json

import pytest

from parser.image import doubao_image_parse, is_doubao_thread_url, parse_image_html


def _script(inner: str) -> str:
    return (
        '<script data-script-src="modern-run-router-data-fn" '
        f'data-fn-args="{html_mod.escape(inner, quote=True)}" nonce="abc123"></script>'
    )


def _page_html(images: list[dict], as_content_v2: bool = True) -> str:
    creations = [{"image": {"image_ori_raw": img}} for img in images]
    inner = {"creation_block": {"creations": creations}}
    content = json.dumps(inner, ensure_ascii=False)
    block = {"content_v2": content} if as_content_v2 else {"content": content}
    message_list = [{"content_block": [block]}]
    payload = [{"data": {"message_snapshot": {"message_list": message_list}}}]
    return "<html><head></head><body>" + _script(json.dumps(payload, ensure_ascii=False)) + "</body></html>"


class TestParseImageHtml:
    def test_extracts_normalized_images(self):
        page = _page_html([{"url": "https://x.com/a.jpg?q=1&w=2", "width": 1024, "height": 768}])
        images = parse_image_html(page)
        assert images == [{"url": "https://x.com/a.jpg?q=1&w=2", "width": 1024, "height": 768}]

    def test_normalizes_amp_entity_in_url(self):
        page = _page_html([{"url": "https://x.com/b.jpg?a=1&b=2&c=3", "width": 640, "height": 480}])
        assert parse_image_html(page)[0]["url"] == "https://x.com/b.jpg?a=1&b=2&c=3"

    def test_returns_multiple_images_in_order(self):
        page = _page_html(
            [
                {"url": "https://x.com/1.jpg", "width": 100, "height": 100},
                {"url": "https://x.com/2.jpg", "width": 200, "height": 200},
            ]
        )
        urls = [i["url"] for i in parse_image_html(page)]
        assert urls == ["https://x.com/1.jpg", "https://x.com/2.jpg"]

    def test_handles_plain_content_string_fallback(self):
        page = _page_html([{"url": "https://x.com/c.jpg", "width": 300, "height": 300}], as_content_v2=False)
        assert parse_image_html(page) == [{"url": "https://x.com/c.jpg", "width": 300, "height": 300}]

    def test_returns_empty_list_when_no_images(self):
        page = "<html><body>" + _script("[]") + "</body></html>"
        assert parse_image_html(page) == []

    def test_raises_keyerror_when_no_script(self):
        with pytest.raises(KeyError):
            parse_image_html("<html><body>no data</body></html>")

    def test_raises_keyerror_when_structure_changed(self):
        payload = [{"data": {"unexpected": True}}]
        page = "<html>" + _script(json.dumps(payload)) + "</html>"
        with pytest.raises(KeyError):
            parse_image_html(page)


class TestDoubaoImageURLValidation:
    def test_rejects_non_thread_url(self):
        with pytest.raises(ValueError):
            doubao_image_parse("https://www.doubao.com/chat/abc")

    def test_rejects_unsupported_domain(self):
        # 千问（qianwen）不支持：校验在发起网络请求前即抛出。
        with pytest.raises(ValueError):
            doubao_image_parse("https://www.qianwen.com/thread/abc")


class TestIsDoubaoThreadURL:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.doubao.com/thread/abc123",
            "https://www.dola.com/thread/abc123",
            "https://ailab.doubao.com/thread/xyz",
        ],
    )
    def test_accepts_doubao_thread_urls(self, url):
        assert is_doubao_thread_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.doubao.com/chat/abc",
            "https://www.qianwen.com/thread/abc",
            "https://example.com/thread/abc",
            "https://www.doubao.com/",  # 无 /thread/
        ],
    )
    def test_rejects_invalid_urls(self, url):
        assert is_doubao_thread_url(url) is False
