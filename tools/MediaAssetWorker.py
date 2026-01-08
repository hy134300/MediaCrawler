import asyncio
import hashlib
import mimetypes
import os
import tempfile

import aiohttp
from minio import S3Error

from tools import MinioStorage, utils
from tools.utils import logger
from web.RateLimiter import RateLimiter


class MediaAssetWorker:
    def __init__(self, store, minio: MinioStorage, concurrency: int = 2):
        self.store = store
        self.minio = minio
        self.semaphore = asyncio.Semaphore(concurrency)
        self.rate_limiter = RateLimiter(rate_bytes_per_sec=1 * 1024 * 1024)

    async def run(self) -> bool:
        items = await self.store.list_pending_assets(limit=100)
        if not items:
            return False

        async with aiohttp.ClientSession() as session:
            tasks = [self._process_one(session, item) for item in items]
            await asyncio.gather(*tasks)

        return True

    async def _process_one(self, session, item: dict):
        async with self.semaphore:
            item_id = item["id"]
            media_fields = item.get("media_fields", {})

            new_fields = {}
            item_failed = False

            for field_name, url in media_fields.items():
                local_file = None
                try:
                    local_file, ext = await self._download(session, url)

                    hash_value = self.file_sha256(local_file)
                    object_name = f"sha256/{hash_value}{ext}"

                    if self._object_exists(object_name):
                        minio_url = f"http://localhost:9000/{self.minio.bucket}/{object_name}"
                    else:
                        minio_url = self.minio.upload_file(local_file, object_name)

                    new_fields[field_name] = minio_url

                except Exception as e:
                    item_failed = True
                    logger.error(f"[ERROR] {e}")
                finally:
                    if local_file and os.path.exists(local_file):
                        os.remove(local_file)

            # ===== item 级别状态 =====
            if item_failed:
                new_fields["asset_status"] = "FAILED"
            else:
                new_fields["asset_status"] = "SUCCESS"

            await self.store.update_asset_status(
                item_id=item_id,
                new_fields=new_fields
            )

    def _object_exists(self, object_name: str) -> bool:
        try:
            self.minio.client.stat_object(self.minio.bucket, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            # 其他错误（权限、网络）要抛出来
            raise

    async def _download(self, session, url: str, retries: int = 3) -> tuple[str, str]:
        timeout = aiohttp.ClientTimeout(
            total=10 * 60,
            sock_connect=30,
            sock_read=120,
        )

        last_exc = None

        for attempt in range(1, retries + 1):
            tmp = None
            try:
                async with session.get(url, timeout=timeout) as resp:
                    resp.raise_for_status()

                    content_type = resp.headers.get("Content-Type", "").split(";")[0]
                    ext = mimetypes.guess_extension(content_type) or ".bin"

                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                    tmp_path = tmp.name

                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        await self.rate_limiter.wait(len(chunk))
                        tmp.write(chunk)

                    tmp.close()

                    # ✅ 只有这里 return，文件一定存在
                    return tmp_path, ext

            except Exception as e:
                last_exc = e
                utils.logger.error(f"[ERROR] {e}")
                if tmp:
                    try:
                        tmp.close()
                        if os.path.exists(tmp.name):
                            os.remove(tmp.name)
                    except OSError:
                        pass

                logger.warning(
                    f"[DOWNLOAD_RETRY] attempt={attempt}/{retries} url={url} err={e}"
                )
                await asyncio.sleep(2 ** attempt)

        raise last_exc

    def _build_object_name(self, item: dict, field_name: str, local_file: str) -> str:
        ext = os.path.splitext(local_file)[-1] or ".bin"
        return f"{item['platform']}/{item['id']}/{field_name}{ext}"


    def file_sha256(self,path: str, chunk_size: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
