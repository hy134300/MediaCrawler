# file: routers/crawler_data_web.py

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

# 导入数据库操作层的函数
from database import crud
from main import CrawlerFactory

router = APIRouter(
    prefix="/api/v2/data",
    tags=["Data"],
)


@router.get("/platforms")
async def get_platforms():
    """获取支持的平台列表"""
    platform_list = [
        {
            "key": key,
            "name": CrawlerFactory.PLATFORM_NAME_MAP.get(key, key)
        }
        for key in CrawlerFactory.CRAWLERS.keys()
    ]
    return {
        "code": 200,
        "message": "获取成功",
        "data": platform_list
    }


@router.get("/keywords")
async def get_keywords():
    """从所有表中获取不重复的关键词列表"""
    try:
        keywords = await crud.get_distinct_keywords()
        return {"code": 200, "message": "获取成功", "data": keywords}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库查询失败: {e}")


@router.get("/list")
async def get_data_list(
    platform: str = Query(..., description="平台, e.g., 'xhs'"),
    keyword: Optional[str] = Query(None, description="搜索关键词(模糊匹配标题)"),
    source_keyword: Optional[str] = Query(None, description="爬虫源关键词(精确匹配)"),
    sort_by: Optional[str] = Query("liked_count", description="排序字段: liked_count, comment_count, create_time"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取统一格式的数据列表，支持分页、筛选和排序"""
    try:
        result = await crud.get_paginated_data_list(
            platform=platform,
            keyword=keyword,
            source_keyword=source_keyword,
            sort_by=sort_by,
            page=page,
            page_size=page_size
        )
        return {"code": 200, "message": "获取成功", "data": result}
    except ValueError as e: # 捕获 crud 中抛出的平台不支持错误
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库查询失败: {e}")