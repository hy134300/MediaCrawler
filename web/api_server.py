# file: api_server.py

import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

import config
from database import db
from tools import utils
from web import crawler_web, crawler_data_web


# 导入新的路由模块


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    utils.logger.info("服务器启动...")
    if config.SAVE_DATA_OPTION in ["db", "sqlite"]:
        await db.init_db(config.SAVE_DATA_OPTION)
        utils.logger.info("数据库已初始化。")

    yield

    if config.SAVE_DATA_OPTION in ["db", "sqlite"]:
        await db.close()
        utils.logger.info("数据库连接已关闭。")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""
    app = FastAPI(
        title="AI Creator Helper API",
        description="用于AI创作者助手的后端API",
        version="1.0.0",
        lifespan=lifespan
    )

    # 注册根路由
    @app.get("/")
    def read_root():
        return {"message": "AI Creator Helper API 正在运行"}

    # 包含其他路由
    app.include_router(crawler_web.router)
    app.include_router(crawler_data_web.router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)