# file: database/data_registry.py

import sqlalchemy
from sqlalchemy import cast, Integer

from database.models import (
    DouyinAweme, XhsNote, BilibiliVideo, KuaishouVideo,
    WeiboNote, TiebaNote, ZhihuContent
)

# 将平台模型、标准化列的定义都集中到这里
from sqlalchemy import cast, Integer
import sqlalchemy

PLATFORM_MODELS = {
    "xhs": (
        XhsNote,
        [
            XhsNote.note_id.label("id"),
            sqlalchemy.literal("xhs").label("platform"),
            XhsNote.title.label("title"),
            XhsNote.nickname.label("nickname"),
            XhsNote.liked_count.label("liked_count"),
            XhsNote.comment_count.label("comment_count"),
            XhsNote.time.label("create_time"),
            XhsNote.note_url.label("note_url"),
            XhsNote.image_list.label("image_list"),
            XhsNote.source_keyword.label("keyword")
        ]
    ),

    "dy": (
        DouyinAweme,
        [
            DouyinAweme.aweme_id.label("id"),
            sqlalchemy.literal("dy").label("platform"),
            DouyinAweme.title.label("title"),
            DouyinAweme.nickname.label("nickname"),
            DouyinAweme.liked_count.label("liked_count"),
            DouyinAweme.comment_count.label("comment_count"),
            DouyinAweme.create_time.label("create_time"),
            DouyinAweme.aweme_url.label("note_url"),
            DouyinAweme.cover_url.label("image_list"),
            DouyinAweme.source_keyword.label("keyword")
        ]
    ),

    "bili": (
        BilibiliVideo,
        [
            BilibiliVideo.video_id.label("id"),
            sqlalchemy.literal("bili").label("platform"),
            BilibiliVideo.title.label("title"),
            BilibiliVideo.nickname.label("nickname"),
            BilibiliVideo.liked_count.label("liked_count"),
            BilibiliVideo.video_comment.label("comment_count"),
            BilibiliVideo.create_time.label("create_time"),
            BilibiliVideo.video_url.label("note_url"),
            BilibiliVideo.video_cover_url.label("image_list"),
            BilibiliVideo.source_keyword.label("keyword")
        ]
    ),

    "ks": (
        KuaishouVideo,
        [
            KuaishouVideo.video_id.label("id"),
            sqlalchemy.literal("ks").label("platform"),
            KuaishouVideo.title.label("title"),
            KuaishouVideo.nickname.label("nickname"),
            KuaishouVideo.liked_count.label("liked_count"),
            sqlalchemy.literal(0).label("comment_count"),
            KuaishouVideo.create_time.label("create_time"),
            KuaishouVideo.video_url.label("note_url"),
            KuaishouVideo.video_cover_url.label("image_list"),
            KuaishouVideo.source_keyword.label("keyword")
        ]
    ),

    "wb": (
        WeiboNote,
        [
            WeiboNote.note_id.label("id"),
            sqlalchemy.literal("wb").label("platform"),
            WeiboNote.content.label("title"),
            WeiboNote.nickname.label("nickname"),
            WeiboNote.liked_count.label("liked_count"),
            WeiboNote.comments_count.label("comment_count"),
            WeiboNote.create_time.label("create_time"),
            WeiboNote.note_url.label("note_url"),
            sqlalchemy.literal("").label("image_list"),
            WeiboNote.source_keyword.label("keyword")
        ]
    ),

    "tieba": (
        TiebaNote,
        [
            TiebaNote.note_id.label("id"),
            sqlalchemy.literal("tieba").label("platform"),
            TiebaNote.title.label("title"),
            TiebaNote.user_nickname.label("nickname"),
            sqlalchemy.literal(0).label("liked_count"),
            TiebaNote.total_replay_num.label("comment_count"),
            TiebaNote.publish_time.label("create_time"),
            TiebaNote.note_url.label("note_url"),
            sqlalchemy.literal("").label("image_list"),
            TiebaNote.source_keyword.label("keyword")
        ]
    ),

    "zhihu": (
        ZhihuContent,
        [
            ZhihuContent.content_id.label("id"),
            sqlalchemy.literal("zhihu").label("platform"),
            ZhihuContent.title.label("title"),
            ZhihuContent.user_nickname.label("nickname"),
            ZhihuContent.voteup_count.label("liked_count"),
            ZhihuContent.comment_count.label("comment_count"),
            ZhihuContent.created_time.label("create_time"),
            ZhihuContent.content_url.label("note_url"),
            sqlalchemy.literal("").label("image_list"),
            ZhihuContent.source_keyword.label("keyword")
        ]
    ),
}


# 用于获取关键词的查询表
KEYWORD_TABLES = [
    XhsNote.source_keyword,
    DouyinAweme.source_keyword,
    BilibiliVideo.source_keyword,
    KuaishouVideo.source_keyword,
    WeiboNote.source_keyword,
    TiebaNote.source_keyword,
    ZhihuContent.source_keyword,
]