"""
市场概览相关API路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from loguru import logger
from ..services.percentile_service import percentile_service
from ..utils.config import COMMON_STOCKS, COMMON_BONDS

router = APIRouter()

@router.get("/market/overview")
async def get_market_overview():
    """
    获取市场概览
    
    Returns:
        Dict: 市场概览信息
    """
    try:
        logger.info("请求市场概览")
        
        # 获取市场概览数据
        result = await percentile_service.get_market_overview()
        
        return {
            "success": True,
            "data": result,
            "message": "获取成功"
        }
        
    except Exception as e:
        logger.error(f"获取市场概览失败: {e}")
        raise HTTPException(status_code=500, detail="获取市场概览失败")

@router.get("/market/summary")
async def get_market_summary():
    """
    获取市场摘要
    
    Returns:
        Dict: 市场摘要信息
    """
    try:
        logger.info("请求市场摘要")
        
        # 获取主要股票和债券的百分位
        stock_results = []
        bond_results = []
        
        # 获取主要股票百分位
        for symbol in COMMON_STOCKS[:5]:  # 只取前5只
            try:
                result = await percentile_service.get_stock_percentile(symbol, "1y")
                stock_results.append({
                    "symbol": symbol,
                    "percentile": result["percentile"],
                    "current_price": result["current_price"]
                })
            except Exception as e:
                logger.warning(f"获取股票 {symbol} 数据失败: {e}")
        
        # 获取主要债券百分位
        for symbol in COMMON_BONDS[:3]:  # 只取前3只
            try:
                result = await percentile_service.get_bond_percentile(symbol, "1y")
                bond_results.append({
                    "symbol": symbol,
                    "percentile": result["percentile"],
                    "current_yield": result["current_yield"]
                })
            except Exception as e:
                logger.warning(f"获取债券 {symbol} 数据失败: {e}")
        
        # 计算市场情绪
        stock_avg_percentile = sum(r["percentile"] for r in stock_results) / len(stock_results) if stock_results else 50
        bond_avg_percentile = sum(r["percentile"] for r in bond_results) / len(bond_results) if bond_results else 50
        
        # 生成市场情绪
        market_sentiment = _generate_market_sentiment(stock_avg_percentile, bond_avg_percentile)
        
        summary = {
            "stock_market": {
                "average_percentile": round(stock_avg_percentile, 2),
                "stocks": stock_results,
                "sentiment": _get_percentile_sentiment(stock_avg_percentile)
            },
            "bond_market": {
                "average_percentile": round(bond_avg_percentile, 2),
                "bonds": bond_results,
                "sentiment": _get_percentile_sentiment(bond_avg_percentile)
            },
            "overall_sentiment": market_sentiment,
            "last_update": "2024-01-01T00:00:00Z"
        }
        
        return {
            "success": True,
            "data": summary,
            "message": "获取成功"
        }
        
    except Exception as e:
        logger.error(f"获取市场摘要失败: {e}")
        raise HTTPException(status_code=500, detail="获取市场摘要失败")

@router.get("/market/heatmap")
async def get_market_heatmap():
    """
    获取市场热力图数据
    
    Returns:
        Dict: 热力图数据
    """
    try:
        logger.info("请求市场热力图")
        
        # 获取所有股票和债券的百分位数据
        all_data = []
        
        # 股票数据
        for symbol in COMMON_STOCKS:
            try:
                result = await percentile_service.get_stock_percentile(symbol, "1y")
                all_data.append({
                    "symbol": symbol,
                    "type": "stock",
                    "percentile": result["percentile"],
                    "value": result["current_price"]
                })
            except Exception as e:
                logger.warning(f"获取股票 {symbol} 数据失败: {e}")
        
        # 债券数据
        for symbol in COMMON_BONDS:
            try:
                result = await percentile_service.get_bond_percentile(symbol, "1y")
                all_data.append({
                    "symbol": symbol,
                    "type": "bond",
                    "percentile": result["percentile"],
                    "value": result["current_yield"]
                })
            except Exception as e:
                logger.warning(f"获取债券 {symbol} 数据失败: {e}")
        
        # 按百分位排序
        all_data.sort(key=lambda x: x["percentile"], reverse=True)
        
        # 生成热力图数据
        heatmap_data = {
            "high_percentile": [item for item in all_data if item["percentile"] > 80],
            "medium_percentile": [item for item in all_data if 20 <= item["percentile"] <= 80],
            "low_percentile": [item for item in all_data if item["percentile"] < 20],
            "all_data": all_data
        }
        
        return {
            "success": True,
            "data": heatmap_data,
            "message": "获取成功"
        }
        
    except Exception as e:
        logger.error(f"获取市场热力图失败: {e}")
        raise HTTPException(status_code=500, detail="获取市场热力图失败")

@router.get("/market/opportunities")
async def get_market_opportunities():
    """
    获取市场投资机会
    
    Returns:
        Dict: 投资机会信息
    """
    try:
        logger.info("请求市场投资机会")
        
        opportunities = {
            "stocks": [],
            "bonds": [],
            "summary": ""
        }
        
        # 寻找低百分位股票（可能存在机会）
        for symbol in COMMON_STOCKS:
            try:
                result = await percentile_service.get_stock_percentile(symbol, "1y")
                if result["percentile"] < 30:  # 低百分位
                    opportunities["stocks"].append({
                        "symbol": symbol,
                        "percentile": result["percentile"],
                        "current_price": result["current_price"],
                        "recommendation": "低位可能存在投资机会"
                    })
            except Exception as e:
                logger.warning(f"获取股票 {symbol} 数据失败: {e}")
        
        # 寻找高百分位债券（收益率高）
        for symbol in COMMON_BONDS:
            try:
                result = await percentile_service.get_bond_percentile(symbol, "1y")
                if result["percentile"] > 70:  # 高百分位（收益率高）
                    opportunities["bonds"].append({
                        "symbol": symbol,
                        "percentile": result["percentile"],
                        "current_yield": result["current_yield"],
                        "recommendation": "收益率较高，可考虑配置"
                    })
            except Exception as e:
                logger.warning(f"获取债券 {symbol} 数据失败: {e}")
        
        # 生成摘要
        stock_count = len(opportunities["stocks"])
        bond_count = len(opportunities["bonds"])
        
        if stock_count > 0 and bond_count > 0:
            opportunities["summary"] = f"发现 {stock_count} 只低位股票和 {bond_count} 只高收益债券"
        elif stock_count > 0:
            opportunities["summary"] = f"发现 {stock_count} 只低位股票"
        elif bond_count > 0:
            opportunities["summary"] = f"发现 {bond_count} 只高收益债券"
        else:
            opportunities["summary"] = "当前市场无明显投资机会"
        
        return {
            "success": True,
            "data": opportunities,
            "message": "获取成功"
        }
        
    except Exception as e:
        logger.error(f"获取市场投资机会失败: {e}")
        raise HTTPException(status_code=500, detail="获取市场投资机会失败")

def _generate_market_sentiment(stock_percentile: float, bond_percentile: float) -> str:
    """生成市场情绪"""
    if stock_percentile > 80 and bond_percentile > 80:
        return "市场整体处于高位，注意风险"
    elif stock_percentile < 20 and bond_percentile < 20:
        return "市场整体处于低位，可能存在机会"
    elif stock_percentile > 80:
        return "股票市场高位，债券市场正常"
    elif stock_percentile < 20:
        return "股票市场低位，可能存在机会"
    elif bond_percentile > 80:
        return "债券收益率高位，股票市场正常"
    elif bond_percentile < 20:
        return "债券收益率低位，股票市场正常"
    else:
        return "市场整体处于正常区间"

def _get_percentile_sentiment(percentile: float) -> str:
    """获取百分位情绪"""
    if percentile > 80:
        return "高位"
    elif percentile < 20:
        return "低位"
    else:
        return "正常" 