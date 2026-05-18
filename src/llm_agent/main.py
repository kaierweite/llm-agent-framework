import os
import sys
import logging
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from llm_agent.config import settings
from llm_agent.database import init_database, create_tables, seed_admin
import llm_agent.models  # noqa: F401 — 注册所有 ORM 模型到 Base.metadata
import llm_agent.services.admin_service  # noqa: F401 — 注册 _SystemSetting 到 Base.metadata
from llm_agent.api.auth import router as auth_router
from llm_agent.api.chat import router as chat_router
from llm_agent.api.knowledge import router as knowledge_router
from llm_agent.api.admin import router as admin_router
from llm_agent.api.user import router as user_router
from llm_agent.api.skill import router as skill_router
from llm_agent.api.kb_share import router as kb_share_router
from llm_agent.api.department import router as department_router
from llm_agent.middleware.rate_limiter import RateLimiterMiddleware
from llm_agent.middleware.request_logger import RequestLoggerMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database(settings.database_url)
    create_tables()
    seed_admin()

    # 启动时清理过期审计日志（保留 90 天）
    from llm_agent.database import SessionLocal
    from llm_agent.services.audit_service import cleanup_old_logs
    try:
        db = SessionLocal()
        deleted = cleanup_old_logs(db, keep_days=90)
        if deleted > 0:
            logging.info(f"[AUDIT] 清理过期审计日志: 删除 {deleted} 条（保留 90 天）")
        db.close()
    except Exception as e:
        logging.warning(f"[AUDIT] 审计日志清理失败: {e}")

    yield


app = FastAPI(
    title="企业知识库问答系统",
    version="1.0.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"[GLOBAL_EXC] {request.method} {request.url.path} → {type(exc).__name__}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal error: {type(exc).__name__}: {str(exc)}"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件：记录所有 API 请求的 trace_id、耗时、脱敏后的请求体
app.add_middleware(RequestLoggerMiddleware)

# 限流中间件：优先 Redis，降级为进程内令牌桶
_redis_url = getattr(settings, "redis_url", None)
app.add_middleware(RateLimiterMiddleware, redis_url=_redis_url)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(knowledge_router)
app.include_router(admin_router)
app.include_router(user_router)
app.include_router(skill_router)
app.include_router(kb_share_router)
app.include_router(department_router)
