"""
配置文件
管理系统的所有配置参数
"""

import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    """系统配置类"""
    
    # 应用配置
    APP_NAME: str = "股债百分位分析系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/market_data.db"
    
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "股债百分位分析系统"
    
    # 数据源配置
    YAHOO_FINANCE_TIMEOUT: int = 30
    TUSHARE_TOKEN: Optional[str] = None
    AKSHARE_TIMEOUT: int = 30
    
    # 百分位计算配置
    PERCENTILE_WINDOW: int = 252  # 一年交易日
    MIN_DATA_POINTS: int = 60     # 最少数据点
    
    # 缓存配置
    CACHE_TTL: int = 3600  # 1小时
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8天
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局配置实例
settings = Settings()

# 常用股票代码列表
COMMON_STOCKS = [
    "000001.SZ",  # 平安银行
    "000002.SZ",  # 万科A
    "000858.SZ",  # 五粮液
    "002415.SZ",  # 海康威视
    "600000.SH",  # 浦发银行
    "600036.SH",  # 招商银行
    "600519.SH",  # 贵州茅台
    "600887.SH",  # 伊利股份
    "000858.SZ",  # 五粮液
    "002594.SZ",  # 比亚迪
]

# 常用债券代码列表
COMMON_BONDS = [
    "019654.SH",  # 国债
    "019668.SH",  # 国债
    "019669.SH",  # 国债
    "019670.SH",  # 国债
    "019671.SH",  # 国债
]

# 行业分类
INDUSTRY_SECTORS = {
    "金融": ["银行", "保险", "证券"],
    "消费": ["食品饮料", "家用电器", "汽车"],
    "科技": ["计算机", "电子", "通信"],
    "医药": ["医药生物"],
    "能源": ["石油石化", "煤炭", "电力"],
    "地产": ["房地产"],
    "制造": ["机械设备", "化工", "钢铁"],
} 