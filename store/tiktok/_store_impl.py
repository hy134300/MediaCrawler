# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/tiktok/_store_impl.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
import json
import time
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

from typing import Any, Dict, Optional, List

from sqlalchemy import desc, func, select, update

from base.base_crawler import AbstractStore
from database.data_registry import PLATFORM_MODELS
from database.db_session import get_session
from database.models import TiktokCreator, TiktokVideo, TiktokVideoComment
from database.mongodb_store_base import MongoDBStoreBase
from store.BaseStore import BaseStore
from tools import utils
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var


class TiktokCsvStoreImplement(AbstractStore, BaseStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="tiktok"
        )



    async def store_content(self, content_item: Dict):
        await self.file_writer.write_to_csv(item=content_item, item_type="contents")

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_to_csv(item=comment_item, item_type="comments")

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_to_csv(item=creator, item_type="creators")


class TiktokDbStoreImplement(AbstractStore, BaseStore):
    def __init__(self, **kwargs):
        _, self.normalized_columns = PLATFORM_MODELS["tt"]

    async def list_pending_assets(self, limit: int = 50) -> List[Dict[str, Any]]:
        async with get_session() as session:
            stmt = (
                select(
                    TiktokVideo.id,
                    TiktokVideo.note_id.label("content_id"),
                    TiktokVideo.video_url,
                    TiktokVideo.image_list
                )
                .where("PENDING" == TiktokVideo.asset_status)
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.all()

            items = []
            for row in rows:
                media_urls = []

                if row.video_url:
                    media_urls.append(row.video_url)

                if row.image_list:
                    try:
                        media_urls.extend(json.loads(row.image_list))
                    except Exception:
                        pass

                if not media_urls:
                    continue

                items.append({
                    "id": row.id,
                    "platform": "xhs",
                    "content_id": row.content_id,
                    "media_type": "video" if row.video_url else "image",
                    "media_urls": media_urls
                })

            return items

    async def update_asset_status(self, *, item_id: str, status: str, stored_urls: Optional[List[str]] = None,
                                  error_msg: Optional[str] = None) -> None:
        async with get_session() as session:
            values = {
                "asset_status": status,
                "asset_ts": int(time.time()),
                "last_modify_ts": int(time.time())
            }

            if stored_urls is not None:
                values["stored_urls"] = json.dumps(stored_urls)

            if error_msg:
                values["asset_error"] = error_msg[:500]

            stmt = update(TiktokVideo).where(item_id == TiktokVideo.id).values(**values)
            await session.execute(stmt)
            await session.commit()

    async def get_paginated_list(
        self,
        *,
        keyword: Optional[str] = None,
        source_keyword: Optional[str] = None,
        sort_by: str = "liked_count",
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        async with get_session() as session:
            table = TiktokVideo.__table__
            data_query = select(*self.normalized_columns)
            count_query = select(func.count()).select_from(table)

            where_clauses = []
            if keyword:
                where_clauses.append(table.c.title.like(f"%{keyword}%"))
            if source_keyword:
                where_clauses.append(table.c.source_keyword == source_keyword)

            if where_clauses:
                data_query = data_query.where(*where_clauses)
                count_query = count_query.where(*where_clauses)

            total_count_result = await session.execute(count_query)
            total_count = total_count_result.scalar_one_or_none() or 0
            if total_count == 0:
                return {"total": 0, "list": []}

            sort_column = next((c for c in self.normalized_columns if c.name == sort_by), None)
            if sort_column is not None:
                data_query = data_query.order_by(desc(sort_column))

            offset = (page - 1) * page_size
            data_query = data_query.offset(offset).limit(page_size)
            data_result = await session.execute(data_query)

            data_list = [dict(row._mapping) for row in data_result.all()]
            return {"total": total_count, "list": data_list}

    async def store_content(self, content_item: Dict):
        video_id = content_item.get("video_id")
        async with get_session() as session:
            result = await session.execute(select(TiktokVideo).where(TiktokVideo.video_id == video_id))
            video_detail = result.scalar_one_or_none()

            if not video_detail:
                content_item["add_ts"] = utils.get_current_timestamp()
                if content_item.get("title"):
                    new_content = TiktokVideo(**content_item)
                    session.add(new_content)
            else:
                for key, value in content_item.items():
                    setattr(video_detail, key, value)
            await session.commit()

    async def store_comment(self, comment_item: Dict):
        comment_id = comment_item.get("comment_id")
        async with get_session() as session:
            result = await session.execute(select(TiktokVideoComment).where(TiktokVideoComment.comment_id == comment_id))
            comment_detail = result.scalar_one_or_none()

            if not comment_detail:
                comment_item["add_ts"] = utils.get_current_timestamp()
                new_comment = TiktokVideoComment(**comment_item)
                session.add(new_comment)
            else:
                for key, value in comment_item.items():
                    setattr(comment_detail, key, value)
            await session.commit()

    async def store_creator(self, creator: Dict):
        user_id = creator.get("user_id")
        async with get_session() as session:
            result = await session.execute(select(TiktokCreator).where(TiktokCreator.user_id == user_id))
            user_detail = result.scalar_one_or_none()

            if not user_detail:
                creator["add_ts"] = utils.get_current_timestamp()
                new_creator = TiktokCreator(**creator)
                session.add(new_creator)
            else:
                for key, value in creator.items():
                    setattr(user_detail, key, value)
            await session.commit()


class TiktokJsonStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="tiktok"
        )

    async def store_content(self, content_item: Dict):
        await self.file_writer.write_single_item_to_json(item=content_item, item_type="contents")

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_single_item_to_json(item=comment_item, item_type="comments")

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_single_item_to_json(item=creator, item_type="creators")


class TiktokSqliteStoreImplement(TiktokDbStoreImplement):
    pass


class TiktokMongoStoreImplement(AbstractStore):
    def __init__(self):
        self.mongo_store = MongoDBStoreBase(collection_prefix="tiktok")

    async def store_content(self, content_item: Dict):
        video_id = content_item.get("video_id")
        if not video_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="contents",
            query={"video_id": video_id},
            data=content_item
        )
        utils.logger.info(f"[TiktokMongoStoreImplement.store_content] Saved video {video_id} to MongoDB")

    async def store_comment(self, comment_item: Dict):
        comment_id = comment_item.get("comment_id")
        if not comment_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="comments",
            query={"comment_id": comment_id},
            data=comment_item
        )
        utils.logger.info(f"[TiktokMongoStoreImplement.store_comment] Saved comment {comment_id} to MongoDB")

    async def store_creator(self, creator_item: Dict):
        user_id = creator_item.get("user_id")
        if not user_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="creators",
            query={"user_id": user_id},
            data=creator_item
        )
        utils.logger.info(f"[TiktokMongoStoreImplement.store_creator] Saved creator {user_id} to MongoDB")


class TiktokExcelStoreImplement:
    def __new__(cls, *args, **kwargs):
        from store.excel_store_base import ExcelStoreBase
        return ExcelStoreBase.get_instance(
            platform="tiktok",
            crawler_type=crawler_type_var.get()
        )
