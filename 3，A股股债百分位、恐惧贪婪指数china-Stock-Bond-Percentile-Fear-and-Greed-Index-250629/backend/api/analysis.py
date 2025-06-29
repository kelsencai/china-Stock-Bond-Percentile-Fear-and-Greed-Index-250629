"""
分析相关API路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from loguru import logger
from ..services.percentile_service import percentile_service
from ..utils.config import COMMON_STOCKS, COMMON_BONDS

router = APIRouter()

@router.post("/analysis/compare")
async def compare_assets(
    symbols: List[str],
    asset_type: str = Query("stock", description="资产类型: stock, bond")
):
    """
    比较多个资产的百分位
    
    Args:
        symbols: 资产代码列表
        asset_type: 资产类型
        
    Returns:
        Dict: 比较结果
    """
    try:
        logger.info(f"请求资产比较: {symbols}, 类型: {asset_type}")
        
        if len(symbols) < 2:
            raise HTTPException(status_code=400, detail="至少需要2个资产进行比较")
        
        if len(symbols) > 10:
            raise HTTPException(status_code=400, detail="最多比较10个资产")
        
        results = []
        errors = []
        
        for symbol in symbols:
            try:
                if asset_type == "stock":
                    result = await percentile_service.get_stock_percentile(symbol, "1y")
                    results.append({
                        "symbol": symbol,
                        "type": "stock",
                        "percentile": result["percentile"],
                        "value": result["current_price"],
                        "statistics": result["statistics"]
                    })
                elif asset_type == "bond":
                    result = await percentile_service.get_bond_percentile(symbol, "1y")
                    results.append({
                        "symbol": symbol,
                        "type": "bond",
                        "percentile": result["percentile"],
                        "value": result["current_yield"],
                        "statistics": result["statistics"]
                    })
                else:
                    raise HTTPException(status_code=400, detail="不支持的资产类型")
                    
            except Exception as e:
                errors.append({"symbol": symbol, "error": str(e)})
        
        # 按百分位排序
        results.sort(key=lambda x: x["percentile"], reverse=True)
        
        # 计算统计信息
        percentiles = [r["percentile"] for r in results]
        avg_percentile = sum(percentiles) / len(percentiles)
        max_percentile = max(percentiles)
        min_percentile = min(percentiles)
        
        comparison = {
            "results": results,
            "errors": errors,
            "statistics": {
                "average_percentile": round(avg_percentile, 2),
                "max_percentile": round(max_percentile, 2),
                "min_percentile": round(min_percentile, 2),
                "range": round(max_percentile - min_percentile, 2)
            },
            "recommendations": _generate_comparison_recommendations(results)
        }
        
        return {
            "success": True,
            "data": comparison,
            "message": "比较分析完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"资产比较失败: {e}")
        raise HTTPException(status_code=500, detail="资产比较失败")

@router.get("/analysis/trend")
async def analyze_trend(
    symbol: str,
    asset_type: str = Query("stock", description="资产类型: stock, bond"),
    days: int = Query(30, description="分析天数", ge=7, le=365)
):
    """
    分析资产趋势
    
    Args:
        symbol: 资产代码
        asset_type: 资产类型
        days: 分析天数
        
    Returns:
        Dict: 趋势分析结果
    """
    try:
        logger.info(f"请求趋势分析: {symbol}, 类型: {asset_type}, 天数: {days}")
        
        # 获取资产数据
        if asset_type == "stock":
            result = await percentile_service.get_stock_percentile(symbol, f"{days}d")
        elif asset_type == "bond":
            result = await percentile_service.get_bond_percentile(symbol, f"{days}d")
        else:
            raise HTTPException(status_code=400, detail="不支持的资产类型")
        
        # 分析趋势
        historical_data = result.get("historical_percentiles", [])
        
        if len(historical_data) < 7:
            raise HTTPException(status_code=400, detail="数据不足，无法分析趋势")
        
        # 计算趋势指标
        percentiles = [item["percentile"] for item in historical_data]
        
        # 计算移动平均
        ma_7 = sum(percentiles[-7:]) / 7 if len(percentiles) >= 7 else sum(percentiles) / len(percentiles)
        ma_14 = sum(percentiles[-14:]) / 14 if len(percentiles) >= 14 else ma_7
        
        # 计算趋势强度
        trend_strength = abs(percentiles[-1] - percentiles[0])
        
        # 判断趋势方向
        if percentiles[-1] > percentiles[0]:
            trend_direction = "上升"
        elif percentiles[-1] < percentiles[0]:
            trend_direction = "下降"
        else:
            trend_direction = "横盘"
        
        # 计算波动率
        volatility = sum(abs(percentiles[i] - percentiles[i-1]) for i in range(1, len(percentiles))) / (len(percentiles) - 1)
        
        trend_analysis = {
            "symbol": symbol,
            "asset_type": asset_type,
            "current_percentile": result["percentile"],
            "trend_direction": trend_direction,
            "trend_strength": round(trend_strength, 2),
            "volatility": round(volatility, 2),
            "ma_7": round(ma_7, 2),
            "ma_14": round(ma_14, 2),
            "historical_percentiles": historical_data,
            "recommendation": _generate_trend_recommendation(
                result["percentile"], 
                trend_direction, 
                trend_strength,
                asset_type
            )
        }
        
        return {
            "success": True,
            "data": trend_analysis,
            "message": "趋势分析完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"趋势分析失败: {e}")
        raise HTTPException(status_code=500, detail="趋势分析失败")

@router.get("/analysis/correlation")
async def analyze_correlation(
    symbol1: str,
    symbol2: str,
    asset_type1: str = Query("stock", description="资产1类型"),
    asset_type2: str = Query("stock", description="资产2类型"),
    days: int = Query(90, description="分析天数", ge=30, le=365)
):
    """
    分析两个资产的相关性
    
    Args:
        symbol1: 资产1代码
        symbol2: 资产2代码
        asset_type1: 资产1类型
        asset_type2: 资产2类型
        days: 分析天数
        
    Returns:
        Dict: 相关性分析结果
    """
    try:
        logger.info(f"请求相关性分析: {symbol1} vs {symbol2}")
        
        # 获取两个资产的数据
        period = f"{days}d"
        
        if asset_type1 == "stock":
            data1 = await percentile_service.get_stock_percentile(symbol1, period)
        elif asset_type1 == "bond":
            data1 = await percentile_service.get_bond_percentile(symbol1, period)
        else:
            raise HTTPException(status_code=400, detail="不支持的资产类型1")
        
        if asset_type2 == "stock":
            data2 = await percentile_service.get_stock_percentile(symbol2, period)
        elif asset_type2 == "bond":
            data2 = await percentile_service.get_bond_percentile(symbol2, period)
        else:
            raise HTTPException(status_code=400, detail="不支持的资产类型2")
        
        # 计算相关性
        historical1 = data1.get("historical_percentiles", [])
        historical2 = data2.get("historical_percentiles", [])
        
        if len(historical1) < 10 or len(historical2) < 10:
            raise HTTPException(status_code=400, detail="数据不足，无法计算相关性")
        
        # 取相同长度的数据
        min_length = min(len(historical1), len(historical2))
        percentiles1 = [item["percentile"] for item in historical1[-min_length:]]
        percentiles2 = [item["percentile"] for item in historical2[-min_length:]]
        
        # 计算相关系数
        correlation = _calculate_correlation(percentiles1, percentiles2)
        
        correlation_analysis = {
            "asset1": {
                "symbol": symbol1,
                "type": asset_type1,
                "current_percentile": data1["percentile"]
            },
            "asset2": {
                "symbol": symbol2,
                "type": asset_type2,
                "current_percentile": data2["percentile"]
            },
            "correlation": round(correlation, 4),
            "correlation_strength": _get_correlation_strength(correlation),
            "interpretation": _interpret_correlation(correlation),
            "recommendation": _generate_correlation_recommendation(correlation)
        }
        
        return {
            "success": True,
            "data": correlation_analysis,
            "message": "相关性分析完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"相关性分析失败: {e}")
        raise HTTPException(status_code=500, detail="相关性分析失败")

def _generate_comparison_recommendations(results: List[Dict]) -> List[str]:
    """生成比较建议"""
    recommendations = []
    
    if not results:
        return recommendations
    
    # 找出最高和最低百分位的资产
    highest = max(results, key=lambda x: x["percentile"])
    lowest = min(results, key=lambda x: x["percentile"])
    
    if highest["percentile"] > 80:
        recommendations.append(f"{highest['symbol']} 处于高位，注意风险")
    
    if lowest["percentile"] < 20:
        recommendations.append(f"{lowest['symbol']} 处于低位，可能存在机会")
    
    # 计算差异
    diff = highest["percentile"] - lowest["percentile"]
    if diff > 50:
        recommendations.append("资产间差异较大，可考虑分散投资")
    
    return recommendations

def _generate_trend_recommendation(percentile: float, direction: str, strength: float, asset_type: str) -> str:
    """生成趋势建议"""
    if asset_type == "stock":
        if percentile > 80 and direction == "上升":
            return "股票处于高位且继续上涨，建议减仓"
        elif percentile < 20 and direction == "下降":
            return "股票处于低位且继续下跌，可考虑分批建仓"
        elif direction == "上升" and strength > 20:
            return "股票趋势强劲上涨，可适度参与"
        elif direction == "下降" and strength > 20:
            return "股票趋势强劲下跌，注意风险"
        else:
            return "股票趋势平稳，可适度关注"
    else:  # bond
        if percentile > 80 and direction == "上升":
            return "债券收益率高位上升，价格下跌，建议观望"
        elif percentile < 20 and direction == "下降":
            return "债券收益率低位下降，价格上涨，可考虑配置"
        else:
            return "债券趋势平稳，可适度关注"

def _calculate_correlation(x: List[float], y: List[float]) -> float:
    """计算相关系数"""
    if len(x) != len(y):
        return 0.0
    
    n = len(x)
    if n < 2:
        return 0.0
    
    # 计算均值
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    # 计算协方差和标准差
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denominator_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    denominator_y = sum((y[i] - mean_y) ** 2 for i in range(n))
    
    if denominator_x == 0 or denominator_y == 0:
        return 0.0
    
    correlation = numerator / (denominator_x * denominator_y) ** 0.5
    return max(-1.0, min(1.0, correlation))  # 限制在[-1, 1]范围内

def _get_correlation_strength(correlation: float) -> str:
    """获取相关性强度描述"""
    abs_corr = abs(correlation)
    if abs_corr >= 0.8:
        return "强相关"
    elif abs_corr >= 0.5:
        return "中等相关"
    elif abs_corr >= 0.3:
        return "弱相关"
    else:
        return "几乎无关"

def _interpret_correlation(correlation: float) -> str:
    """解释相关性"""
    if correlation > 0.8:
        return "两个资产高度正相关，走势基本一致"
    elif correlation > 0.5:
        return "两个资产正相关，走势较为一致"
    elif correlation > 0.3:
        return "两个资产弱正相关，走势有一定一致性"
    elif correlation > -0.3:
        return "两个资产几乎无关，走势独立"
    elif correlation > -0.5:
        return "两个资产弱负相关，走势有一定反向性"
    elif correlation > -0.8:
        return "两个资产负相关，走势较为反向"
    else:
        return "两个资产高度负相关，走势基本相反"

def _generate_correlation_recommendation(correlation: float) -> str:
    """生成相关性投资建议"""
    abs_corr = abs(correlation)
    if abs_corr > 0.8:
        return "相关性很高，不建议同时持有，可考虑分散投资"
    elif abs_corr > 0.5:
        return "相关性较高，可适度分散投资"
    elif abs_corr < 0.3:
        return "相关性较低，适合分散投资"
    else:
        return "相关性适中，可根据投资策略决定" 