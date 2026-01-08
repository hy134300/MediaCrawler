import asyncio

from database.crud import get_store_by_platform
from tools.MediaAssetWorker import MediaAssetWorker
from tools.MinioStorage import MinioStorage


async def run_upload(plateform):
    store = get_store_by_platform(plateform)
    minio = MinioStorage()

    worker = MediaAssetWorker(
        store=store,
        minio=minio,
        concurrency=2
    )

    while True:
        has_work = await worker.run()
        idle_sleep = 1
        max_sleep = 30
        if has_work:
            idle_sleep = 1
        else:
            idle_sleep = min(idle_sleep * 2, max_sleep)

        await asyncio.sleep(idle_sleep)

if __name__ == "__main__":
    asyncio.run(run_upload("dy"))
