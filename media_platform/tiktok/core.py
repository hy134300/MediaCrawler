# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tiktok/core.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import os
import random
from asyncio import Task
from typing import Any, Dict, List, Optional

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import tiktok as tiktok_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import TikTokClient
from .exception import DataFetchError
from .help import parse_video_info_from_url, parse_creator_info_from_url
from .login import TikTokLogin


class TikTokCrawler(AbstractCrawler):
    context_page: Page
    tt_client: TikTokClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.tiktok.com"
        self.cdp_manager = None
        self.ip_proxy_pool = None  # 代理IP池，用于代理自动刷新

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[TikTokCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    None,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[TikTokCrawler] 使用标准模式启动浏览器")
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS,
                )
                # stealth.min.js is a js script to prevent the website from detecting the crawler.
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.tt_client = await self.create_tiktok_client(httpx_proxy_format)
            if not await self.tt_client.pong(browser_context=self.browser_context):
                login_obj = TikTokLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # you phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.tt_client.update_cookies(browser_context=self.browser_context)
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_videos()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creators_and_videos()

            utils.logger.info("[TikTokCrawler.start] TikTok Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("[TikTokCrawler.search] Begin search tiktok keywords")
        tt_limit_count = config.TT_SEARCH_COUNT or 10
        if config.CRAWLER_MAX_NOTES_COUNT < tt_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = tt_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[TikTokCrawler.search] Current keyword: {keyword}")
            video_list: List[str] = []
            page = 0
            search_id = ""
            while (page - start_page + 1) * tt_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[TikTokCrawler.search] Skip {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[TikTokCrawler.search] search tiktok keyword: {keyword}, page: {page}")
                    posts_res = await self.tt_client.search_info_by_keyword(
                        keyword=keyword,
                        offset=page * tt_limit_count - tt_limit_count,
                        search_id=search_id,
                    )
                    if posts_res.get("data") is None or posts_res.get("data") == []:
                        utils.logger.info(f"[TikTokCrawler.search] search tiktok keyword: {keyword}, page: {page} is empty,{posts_res.get('data')}`")
                        break
                except DataFetchError:
                    utils.logger.error(f"[TikTokCrawler.search] search tiktok keyword: {keyword} failed")
                    break

                page += 1
                if "data" not in posts_res:
                    utils.logger.error(f"[TikTokCrawler.search] search tiktok keyword: {keyword} failed，账号也许被风控了。")
                    break
                search_id = posts_res.get("extra", {}).get("logid", "")
                for post_item in posts_res.get("data"):
                    video_info = self._extract_video_info_from_search_item(post_item)
                    if not video_info:
                        continue
                    video_id = self._extract_video_id(video_info)
                    if not video_id:
                        continue
                    video_list.append(video_id)
                    await tiktok_store.update_tiktok_video(video_item=video_info)
                    await self.get_video_media(video_item=video_info)
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[TikTokCrawler.search] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {page-1}")
            utils.logger.info(f"[TikTokCrawler.search] keyword:{keyword}, video_list:{video_list}")
            await self.batch_get_video_comments(video_list)

    async def get_specified_videos(self):
        """Get the information and comments of the specified post from URLs or IDs"""
        utils.logger.info("[TikTokCrawler.get_specified_videos] Parsing video URLs...")
        video_id_list = []
        for video_url in config.TT_SPECIFIED_ID_LIST:
            try:
                video_info = parse_video_info_from_url(video_url)

                if video_info.url_type == "short":
                    utils.logger.info(f"[TikTokCrawler.get_specified_videos] Resolving short link: {video_url}")
                    resolved_url = await self.tt_client.resolve_short_url(video_url)
                    if resolved_url:
                        video_info = parse_video_info_from_url(resolved_url)
                        utils.logger.info(f"[TikTokCrawler.get_specified_videos] Short link resolved to video ID: {video_info.video_id}")
                    else:
                        utils.logger.error(f"[TikTokCrawler.get_specified_videos] Failed to resolve short link: {video_url}")
                        continue

                video_id_list.append(video_info.video_id)
                utils.logger.info(f"[TikTokCrawler.get_specified_videos] Parsed video ID: {video_info.video_id} from {video_url}")
            except ValueError as e:
                utils.logger.error(f"[TikTokCrawler.get_specified_videos] Failed to parse video URL: {e}")
                continue

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_video_detail(video_id=video_id, semaphore=semaphore) for video_id in video_id_list]
        video_details = await asyncio.gather(*task_list)
        for video_detail in video_details:
            if video_detail is not None:
                await tiktok_store.update_tiktok_video(video_item=video_detail)
                await self.get_video_media(video_item=video_detail)
        await self.batch_get_video_comments(video_id_list)

    async def get_video_detail(self, video_id: str, semaphore: asyncio.Semaphore) -> Any:
        """Get video detail"""
        async with semaphore:
            try:
                result = await self.tt_client.get_video_by_id(video_id)
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[TikTokCrawler.get_video_detail] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching video {video_id}")
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[TikTokCrawler.get_video_detail] Get video detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[TikTokCrawler.get_video_detail] have not fund note detail video_id:{video_id}, err: {ex}")
                return None

    async def batch_get_video_comments(self, video_list: List[str]) -> None:
        """
        Batch get video comments
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info("[TikTokCrawler.batch_get_video_comments] Crawling comment mode is not enabled")
            return

        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for video_id in video_list:
            task = asyncio.create_task(self.get_comments(video_id, semaphore), name=video_id)
            task_list.append(task)
        if len(task_list) > 0:
            await asyncio.wait(task_list)

    async def get_comments(self, video_id: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            try:
                crawl_interval = config.CRAWLER_MAX_SLEEP_SEC
                await self.tt_client.get_video_all_comments(
                    video_id=video_id,
                    crawl_interval=crawl_interval,
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=tiktok_store.batch_update_tiktok_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
                await asyncio.sleep(crawl_interval)
                utils.logger.info(f"[TikTokCrawler.get_comments] Sleeping for {crawl_interval} seconds after fetching comments for video {video_id}")
                utils.logger.info(f"[TikTokCrawler.get_comments] video_id: {video_id} comments have all been obtained and filtered ...")
            except DataFetchError as e:
                utils.logger.error(f"[TikTokCrawler.get_comments] video_id: {video_id} get comments failed, error: {e}")

    async def get_creators_and_videos(self) -> None:
        """
        Get the information and videos of the specified creator from URLs or IDs
        """
        utils.logger.info("[TikTokCrawler.get_creators_and_videos] Begin get tiktok creators")
        utils.logger.info("[TikTokCrawler.get_creators_and_videos] Parsing creator URLs...")

        for creator_url in config.TT_CREATOR_ID_LIST:
            try:
                creator_info_parsed = parse_creator_info_from_url(creator_url)
                unique_id = creator_info_parsed.unique_id
                utils.logger.info(f"[TikTokCrawler.get_creators_and_videos] Parsed unique_id: {unique_id} from {creator_url}")
            except ValueError as e:
                utils.logger.error(f"[TikTokCrawler.get_creators_and_videos] Failed to parse creator URL: {e}")
                continue

            creator_info: Dict = await self.tt_client.get_user_info(unique_id)
            if creator_info:
                await tiktok_store.update_tiktok_creator(creator=creator_info)

            all_video_list = await self.tt_client.get_all_user_video_posts(unique_id=unique_id, callback=self.fetch_creator_video_detail)

            video_ids = [self._extract_video_id(video_item) for video_item in all_video_list]
            await self.batch_get_video_comments([video_id for video_id in video_ids if video_id])

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = []
        for post_item in video_list:
            video_id = self._extract_video_id(post_item)
            if not video_id:
                continue
            task_list.append(self.get_video_detail(video_id, semaphore))

        note_details = await asyncio.gather(*task_list)
        for video_item in note_details:
            if video_item is not None:
                await tiktok_store.update_tiktok_video(video_item=video_item)
                await self.get_video_media(video_item=video_item)

    async def create_tiktok_client(self, httpx_proxy: Optional[str]) -> TikTokClient:
        """Create tiktok client"""
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())  # type: ignore
        tiktok_client = TikTokClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Host": "www.tiktok.com",
                "Origin": "https://www.tiktok.com/",
                "Referer": "https://www.tiktok.com/",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,
        )
        return tiktok_client

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={
                    "width": 1920,
                    "height": 1080
                },
                user_agent=user_agent,
            )  # type: ignore
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        使用CDP模式启动浏览器
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

            await self.cdp_manager.add_stealth_script()

            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[TikTokCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[TikTokCrawler] CDP模式启动失败，回退到标准模式: {e}")
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self) -> None:
        """Close browser context"""
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[TikTokCrawler.close] Browser context closed ...")

    async def get_video_media(self, video_item: Dict):
        """
        获取 TikTok 媒体资源（图片或视频）
        """
        if not config.ENABLE_GET_MEIDAS:
            utils.logger.info("[TikTokCrawler.get_video_media] Crawling image mode is not enabled")
            return
        image_urls = self._extract_image_urls(video_item)
        if image_urls:
            await self.get_video_images(video_item, image_urls)
        else:
            await self.get_video_video(video_item)

    async def get_video_images(self, video_item: Dict, image_urls: List[str]):
        """
        get video images. please use get_video_media
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        video_id = self._extract_video_id(video_item)
        if not video_id:
            return
        pic_num = 0
        for url in image_urls:
            if not url:
                continue
            content = await self.tt_client.get_video_media(url)
            await asyncio.sleep(random.random())
            if content is None:
                continue
            extension_file_name = f"{pic_num:>03d}.jpeg"
            pic_num += 1
            utils.logger.info(f"[TikTokCrawler.get_video_images] Fetched image {extension_file_name} for video {video_id} ({len(content)} bytes)")

    async def get_video_video(self, video_item: Dict):
        """
        get video file. please use get_video_media
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        video_id = self._extract_video_id(video_item)
        if not video_id:
            return
        video_download_url = self._extract_video_download_url(video_item)
        if not video_download_url:
            return
        content = await self.tt_client.get_video_media(video_download_url)
        await asyncio.sleep(random.random())
        if content is None:
            return
        utils.logger.info(f"[TikTokCrawler.get_video_video] Fetched video for {video_id} ({len(content)} bytes)")

    def _extract_video_info_from_search_item(self, post_item: Dict) -> Optional[Dict]:
        if not isinstance(post_item, dict):
            return None
        if "video_info" in post_item and isinstance(post_item.get("video_info"), dict):
            return post_item.get("video_info")
        if "item" in post_item and isinstance(post_item.get("item"), dict):
            return post_item.get("item")
        item_info = post_item.get("item_info")
        if isinstance(item_info, dict):
            item_struct = item_info.get("item_struct")
            if isinstance(item_struct, dict):
                return item_struct
            return item_info
        return post_item

    def _extract_video_id(self, video_item: Dict) -> str:
        if not isinstance(video_item, dict):
            return ""
        video_id = video_item.get("video_id") or video_item.get("id")
        return str(video_id) if video_id else ""

    def _extract_image_urls(self, video_item: Dict) -> List[str]:
        urls: List[str] = []
        images = video_item.get("images") or video_item.get("image_urls") or []
        if isinstance(images, list):
            for image in images:
                if isinstance(image, str):
                    urls.append(image)
                elif isinstance(image, dict):
                    url_list = image.get("url_list") or image.get("urlList") or []
                    if isinstance(url_list, list) and url_list:
                        urls.append(url_list[-1])
        return urls

    def _extract_video_download_url(self, video_item: Dict) -> str:
        for key in ("video_download_url", "download_url", "play_url", "video_url"):
            url = video_item.get(key)
            if isinstance(url, str) and url:
                return url
        video_obj = video_item.get("video", {})
        if isinstance(video_obj, dict):
            for key in ("download_addr", "play_addr", "downloadAddr", "playAddr"):
                url_list = video_obj.get(key, {}).get("url_list") if isinstance(video_obj.get(key), dict) else None
                if isinstance(url_list, list) and url_list:
                    return url_list[-1]
        return ""
