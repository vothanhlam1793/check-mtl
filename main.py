import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router

app = FastAPI(
    title="MTL Validator API",
    description="Service kiểm tra file Excel MTL đúng chuẩn",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Serve static UI if exists
ui_path = os.path.join(os.path.dirname(__file__), "test-ui.html")
if os.path.exists(ui_path):
    @app.get("/")
    async def root():
        from fastapi.responses import FileResponse
        return FileResponse(ui_path, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
