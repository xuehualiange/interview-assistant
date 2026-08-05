# 多 Agent 协作求职助手 — 后端 Docker 镜像
#
# 为什么用 python:3.11-slim 而不是 alpine：
# 1. 兼容性：slim 基于 Debian glibc，绝大多数 Python 轮子（wheel）直接可用；
#    alpine 使用 musl libc，部分含 C 扩展的包（如 numpy、cryptography）需源码编译或根本不支持
# 2. 构建速度：slim 预编译 wheel 多，pip install 更快；alpine 常触发 gcc/musl-dev 编译链
# 3. 调试友好：Debian 系工具链成熟，容器内排查问题更方便
# 4. 体积权衡：alpine 镜像更小，但 langchain / sqlalchemy 等依赖装完后差距不大；
#    slim 在「体积 vs 兼容性」上更适合 Python AI 项目

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装依赖（先复制 requirements.txt 利用 Docker 层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 创建数据目录（SQLite 持久化）与非 root 用户
RUN mkdir -p /app/data \
    && useradd --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

# 暴露 FastAPI 端口
EXPOSE 8000

# 健康检查：配合 docker-compose healthcheck 与 /health 接口
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# 启动 FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
