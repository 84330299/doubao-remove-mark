import base64
import html as html_mod
import json

import pytest

from parser.video import (
    _build_unwatermarked_url,
    _extract_fallback_apis,
    _extract_poster_urls,
    _parse_doubao_video_response,
    doubao_video_parse,
)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _wrapped_url(url: str) -> str:
    return _b64(url.encode())


def _script(inner: str) -> str:
    return (
        '<script data-script-src="modern-run-router-data-fn" '
        f'data-fn-args="{html_mod.escape(inner, quote=True)}" nonce="abc123"></script>'
    )


class TestBuildUnwatermarkedURL:
    def test_adds_unwatermarked_params_and_keeps_existing(self):
        url = "https://v3.douyinvod.com/video/fplay/abc?foo=1&bar=2"
        result = _build_unwatermarked_url(url)
        params = dict(p.split("=") for p in result.split("?")[1].split("&"))
        assert params["codec_type"] == "8"
        assert params["logo_type"] == "unwatermarked"
        assert params["foo"] == "1"
        assert params["bar"] == "2"
        assert result.startswith("https://v3.douyinvod.com/video/fplay/abc?")

    def test_accepts_snssdk_and_dola_hosts(self):
        for host in ("v3.snssdk.com", "v3.dola.com"):
            url = f"https://{host}/video/fplay/x?a=1"
            assert "logo_type=unwatermarked" in _build_unwatermarked_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://v3.douyinvod.com/video/fplay/abc?a=1",  # 非 https
            "https://evil.example.com/video/fplay/abc?a=1",  # 不受信域名
            "https://v3.douyinvod.com/other/path?a=1",  # 非 /video/fplay/
        ],
    )
    def test_rejects_untrusted_fallback_api(self, url):
        with pytest.raises(ValueError):
            _build_unwatermarked_url(url)


class TestExtractFallbackAPIs:
    def test_extracts_unescapes_and_deduplicates(self):
        args = json.dumps(
            {
                "data": {
                    "video": {
                        "fallback_api": "https:\\/\\/v3.douyinvod.com\\/video\\/fplay\\/a?a=1\\u0026b=2",
                        "nested": [{"fallback_api": "https://v3.douyinvod.com/video/fplay/b?x=1"}],
                    }
                }
            }
        )
        page = "<html><body>" + _script(args) + "</body></html>"
        apis = _extract_fallback_apis(page)
        assert apis == [
            "https://v3.douyinvod.com/video/fplay/a?a=1&b=2",
            "https://v3.douyinvod.com/video/fplay/b?x=1",
        ]

    def test_returns_empty_when_no_fallback_api(self):
        args = json.dumps({"data": {"video": {"url": "https://x.com"}}})
        page = "<html>" + _script(args) + "</html>"
        assert _extract_fallback_apis(page) == []

    def test_raises_keyerror_when_no_script(self):
        with pytest.raises(KeyError):
            _extract_fallback_apis("<html><body>none</body></html>")


class TestExtractPosterUrls:
    def test_maps_vid_to_poster_url(self):
        args = json.dumps(
            {
                "data": {
                    "message": {
                        "vid": "VID1",
                        "poster_url": "https://p26-sign.douyinpic.com/tos/p1~tplv-noop.image?a=1",
                        "nested": [
                            {"vid": "VID2", "poster_url": "https://p3-sign.douyinpic.com/tos/p2~tplv-noop.image?b=2"}
                        ],
                    }
                }
            }
        )
        page = "<html><body>" + _script(args) + "</body></html>"
        assert _extract_poster_urls(page) == {
            "VID1": "https://p26-sign.douyinpic.com/tos/p1~tplv-noop.image?a=1",
            "VID2": "https://p3-sign.douyinpic.com/tos/p2~tplv-noop.image?b=2",
        }

    def test_first_poster_wins_on_duplicate_vid(self):
        args = json.dumps(
            {
                "videos": [
                    {"vid": "VID1", "poster_url": "https://a.douyinpic.com/tos/1"},
                    {"vid": "VID1", "poster_url": "https://b.douyinpic.com/tos/2"},
                ]
            }
        )
        page = "<html><body>" + _script(args) + "</body></html>"
        assert _extract_poster_urls(page) == {"VID1": "https://a.douyinpic.com/tos/1"}

    def test_ignores_non_https_and_missing_poster(self):
        args = json.dumps(
            {
                "vid": "VID1",
                "poster_url": "http://insecure.example/tos/2",
                "no_poster": {"vid": "VID3", "other": 1},
            }
        )
        page = "<html><body>" + _script(args) + "</body></html>"
        assert _extract_poster_urls(page) == {}

    def test_raises_keyerror_when_no_script(self):
        with pytest.raises(KeyError):
            _extract_poster_urls("<html><body>none</body></html>")


def _response_payload(main_url: str, resolution: tuple[int, int] = (1080, 1920), extra: dict | None = None):
    width, height = resolution
    entry = {
        "main_url": main_url,
        "width": width,
        "height": height,
        "definition": "2k",
        "codec_type": "h264",
        "duration": 12.5,
    }
    payload = {
        "data": {
            "video_info": {
                "vid": "VID123",
                "key_seed": "ignored-for-base64",
                "video_list": {"high": entry},
            }
        }
    }
    if extra:
        payload["data"]["video_info"].update(extra)
    return payload


class TestParseDoubaoVideoResponse:
    def test_decodes_video_and_normalizes(self):
        payload = _response_payload(_wrapped_url("https://v3.douyinvod.com/video/fplay/out.mp4"))
        result = _parse_doubao_video_response(payload, "fallback")
        assert result["url"] == "https://v3.douyinvod.com/video/fplay/out.mp4"
        assert result["width"] == 1080
        assert result["height"] == 1920
        assert result["vid"] == "VID123"
        assert result["definition"] == "2k"
        assert result["codec_type"] == "h264"
        assert result["duration"] == 12.5

    def test_picks_highest_resolution_entry(self):
        url_lo = _wrapped_url("https://v3.douyinvod.com/video/fplay/lo.mp4")
        url_hi = _wrapped_url("https://v3.douyinvod.com/video/fplay/hi.mp4")
        payload = _response_payload(url_lo)
        payload["data"]["video_info"]["video_list"] = {
            "lo": {"main_url": url_lo, "width": 720, "height": 1280},
            "hi": {"main_url": url_hi, "width": 2160, "height": 3840, "definition": "4k"},
        }
        result = _parse_doubao_video_response(payload, "fallback")
        assert result["url"] == "https://v3.douyinvod.com/video/fplay/hi.mp4"
        assert result["width"] == 2160

    def test_raises_keyerror_when_no_main_url(self):
        payload = {"data": {"video_info": {"video_list": {"x": {"width": 1}}}}}
        with pytest.raises(KeyError):
            _parse_doubao_video_response(payload, "fallback")

    def test_raises_valueerror_when_url_undecodable(self):
        payload = _response_payload("!!!not-a-valid-token!!!")
        with pytest.raises(ValueError):
            _parse_doubao_video_response(payload, "fallback")


class TestDoubaoVideoParseValidation:
    def test_rejects_non_thread_url(self):
        with pytest.raises(ValueError):
            doubao_video_parse("https://www.doubao.com/chat/abc")

    def test_rejects_unsupported_domain(self):
        with pytest.raises(ValueError):
            doubao_video_parse("https://www.qianwen.com/thread/abc")


class _FakeResp:
    def __init__(self, text: str = "", payload: dict | None = None):
        self.text = text
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class TestDoubaoVideoParsePosterFallback:
    FALLBACK_API = "https://v3.douyinvod.com/video/fplay/abc?x=1"
    VID = "VID123"
    SSR_POSTER = "https://p26-sign.douyinpic.com/tos/p1~tplv-noop.image?a=1"

    def _page_html(self) -> str:
        payload = {
            "data": {
                "message": {
                    "vid": self.VID,
                    "poster_url": self.SSR_POSTER,
                    "video": {"fallback_api": self.FALLBACK_API},
                }
            }
        }
        return _script(json.dumps(payload))

    def _stub_fetch(self, monkeypatch, api_payload: dict):
        calls = iter([_FakeResp(text=self._page_html()), _FakeResp(payload=api_payload)])
        monkeypatch.setattr("parser.video._fetch", lambda *a, **k: next(calls))

    def test_falls_back_to_ssr_poster_when_api_lacks_it(self, monkeypatch):
        api_payload = _response_payload(_wrapped_url("https://v3.douyinvod.com/video/fplay/out.mp4"))
        self._stub_fetch(monkeypatch, api_payload)

        result = doubao_video_parse("https://www.doubao.com/thread/abc123")
        assert result[0]["poster_url"] == self.SSR_POSTER

    def test_api_poster_takes_precedence_over_ssr(self, monkeypatch):
        api_payload = _response_payload(_wrapped_url("https://v3.douyinvod.com/video/fplay/out.mp4"))
        api_payload["data"]["video_info"]["poster_url"] = "https://api.example/tos/api"
        self._stub_fetch(monkeypatch, api_payload)

        result = doubao_video_parse("https://www.doubao.com/thread/abc123")
        assert result[0]["poster_url"] == "https://api.example/tos/api"
