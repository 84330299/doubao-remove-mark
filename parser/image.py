"""豆包图片解析：从分享页 HTML 中提取无水印原图。"""

import json
import re

import httpx


def _extract_payload(html_str: str):
    patterns = [
        'data-script-src="modern-run-router-data-fn" data-fn-args="(.*?)" nonce="',
        'data-script-src="modern-run-window-fn" data-fn-name="mergeLoaderData" data-fn-args="(.*?)" nonce="',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_str, re.DOTALL)
        if match:
            return json.loads(match.group(1).replace("&quot;", '"'))
    raise KeyError("无法解析页面数据，请确认链接是否有效")


def _iter_image_urls(json_data):
    for data in json_data:
        if isinstance(data, dict) and data.get("data"):
            message_list = data["data"]["message_snapshot"]["message_list"]
        elif isinstance(data, list) and data:
            router_data_fn = json.loads(data[0]["routerDataFnArgs"][0])
            message_list = router_data_fn["data"]["message_snapshot"]["message_list"]
        else:
            message_list = []

        for message in message_list:
            if not message.get("content_block"):
                continue
            for m2 in message["content_block"]:
                if m2.get("content_v2"):
                    json_data2 = json.loads(m2["content_v2"])
                else:
                    json_data2 = json.loads(m2["content"]) if isinstance(m2["content"], str) else m2["content"]

                if not json_data2.get("creation_block"):
                    continue
                for image in json_data2["creation_block"]["creations"]:
                    raw = image["image"]["image_ori_raw"]
                    raw["url"] = raw["url"].replace("&amp;", "&")
                    yield raw


def parse_image_html(html_str: str, return_raw: bool = False):
    """从豆包分享页 HTML 中解析图片（纯逻辑，供测试与 doubao_image_parse 复用）。"""
    json_data = _extract_payload(html_str)
    if return_raw:
        return json_data
    return [
        {
            "url": item["url"],
            "width": item.get("width"),
            "height": item.get("height"),
        }
        for item in _iter_image_urls(json_data)
    ]


def is_doubao_thread_url(url: str) -> bool:
    host_match = re.search(r"//([^/]+)/", url + "/")
    host = host_match.group(1).lower() if host_match else ""
    valid_host = host in ("www.doubao.com", "www.dola.com") or host.endswith((".doubao.com", ".dola.com"))
    return valid_host and "/thread/" in url


def _fetch(url: str, headers: dict) -> httpx.Response:
    """请求页面；SSL 证书校验失败时（代理/杀软拦截）降级重试。"""
    try:
        with httpx.Client(timeout=httpx.Timeout(10, read=60)) as client:
            return client.get(url, headers=headers)
    except httpx.ConnectError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
    with httpx.Client(timeout=httpx.Timeout(10, read=60), verify=False) as client:
        return client.get(url, headers=headers)


def doubao_image_parse(url: str, return_raw: bool = False):
    """解析豆包对话分享链接中的无水印图片列表。"""
    if not is_doubao_thread_url(url):
        raise ValueError("链接格式不正确，请使用豆包对话链接（包含 /thread/）")

    headers = {
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
        ),
    }

    try:
        response = _fetch(url, headers)
        html_str = response.text
    except httpx.RequestError as e:
        raise ValueError(f"网络请求失败，请检查网络连接: {str(e)}") from e

    return parse_image_html(html_str, return_raw=return_raw)
