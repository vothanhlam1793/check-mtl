from datetime import datetime, timedelta
from typing import List, Optional

from config import TemplateConfig, WBS_PATTERN
from app.schemas import ErrorItem

EXCEL_EPOCH = datetime(1899, 12, 30)
SENTINEL_DATE_SERIAL = 11403  # 1931-03-21 = "chưa xác định ngày kết thúc"
SENTINEL_DATE = datetime(1931, 3, 21)  # Same sentinel as datetime object

def _is_sentinel(value) -> bool:
    """Check if value is a sentinel/placeholder date (< year 2000 = not a real date)."""
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return int(value) == SENTINEL_DATE_SERIAL
    if isinstance(value, datetime):
        return value.year < 2000
    return False


def excel_serial_to_date(value, date_format: str = "serial") -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if date_format == "serial" and isinstance(value, (int, float)):
        try:
            if value < 1 or value > 100000:
                return None
            return EXCEL_EPOCH + timedelta(days=int(value))
        except Exception:
            return None
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
    if isinstance(value, (int, float)):
        try:
            return EXCEL_EPOCH + timedelta(days=int(value))
        except Exception:
            return None
    return None


def validate_row(row: tuple, row_num: int, template: TemplateConfig) -> List[ErrorItem]:
    """Step D: validate a single data row against the detected template."""
    errors = []
    col_map = {c: i for i, c in enumerate("ABCDEFGH")}

    def get_val(col_letter):
        idx = col_map.get(col_letter, 0)
        return row[idx].value if idx < len(row) else None

    def get_str(col_letter):
        v = get_val(col_letter)
        return str(v).strip() if v else ""

    wbs_str = get_str("A")

    # --- WBS (column A) ---
    if not wbs_str:
        errors.append(ErrorItem(
            row=row_num, wbs="(rỗng)", col="A", field="WBS",
            received="(trống)", reason="WBS bị trống — nếu đây là ghi chú thủ công thì có thể bỏ qua",
            severity="WARNING", fix="Điền mã WBS nếu là hạng mục chính thức, hoặc bỏ qua nếu là ghi chú"
        ))
    elif not WBS_PATTERN.match(wbs_str):
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col="A", field="WBS",
            received=wbs_str, reason="Sai định dạng WBS",
            severity="ERROR", fix="Định dạng: số phân cấp bởi dấu chấm (VD: 9.1)"
        ))

    # --- Task (column B) ---
    task_str = get_str("B")
    if not task_str:
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col="B", field=template.columns.get("B", "Tên công việc"),
            received="(trống)", reason="Tên công việc bị trống",
            severity="ERROR", fix="Điền tên đầu việc"
        ))

    # --- Duration (column C) ---
    dur_str = get_str("C")
    if dur_str and not template.duration_pattern.match(dur_str):
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col="C", field=template.columns.get("C", "Số ngày"),
            received=dur_str, reason="Sai định dạng số ngày",
            severity="ERROR", fix=f"Định dạng: '{template.duration_pattern.pattern}' (VD: '30 d' hoặc '30 days')"
        ))

    # --- Start date (column D) ---
    date_start_raw = get_val("D")
    is_sentinel_start = _is_sentinel(date_start_raw)
    dt_start = None if is_sentinel_start else excel_serial_to_date(date_start_raw, template.date_format)
    if date_start_raw is not None and not is_sentinel_start and dt_start is None:
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col="D", field=template.columns.get("D", "Ngày bắt đầu"),
            received=str(date_start_raw), reason="Ngày bắt đầu không hợp lệ",
            severity="ERROR", fix="Điền ngày đúng định dạng"
        ))

    # --- Finish date (column E) ---
    date_finish_raw = get_val("E")
    is_sentinel_finish = _is_sentinel(date_finish_raw)
    dt_finish = None if is_sentinel_finish else excel_serial_to_date(date_finish_raw, template.date_format)
    if date_finish_raw is not None and not is_sentinel_finish and dt_finish is None:
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col="E", field=template.columns.get("E", "Ngày kết thúc"),
            received=str(date_finish_raw), reason="Ngày kết thúc không hợp lệ",
            severity="ERROR", fix="Điền ngày đúng định dạng"
        ))

    # --- Date order ---
    if dt_start and dt_finish and dt_finish < dt_start:
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col="E", field=template.columns.get("E", "Ngày kết thúc"),
            received=dt_finish.strftime("%d/%m/%Y"),
            reason=f"Ngày kết thúc ({dt_finish.strftime('%d/%m/%Y')}) < Ngày bắt đầu ({dt_start.strftime('%d/%m/%Y')})",
            severity="ERROR", fix=f"Sửa ngày kết thúc >= {dt_start.strftime('%d/%m/%Y')}"
        ))

    # --- Status (template A: column G, template B: column F) ---
    status_col_letter = "G" if template.has_predecessors else "F"
    status_str = get_str(status_col_letter)
    if status_str and status_str not in template.valid_statuses:
        valid_list = ", ".join(sorted(template.valid_statuses))
        errors.append(ErrorItem(
            row=row_num, wbs=wbs_str, col=status_col_letter,
            field=template.columns.get(status_col_letter, "Trạng thái"),
            received=status_str, reason="Trạng thái không hợp lệ",
            severity="ERROR", fix=f"Chọn: {valid_list}, hoặc để trống"
        ))

    return errors
