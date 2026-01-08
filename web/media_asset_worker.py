import asyncio
import hashlib
import mimetypes
import os
import tempfile
from urllib.parse import urlparse

import aiohttp

from tools.MinioStorage import MinioStorage
from tools.utils import logger
from web.RateLimiter import RateLimiter


class MediaAssetWorker:
    def __init__(self, store, max_concurrency: int = 3):
        """
        store: 你的 DB Store（DouyinStore / XhsStore 等的统一接口）
        """
        self.store = store
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.minio = MinioStorage()
        self.rate_limiter = RateLimiter(rate_bytes_per_sec=1 * 1024 * 1024)

    async def run(self):
        logger.info("[MediaAssetWorker] 开始处理媒体资产")

        # 1. 查所有待处理的媒体
        items = await self.store.list_pending_assets()
        if not items:
            logger.info("[MediaAssetWorker] 没有待处理媒体")
            return

        async with aiohttp.ClientSession() as session:
            tasks = [
                self._process_one(session, item)
                for item in items
            ]
            await asyncio.gather(*tasks)

        logger.info("[MediaAssetWorker] 媒体资产处理完成")


    def _get_ext_from_url(self, url: str) -> str:
        path = urlparse(url).path
        ext = os.path.splitext(path)[-1]
        return ext if ext else ".bin"

    async def _process_one(self, session, item: dict):
        async with self.semaphore:
            try:
                async with self.semaphore:
                    item_id = item["id"]
                    media_fields = item.get("media_fields", {})

                    new_fields = {}

                    for field_name, url in media_fields.items():
                        local_file = None
                        try:
                            local_file, ext = await self._download(session, url)
                            #object_name = f"{item['platform']}/{item_id}/{field_name}{ext}"
                            hash_value = self.file_sha256(local_file)

                            object_name = f"sha256/{hash_value}{ext}"
                            # 如果已存在，直接拼 URL，不再上传
                            if self.minio.client.stat_object(self.minio.bucket, object_name):
                                minio_url = f"http://localhost:9000/{self.minio.bucket}/{object_name}"
                            else:
                                minio_url = self.minio.upload_file(local_file, object_name)
                            #minio_url = self.minio.upload_file(local_file, object_name)
                            new_fields[field_name] = minio_url
                        except Exception as e:
                            success = False
                            error_msg = str(e)
                            break
                        finally:
                            if local_file and os.path.exists(local_file):
                                os.remove(local_file)

                    # ✅ 一次性更新所有字段
                    await self.store.update_asset_status(item_id=item_id, new_fields=new_fields)
                logger.info(f"[MediaAssetWorker] DONE {item['content_id']}")

            except Exception as e:
                logger.error(f"[MediaAssetWorker] FAILED {item['content_id']} {e}")
                await self.store.update_asset_status(
                    item_id=item["id"],
                    status="FAILED"
                )

    import aiohttp

    async def _download(self, session: aiohttp.ClientSession, url: str) -> tuple[str, str]:
        timeout = aiohttp.ClientTimeout(
            total=None,  # ❗不限制总时间
            sock_connect=30,  # 连接超时
            sock_read=30  # 单次读取超时
        )

        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()

            # 1️⃣ 判断文件类型
            content_type = resp.headers.get("Content-Type", "").split(";")[0]
            ext = mimetypes.guess_extension(content_type) or ""

            # 抖音兜底
            if not ext and "douyin.com/aweme/v1/play" in url:
                ext = ".mp4"

            if not ext:
                ext = ".bin"

            # 2️⃣ 流式写入临时文件
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)

            try:
                async for chunk in resp.content.iter_chunked(1024 * 1024):  # 1MB
                    await self.rate_limiter.wait(len(chunk))
                    tmp.write(chunk)
            finally:
                tmp.close()

            return tmp.name, ext

    def _build_object_name(self, item: dict, field_name: str, local_file: str) -> str:
        ext = os.path.splitext(local_file)[-1] or ".bin"
        return f"{item['platform']}/{item['id']}/{field_name}{ext}"

    import hashlib

    def file_sha256(path: str, chunk_size: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
