# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/tiktok_config.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

# TikTok 平台配置

# 指定 TikTok 视频 URL 列表 (支持多种格式)
# 支持格式:
# 1. 完整视频URL: "https://www.tiktok.com/@username/video/7351234567890123456"
# 2. 短链接: "https://vm.tiktok.com/xxxxx/"
# 3. 纯视频ID: "7351234567890123456"
TT_SPECIFIED_ID_LIST = [
    "https://www.tiktok.com/@scout2015/video/7351234567890123456",
    "https://vm.tiktok.com/xxxxxx/",
    "7351234567890123456",
]

# 指定 TikTok 创作者 URL 列表 (支持完整URL或 unique_id)
# 支持格式:
# 1. 创作者主页URL: "https://www.tiktok.com/@username"
# 2. unique_id: "username" 或 "@username"
TT_CREATOR_ID_LIST = [
    "https://www.tiktok.com/@scout2015",
    "@scout2015",
    "scout2015",
]

# TikTok 搜索配置
TT_SEARCH_COUNT = 12
TT_SEARCH_REGION = ""
TT_SEARCH_EXTRA_PARAMS = {}
TT_SEARCH_EXTRA_HEADERS = {}
TT_DEVICE_ID = ""
TT_VERIFY_FP = ""
TT_MS_TOKEN = ""
TT_WEB_SEARCH_CODE = ""
TT_CLIENT_AB_VERSIONS = ""
TT_LOG_MASK_SENSITIVE = False
