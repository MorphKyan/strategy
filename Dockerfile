FROM node:24-bookworm-slim AS dashboard-build

WORKDIR /dashboard
RUN npm install --global pnpm@11.25.0
COPY platform/dashboard_web/package.json platform/dashboard_web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY platform/dashboard_web ./
RUN pnpm build

FROM python:3.11-slim

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends tzdata fonts-wqy-zenhei \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo Asia/Shanghai > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
COPY platform /app/platform
COPY --from=dashboard-build /dashboard/dist /app/platform/dashboard_web/dist
WORKDIR /app/platform
EXPOSE 8501
CMD ["python", "-m", "uvicorn", "src.platform_dashboard.api:app", "--host", "0.0.0.0", "--port", "8501"]
