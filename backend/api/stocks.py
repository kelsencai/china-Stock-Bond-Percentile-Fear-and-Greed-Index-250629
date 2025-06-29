"""
股票相关API路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from loguru import logger
from ..services.percentile_service import percentile_service
from ..utils.config import COMMON_STOCKS

router = APIRouter()

@router.get("/stocks")
async def get_stock_list():
    """
    获取股票列表
    
    Returns:
        List: 常用股票列表
    """
    try:
        return {
            "stocks": COMMON_STOCKS,
            "count": len(COMMON_STOCKS),
            "description": "常用股票代码列表"
        }
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取股票列表失败")

@router.get("/stock/{symbol}/percentile")
async def get_stock_percentile(
    symbol: str,
    period: str = Query("1y", description="数据周期: 1y, 2y, 5y")
):
    """
    获取股票百分位
    
    Args:
        symbol: 股票代码 (如: 000001.SZ)
        period: 数据周期
        
    Returns:
        Dict: 股票百分位信息
    """
    try:
        logger.info(f"请求股票百分位: {symbol}, 周期: {period}")
        
        # 验证股票代码格式
        if not symbol or len(symbol) < 3:
            raise HTTPException(status_code=400, detail="股票代码格式不正确")
        
        # 获取百分位数据
        result = await percentile_service.get_stock_percentile(symbol, period)
        
        return {
            "success": True,
            "data": result,
            "message": "获取成功"
        }
        
    except ValueError as e:
        logger.warning(f"股票百分位计算失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取股票百分位失败: {e}")
        raise HTTPException(status_code=500, detail="获取股票百分位失败")

@router.get("/stocks/batch")
async def get_batch_stock_percentiles(
    symbols: str = Query(..., description="股票代码列表，用逗号分隔"),
    period: str = Query("1y", description="数据周期")
):
    """
    批量获取股票百分位
    
    Args:
        symbols: 股票代码列表，用逗号分隔
        period: 数据周期
        
    Returns:
        List: 股票百分位信息列表
    """
    try:
        # 解析股票代码列表
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        
        if not symbol_list:
            raise HTTPException(status_code=400, detail="请提供有效的股票代码")
        
        if len(symbol_list) > 20:
            raise HTTPException(status_code=400, detail="单次最多查询20只股票")
        
        results = []
        errors = []
        
        for symbol in symbol_list:
            try:
                result = await percentile_service.get_stock_percentile(symbol, period)
                results.append(result)
            except Exception as e:
                errors.append({"symbol": symbol, "error": str(e)})
        
        return {
            "success": True,
            "data": {
                "results": results,
                "errors": errors,
                "total": len(symbol_list),
                "success_count": len(results),
                "error_count": len(errors)
            },
            "message": f"批量查询完成，成功: {len(results)}, 失败: {len(errors)}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量获取股票百分位失败: {e}")
        raise HTTPException(status_code=500, detail="批量获取股票百分位失败")

@router.get("/stock/{symbol}/trend")
async def get_stock_trend(
    symbol: str,
    days: int = Query(30, description="趋势天数", ge=7, le=365)
):
    """
    获取股票趋势分析
    
    Args:
        symbol: 股票代码
        days: 趋势天数
        
    Returns:
        Dict: 趋势分析结果
    """
    try:
        logger.info(f"请求股票趋势分析: {symbol}, 天数: {days}")
        
        # 获取股票数据
        period = f"{days}d" if days <= 365 else "1y"
        result = await percentile_service.get_stock_percentile(symbol, period)
        
        # 分析趋势
        historical_data = result.get("historical_percentiles", [])
        
        if len(historical_data) < 7:
            raise HTTPException(status_code=400, detail="数据不足，无法分析趋势")
        
        # 计算趋势
        recent_percentiles = [item["percentile"] for item in historical_data[-7:]]
        trend = "上升" if recent_percentiles[-1] > recent_percentiles[0] else "下降"
        
        # 计算趋势强度
        trend_strength = abs(recent_percentiles[-1] - recent_percentiles[0])
        
        trend_analysis = {
            "trend": trend,
            "trend_strength": round(trend_strength, 2),
            "recent_percentiles": recent_percentiles,
            "current_percentile": result["percentile"],
            "recommendation": _generate_recommendation(result["percentile"], trend)
        }
        
        return {
            "success": True,
            "data": {
                **result,
                "trend_analysis": trend_analysis
            },
            "message": "趋势分析完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票趋势失败: {e}")
        raise HTTPException(status_code=500, detail="获取股票趋势失败")

def _generate_recommendation(percentile: float, trend: str) -> str:
    """生成投资建议"""
    if percentile > 80:
        if trend == "上升":
            return "高位继续上涨，注意风险，建议减仓"
        else:
            return "高位回落，注意风险，建议观望"
    elif percentile < 20:
        if trend == "上升":
            return "低位反弹，可能存在机会，建议关注"
        else:
            return "低位继续下跌，可能存在机会，建议分批建仓"
    else:
        if trend == "上升":
            return "正常区间上涨，可适度参与"
        else:
            return "正常区间下跌，可适度关注" 