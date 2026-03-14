# -*- coding: utf-8 -*-
"""AI 图片编辑模块 — 调用 ByteDance Seedream 模型对用户上传的图片进行风格化编辑。

对外暴露:
    - generate_edited_image(prompt, image_url, api_key) → 编辑后的图片 URL
    - download_image(image_url, output_dir, file_name) → 本地保存路径
"""

import json
import os
import time
import logging
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ── 可复用 HTTP 会话，自带重试策略 ──
_session = requests.Session()
_retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
_session.mount("https://", HTTPAdapter(max_retries=_retries))

# ── 配置项（全部从环境变量读取，.env 由 main.py 启动时加载） ──
DEFAULT_API_KEY = os.environ.get("IMAGE_EDIT_API_KEY", "")
IMAGE_EDIT_ENDPOINT = os.environ.get(
    "IMAGE_EDIT_BASE_URL", "https://image.onerouter.pro/v1/images/edits"
)
IMAGE_EDIT_MODEL = os.environ.get(
    "IMAGE_EDIT_MODEL", "google/nano-banana-image-to-image"
)


def generate_edited_image(
    prompt: str,
    image_url: str,
    api_key: Optional[str] = None,
    timeout: int = 300,
) -> str:
    """调用 ByteDance Seedream API 对图片进行 AI 编辑。

    Args:
        prompt: 编辑提示词（描述期望的输出效果）
        image_url: 原始图片的公网 URL 或 base64 data URI
        api_key: API 密钥，不传则使用默认值
        timeout: 请求超时秒数，默认 300

    Returns:
        编辑后图片的 URL 字符串

    Raises:
        requests.HTTPError: API 返回非 2xx 状态码
        KeyError: 响应 JSON 中缺少预期字段
        ValueError: 未配置 API Key
    """
    key = api_key or DEFAULT_API_KEY
    if not key:
        raise ValueError("未配置 IMAGE_EDIT_API_KEY，请在 .env 文件中设置")

    start_time = time.perf_counter()

    response = _session.post(
        IMAGE_EDIT_ENDPOINT,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "model": IMAGE_EDIT_MODEL,
                "prompt": prompt,
                "image_urls": [image_url],
                "n": 1,
                "output_format": "url",
            }
        ),
        timeout=timeout,
    )

    # 先打印原始响应，便于排查任何非 2xx 错误
    if not response.ok:
        logger.error(
            "AI API 原始响应 status=%d body=%s",
            response.status_code,
            response.text[:3000],
        )

    # 鉴权失败时，提取 API 返回的详细错误信息
    if response.status_code == 401:
        raise PermissionError(
            "API 鉴权失败 (401 Unauthorized)，请检查 API Key 是否有效"
        )
    if response.status_code == 402:
        raise PermissionError("API 余额不足 (402 Payment Required)，请充值后重试")
    response.raise_for_status()

    result = response.json()

    edited_url = result["data"][0]["url"]
    duration = time.perf_counter() - start_time
    logger.info(
        "AI 图片编辑完成 | prompt=%s | result_url=%s | duration=%.2fs",
        prompt,
        edited_url,
        duration,
    )
    return edited_url


def download_image(
    image_url: str,
    output_dir: str = ".",
    file_name: Optional[str] = None,
) -> str:
    """下载图片到本地。

    Args:
        image_url: 图片 URL
        output_dir: 保存目录
        file_name: 保存文件名，不传则自动生成

    Returns:
        本地保存路径
    """
    os.makedirs(output_dir, exist_ok=True)

    if file_name is None:
        parsed_url = urlparse(image_url)
        ext = os.path.splitext(parsed_url.path)[1] or ".jpg"
        file_name = f"ai_edited{ext}"

    output_path = os.path.join(output_dir, file_name)
    resp = requests.get(image_url, timeout=60)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(resp.content)

    logger.info("图片已下载 | path=%s | size=%d bytes", output_path, len(resp.content))
    return output_path
