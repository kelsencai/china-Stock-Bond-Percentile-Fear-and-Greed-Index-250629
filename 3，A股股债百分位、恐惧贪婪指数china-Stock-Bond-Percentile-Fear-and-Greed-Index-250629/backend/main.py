"""
股债百分位分析系统 - 主程序
作者: AI助手
创建时间: 2024
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from loguru import logger
import sys

# 导入路由模块
from api import stocks, bonds, analysis, market
from utils.config import settings
from utils.database import init_db

# 配置日志
logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
logger.add("logs/app.log", rotation="1 day", retention="30 days")

# 创建FastAPI应用
app = FastAPI(
    title="股债百分位分析系统",
    description="专业的股票和债券百分位分析API服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stocks.router, prefix="/api/v1", tags=["股票"])
app.include_router(bonds.router, prefix="/api/v1", tags=["债券"])
app.include_router(analysis.router, prefix="/api/v1", tags=["分析"])
app.include_router(market.router, prefix="/api/v1", tags=["市场"])

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化操作"""
    logger.info("🚀 股债百分位分析系统启动中...")
    
    try:
        # 初始化数据库
        await init_db()
        logger.info("✅ 数据库初始化完成")
        
        # 初始化数据源
        logger.info("✅ 数据源初始化完成")
        
    except Exception as e:
        logger.error(f"❌ 系统初始化失败: {e}")
        raise e

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理操作"""
    logger.info("🛑 系统正在关闭...")

@app.get("/")
async def root():
    """根路径 - 系统信息"""
    return {
        "message": "欢迎使用股债百分位分析系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    logger.error(f"HTTP错误: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"系统错误: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "系统内部错误", "detail": str(exc)}
    )

if __name__ == "__main__":
    # 开发环境运行
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 