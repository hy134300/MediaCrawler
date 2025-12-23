# file: store/base.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseStore(ABC):
    """
    所有平台数据存储实现的抽象基类 (接口)
    """

    @abstractmethod
    async def get_paginated_list(
            self,
            *,  # 使用*强制后面的参数为关键字参数，增加可读性
            keyword: Optional[str] = None,
            source_keyword: Optional[str] = None,
            sort_by: str = "liked_count",
            page: int = 1,
            page_size: int = 10
    ) -> Dict[str, Any]:
        """
        一个统一的、支持分页/筛选/排序的查询方法。

        返回一个字典，包含:
        {
            "total": <总记录数>,
            "list": [<查询到的数据列表>]
        }
        """
        pass

    # 你可以根据需要添加其他通用接口，例如:
    # @abstractmethod
    # async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
    #     pass