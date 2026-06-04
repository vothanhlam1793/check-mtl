import os
import tempfile
import shutil

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from app.schemas import ValidationResult, ErrorResponse, DifyExportResponse
from app.validator.engine import run_validation
from app.validator.word_export import export_word
from app.validator.word_export_pro import export_word_pro

router = APIRouter(prefix="/api/v1", tags=["validate"])

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "mtl_uploads")
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")


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


@router.post("/export-word")
async def export_word_file(
    file: UploadFile = File(...),
    reviewer_name: str = Form(""),
):
    """Upload & validate, then export BC THẨM ĐỊNH Word file."""
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
        output_path = export_word(tmp_path, original_name, reviewer_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Thiếu file template: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xuất Word: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    output_name = original_name.rsplit(".", 1)[0] + "_BC_THAM_DINH.docx"
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=output_name,
    )


@router.post("/export-word-pro")
async def export_word_pro_file(
    file: UploadFile = File(...),
    reviewer_name: str = Form(""),
):
    """Upload & validate, then export BC THẨM ĐỊNH (PRO — đầy đủ tất cả section kể cả OK)."""
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
        output_path = export_word_pro(tmp_path, original_name, reviewer_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Thiếu file template: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xuất Word: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    output_name = original_name.rsplit(".", 1)[0] + "_BC_THAM_DINH_PRO.docx"
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=output_name,
    )


@router.post("/export-word-dify", response_model=DifyExportResponse)
async def export_word_dify(
    file: UploadFile = File(...),
    reviewer_name: str = Form(""),
):
    """Upload, validate, export BC Thẩm Định Word → trả JSON có link download cho Dify Agent."""
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    original_name = file.filename
    token = os.urandom(6).hex()
    tmp_path = os.path.join(UPLOAD_DIR, f"tmp_{token}_{original_name}")
    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        file.file.close()

    try:
        validation_result = run_validation(tmp_path, original_name)
        output_path = export_word(tmp_path, original_name, reviewer_name)
        safe_name = original_name.rsplit(".", 1)[0].replace(" ", "_")
        output_name = safe_name + f"_BC_THAM_DINH_{token}.docx"
        dest = os.path.join(OUTPUTS_DIR, output_name)
        shutil.move(output_path, dest)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=f"Lỗi xuất Word: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    msgs = validation_result.messages
    return DifyExportResponse(
        status=validation_result.status,
        file_name=original_name,
        download_url=f"/outputs/{output_name}",
        download_filename=output_name,
        summary=validation_result.summary,
        user_message=msgs.user_message,
        status_hint=msgs.status_hint,
        next_actions=msgs.next_actions,
    )


@router.post("/export-word-pro-dify", response_model=DifyExportResponse)
async def export_word_pro_dify(
    file: UploadFile = File(...),
    reviewer_name: str = Form(""),
):
    """Upload, validate, export BC Thẩm Định PRO Word → trả JSON có link download cho Dify Agent."""
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    original_name = file.filename
    token = os.urandom(6).hex()
    tmp_path = os.path.join(UPLOAD_DIR, f"tmp_{token}_{original_name}")
    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        file.file.close()

    try:
        validation_result = run_validation(tmp_path, original_name)
        output_path = export_word_pro(tmp_path, original_name, reviewer_name)
        safe_name = original_name.rsplit(".", 1)[0].replace(" ", "_")
        output_name = safe_name + f"_BC_THAM_DINH_PRO_{token}.docx"
        dest = os.path.join(OUTPUTS_DIR, output_name)
        shutil.move(output_path, dest)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=f"Lỗi xuất Word: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    msgs = validation_result.messages
    return DifyExportResponse(
        status=validation_result.status,
        file_name=original_name,
        download_url=f"/outputs/{output_name}",
        download_filename=output_name,
        summary=validation_result.summary,
        user_message=msgs.user_message,
        status_hint=msgs.status_hint,
        next_actions=msgs.next_actions,
    )
