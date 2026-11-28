# Platform 策略看板

看板包含概览、组合总览、组合详情、市场数据、回测分析、回测对比和策略配置。Vue 负责展示和交互，FastAPI 复用现有 Python 数据读取与统计逻辑。图表按需加载 Plotly。界面标准见 [DESIGN.md](DESIGN.md)。

## 本地运行

使用项目 Python、Node.js 24 和 pnpm 11。在仓库根目录安装依赖并启动。

~~~powershell
.\env\Scripts\python.exe -m pip install -r requirements.txt
pnpm -C platform/dashboard_web install --frozen-lockfile
pnpm -C platform/dashboard_web build
.\env\Scripts\python.exe platform\scripts\run_dashboard.py
~~~

打开 [本地看板](http://127.0.0.1:8501/)。可通过环境变量 PORT 修改端口。点击「刷新数据」重新读取本地文件。

前端开发时，在一个终端用 Uvicorn 打开 API，在另一个终端启动 Vite。

~~~powershell
.\env\Scripts\python.exe -m uvicorn src.platform_dashboard.api:app --app-dir platform --host 127.0.0.1 --port 8765
pnpm -C platform/dashboard_web dev
~~~

现有 Docker Compose 配置在构建阶段打包前端，运行时由 Uvicorn 在 8501 提供 API 和静态文件。数据和结果使用现有只读挂载。
