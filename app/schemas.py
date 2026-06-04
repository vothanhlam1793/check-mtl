from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ErrorItem(BaseModel):
    row: int
    wbs: Optional[str] = None
    col: Optional[str] = None
    field: str
    received: Optional[str] = None
    reason: str
    severity: str
    fix: Optional[str] = None


class ErrorGroup(BaseModel):
    field: str
    count: int
    rows: List[int] = []
    sample_reason: str = ""
    sample_fix: str = ""
    severity: str = "ERROR"


class Messages(BaseModel):
    summary: str = ""
    status_hint: str = ""
    template_detected: str = ""
    next_actions: List[str] = []
    user_message: str = ""
    error_groups: List[ErrorGroup] = []


class WbsSection(BaseModel):
    wbs: str
    task_name: str = ""
    total_items: int = 0
    error_count: int = 0
    status: str = "OK"


class MetaInfo(BaseModel):
    data_sheet: str
    detected_scope_wbs: List[str] = []
    detected_scope_label: str = ""
    rows_scanned: int = 0
    rows_skipped: int = 0
    wbs_sections: List[WbsSection] = []


class CoverInfo(BaseModel):
    company_found: bool = True
    scale_filled: bool = True
    yc_filled: bool = True
    rev: int = 1
    adjustment_filled: bool = True


class Summary(BaseModel):
    total_errors: int = 0
    total_warnings: int = 0
    bold_mandatory_missing: int = 0
    data_errors: int = 0
    cover_errors: int = 0
    cover_warnings: int = 0


class ValidationResult(BaseModel):
    status: str
    file_name: str
    checked_at: str
    meta: MetaInfo
    summary: Summary
    errors: List[ErrorItem] = []
    messages: Messages = Messages()


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    code: str


class DifyExportResponse(BaseModel):
    status: str
    file_name: str
    download_url: str
    download_filename: str
    summary: Summary
    user_message: str = ""
    status_hint: str = ""
    next_actions: List[str] = []
