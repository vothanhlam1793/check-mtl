import os
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# ── Serve OpenAPI spec cho Dify import ──
OPENAPI_PATH = os.path.join(BASE_DIR, "openapi.yaml")
if os.path.exists(OPENAPI_PATH):
    @app.get("/dify/openapi.json", include_in_schema=False)
    async def dify_openapi_json():
        with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)
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


# ── Serve static UI if exists ──
ui_path = os.path.join(BASE_DIR, "test-ui.html")
if os.path.exists(ui_path):
    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(ui_path, media_type="text/html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
