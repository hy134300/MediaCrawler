# file: routers/crawler_web.py

from fastapi import APIRouter, BackgroundTasks

from crawler_task import CrawlerConfig
# 导入服务层的函数
from task_manager import (
    create_crawler_task,
    get_task_status,
    run_crawler_task_wrapper,
    CRAWLER_LOCK
)

# 创建一个路由实例
router = APIRouter(
    prefix="/api/v2/crawler",  # 定义路由前缀
    tags=["Crawler"],  # 定义 API 文档标签
)


@router.post("/start")
async def start_crawler(
        task_config: CrawlerConfig,
        background_tasks: BackgroundTasks
):
    """启动爬虫任务 API"""
    task_id = create_crawler_task(task_config)

    # 立即获取锁，确保在任务加入后台前，其他请求无法启动新任务
    await CRAWLER_LOCK.acquire()

    # 将 task_id 传递给后台任务
    background_tasks.add_task(run_crawler_task_wrapper, task_id, task_config)

    return {
        "code": 200,
        "message": "爬虫任务已在后台启动",
        "data": {
            "platform": task_config.PLATFORM,
            "keywords": task_config.KEYWORDS,
            "task_id": task_id
        }
    }


@router.get("/status/{task_id}")
async def get_crawler_status(task_id: str):
    """获取爬虫任务的状态"""
    status = get_task_status(task_id)
    return {
        "code": 200,
        "message": "获取状态成功",
        "data": {
            "task_id": task_id,
            "status": status.get("status"),
            "message": status.get("message")
        }
    }