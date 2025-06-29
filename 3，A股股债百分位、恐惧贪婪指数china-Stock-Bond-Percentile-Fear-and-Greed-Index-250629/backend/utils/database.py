"""
数据库配置和初始化
"""

import os
import sqlite3
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from loguru import logger
from .config import settings

# 创建数据库目录
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 创建SQLAlchemy引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

async def init_db():
    """初始化数据库"""
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
        
        # 初始化基础数据
        await init_basic_data()
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise e

async def init_basic_data():
    """初始化基础数据"""
    try:
        db = SessionLocal()
        
        # 这里可以添加一些基础数据的初始化
        # 比如常用股票列表、行业分类等
        
        db.close()
        logger.info("基础数据初始化完成")
        
    except Exception as e:
        logger.error(f"基础数据初始化失败: {e}")
        raise e

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 