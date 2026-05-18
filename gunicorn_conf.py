"""
Gunicorn 配置文件 — 多 Worker + Uvicorn Worker 类

用法：
  gunicorn llm_agent.main:app -c gunicorn_conf.py

或开发模式直接：
  uvicorn llm_agent.main:app --host 0.0.0.0 --port 8000

Worker 数量建议：CPU 核心数 * 2 + 1
- 4 核机器：9 workers
- 8 核机器：17 workers
- 也可以通过环境 WORKERS 覆盖
"""

import os
import multiprocessing

# 绑定地址
bind = os.getenv("BIND", "0.0.0.0:8000")

# Worker 数量：环境变量优先，否则 CPU*2+1
workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))

# 使用 uvicorn worker 类（支持 async）
worker_class = "uvicorn.workers.UvicornWorker"

# Worker 连接超时（秒）
timeout = 120

# 优雅关闭超时
graceful_timeout = 30

# 预加载应用（减少每个 worker 的启动时间，共享内存）
preload_app = True

# 每个 worker 处理的最大请求数后重启（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 日志
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# 进程名
proc_name = "llm-agent"


def post_fork(server, worker):
    """Worker fork 后重建独立的数据库连接池和 Redis 连接。

    preload_app=True 时，master 进程加载 app 后 fork 出 worker。
    fork 后子进程会继承父进程的 engine/连接池/Redis 连接，
    多个 worker 共享同一个连接池会导致连接复用冲突和数据损坏。
    此钩子在每个 worker fork 后立即重建独立的资源。
    """
    server.log.info(f"[worker {worker.pid}] 正在重建数据库和 Redis 连接...")

    # 重建数据库连接池
    from llm_agent.database import reinit_database
    reinit_database()

    # 重建 Redis 连接
    from llm_agent.redis_client import reinit_redis
    reinit_redis()

    server.log.info(f"[worker {worker.pid}] 资源重建完成")


def on_starting(server):
    """Master 进程启动时打印配置信息。"""
    server.log.info(f"启动 Gunicorn: workers={workers}, bind={bind}")


def worker_exit(server, worker):
    """Worker 退出时清理资源。"""
    from llm_agent.database import engine
    if engine is not None:
        try:
            engine.dispose()
        except Exception:
            pass
    server.log.info(f"[worker {worker.pid}] 已退出，资源已清理")
