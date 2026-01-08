# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tiktok/help.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
import random
import re
from model.m_tiktok import VideoUrlInfo, CreatorUrlInfo
from tools.crawler_util import extract_url_params_to_dict


def get_web_id() -> str:
    """
    生成随机的webid
    """

    def e(t):
        if t is not None:
            return str(t ^ (int(16 * random.random()) >> (t // 4)))
        else:
            return ''.join(
                [str(int(1e7)), '-', str(int(1e3)), '-', str(int(4e3)), '-', str(int(8e3)), '-', str(int(1e11))]
            )

    web_id = ''.join(
        e(int(x)) if x in '018' else x for x in e(None)
    )
    return web_id.replace('-', '')[:19]


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    """
    从 TikTok 视频URL中解析出视频ID
    支持以下格式:
    1. 普通视频链接: https://www.tiktok.com/@username/video/7351234567890123456
    2. 短链接: https://vm.tiktok.com/xxxxx/ (需要client解析)
    3. 纯ID: 7351234567890123456

    Args:
        url: TikTok 视频链接或ID
    Returns:
        VideoUrlInfo: 包含视频ID的对象
    """
    if url.isdigit():
        return VideoUrlInfo(video_id=url, url_type="normal")

    if "vm.tiktok.com" in url or "vt.tiktok.com" in url or (url.startswith("http") and "video" not in url):
        return VideoUrlInfo(video_id="", url_type="short")

    params = extract_url_params_to_dict(url)
    item_id = params.get("item_id") or params.get("itemId")
    if item_id:
        return VideoUrlInfo(video_id=item_id, url_type="normal")

    video_pattern = r'/video/(\d+)'
    match = re.search(video_pattern, url)
    if match:
        video_id = match.group(1)
        return VideoUrlInfo(video_id=video_id, url_type="normal")

    raise ValueError(f"无法从URL中解析出视频ID: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """
    从 TikTok 创作者主页URL中解析出创作者ID (unique_id)
    支持以下格式:
    1. 创作者主页: https://www.tiktok.com/@username
    2. 纯ID: username 或 @username
    """
    if url.startswith("@"):
        return CreatorUrlInfo(unique_id=url.lstrip("@"))
    if not url.startswith("http") and "tiktok.com" not in url:
        return CreatorUrlInfo(unique_id=url)

    user_pattern = r'/@([^/?]+)'
    match = re.search(user_pattern, url)
    if match:
        unique_id = match.group(1)
        return CreatorUrlInfo(unique_id=unique_id)

    raise ValueError(f"无法从URL中解析出创作者ID: {url}")


if __name__ == '__main__':
    print("=== 视频URL解析测试 ===")
    test_urls = [
        "https://www.tiktok.com/@scout2015/video/7351234567890123456",
        "https://vm.tiktok.com/xxxxxx/",
        "7351234567890123456",
    ]
    for url in test_urls:
        try:
            result = parse_video_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  结果: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  错误: {e}\n")

    print("=== 创作者URL解析测试 ===")
    test_creator_urls = [
        "https://www.tiktok.com/@scout2015",
        "@scout2015",
        "scout2015",
    ]
    for url in test_creator_urls:
        try:
            result = parse_creator_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  结果: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  错误: {e}\n")
