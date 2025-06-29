"""
百分位计算服务
核心业务逻辑：计算股票和债券的百分位
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf
import akshare as ak
from loguru import logger
from ..utils.config import settings

class PercentileService:
    """百分位计算服务类"""
    
    def __init__(self):
        self.window = settings.PERCENTILE_WINDOW
        self.min_data_points = settings.MIN_DATA_POINTS
    
    async def get_stock_percentile(self, symbol: str, period: str = "1y") -> Dict:
        """
        获取股票百分位
        
        Args:
            symbol: 股票代码 (如: 000001.SZ)
            period: 数据周期 (如: 1y, 2y, 5y)
            
        Returns:
            Dict: 包含百分位信息的字典
        """
        try:
            logger.info(f"开始计算股票 {symbol} 的百分位")
            
            # 获取股票数据
            stock_data = await self._get_stock_data(symbol, period)
            
            if stock_data is None or len(stock_data) < self.min_data_points:
                raise ValueError(f"股票 {symbol} 数据不足，无法计算百分位")
            
            # 计算百分位
            current_price = stock_data['Close'].iloc[-1]
            percentile = self._calculate_percentile(stock_data['Close'], current_price)
            
            # 计算历史百分位序列
            historical_percentiles = self._calculate_historical_percentiles(stock_data['Close'])
            
            # 获取统计信息
            stats = self._calculate_statistics(stock_data['Close'])
            
            result = {
                "symbol": symbol,
                "current_price": round(current_price, 2),
                "percentile": round(percentile, 2),
                "period": period,
                "data_points": len(stock_data),
                "last_update": datetime.now().isoformat(),
                "statistics": stats,
                "historical_percentiles": historical_percentiles.tail(30).to_dict('records')  # 最近30天
            }
            
            logger.info(f"股票 {symbol} 百分位计算完成: {percentile:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"计算股票 {symbol} 百分位失败: {e}")
            raise e
    
    async def get_bond_percentile(self, symbol: str, period: str = "1y") -> Dict:
        """
        获取债券百分位
        
        Args:
            symbol: 债券代码
            period: 数据周期
            
        Returns:
            Dict: 包含百分位信息的字典
        """
        try:
            logger.info(f"开始计算债券 {symbol} 的百分位")
            
            # 获取债券数据
            bond_data = await self._get_bond_data(symbol, period)
            
            if bond_data is None or len(bond_data) < self.min_data_points:
                raise ValueError(f"债券 {symbol} 数据不足，无法计算百分位")
            
            # 债券使用收益率计算百分位
            current_yield = bond_data['yield'].iloc[-1]
            percentile = self._calculate_percentile(bond_data['yield'], current_yield)
            
            # 计算历史百分位序列
            historical_percentiles = self._calculate_historical_percentiles(bond_data['yield'])
            
            # 获取统计信息
            stats = self._calculate_statistics(bond_data['yield'])
            
            result = {
                "symbol": symbol,
                "current_yield": round(current_yield, 4),
                "percentile": round(percentile, 2),
                "period": period,
                "data_points": len(bond_data),
                "last_update": datetime.now().isoformat(),
                "statistics": stats,
                "historical_percentiles": historical_percentiles.tail(30).to_dict('records')
            }
            
            logger.info(f"债券 {symbol} 百分位计算完成: {percentile:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"计算债券 {symbol} 百分位失败: {e}")
            raise e
    
    async def get_market_overview(self) -> Dict:
        """
        获取市场概览
        
        Returns:
            Dict: 市场概览信息
        """
        try:
            logger.info("开始计算市场概览")
            
            # 获取主要指数数据
            indices = ["^GSPC", "^IXIC", "^DJI", "000300.SS", "000001.SS"]
            market_data = {}
            
            for index in indices:
                try:
                    data = await self._get_stock_data(index, "1y")
                    if data is not None and len(data) > 0:
                        current_price = data['Close'].iloc[-1]
                        percentile = self._calculate_percentile(data['Close'], current_price)
                        market_data[index] = {
                            "current_price": round(current_price, 2),
                            "percentile": round(percentile, 2)
                        }
                except Exception as e:
                    logger.warning(f"获取指数 {index} 数据失败: {e}")
            
            result = {
                "market_data": market_data,
                "last_update": datetime.now().isoformat(),
                "summary": self._generate_market_summary(market_data)
            }
            
            logger.info("市场概览计算完成")
            return result
            
        except Exception as e:
            logger.error(f"计算市场概览失败: {e}")
            raise e
    
    async def _get_stock_data(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """获取股票数据"""
        try:
            # 尝试使用yfinance获取数据
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                # 如果yfinance没有数据，尝试使用akshare
                if symbol.endswith('.SZ') or symbol.endswith('.SH'):
                    # 转换代码格式
                    ak_symbol = symbol.replace('.SZ', '').replace('.SH', '')
                    data = ak.stock_zh_a_hist(symbol=ak_symbol, period="daily", adjust="qfq")
                    if not data.empty:
                        data = data.rename(columns={
                            '日期': 'Date',
                            '开盘': 'Open',
                            '收盘': 'Close',
                            '最高': 'High',
                            '最低': 'Low',
                            '成交量': 'Volume'
                        })
                        data['Date'] = pd.to_datetime(data['Date'])
                        data.set_index('Date', inplace=True)
            
            return data if not data.empty else None
            
        except Exception as e:
            logger.error(f"获取股票数据失败 {symbol}: {e}")
            return None
    
    async def _get_bond_data(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """获取债券数据"""
        try:
            # 使用akshare获取债券数据
            data = ak.bond_zh_us_rate()
            
            # 这里需要根据具体的债券代码进行数据获取
            # 暂时返回模拟数据
            dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
            yields = np.random.normal(3.5, 0.5, 252)  # 模拟收益率数据
            
            data = pd.DataFrame({
                'Date': dates,
                'yield': yields
            })
            data.set_index('Date', inplace=True)
            
            return data
            
        except Exception as e:
            logger.error(f"获取债券数据失败 {symbol}: {e}")
            return None
    
    def _calculate_percentile(self, series: pd.Series, value: float) -> float:
        """计算百分位"""
        try:
            # 使用滚动窗口计算百分位
            if len(series) >= self.window:
                recent_data = series.tail(self.window)
            else:
                recent_data = series
            
            # 计算百分位
            percentile = (recent_data < value).mean() * 100
            return percentile
            
        except Exception as e:
            logger.error(f"计算百分位失败: {e}")
            return 50.0  # 返回中位数
    
    def _calculate_historical_percentiles(self, series: pd.Series) -> pd.Series:
        """计算历史百分位序列"""
        try:
            percentiles = []
            dates = []
            
            for i in range(self.window, len(series)):
                window_data = series.iloc[i-self.window:i]
                current_value = series.iloc[i]
                percentile = (window_data < current_value).mean() * 100
                percentiles.append(percentile)
                dates.append(series.index[i])
            
            return pd.Series(percentiles, index=dates)
            
        except Exception as e:
            logger.error(f"计算历史百分位失败: {e}")
            return pd.Series()
    
    def _calculate_statistics(self, series: pd.Series) -> Dict:
        """计算统计信息"""
        try:
            return {
                "mean": round(series.mean(), 2),
                "median": round(series.median(), 2),
                "std": round(series.std(), 2),
                "min": round(series.min(), 2),
                "max": round(series.max(), 2),
                "q25": round(series.quantile(0.25), 2),
                "q75": round(series.quantile(0.75), 2)
            }
        except Exception as e:
            logger.error(f"计算统计信息失败: {e}")
            return {}
    
    def _generate_market_summary(self, market_data: Dict) -> str:
        """生成市场摘要"""
        try:
            if not market_data:
                return "暂无市场数据"
            
            avg_percentile = np.mean([data['percentile'] for data in market_data.values()])
            
            if avg_percentile > 80:
                return "市场处于高位，注意风险"
            elif avg_percentile < 20:
                return "市场处于低位，可能存在机会"
            else:
                return "市场处于正常区间"
                
        except Exception as e:
            logger.error(f"生成市场摘要失败: {e}")
            return "市场数据异常"

# 创建全局服务实例
percentile_service = PercentileService() 