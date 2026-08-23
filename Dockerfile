# EmpathyLens — 可复现的评估环境
#
# 目的：让任何人在任何机器上都能复现这套评估管道的运行环境，不受本地 Python 版本、
# 系统库、依赖版本差异影响。这直接支撑项目 Sub-RQ 3（工具层：评估框架的可复用性）——
# "可复用" 不能只是声称，得能真的在别人机器上跑起来。
#
# 构建：docker build -t empathylens:latest .
# 校验：docker run --rm empathylens:latest            # 默认跑零成本校验
# 交互：docker run --rm -it empathylens:latest bash   # 进容器手动操作
#
# ⚠️ 关于 API 密钥：镜像里【不含】任何密钥，也不应该在构建时通过 ARG 传入
#    （ARG 会留在镜像层历史里，等于泄露）。需要真实调用时在运行时挂载 .env：
#      docker run --rm --env-file .env empathylens:latest make tier1
#    但请注意：容器里跑计费调用同样受 Tier 协议约束，不要在容器里绕过人工检查点。

FROM python:3.12-slim

# 系统层依赖：
#   - make：Makefile 命令入口
#   - git：部分工具链会查询版本信息
# 装完立刻清理 apt 缓存，避免镜像里留下无用的几十 MB。
RUN apt-get update && apt-get install -y --no-install-recommends \
        make \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先单独拷贝 requirements.txt 再装依赖，最后才拷贝源码——
# 这样只要依赖没变，改代码时 Docker 能复用已缓存的依赖层，重建快很多。
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 拷贝项目内容（.dockerignore 已排除 .venv / .env / .git 等）
COPY . .

# 不用 root 跑，符合容器安全惯例
RUN useradd --create-home --shell /bin/bash runner \
    && chown -R runner:runner /app
USER runner

# Python 行为调整：不写 .pyc、输出不缓冲（容器日志能实时看到）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 默认行为：跑零成本校验。刻意不设成任何会计费的命令。
CMD ["make", "validate"]
