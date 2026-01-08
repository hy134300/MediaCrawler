import asyncio
import random
from typing import Dict, List, Callable, Optional
from playwright.async_api import BrowserContext, Page


class DouyinBrowserClient:
    """
    用真实浏览器行为抓取抖音创作者 & 视频
    - 不主动调用任何 API
    - 只通过页面访问 + 被动监听
    """

    def __init__(self, context: BrowserContext):
        self.context = context
        self.page: Optional[Page] = None

        self._creator_data: Dict = {}
        self._aweme_map: Dict[str, Dict] = {}

    # ========= 生命周期 =========

    async def open(self):
        self.page = await self.context.new_page()
        self._bind_listeners()

    async def close(self):
        if self.page:
            await self.page.close()
            self.page = None

    # ========= 内部监听 =========

    def _bind_listeners(self):
        self.page.on("response", self._on_response)

    async def _on_response(self, response):
        try:
            url = response.url

            # 1️⃣ 创作者信息（浏览器自己触发）
            if "/aweme/v1/web/user/profile" in url:
                data = await response.json()
                self._creator_data = data

            # 2️⃣ 创作者视频列表（滚动触发）
            elif "/aweme/v1/web/aweme/post/" in url:
                data = await response.json()
                for aweme in data.get("aweme_list", []):
                    self._aweme_map[aweme["aweme_id"]] = aweme

            # 3️⃣ 视频详情（点击视频触发）
            elif "/aweme/v1/web/aweme/detail/" in url:
                data = await response.json()
                aweme = data.get("aweme_detail", {})
                aweme_id = aweme.get("aweme_id")
                if aweme_id:
                    self._aweme_map[aweme_id] = aweme

        except Exception:
            pass

    # ========= 对外方法 =========

    async def get_user_info(self, sec_user_id: str) -> Dict:
        """
        打开创作者主页，返回 user_info（结构与 API 版本一致）
        """
        assert self.page, "BrowserClient not opened"

        self._creator_data = {}

        await self.page.goto(
            f"https://www.douyin.com/user/{sec_user_id}",
            wait_until="domcontentloaded"
        )

        # 模拟真人停留
        await self.page.wait_for_timeout(random.randint(8000, 12000))

        return self._creator_data

    async def get_all_user_aweme_posts(
        self,
        sec_user_id: str,
        callback: Optional[Callable[[Dict], None]] = None,
        max_scroll: int = 12
    ) -> List[Dict]:
        """
        滚动创作者主页，获取所有视频（尽量多）
        """
        assert self.page, "BrowserClient not opened"

        self._aweme_map = {}

        await self.page.goto(
            f"https://www.douyin.com/user/{sec_user_id}",
            wait_until="domcontentloaded"
        )

        await self.page.wait_for_timeout(random.randint(6000, 9000))

        last_count = 0

        for i in range(max_scroll):
            # 真人滚动
            await self.page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )

            wait = random.randint(4000, 7000)
            await self.page.wait_for_timeout(wait)

            if len(self._aweme_map) == last_count:
                # 没新增，认为到底了
                break

            last_count = len(self._aweme_map)

        aweme_list = list(self._aweme_map.values())

        if callback:
            for aweme in aweme_list:
                await callback(aweme)

        return aweme_list

    async def fetch_video_detail_by_click(self, aweme_id: str) -> Dict:
        """
        通过“真实打开视频页”获取视频详情
        """
        assert self.page, "BrowserClient not opened"

        await self.page.goto(
            f"https://www.douyin.com/video/{aweme_id}",
            wait_until="domcontentloaded"
        )

        await self.page.wait_for_timeout(random.randint(6000, 10000))

        return self._aweme_map.get(aweme_id, {})
