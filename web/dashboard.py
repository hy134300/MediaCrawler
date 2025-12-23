from fastapi import APIRouter, Query, HTTPException
from services.analysis import AnalysisService # 导入我们刚创建的服务

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
service = AnalysisService() # 实例化服务

@router.get("/stats")
async def get_stats(
    keyword: str = Query(..., description="分析的源关键词"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD")
):
    """
    获取核心统计卡片数据
    """
    try:
        data = await service.get_stats(keyword, start_date, end_date)
        return {"code": 0, "message": "获取成功", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析统计数据失败: {e}")

@router.get("/hot-related-words")
async def get_hot_related_words(
    keyword: str = Query(..., description="分析的源关键词"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD")
):
    """
    获取词云图数据
    """
    try:
        data = await service.get_hot_related_words(keyword, start_date, end_date)
        return {"code": 0, "message": "获取成功", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析词云图数据失败: {e}")

@router.get("/trends")
async def get_trends(
    keyword: str = Query(..., description="分析的源关键词"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD")
):
    """
    获取折线图趋势数据
    """
    try:
        data = await service.get_trends(keyword, start_date, end_date)
        return {"code": 0, "message": "获取成功", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析趋势数据失败: {e}")
