import asyncio
import random
import json
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

USER_URL = "https://www.douyin.com/user/MS4wLjABAAAA_G8KJ-bz3kwfpsTc0883F4Rh43FkjksHrUGS0UZax8M?from_tab_name=main"

async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./chrome-profile-douyin",
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        page = await context.new_page()

        # 1. 打开主页并滚动抓取 aweme_id 列表
        await page.goto(USER_URL, wait_until="domcontentloaded")
        print("正在加载主页，并滚动抓取所有视频ID...")

        # 重复下拉让更多视频出来
        for i in range(8):  # 可根据创作者视频数量调整次数
            print(f"下拉分页 {i+1}/8")
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(random.randint(3000, 5000))

        # 从 DOM 获取所有视频卡片链接
        video_elements = await page.locator("a[href*='/video/']").element_handles()
        aweme_ids = []
        for ele in video_elements:
            href = await ele.get_attribute("href")
            if href and "/video/" in href:
                vid = href.split("/video/")[-1].split("?")[0]
                if vid not in aweme_ids:
                    aweme_ids.append(vid)

        print(f"共抓取到 {len(aweme_ids)} 个视频")

        results = []

        # 2. 逐个打开视频详情页抓取信息
        async def capture_video_info(video_id):
            # 监听 detail 接口
            video_data = {}

            async def on_response(r):
                try:
                    if "/aweme/v1/web/aweme/detail/" in r.url:
                        data = await r.json()
                        aweme = data.get("aweme_detail", {})
                        video = aweme.get("video", {})
                        play_addr = video.get("play_addr", {})
                        video_data.update({
                            "video_urls": play_addr.get("url_list", []),
                            "api_desc": aweme.get("desc"),
                            "statistics": aweme.get("statistics")
                        })
                except Exception:
                    pass

            page.on("response", on_response)

            video_page = f"https://www.douyin.com/video/{video_id}"
            print("打开视频详情:", video_page)

            try:
                await page.goto(video_page, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(5000, 9000))
            except PlaywrightTimeoutError:
                print("⚠️ 页面加载超时", video_page)

            # 页面 DOM 信息
            title = await page.title()

            # 尝试抓作者昵称 DOM
            author = None
            try:
                author = await page.locator("a[href*='/user/']").first.text_content()
            except Exception:
                pass

            # 页面展示文案
            page_desc = None
            try:
                page_desc = await page.locator("div:has-text('#')").first.text_content()
            except Exception:
                pass

            info = {
                "aweme_id": video_id,
                "page_title": title,
                "author": author,
                "page_desc": page_desc,
                **video_data
            }

            return info

        # 抓取每个视频详情
        for i, vid in enumerate(aweme_ids):
            print(f"\n[{i+1}/{len(aweme_ids)}] 采集视频: {vid}")
            info = await capture_video_info(vid)
            results.append(info)

            # 等待更像真人
            wait_sec = random.randint(8, 15)
            print(f"  等待 {wait_sec} 秒再抓下一个")
            await page.wait_for_timeout(wait_sec * 1000)

        # 3. 保存所有结果
        with open("douyin_all_videos.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print("抓取完成 🟢 视频总数:", len(results))
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
