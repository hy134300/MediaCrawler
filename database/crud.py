# file: database/crud.py
import json
from typing import Optional, Dict, Any, List, Coroutine

from sqlalchemy import literal_column
from sqlalchemy.future import select
from sqlalchemy.sql.expression import union_all

from database.data_registry import KEYWORD_TABLES
from database.db_session import get_session
from store.BaseStore import BaseStore
from store.bilibili import BiliDbStoreImplement
from store.douyin._store_impl import DouyinDbStoreImplement
from store.kuaishou import KuaishouDbStoreImplement
from store.tiktok import TiktokDbStoreImplement
from store.weibo import WeiboDbStoreImplement
from store.xhs._store_impl import XhsDbStoreImplement
from store.zhihu import ZhihuDbStoreImplement

# ... 导入所有平台的 Store 实现 ...

# 创建一个 Store 实例的注册表/工厂
# 在应用启动时初始化这些实例
STORE_REGISTRY: Dict[str, BaseStore] = {
    "xhs": XhsDbStoreImplement(),
    "dy": DouyinDbStoreImplement(),
    "tt": TiktokDbStoreImplement(),
    "bili": BiliDbStoreImplement(),
    "ks": KuaishouDbStoreImplement(),
    "wb": WeiboDbStoreImplement(),
    "zhihu": ZhihuDbStoreImplement(),

}

def get_store_by_platform(platform: str) -> Optional[BaseStore]:
    """根据平台名称获取对应的 Store 实例"""
    return STORE_REGISTRY.get(platform)


async def get_paginated_data_list(
        platform: str,
        **kwargs
) -> Dict[str, Any]:
    store = get_store_by_platform(platform)
    if not store:
        raise ValueError(f"不支持的平台: {platform}")

    result = await store.get_paginated_list(**kwargs)

    if "list" in result:
        for item in result["list"]:
            # --- 核心修改：针对逗号分隔字符串的清洗逻辑 ---
            if "image_list" in item:
                raw_val = item["image_list"]

                # 情况 0: 如果已经是 list (某些数据库驱动自动转了)，直接跳过
                if isinstance(raw_val, list):
                    continue

                if isinstance(raw_val, str):
                    try:
                        # 第一步：去除首尾可能存在的 多余引号
                        # 比如数据库里是 "\"http://a.com,http://b.com\""
                        # strip后变成 "http://a.com,http://b.com"
                        clean_str = raw_val.strip().strip('"').strip("'")

                        # 第二步：判断格式
                        if clean_str.startswith("["):
                            # A. 如果是 JSON 数组格式 "['url1', 'url2']"
                            try:
                                loaded = json.loads(clean_str)
                                # 再次确保里面是干净的字符串
                                item["image_list"] = [
                                    u.strip() for u in loaded if isinstance(u, str)
                                ]
                            except:
                                item["image_list"] = []
                        elif "," in clean_str:
                            # B. 🔥 你的情况：逗号分隔的字符串 "url1,url2,url3"
                            item["image_list"] = [
                                url.strip() for url in clean_str.split(",") if url.strip()
                            ]
                        elif clean_str.startswith("http"):
                            # C. 只有一张图，且没有逗号
                            item["image_list"] = [clean_str]
                        else:
                            # D. 空或者脏数据
                            item["image_list"] = []

                    except Exception as e:
                        print(f"[Warning] 图片列表解析失败: {e}, 原始数据: {raw_val}")
                        item["image_list"] = []
                else:
                    item["image_list"] = []

            # --- tag_list 也建议做类似处理 ---
            if "tag_list" in item and isinstance(item["tag_list"], str):
                raw_tag = item["tag_list"].strip().strip('"').strip("'")
                if raw_tag.startswith("["):
                    try:
                        item["tag_list"] = json.loads(raw_tag)
                    except:
                        item["tag_list"] = []
                elif "," in raw_tag:
                    item["tag_list"] = raw_tag.split(",")

    return result


async def get_distinct_keywords() -> List[Dict[str, Any]]:
    # 1. 定义对应的平台 Key (顺序必须与 KEYWORD_TABLES 一致!)
    # xhs, dy, bili, ks, wb, tieba, zhihu
    platform_keys = ["xhs", "dy", "tt", "bili", "ks", "wb", "tieba", "zhihu"]

    queries = []

    # 2. 使用 zip 将列对象和平台名配对
    for col, platform in zip(KEYWORD_TABLES, platform_keys):
        q = select(
            col.label("keyword"),
            literal_column(f"'{platform}'").label("platform")
        ).where(col.isnot(None))  # 过滤空值
        queries.append(q)

    if not queries:
        return []

    # 3. 联合查询 (Union All)
    union_query = union_all(*queries)

    # 将 union 结果转为子查询，以便进行 distinct 筛选
    u_sub = union_query.subquery()

    # 查出 (关键词, 平台) 的所有去重组合
    final_query = select(u_sub.c.keyword, u_sub.c.platform).distinct()

    async with get_session() as session:
        result = await session.execute(final_query)
        rows = result.all()

        # 4. 数据聚合：把同一个关键词对应的所有平台合并
        # 目标格式: {"迪士尼": {"xhs", "dy"}, "Python": {"bili"}}
        data_map = {}

        for row in rows:
            kw = row.keyword
            plt = row.platform

            # 排除空关键词
            if not kw or not str(kw).strip():
                continue

            if kw not in data_map:
                data_map[kw] = set()
            data_map[kw].add(plt)

        # 5. 格式化返回
        return [
            {"value": kw, "platforms": list(plts)}
            for kw, plts in data_map.items()
        ]
