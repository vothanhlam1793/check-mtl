import os
import tempfile
import shutil

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from app.schemas import ValidationResult, ErrorResponse
from app.validator.engine import run_validation

router = APIRouter(prefix="/api/v1", tags=["validate"])

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "mtl_uploads")


@router.post("/validate", response_model=ValidationResult)
async def validate_file(
    file: UploadFile = File(...),
    employee_id: str = Form(""),
):
    """Upload and validate an MTL Excel file."""
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    original_name = file.filename
    tmp_path = os.path.join(UPLOAD_DIR, f"tmp_{os.urandom(8).hex()}_{original_name}")
    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        file.file.close()

    try:
        result = run_validation(tmp_path, original_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return result


@router.get("/health")
async def health():
    return {"status": "ok", "service": "mtl-validator"}
