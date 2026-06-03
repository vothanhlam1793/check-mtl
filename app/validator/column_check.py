import openpyxl
from typing import List

from app.validator.infer import InferredLayout


def check_columns(ws: openpyxl.worksheet.worksheet.Worksheet,
                  layout: InferredLayout) -> List[str]:
    """Step B: basic header validation — WBS must exist, all core fields detected."""
    errors = []

    hr = layout.header_row

    # Check WBS column exists
    wbs_val = str(ws.cell(row=hr, column=layout.wbs_col + 1).value or "").strip()
    if wbs_val.upper() != "WBS":
        errors.append(f"Cột A (vị trí {layout.wbs_col + 1}) không có tiêu đề 'WBS'")

    # Check task column
    task_val = str(ws.cell(row=hr, column=layout.task_col + 1).value or "").strip()
    if not task_val:
        errors.append(f"Cột {chr(65 + layout.task_col)} không có tiêu đề")

    # Check we have date columns
    if layout.start_col < 0 or layout.finish_col < 0:
        errors.append("Không phát hiện được cột ngày bắt đầu / ngày kết thúc")

    # Check status column
    if layout.status_col < 0:
        errors.append("Không phát hiện được cột trạng thái công việc")

    return errors
