import os
import yaml
import copy
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from app.api import router

app = FastAPI(
    title="MTL Validator API",
    description="Service kiểm tra file Excel MTL đúng chuẩn — tự động nhận diện cấu trúc, kiểm tra Cover + dữ liệu tiến độ. Tích hợp với Dify Agent.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

BASE_DIR = os.path.dirname(__file__)

OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")


def _resolve_base_url(request: Request) -> str:
    env_url = os.getenv("API_BASE_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")
    host = request.headers.get("host", "localhost:8000")
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme or "http")
    return f"{scheme}://{host}"


# ── Serve OpenAPI spec cho Dify import (auto-inject server URL) ──
OPENAPI_PATH = os.path.join(BASE_DIR, "openapi.yaml")
if os.path.exists(OPENAPI_PATH):
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        _OPENAPI_SPEC = yaml.safe_load(f)

    @app.get("/dify/openapi.json", include_in_schema=False)
    async def dify_openapi_json(request: Request):
        spec = copy.deepcopy(_OPENAPI_SPEC)
        base_url = _resolve_base_url(request)
        spec["servers"] = [{"url": base_url, "description": "Auto-detected server"}]
        return spec

    @app.get("/dify/openapi.yaml", include_in_schema=False)
    async def dify_openapi_yaml():
        return FileResponse(OPENAPI_PATH, media_type="application/x-yaml")


# ── Serve Swagger UI dùng spec tuỳ chỉnh ──
SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>MTL Validator API - Swagger</title>
  <meta charset="utf-8"/>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"/>
  <style>body { margin: 0; } .topbar { display: none; }</style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({
      url: "/dify/openapi.json",
      dom_id: "#swagger-ui",
      presets: [SwaggerUIBundle.presets.apis],
      layout: "BaseLayout",
      deepLinking: true
    });
  </script>
</body>
</html>"""

@app.get("/api-docs", include_in_schema=False)
async def custom_swagger():
    return HTMLResponse(SWAGGER_HTML)


# ── Serve báo cáo quản lý (business report) ──
REPORT_PATH = os.path.join(BASE_DIR, "report-management.html")
if os.path.exists(REPORT_PATH):
    @app.get("/report", include_in_schema=False)
    async def management_report():
        return FileResponse(REPORT_PATH, media_type="text/html")


# ── Serve GMS Tools (upload + export Word) ──
GMS_TOOLS_PATH = os.path.join(BASE_DIR, "gms-tools.html")
if os.path.exists(GMS_TOOLS_PATH):
    @app.get("/gms-tools", include_in_schema=False)
    async def gms_tools():
        return FileResponse(GMS_TOOLS_PATH, media_type="text/html")


# ── Serve GMS Tools PRO (full WBS section view + export) ──
GMS_TOOLS_PRO_PATH = os.path.join(BASE_DIR, "gms-tools-pro.html")
if os.path.exists(GMS_TOOLS_PRO_PATH):
    @app.get("/gms-tools-pro", include_in_schema=False)
    async def gms_tools_pro():
        return FileResponse(GMS_TOOLS_PRO_PATH, media_type="text/html")


# ── Serve static UI if exists ──
ui_path = os.path.join(BASE_DIR, "test-ui.html")
if os.path.exists(ui_path):
    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(ui_path, media_type="text/html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
