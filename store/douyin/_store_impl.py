# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/douyin/_store_impl.py
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


# -*- coding: utf-8 -*-
# @Author  : persist1@126.com
# @Time    : 2025/9/5 19:34
# @Desc    : 抖音存储实现类
import asyncio
import json
import os
import pathlib
from typing import Dict, Optional, Any

from sqlalchemy import select, func, desc

import config
from base.base_crawler import AbstractStore
from database.data_registry import PLATFORM_MODELS
from database.db_session import get_session
from database.models import DouyinAweme, DouyinAwemeComment, DyCreator
from store.BaseStore import BaseStore
from tools import utils, words
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var
from database.mongodb_store_base import MongoDBStoreBase


class DouyinCsvStoreImplement(AbstractStore,BaseStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="douyin"
        )

    async def store_content(self, content_item: Dict):
        """
        Douyin content CSV storage implementation
        Args:
            content_item: note item dict

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=content_item,
            item_type="contents"
        )

    async def store_comment(self, comment_item: Dict):
        """
        Douyin comment CSV storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=comment_item,
            item_type="comments"
        )



    async def store_creator(self, creator: Dict):
        """
        Douyin creator CSV storage implementation
        Args:
            creator: creator item dict

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=creator,
            item_type="creators"
        )


class DouyinDbStoreImplement(AbstractStore,BaseStore):
    def __init__(self, **kwargs):
        _, self.normalized_columns = PLATFORM_MODELS["dy"]

    async def get_paginated_list(self, *, keyword: Optional[str] = None, source_keyword: Optional[str] = None,
                                 sort_by: str = "liked_count", page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        async with get_session() as session:
            # 1. 定义要查询的表
            table = DouyinAweme.__table__

            # 2. 构建基础查询语句
            #    - data_query 用于获取数据列表
            #    - count_query 用于获取总记录数
            data_query = select(*self.normalized_columns)
            count_query = select(func.count()).select_from(table)

            # 3. 添加筛选条件 (where)
            where_clauses = []
            if keyword:
                # `keyword` 用于模糊搜索标题
                where_clauses.append(table.c.title.like(f"%{keyword}%"))
            if source_keyword:
                # `source_keyword` 用于精确匹配源关键词
                where_clauses.append(table.c.source_keyword == source_keyword)

            # 如果有筛选条件，应用到两个查询上
            if where_clauses:
                data_query = data_query.where(*where_clauses)
                count_query = count_query.where(*where_clauses)

            # 4. 执行总数查询 (在应用分页之前！)
            total_count_result = await session.execute(count_query)
            total_count = total_count_result.scalar_one_or_none() or 0

            if total_count == 0:
                # 如果总数为0，没必要继续查数据，直接返回空列表
                return {"total": 0, "list": []}

            # 5. 添加排序 (order_by)
            sort_column = next((c for c in self.normalized_columns if c.name == sort_by), None)
            if sort_column is not None:
                data_query = data_query.order_by(desc(sort_column))

            # 6. 添加分页 (limit / offset) - 这才是分页的关键！
            #    - offset: 跳过多少条记录
            #    - limit:  最多取多少条记录
            offset = (page - 1) * page_size
            data_query = data_query.offset(offset).limit(page_size)

            # 7. 执行最终的数据查询
            data_result = await session.execute(data_query)

            # 8. 组装并返回最终结果
            data_list = [dict(row._mapping) for row in data_result.all()]

            return {
                "total": total_count,
                "list": data_list
            }

    async def store_content(self, content_item: Dict):
        """
        Douyin content DB storage implementation
        Args:
            content_item: content item dict
        """
        aweme_id = content_item.get("aweme_id")
        async with get_session() as session:
            result = await session.execute(select(DouyinAweme).where(DouyinAweme.aweme_id == aweme_id))
            aweme_detail = result.scalar_one_or_none()

            if not aweme_detail:
                content_item["add_ts"] = utils.get_current_timestamp()
                if content_item.get("title"):
                    new_content = DouyinAweme(**content_item)
                    session.add(new_content)
            else:
                for key, value in content_item.items():
                    setattr(aweme_detail, key, value)
            await session.commit()

    async def store_comment(self, comment_item: Dict):
        """
        Douyin comment DB storage implementation
        Args:
            comment_item: comment item dict
        """
        comment_id = comment_item.get("comment_id")
        async with get_session() as session:
            result = await session.execute(select(DouyinAwemeComment).where(DouyinAwemeComment.comment_id == comment_id))
            comment_detail = result.scalar_one_or_none()

            if not comment_detail:
                comment_item["add_ts"] = utils.get_current_timestamp()
                new_comment = DouyinAwemeComment(**comment_item)
                session.add(new_comment)
            else:
                for key, value in comment_item.items():
                    setattr(comment_detail, key, value)
            await session.commit()

    async def store_creator(self, creator: Dict):
        """
        Douyin creator DB storage implementation
        Args:
            creator: creator dict
        """
        user_id = creator.get("user_id")
        async with get_session() as session:
            result = await session.execute(select(DyCreator).where(DyCreator.user_id == user_id))
            user_detail = result.scalar_one_or_none()

            if not user_detail:
                creator["add_ts"] = utils.get_current_timestamp()
                new_creator = DyCreator(**creator)
                session.add(new_creator)
            else:
                for key, value in creator.items():
                    setattr(user_detail, key, value)
            await session.commit()


class DouyinJsonStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="douyin"
        )

    async def store_content(self, content_item: Dict):
        """
        content JSON storage implementation
        Args:
            content_item:

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=content_item,
            item_type="contents"
        )

    async def store_comment(self, comment_item: Dict):
        """
        comment JSON storage implementation
        Args:
            comment_item:

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=comment_item,
            item_type="comments"
        )

    async def store_creator(self, creator: Dict):
        """
        creator JSON storage implementation
        Args:
            creator:

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=creator,
            item_type="creators"
        )



class DouyinSqliteStoreImplement(DouyinDbStoreImplement):
    pass


class DouyinMongoStoreImplement(AbstractStore):
    """抖音MongoDB存储实现"""

    def __init__(self):
        self.mongo_store = MongoDBStoreBase(collection_prefix="douyin")

    async def store_content(self, content_item: Dict):
        """
        存储视频内容到MongoDB
        Args:
            content_item: 视频内容数据
        """
        aweme_id = content_item.get("aweme_id")
        if not aweme_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="contents",
            query={"aweme_id": aweme_id},
            data=content_item
        )
        utils.logger.info(f"[DouyinMongoStoreImplement.store_content] Saved aweme {aweme_id} to MongoDB")

    async def store_comment(self, comment_item: Dict):
        """
        存储评论到MongoDB
        Args:
            comment_item: 评论数据
        """
        comment_id = comment_item.get("comment_id")
        if not comment_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="comments",
            query={"comment_id": comment_id},
            data=comment_item
        )
        utils.logger.info(f"[DouyinMongoStoreImplement.store_comment] Saved comment {comment_id} to MongoDB")

    async def store_creator(self, creator_item: Dict):
        """
        存储创作者信息到MongoDB
        Args:
            creator_item: 创作者数据
        """
        user_id = creator_item.get("user_id")
        if not user_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="creators",
            query={"user_id": user_id},
            data=creator_item
        )
        utils.logger.info(f"[DouyinMongoStoreImplement.store_creator] Saved creator {user_id} to MongoDB")


class DouyinExcelStoreImplement:
    """抖音Excel存储实现 - 全局单例"""

    def __new__(cls, *args, **kwargs):
        from store.excel_store_base import ExcelStoreBase
        return ExcelStoreBase.get_instance(
            platform="douyin",
            crawler_type=crawler_type_var.get()
        )
