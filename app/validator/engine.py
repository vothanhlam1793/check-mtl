from datetime import datetime
from typing import List
from collections import defaultdict

from app.schemas import ValidationResult, ErrorItem, MetaInfo, Summary, Messages, ErrorGroup, WbsSection
from app.validator.file_check import check_and_open_file, FileCheckError
from app.validator.column_check import check_columns
from app.validator.cover_check import check_cover
from app.validator.scope_detector import detect_scope
from app.validator.data_check import validate_row


def _build_messages(errors: List[ErrorItem], file_name: str, layout, total_rows: int) -> Messages:
    """Generate rich, agent-friendly messages from validation results."""

    crits = [e for e in errors if e.severity == "CRITICAL"]
    errs = [e for e in errors if e.severity == "ERROR"]
    warns = [e for e in errors if e.severity == "WARNING"]

    groups = defaultdict(lambda: {"rows": [], "reason": "", "fix": "", "severity": ""})
    for e in errors:
        key = f"{e.severity}|{e.field}"
        groups[key]["rows"].append(e.row)
        groups[key]["reason"] = e.reason
        groups[key]["fix"] = e.fix or ""
        groups[key]["severity"] = e.severity

    error_groups = []
    for key, g in groups.items():
        sev, field = key.split("|", 1)
        error_groups.append(ErrorGroup(
            field=field, count=len(g["rows"]),
            rows=sorted(g["rows"])[:10],
            sample_reason=g["reason"], sample_fix=g["fix"], severity=sev
        ))

    if crits:
        status_hint = "BLOCKED"
    elif errs:
        status_hint = "FAIL_NEED_FIX"
    elif warns:
        status_hint = "PASS_WITH_NOTES"
    else:
        status_hint = "PASS_CLEAN"

    parts = [f"File `{file_name}`. Đã quét {total_rows} dòng có dữ liệu."]
    if crits:
        parts.append(f"**{len(crits)} lỗi NGHIÊM TRỌNG** — bắt buộc sửa ngay.")
    if errs:
        parts.append(f"**{len(errs)} lỗi** cần sửa trước khi nộp lại.")
    if warns:
        parts.append(f"{len(warns)} cảnh báo — có thể bỏ qua nếu là ghi chú.")
    if not crits and not errs and not warns:
        parts.append("Không phát hiện lỗi nào.")

    summary = " ".join(parts)

    next_actions = []
    if crits:
        fields = {e.field for e in crits}
        next_actions.append(f"YEU CAU GAP: sửa {len(crits)} lỗi CRITICAL ở: {', '.join(fields)}")
    if errs:
        for g in error_groups:
            if g.severity == "ERROR":
                next_actions.append(f"Sửa {g.count} lỗi ở `{g.field}` — dòng {g.rows[:3]}{'...' if len(g.rows) > 3 else ''}")
    if warns:
        next_actions.append(f"Xem xét {len(warns)} cảnh báo — có thể bỏ qua nếu là ghi chú thủ công")
    if not crits and not errs:
        if warns:
            next_actions.append("File đạt chuẩn. Có thể chuyển sang bước đối chiếu tiến độ.")
        else:
            next_actions.append("File hoàn hảo. Chuyển sang bước đối chiếu tiến độ.")

    user_lines = []
    cover_crits = [e for e in errors if e.col == "Cover" and e.severity == "CRITICAL"]
    cover_warns = [e for e in errors if e.col == "Cover" and e.severity == "WARNING"]
    data_crits = [e for e in errors if e.col != "Cover" and e.severity == "CRITICAL"]
    data_errs = [e for e in errors if e.col != "Cover" and e.severity == "ERROR"]
    data_warns = [e for e in errors if e.col != "Cover" and e.severity == "WARNING"]

    if cover_crits:
        user_lines.append("LOI COVER:")
        for e in cover_crits:
            user_lines.append(f"  [CRITICAL] {e.reason}")
    if cover_warns:
        if not cover_crits:
            user_lines.append("LUU Y COVER:")
        for e in cover_warns:
            user_lines.append(f"  [WARNING] {e.reason}")

    if status_hint == "PASS_CLEAN":
        user_lines.append(f"File `{file_name}` đã đạt chuẩn. Không có lỗi nào.")
    elif status_hint == "PASS_WITH_NOTES":
        if data_warns:
            user_lines.append(f"File `{file_name}` đạt chuẩn, có {len(data_warns)} lưu ý nhỏ:")
        else:
            user_lines.append(f"File `{file_name}` đạt chuẩn với {len(cover_warns)} lưu ý về Cover.")
        for g in error_groups:
            if g.severity == "WARNING" and g.field not in ("Tên công ty", "Quy mô dự án", "Yêu cầu chung", "Điều chỉnh số", "Ngày trên Cover"):
                user_lines.append(f"  - {g.count} dòng: {g.sample_reason}. Nếu là ghi chú thì bỏ qua.")
    else:
        user_lines.append(f"File `{file_name}` cần sửa {len(crits) + len(errs)} lỗi:")
        if cover_crits or cover_warns:
            user_lines.append("")
        for g in error_groups:
            if g.severity in ("CRITICAL", "ERROR"):
                cover_fields = ["Tên công ty", "Quy mô dự án", "Yêu cầu chung", "Điều chỉnh số", "Ngày trên Cover"]
                if g.field in cover_fields:
                    continue
                user_lines.append(f"  [{g.severity}] {g.field} ({g.count} dòng): {g.sample_reason}")
                if g.sample_fix:
                    user_lines.append(f"      Cach sua: {g.sample_fix}")
        user_lines.append("")
        user_lines.append("Vui long sua cac loi tren va gui lai file.")

    user_message = "\n".join(user_lines)

    return Messages(
        summary=summary,
        status_hint=status_hint,
        next_actions=next_actions,
        user_message=user_message,
        error_groups=error_groups
    )


def run_validation(file_path: str, original_filename: str = "") -> ValidationResult:
    errors: List[ErrorItem] = []
    bold_missing_count = 0

    try:
        wb, data_sheet_name, cover_sheet_name, layout = check_and_open_file(file_path)
    except FileCheckError as e:
        return ValidationResult(
            status="error",
            file_name=original_filename or file_path,
            checked_at=datetime.now().isoformat(),
            meta=MetaInfo(data_sheet="", rows_scanned=0, rows_skipped=0),
            summary=Summary(),
            errors=[ErrorItem(row=0, col=None, field="FILE", received="N/A", reason=str(e), severity="CRITICAL")]
        )

    cover_errors: List[ErrorItem] = []
    if cover_sheet_name and cover_sheet_name in wb.sheetnames:
        cover_ws = wb[cover_sheet_name]
        cover_errors = check_cover(cover_ws, original_filename or "")
    errors.extend(cover_errors)

    ws = wb[data_sheet_name]

    col_errors = check_columns(ws, layout)
    for msg in col_errors:
        errors.append(ErrorItem(
            row=layout.header_row, col="Header", field="Cấu trúc",
            received="", reason=msg, severity="CRITICAL",
            fix="Kiểm tra lại cấu trúc file"
        ))
    if col_errors:
        wb.close()
        cover_errors_count = len([e for e in cover_errors if e.severity in ("CRITICAL", "ERROR")])
        cover_warnings_count = len([e for e in cover_errors if e.severity == "WARNING"])
        meta = MetaInfo(data_sheet=data_sheet_name)
        return ValidationResult(
            status="fail", file_name=original_filename,
            checked_at=datetime.now().isoformat(),
            meta=meta, summary=Summary(
                total_errors=len(errors), data_errors=len(errors),
                cover_errors=cover_errors_count, cover_warnings=cover_warnings_count
            ),
            errors=errors
        )

    scope_info = detect_scope(ws, layout)

    for row_num, label in scope_info.rows_mandatory_missing.items():
        errors.append(ErrorItem(
            row=row_num, wbs=label, col=None, field="Toàn bộ dòng",
            received="(trống)",
            reason=f"Hạng mục BOLD bắt buộc báo cáo nhưng chưa điền: {label}",
            severity="CRITICAL", fix="Điền ngày và trạng thái"
        ))
    bold_missing_count = len(scope_info.rows_mandatory_missing)

    data_error_count = 0
    max_col = max(layout.wbs_col, layout.task_col, layout.duration_col,
                  layout.start_col, layout.finish_col, layout.status_col, layout.notes_col) + 1

    for row_num in sorted(scope_info.rows_to_validate):
        row_data = tuple(ws.cell(row=row_num, column=c + 1) for c in range(max_col))
        row_errors = validate_row(row_data, row_num, layout)
        if row_errors:
            errors.extend(row_errors)
            data_error_count += len([e for e in row_errors if e.severity == "ERROR"])

    # Build WBS sections summary (for word_export_pro & section view)
    section_items = {}  # sec -> {"items": [(row_num, wbs, task)], "task_name": ""}
    for r in range(layout.header_row + 1, ws.max_row + 1):
        wbs_v = ws.cell(row=r, column=layout.wbs_col + 1).value
        task_v = ws.cell(row=r, column=layout.task_col + 1).value
        if wbs_v is not None and str(wbs_v).strip():
            wbs_str = str(wbs_v).strip()
            task_str = str(task_v).strip() if task_v else ""
            parts = wbs_str.split(".")
            if len(parts) >= 2:
                sec = f"{parts[0]}.{parts[1]}"
            else:
                sec = parts[0]
            if sec not in section_items:
                section_items[sec] = {"items": [], "task_name": ""}
            section_items[sec]["items"].append((r, wbs_str, task_str))
            if wbs_str == sec and task_str and not section_items[sec]["task_name"]:
                section_items[sec]["task_name"] = task_str

    for sec, sis in section_items.items():
        if not sis["task_name"]:
            for _, _, task in sis["items"]:
                if task:
                    sis["task_name"] = task
                    break

    error_by_row = defaultdict(int)
    for e in errors:
        if e.row > 0:
            error_by_row[e.row] += 1

    wbs_sections = []
    for sec in sorted(section_items.keys(),
                       key=lambda x: (int(x.split(".")[0]) if x.split(".")[0].isdigit() else 999,
                                      int(x.split(".")[1]) if "." in x and x.split(".")[1].isdigit() else 0)):
        sis = section_items[sec]
        total = len(sis["items"])
        err_cnt = sum(error_by_row.get(r, 0) for r, _, _ in sis["items"])
        wbs_sections.append(WbsSection(
            wbs=sec,
            task_name=sis["task_name"],
            total_items=total,
            error_count=err_cnt,
            status="HAS_ERRORS" if err_cnt > 0 else "OK"
        ))

    wb.close()

    total_errors = len(errors)
    critical_and_errors = len([e for e in errors if e.severity in ("CRITICAL", "ERROR")])
    total_warnings = len([e for e in errors if e.severity == "WARNING"])
    cover_errors_count = len([e for e in cover_errors if e.severity in ("CRITICAL", "ERROR")])
    cover_warnings_count = len([e for e in cover_errors if e.severity == "WARNING"])
    status = "pass" if critical_and_errors == 0 else "fail"

    meta = MetaInfo(
        data_sheet=data_sheet_name,
        detected_scope_wbs=sorted(scope_info.scope_wbs)[:20],
        detected_scope_label=scope_info.scope_label,
        rows_scanned=len(scope_info.rows_to_validate),
        rows_skipped=scope_info.rows_skipped,
        wbs_sections=wbs_sections
    )

    messages = _build_messages(errors, original_filename, layout, scope_info.total_data_rows)

    return ValidationResult(
        status=status, file_name=original_filename,
        checked_at=datetime.now().isoformat(),
        meta=meta,
        summary=Summary(
            total_errors=total_errors,
            total_warnings=total_warnings,
            bold_mandatory_missing=bold_missing_count,
            data_errors=data_error_count,
            cover_errors=cover_errors_count,
            cover_warnings=cover_warnings_count
        ),
        errors=errors,
        messages=messages
    )
