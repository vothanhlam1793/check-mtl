from datetime import datetime, timedelta
from typing import List, Optional

from config import WBS_PATTERN, DURATION_PATTERNS, EXCEL_EPOCH
from app.validator.infer import InferredLayout
from app.schemas import ErrorItem


def excel_serial_to_date(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return EXCEL_EPOCH + timedelta(days=int(value))
        except Exception:
            return None
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
    return None


def _is_sentinel(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return int(value) < 2000
    if isinstance(value, datetime):
        return value.year < 2000
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(value.strip(), fmt)
                if dt.year < 2000:
                    return True
            except ValueError:
                continue
    return False


def validate_row(row: tuple, row_num: int, layout: InferredLayout) -> List[ErrorItem]:
    """Validate a single data row using inferred column layout."""
    errors = []

    def get_val(col_idx):
        return row[col_idx].value if 0 <= col_idx < len(row) else None

    def get_str(col_idx):
        v = get_val(col_idx)
        return str(v).strip() if v else ""

    col_letters = "ABCDEFGHIJKLMNOP"

    wbs_str = get_str(layout.wbs_col)
    wbs_letter = col_letters[layout.wbs_col] if layout.wbs_col < len(col_letters) else "?"

    # ── WBS ──
    if not wbs_str:
        errors.append(ErrorItem(
            row=row_num, wbs="(rỗng)", col=wbs_letter, field="WBS",
            received="(trống)", reason="WBS bị trống — nếu là ghi chú thủ công thì có thể bỏ qua",
            severity="WARNING", fix="Điền mã WBS nếu là hạng mục chính thức"
        ))
    elif not WBS_PATTERN.match(wbs_str):
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col=wbs_letter, field="WBS",
            received=wbs_str, reason="Sai định dạng WBS",
            severity="ERROR", fix="Định dạng: số phân cấp bởi dấu chấm (VD: 9.1)"
        ))

    # ── Task name ──
    task_str = get_str(layout.task_col)
    task_letter = col_letters[layout.task_col] if layout.task_col < len(col_letters) else "?"
    if not task_str:
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col=task_letter, field="Tên công việc",
            received="(trống)", reason="Tên công việc bị trống",
            severity="ERROR", fix="Điền tên công việc"
        ))

    # ── Duration ──
    dur_str = get_str(layout.duration_col)
    dur_letter = col_letters[layout.duration_col] if layout.duration_col < len(col_letters) else "?"
    if dur_str and not dur_str.startswith("="):
        ok = any(pat.match(dur_str) for pat in DURATION_PATTERNS)
        if not ok:
            try:
                float(dur_str)  # Accept any positive number as raw duration
                ok = True
            except ValueError:
                pass
        if not ok:
            errors.append(ErrorItem(
                row=row_num, wbs=wbs_str, col=dur_letter, field="Thời lượng",
                received=dur_str, reason="Sai định dạng thời lượng",
                severity="ERROR", fix="Định dạng: '30 d' hoặc '30 days'"
            ))

    # ── Start date ──
    start_raw = get_val(layout.start_col)
    start_letter = col_letters[layout.start_col] if layout.start_col < len(col_letters) else "?"
    if isinstance(start_raw, str) and start_raw.startswith("="):
        start_raw = None
    is_sentinel_start = _is_sentinel(start_raw)
    dt_start = None if is_sentinel_start else excel_serial_to_date(start_raw)
    if start_raw is not None and not is_sentinel_start and dt_start is None:
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col=start_letter, field="Ngày bắt đầu",
            received=str(start_raw)[:30], reason="Ngày bắt đầu không hợp lệ",
            severity="ERROR", fix="Điền ngày đúng định dạng"
        ))

    # ── Finish date ──
    finish_raw = get_val(layout.finish_col)
    finish_letter = col_letters[layout.finish_col] if layout.finish_col < len(col_letters) else "?"
    if isinstance(finish_raw, str) and finish_raw.startswith("="):
        finish_raw = None
    is_sentinel_finish = _is_sentinel(finish_raw)
    dt_finish = None if is_sentinel_finish else excel_serial_to_date(finish_raw)
    if finish_raw is not None and not is_sentinel_finish and dt_finish is None:
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col=finish_letter, field="Ngày kết thúc",
            received=str(finish_raw)[:30], reason="Ngày kết thúc không hợp lệ",
            severity="ERROR", fix="Điền ngày đúng định dạng"
        ))

    # ── Date order ──
    if dt_start and dt_finish and dt_finish < dt_start:
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col=finish_letter, field="Ngày kết thúc",
            received=dt_finish.strftime("%d/%m/%Y"),
            reason=f"Ngày kết thúc ({dt_finish.strftime('%d/%m/%Y')}) < Ngày bắt đầu ({dt_start.strftime('%d/%m/%Y')})",
            severity="ERROR", fix=f"Sửa ngày kết thúc >= {dt_start.strftime('%d/%m/%Y')}"
        ))

    # ── Status ──
    status_str = get_str(layout.status_col)
    status_letter = col_letters[layout.status_col] if layout.status_col < len(col_letters) else "?"
    if status_str and layout.sample_statuses:
        if status_str not in layout.sample_statuses:
            # Accept any reasonable status text that's not too long
            if len(status_str) > 50:
                errors.append(ErrorItem(
                    row=row_num, wbs=wbs_str, col=status_letter, field="Trạng thái",
                    received=status_str[:30], reason="Trạng thái quá dài, có thể là ghi chú nhầm cột",
                    severity="WARNING", fix="Nhập trạng thái ngắn gọn hoặc để trống"
                ))

    return errors
