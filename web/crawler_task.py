from typing import Dict

from pydantic import BaseModel, Field

import config
# 这是一个关键的导入
# 这行代码假设您是从项目根目录（MediaCrawler/）
# 运行 uvicorn (例如: uvicorn web.api_server:app)
# 并且根目录在 Python 的搜索路径 (sys.path) 中
from main import CrawlerFactory
from tools import utils


class CrawlerConfig(BaseModel):
    """
    定义前端可以传递的配置项
    所有字段都与 base_config.py 对应
    使用 Field(default=...) 来设置默认值
    """
    PLATFORM: str = Field(default=config.PLATFORM)
    KEYWORDS: str = Field(default=config.KEYWORDS)
    LOGIN_TYPE: str = Field(default=config.LOGIN_TYPE)
    COOKIES: str = Field(default=config.COOKIES)
    CRAWLER_TYPE: str = Field(default=config.CRAWLER_TYPE)

    ENABLE_IP_PROXY: bool = Field(default=config.ENABLE_IP_PROXY)
    IP_PROXY_POOL_COUNT: int = Field(default=config.IP_PROXY_POOL_COUNT)
    IP_PROXY_PROVIDER_NAME: str = Field(default=config.IP_PROXY_PROVIDER_NAME)

    HEADLESS: bool = Field(default=config.HEADLESS)
    SAVE_LOGIN_STATE: bool = Field(default=config.SAVE_LOGIN_STATE)

    ENABLE_CDP_MODE: bool = Field(default=config.ENABLE_CDP_MODE)
    CDP_DEBUG_PORT: int = Field(default=config.CDP_DEBUG_PORT)
    CUSTOM_BROWSER_PATH: str = Field(default=config.CUSTOM_BROWSER_PATH)
    CDP_HEADLESS: bool = Field(default=config.CDP_HEADLESS)
    BROWSER_LAUNCH_TIMEOUT: int = Field(default=config.BROWSER_LAUNCH_TIMEOUT)
    AUTO_CLOSE_BROWSER: bool = Field(default=config.AUTO_CLOSE_BROWSER)

    # 默认保存选项改为 "db"
    SAVE_DATA_OPTION: str = Field(default="db")

    USER_DATA_DIR: str = Field(default=config.USER_DATA_DIR)
    START_PAGE: int = Field(default=config.START_PAGE)
    CRAWLER_MAX_NOTES_COUNT: int = Field(default=config.CRAWLER_MAX_NOTES_COUNT)
    MAX_CONCURRENCY_NUM: int = Field(default=config.MAX_CONCURRENCY_NUM)

    ENABLE_GET_MEIDAS: bool = Field(default=config.ENABLE_GET_MEIDAS)
    ENABLE_GET_COMMENTS: bool = Field(default=config.ENABLE_GET_COMMENTS)
    CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES: int = Field(default=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES)
    ENABLE_GET_SUB_COMMENTS: bool = Field(default=config.ENABLE_GET_SUB_COMMENTS)

    ENABLE_GET_WORDCLOUD: bool = Field(default=config.ENABLE_GET_WORDCLOUD)
    CUSTOM_WORDS: Dict[str, str] = Field(default_factory=dict)
    STOP_WORDS_FILE: str = Field(default=config.STOP_WORDS_FILE)
    FONT_PATH: str = Field(default=config.FONT_PATH)
    CRAWLER_MAX_SLEEP_SEC: int = Field(default=config.CRAWLER_MAX_SLEEP_SEC)

    # 允许 Pydantic 模型接受未在上面定义的额外字段（如果有的话）
    class Config:
        extra = 'allow'


async def run_crawler_task(task_config: CrawlerConfig):
    """
    执行爬虫任务的核心函数
    (已移除 try...except 块, 让异常自然抛出)
    """
    utils.logger.info(f"[API_TASK] 接收到爬虫任务: 平台={task_config.PLATFORM}, 关键词={task_config.KEYWORDS}")

    # 1. 动态修改全局配置
    utils.logger.info("[API_TASK] 正在动态更新全局配置...")

    for key, value in task_config.dict().items():
        if hasattr(config, key):
            setattr(config, key, value)

    utils.logger.info(f"[API_TASK] 配置更新完毕, 将使用 {config.SAVE_DATA_OPTION} 保存数据")

    # 2. 初始化爬虫
    utils.logger.info("[API_TASK] 准备启动爬虫...")
    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)

    # 3. 启动爬虫
    # await crawler.start() 会阻塞在这里，如果失败，异常将向上抛出
    await crawler.start()

    utils.logger.info(f"[API_TASK] 爬虫任务执行成功: {task_config.PLATFORM}")

