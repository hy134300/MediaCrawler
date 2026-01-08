# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/tiktok/__init__.py
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

from typing import Dict, List

import config
from tools import utils
from var import source_keyword_var

from ._store_impl import *


class TiktokStoreFactory:
    STORES = {
        "csv": TiktokCsvStoreImplement,
        "db": TiktokDbStoreImplement,
        "json": TiktokJsonStoreImplement,
        "sqlite": TiktokSqliteStoreImplement,
        "mongodb": TiktokMongoStoreImplement,
        "excel": TiktokExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = TiktokStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[TiktokStoreFactory.create_store] Invalid save option only supported csv or db or json or sqlite or mongodb or excel ...")
        return store_class()


async def update_tiktok_video(video_item: Dict):
    video_id = video_item.get("video_id")
    if not video_id:
        return
    save_content_item = {
        "video_id": video_id,
        "title": video_item.get("title", ""),
        "desc": video_item.get("desc", ""),
        "create_time": video_item.get("create_time"),
        "user_id": video_item.get("author_id"),
        "user_unique_id": video_item.get("author_unique_id"),
        "nickname": video_item.get("nickname"),
        "avatar": video_item.get("avatar"),
        "user_signature": video_item.get("user_signature"),
        "ip_location": video_item.get("ip_location", ""),
        "liked_count": str(video_item.get("liked_count", "")),
        "collected_count": str(video_item.get("collected_count", "")),
        "comment_count": str(video_item.get("comment_count", "")),
        "share_count": str(video_item.get("share_count", "")),
        "last_modify_ts": utils.get_current_timestamp(),
        "video_url": video_item.get("video_url"),
        "cover_url": video_item.get("cover_url"),
        "video_download_url": video_item.get("video_download_url"),
        "music_download_url": video_item.get("music_download_url"),
        "source_keyword": source_keyword_var.get(),
    }
    utils.logger.info(f"[store.tiktok.update_tiktok_video] TikTok video id:{video_id}, title:{save_content_item.get('title')}")
    await TiktokStoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_tiktok_comments(video_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_tiktok_comment(video_id, comment_item)


async def update_tiktok_comment(video_id: str, comment_item: Dict):
    comment_id = comment_item.get("comment_id") or comment_item.get("cid")
    save_comment_item = {
        "comment_id": comment_id,
        "video_id": video_id,
        "content": comment_item.get("text") or comment_item.get("content"),
        "create_time": comment_item.get("create_time") or comment_item.get("createTime"),
        "user_id": comment_item.get("user_id") or comment_item.get("uid"),
        "nickname": comment_item.get("nickname"),
        "avatar": comment_item.get("avatar"),
        "sub_comment_count": str(comment_item.get("sub_comment_count", 0)),
        "like_count": str(comment_item.get("like_count", 0)),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.tiktok.update_tiktok_comment] TikTok comment: {comment_id}")
    await TiktokStoreFactory.create_store().store_comment(comment_item=save_comment_item)


async def update_tiktok_creator(creator: Dict):
    save_creator_item = {
        "user_id": creator.get("user_id"),
        "unique_id": creator.get("unique_id"),
        "nickname": creator.get("nickname"),
        "avatar": creator.get("avatar"),
        "ip_location": creator.get("ip_location", ""),
        "desc": creator.get("desc", ""),
        "gender": creator.get("gender"),
        "follows": creator.get("follows"),
        "fans": creator.get("fans"),
        "interaction": creator.get("interaction"),
        "videos_count": creator.get("videos_count"),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.tiktok.update_tiktok_creator] TikTok creator id:{save_creator_item.get('user_id')}")
    await TiktokStoreFactory.create_store().store_creator(creator=save_creator_item)
