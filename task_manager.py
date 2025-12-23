# file: services/task_manager.py

import asyncio
import uuid
from typing import Dict

from fastapi import HTTPException
from tools import utils
from web.crawler_task import CrawlerConfig, run_crawler_task

# 创建一个全局的爬虫任务锁
CRAWLER_LOCK = asyncio.Lock()

# 创建一个全局字典来存储任务状态
# 注意: 在多进程环境中 (如 Gunicorn)，应使用 Redis 或数据库代替
CRAWLER_TASKS_STATUS: Dict[str, dict] = {}


async def run_crawler_task_wrapper(task_id: str, task_config: CrawlerConfig):
    """
    一个包裹函数，用于在后台任务中安全地获取和释放锁，并更新任务状态
    """
    try:
        # 注意：锁的获取现在移到调用方，以立即响应 API 请求
        utils.logger.info(f"[TASK_MANAGER] 任务开始执行: {task_id}")
        CRAWLER_TASKS_STATUS[task_id] = {"status": "running", "message": f"正在爬取: {task_config.PLATFORM} ..."}

        await run_crawler_task(task_config)

        CRAWLER_TASKS_STATUS[task_id] = {"status": "success", "message": "爬取任务已成功完成！"}
        utils.logger.info(f"[TASK_MANAGER] 任务执行成功: {task_id}")

    except Exception as e:
        error_message = str(e)
        utils.logger.error(f"[TASK_MANAGER] 后台任务执行失败: {task_id}, 错误: {error_message}")
        CRAWLER_TASKS_STATUS[task_id] = {"status": "failed", "message": error_message}
    finally:
        # 任务结束后释放锁
        CRAWLER_LOCK.release()
        utils.logger.info(f"[TASK_MANAGER] 任务流程结束, 释放任务锁: {task_id}")


def create_crawler_task(task_config: CrawlerConfig) -> str:
    """
    检查锁并创建新的爬虫任务
    """
    if CRAWLER_LOCK.locked():
        utils.logger.warning("[TASK_MANAGER] 尝试启动任务失败: 已有任务在运行")
        raise HTTPException(
            status_code=429,
            detail="已有爬虫任务在运行，请等待任务结束后再试。"
        )

    task_id = str(uuid.uuid4())
    CRAWLER_TASKS_STATUS[task_id] = {"status": "pending", "message": "任务已加入队列，等待启动..."}

    return task_id


def get_task_status(task_id: str) -> dict:
    """
    获取指定任务的状态
    """
    status = CRAWLER_TASKS_STATUS.get(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="未找到该任务ID，或任务已过期")
    return status