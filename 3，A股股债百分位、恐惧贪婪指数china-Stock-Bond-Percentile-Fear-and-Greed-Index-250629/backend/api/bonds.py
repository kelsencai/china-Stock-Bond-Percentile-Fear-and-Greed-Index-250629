"""
债券相关API路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from loguru import logger
from ..services.percentile_service import percentile_service
from ..utils.config import COMMON_BONDS

router = APIRouter()

@router.get("/bonds")
async def get_bond_list():
    """
    获取债券列表
    
    Returns:
        List: 常用债券列表
    """
    try:
        return {
            "bonds": COMMON_BONDS,
            "count": len(COMMON_BONDS),
            "description": "常用债券代码列表"
        }
    except Exception as e:
        logger.error(f"获取债券列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取债券列表失败")

@router.get("/bond/{symbol}/percentile")
async def get_bond_percentile(
    symbol: str,
    period: str = Query("1y", description="数据周期: 1y, 2y, 5y")
):
    """
    获取债券百分位
    
    Args:
        symbol: 债券代码
        period: 数据周期
        
    Returns:
        Dict: 债券百分位信息
    """
    try:
        logger.info(f"请求债券百分位: {symbol}, 周期: {period}")
        
        # 验证债券代码格式
        if not symbol or len(symbol) < 3:
            raise HTTPException(status_code=400, detail="债券代码格式不正确")
        
        # 获取百分位数据
        result = await percentile_service.get_bond_percentile(symbol, period)
        
        return {
            "success": True,
            "data": result,
            "message": "获取成功"
        }
        
    except ValueError as e:
        logger.warning(f"债券百分位计算失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取债券百分位失败: {e}")
        raise HTTPException(status_code=500, detail="获取债券百分位失败")

@router.get("/bonds/batch")
async def get_batch_bond_percentiles(
    symbols: str = Query(..., description="债券代码列表，用逗号分隔"),
    period: str = Query("1y", description="数据周期")
):
    """
    批量获取债券百分位
    
    Args:
        symbols: 债券代码列表，用逗号分隔
        period: 数据周期
        
    Returns:
        List: 债券百分位信息列表
    """
    try:
        # 解析债券代码列表
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        
        if not symbol_list:
            raise HTTPException(status_code=400, detail="请提供有效的债券代码")
        
        if len(symbol_list) > 10:
            raise HTTPException(status_code=400, detail="单次最多查询10只债券")
        
        results = []
        errors = []
        
        for symbol in symbol_list:
            try:
                result = await percentile_service.get_bond_percentile(symbol, period)
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
        logger.error(f"批量获取债券百分位失败: {e}")
        raise HTTPException(status_code=500, detail="批量获取债券百分位失败")

@router.get("/bond/{symbol}/trend")
async def get_bond_trend(
    symbol: str,
    days: int = Query(30, description="趋势天数", ge=7, le=365)
):
    """
    获取债券趋势分析
    
    Args:
        symbol: 债券代码
        days: 趋势天数
        
    Returns:
        Dict: 趋势分析结果
    """
    try:
        logger.info(f"请求债券趋势分析: {symbol}, 天数: {days}")
        
        # 获取债券数据
        period = f"{days}d" if days <= 365 else "1y"
        result = await percentile_service.get_bond_percentile(symbol, period)
        
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
            "recommendation": _generate_bond_recommendation(result["percentile"], trend)
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
        logger.error(f"获取债券趋势失败: {e}")
        raise HTTPException(status_code=500, detail="获取债券趋势失败")

def _generate_bond_recommendation(percentile: float, trend: str) -> str:
    """生成债券投资建议"""
    if percentile > 80:
        if trend == "上升":
            return "收益率处于高位且继续上升，债券价格下跌，建议观望"
        else:
            return "收益率处于高位但开始回落，债券价格可能反弹，可适度关注"
    elif percentile < 20:
        if trend == "上升":
            return "收益率处于低位且开始上升，债券价格可能下跌，注意风险"
        else:
            return "收益率处于低位且继续下降，债券价格上涨，可适度配置"
    else:
        if trend == "上升":
            return "收益率正常区间上升，债券价格下跌，可适度减仓"
        else:
            return "收益率正常区间下降，债券价格上涨，可适度增仓" 