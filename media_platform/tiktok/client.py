# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tiktok/client.py
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
import copy
import urllib.parse
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Union

import httpx
from playwright.async_api import BrowserContext, Page

import config
from base.base_crawler import AbstractApiClient
from proxy.proxy_mixin import ProxyRefreshMixin
from tools import utils

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool

from .exception import DataFetchError
from .field import PublishTimeType, SearchChannelType, SearchSortType
from .help import get_web_id


class TikTokClient(AbstractApiClient, ProxyRefreshMixin):

    def __init__(
        self,
        timeout=60,
        proxy=None,
        *,
        headers: Dict,
        playwright_page: Optional[Page],
        cookie_dict: Dict,
        proxy_ip_pool: Optional["ProxyIpPool"] = None,
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = "https://www.tiktok.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self.init_proxy_pool(proxy_ip_pool)

    async def __process_req_params(
        self,
        uri: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        request_method="GET",
    ):
        if not params:
            return
        headers = headers or self.headers
        local_storage: Dict = {}
        if self.playwright_page is not None:
            local_storage = await self.playwright_page.evaluate("() => window.localStorage")
        ms_token = config.TT_MS_TOKEN or local_storage.get("msToken") or local_storage.get("xmst")
        common_params = {
            "device_platform": "webapp",
            "aid": "1988",
            "channel": "channel_pc_web",
            "version_code": "1.0.0",
            "version_name": "1.0.0",
            "cookie_enabled": "true",
            "browser_language": "en-US",
            "browser_platform": "MacIntel",
            "browser_name": "Chrome",
            "browser_version": "120.0.0.0",
            "browser_online": "true",
            "engine_name": "Blink",
            "os_name": "Mac OS",
            "os_version": "10.15.7",
            "cpu_core_num": "8",
            "device_memory": "8",
            "engine_version": "109.0",
            "platform": "PC",
            "screen_width": "2560",
            "screen_height": "1440",
            "webid": get_web_id(),
        }
        if ms_token:
            common_params["msToken"] = ms_token
        if config.TT_VERIFY_FP:
            common_params["verifyFp"] = config.TT_VERIFY_FP
        if config.TT_DEVICE_ID:
            common_params["device_id"] = config.TT_DEVICE_ID
        params.update(common_params)

    async def request(self, method, url, **kwargs):
        await self._refresh_proxy_if_expired()

        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)
        try:
            if response.text == "" or response.text == "blocked":
                utils.logger.error(f"request params incrr, response.text: {response.text}")
                raise Exception("account blocked")
            return response.json()
        except Exception as e:
            raise DataFetchError(f"{e}, {response.text}")

    async def get(self, uri: str, params: Optional[Dict] = None, headers: Optional[Dict] = None):
        """
        GET请求
        """
        await self.__process_req_params(uri, params, headers)
        headers = headers or self.headers
        return await self.request(method="GET", url=f"{self._host}{uri}", params=params, headers=headers)

    async def post(self, uri: str, data: dict, headers: Optional[Dict] = None):
        await self.__process_req_params(uri, data, headers, request_method="POST")
        headers = headers or self.headers
        return await self.request(method="POST", url=f"{self._host}{uri}", data=data, headers=headers)

    async def pong(self, browser_context: BrowserContext) -> bool:
        if self.playwright_page is not None:
            local_storage = await self.playwright_page.evaluate("() => window.localStorage")
            if local_storage.get("HasUserLogin", "") == "1":
                return True

        _, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        return bool(cookie_dict.get("sessionid") or cookie_dict.get("sid_tt"))

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def search_info_by_keyword(
        self,
        keyword: str,
        offset: int = 0,
        search_channel: SearchChannelType = SearchChannelType.GENERAL,
        sort_type: SearchSortType = SearchSortType.GENERAL,
        publish_time: PublishTimeType = PublishTimeType.UNLIMITED,
        search_id: str = "",
    ):
        """
        TikTok Web Search API
        """
        query_params = {
            "keyword": keyword,
            "offset": offset,
            "count": config.TT_SEARCH_COUNT or 12,
            "search_id": search_id,
            "search_channel": search_channel.value,
        }
        if config.TT_SEARCH_REGION:
            query_params["region"] = config.TT_SEARCH_REGION
        if sort_type.value != SearchSortType.GENERAL.value or publish_time.value != PublishTimeType.UNLIMITED.value:
            query_params["sort_type"] = sort_type.value
            query_params["publish_time"] = publish_time.value
        if config.TT_SEARCH_EXTRA_PARAMS:
            query_params.update(config.TT_SEARCH_EXTRA_PARAMS)

        referer_url = f"https://www.tiktok.com/search?q={urllib.parse.quote(keyword)}"
        headers = copy.copy(self.headers)
        headers["Referer"] = referer_url
        if config.TT_SEARCH_EXTRA_HEADERS:
            headers.update(config.TT_SEARCH_EXTRA_HEADERS)
        return await self.get("/api/search/general/full/", query_params, headers=headers)

    async def get_video_by_id(self, video_id: str) -> Any:
        """
        TikTok Video Detail API
        """
        params = {"item_id": video_id}
        headers = copy.copy(self.headers)
        headers.pop("Origin", None)
        res = await self.get("/api/item/detail/", params, headers)
        item_info = res.get("itemInfo") or res.get("item_info") or {}
        if isinstance(item_info, dict):
            item_list = item_info.get("itemStruct") or item_info.get("item_struct")
            if isinstance(item_list, dict):
                return item_list
        return res.get("item", res)

    async def get_video_comments(self, video_id: str, cursor: int = 0):
        uri = "/api/comment/list/"
        params = {"item_id": video_id, "cursor": cursor, "count": 20}
        return await self.get(uri, params)

    async def get_sub_comments(self, video_id: str, comment_id: str, cursor: int = 0):
        uri = "/api/comment/list/reply/"
        params = {
            "comment_id": comment_id,
            "cursor": cursor,
            "count": 20,
            "item_id": video_id,
        }
        return await self.get(uri, params)

    async def get_video_all_comments(
        self,
        video_id: str,
        crawl_interval: float = 1.0,
        is_fetch_sub_comments=False,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ):
        result = []
        comments_has_more = 1
        comments_cursor = 0
        while comments_has_more and len(result) < max_count:
            comments_res = await self.get_video_comments(video_id, comments_cursor)
            comments_has_more = comments_res.get("has_more", 0)
            comments_cursor = comments_res.get("cursor", 0)
            comments = comments_res.get("comments", [])
            if not comments:
                continue
            if len(result) + len(comments) > max_count:
                comments = comments[:max_count - len(result)]
            result.extend(comments)
            if callback:
                await callback(video_id, comments)

            await asyncio.sleep(crawl_interval)
            if not is_fetch_sub_comments:
                continue
            for comment in comments:
                reply_comment_total = comment.get("reply_comment_total") or comment.get("replyCount", 0)

                if reply_comment_total > 0:
                    comment_id = comment.get("cid") or comment.get("comment_id")
                    if not comment_id:
                        continue
                    sub_comments_has_more = 1
                    sub_comments_cursor = 0

                    while sub_comments_has_more:
                        sub_comments_res = await self.get_sub_comments(video_id, comment_id, sub_comments_cursor)
                        sub_comments_has_more = sub_comments_res.get("has_more", 0)
                        sub_comments_cursor = sub_comments_res.get("cursor", 0)
                        sub_comments = sub_comments_res.get("comments", [])

                        if not sub_comments:
                            continue
                        result.extend(sub_comments)
                        if callback:
                            await callback(video_id, sub_comments)
                        await asyncio.sleep(crawl_interval)
        return result

    async def get_user_info(self, unique_id: str):
        uri = "/api/user/detail/"
        params = {
            "uniqueId": unique_id,
        }
        return await self.get(uri, params)

    async def get_user_video_posts(self, unique_id: str, max_cursor: str = "") -> Dict:
        uri = "/api/post/item_list/"
        params = {
            "uniqueId": unique_id,
            "count": 18,
            "cursor": max_cursor,
        }
        return await self.get(uri, params)

    async def get_all_user_video_posts(self, unique_id: str, callback: Optional[Callable] = None):
        posts_has_more = 1
        max_cursor = ""
        result = []
        while posts_has_more == 1:
            video_post_res = await self.get_user_video_posts(unique_id, max_cursor)
            posts_has_more = video_post_res.get("has_more", 0)
            max_cursor = video_post_res.get("cursor", "")
            video_list = video_post_res.get("itemList") or video_post_res.get("item_list") or []
            utils.logger.info(f"[TikTokClient.get_all_user_video_posts] get unique_id:{unique_id} video len : {len(video_list)}")
            if callback:
                await callback(video_list)
            result.extend(video_list)
        return result

    async def get_video_media(self, url: str) -> Union[bytes, None]:
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            try:
                response = await client.request("GET", url, timeout=self.timeout, follow_redirects=True)
                response.raise_for_status()
                if not response.reason_phrase == "OK":
                    utils.logger.error(f"[TikTokClient.get_video_media] request {url} err, res:{response.text}")
                    return None
                else:
                    return response.content
            except httpx.HTTPError as exc:
                utils.logger.error(f"[TikTokClient.get_video_media] {exc.__class__.__name__} for {exc.request.url} - {exc}")
                return None

    async def resolve_short_url(self, short_url: str) -> str:
        """
        解析 TikTok 短链接,获取重定向后的真实URL
        """
        async with httpx.AsyncClient(proxy=self.proxy, follow_redirects=False) as client:
            try:
                utils.logger.info(f"[TikTokClient.resolve_short_url] Resolving short URL: {short_url}")
                response = await client.get(short_url, timeout=10)

                if response.status_code in [301, 302, 303, 307, 308]:
                    redirect_url = response.headers.get("Location", "")
                    utils.logger.info(f"[TikTokClient.resolve_short_url] Resolved to: {redirect_url}")
                    return redirect_url
                else:
                    utils.logger.warning(f"[TikTokClient.resolve_short_url] Unexpected status code: {response.status_code}")
                    return ""
            except Exception as e:
                utils.logger.error(f"[TikTokClient.resolve_short_url] Failed to resolve short URL: {e}")
                return ""
