import openpyxl
from typing import Tuple, Optional

from config import COVER_SHEET_NAMES, SKIP_SHEET_SUBSTRINGS
from app.validator.infer import infer_columns, InferredLayout


class FileCheckError(Exception):
    pass


def check_and_open_file(file_path: str) -> Tuple[openpyxl.Workbook, str, str, InferredLayout]:
    """Step A: open file, verify sheets, auto-infer column layout.
    Returns (workbook, data_sheet_name, cover_sheet_name, inferred_layout).
    """
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
    except Exception as e:
        raise FileCheckError(f"Không thể mở file. Lỗi: {e}")

    sheet_names = wb.sheetnames

    cover_sheet = None
    data_sheet_name = ""

    # Find Cover
    for name in sheet_names:
        if name.lower() in COVER_SHEET_NAMES or name.lower().startswith("cover"):
            cover_sheet = name
            break

    if not cover_sheet:
        wb.close()
        raise FileCheckError("Thiếu sheet 'Cover'. Sheet hiện có: " + ", ".join(sheet_names))

    # Find data sheet — skip Cover, template sheets, special sheets
    for name in sheet_names:
        ln = name.lower()
        if ln in COVER_SHEET_NAMES or ln.startswith("cover"):
            continue
        if any(skip in ln for skip in SKIP_SHEET_SUBSTRINGS):
            continue
        if ln == "sheet3":
            continue
        data_sheet_name = name
        break

    if not data_sheet_name:
        # Fallback: pick any non-Cover sheet
        for name in sheet_names:
            if name != cover_sheet:
                data_sheet_name = name
                break

    if not data_sheet_name:
        wb.close()
        raise FileCheckError("Không tìm thấy sheet dữ liệu. Sheet hiện có: " + ", ".join(sheet_names))

    ws = wb[data_sheet_name]

    # Auto-infer column layout
    layout = infer_columns(ws)
    if layout is None:
        wb.close()
        raise FileCheckError(
            f"Không thể xác định cấu trúc dữ liệu. "
            f"Cần có cột A='WBS' ở một trong các dòng 1-10 của sheet '{data_sheet_name}'."
        )

    layout.data_sheet_name = data_sheet_name

    return wb, data_sheet_name, cover_sheet, layout
