import os
import shutil
import copy
import re
from datetime import datetime
from typing import List, Optional
from collections import defaultdict

from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn

from app.schemas import ErrorItem
from app.validator.engine import run_validation

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "template-bc-tham-dinh.docx")


def _extract_project_info(file_name: str) -> dict:
    """Extract project info from filename pattern."""
    info = {
        "ten_du_an": "",
        "khu_vuc": "",
        "nhom_du_an": "",
    }

    fn_upper = file_name.upper()

    pt_match = re.search(r"PHUOC\s*THIEN\s*(\d+[A-Z]*)", fn_upper)
    tt_match = re.search(r"TAI\s*TIEN", fn_upper)
    ln_match = re.search(r"LA\s*NGA|KDT\s*LA\s*NGA", fn_upper)
    tro_match = re.search(r"TROPICANA", fn_upper)
    gm_match = re.search(r"GRAND\s*MERCURE", fn_upper)
    mor_match = re.search(r"MORITO|HO\s*TRAM", fn_upper)
    hl_match = re.search(r"HOANG\s*LONG", fn_upper)
    hab_match = re.search(r"HABANA", fn_upper)
    rmn_match = re.search(r"RMN", fn_upper)

    if pt_match:
        info["ten_du_an"] = f"Phước Thiền {pt_match.group(1)}"
    elif tt_match:
        info["ten_du_an"] = "Tài Tiến"
    elif ln_match:
        info["ten_du_an"] = "La Nga"
    elif tro_match:
        info["ten_du_an"] = "Tropicana"
    elif gm_match:
        info["ten_du_an"] = "Grand Mercure"
    elif mor_match:
        info["ten_du_an"] = "Morito Hồ Tràm"
    elif hl_match:
        info["ten_du_an"] = "Hoàng Long"
    elif hab_match:
        info["ten_du_an"] = "Habana Island"
    elif rmn_match:
        info["ten_du_an"] = "RMN"
    else:
        info["ten_du_an"] = file_name.rsplit(".", 1)[0][:50]

    area_map = {
        "PHUOC THIEN": "Đồng Nai 2",
        "TAI TIEN": "Đồng Nai 2",
        "LA NGA": "Đồng Nai 2",
        "TROPICANA": "Bà Rịa - Vũng Tàu",
        "GRAND MERCURE": "Bà Rịa - Vũng Tàu",
        "MORITO": "Bà Rịa - Vũng Tàu",
        "HO TRAM": "Bà Rịa - Vũng Tàu",
        "HOANG LONG": "Bà Rịa - Vũng Tàu",
        "HABANA": "Bà Rịa - Vũng Tàu",
        "RMN": "Bà Rịa - Vũng Tàu",
    }
    info["khu_vuc"] = ""
    for key, val in area_map.items():
        if key in fn_upper:
            info["khu_vuc"] = val
            break

    group_match = re.search(r'DN(\d+)', fn_upper)
    if group_match:
        info["nhom_du_an"] = group_match.group(1)

    return info


def _set_cell_text(cell, text: str, bold: bool = False, font_name: str = "Tahoma", font_size: float = 10):
    """Set cell text with formatting."""
    p = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
    p.clear()
    run = p.add_run(str(text))
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.font.bold = bold


def _add_row(table, cells_data: List[dict]):
    """Add a row at end of table and fill cells."""
    row = table.add_row()
    for ci, data in enumerate(cells_data):
        if ci < len(row.cells):
            _set_cell_text(
                row.cells[ci],
                data.get("text", ""),
                bold=data.get("bold", False)
            )


def _remove_rows_from(table, start_idx: int):
    """Remove all rows from start_idx onwards."""
    while len(table.rows) > start_idx:
        tr = table.rows[-1]._tr
        table._tbl.remove(tr)


def _build_cover_rows(cover_errors: List[ErrorItem]) -> List[List[dict]]:
    """Build table rows for Cover errors (Section A)."""
    rows = []
    crits = [e for e in cover_errors if e.severity == "CRITICAL"]
    warns = [e for e in cover_errors if e.severity == "WARNING"]

    if crits:
        for e in crits:
            rows.append([
                {"text": ""},
                {"text": ""},
                {"text": ""},
                {"text": f"{e.field}"},
                {"text": f"[NGHIÊM TRỌNG] {e.reason}"},
                {"text": ""},
                {"text": ""},
            ])
    if warns:
        for e in warns:
            rows.append([
                {"text": ""},
                {"text": ""},
                {"text": ""},
                {"text": f"{e.field}"},
                {"text": f"[Nhắc nhở] {e.reason}"},
                {"text": ""},
                {"text": ""},
            ])
    if not crits and not warns:
        rows.append([
            {"text": ""},
            {"text": ""},
            {"text": ""},
            {"text": "Thông tin dự án trên Cover"},
            {"text": "Đầy đủ, không có lỗi."},
            {"text": ""},
            {"text": ""},
        ])
    return rows


def _build_data_rows(errors: List[ErrorItem]) -> List[List[dict]]:
    """Build table rows for data errors (Section B), grouped by pattern."""
    data_errors = [e for e in errors if e.col != "Cover" and e.severity in ("CRITICAL", "ERROR", "WARNING")]
    if not data_errors:
        return [[
            {"text": ""}, {"text": ""}, {"text": ""},
            {"text": "Dữ liệu tiến độ"},
            {"text": "Không có lỗi dữ liệu."},
            {"text": ""}, {"text": ""},
        ]]

    sev_labels = {"CRITICAL": "[NGHIÊM TRỌNG]", "ERROR": "[Lỗi]", "WARNING": "[Nhắc nhở]"}

    pattern_groups = defaultdict(lambda: {"rows": [], "field": ""})
    for e in data_errors:
        key = (e.severity, e.reason[:60])
        pattern_groups[key]["rows"].append(e.row)
        pattern_groups[key]["field"] = e.field or ""

    rows = []
    for (sev, reason), group in sorted(pattern_groups.items()):
        row_list = group["rows"]
        field = group["field"]
        sev_label = sev_labels.get(sev, "")

        if len(row_list) > 5:
            rows.append([
                {"text": ""}, {"text": ""}, {"text": ""},
                {"text": f"{field} ({len(row_list)} dòng)"},
                {"text": f"{sev_label} {reason}"},
                {"text": ""}, {"text": ""},
            ])
            rows.append([
                {"text": ""}, {"text": ""}, {"text": ""},
                {"text": f"  Dòng: {row_list[0]}, {row_list[1]}, {row_list[2]}... đến {row_list[-1]}"},
                {"text": ""}, {"text": ""}, {"text": ""},
            ])
        else:
            for row_num in row_list:
                rows.append([
                    {"text": ""}, {"text": ""}, {"text": ""},
                    {"text": f"Dòng {row_num} — {field}"},
                    {"text": f"{sev_label} {reason}"},
                    {"text": ""}, {"text": ""},
                ])

    return rows


def export_word(file_path: str, original_filename: str, reviewer_name: str = "") -> str:
    """Export validation result to Word (.docx) using the BC THẨM ĐỊNH template.
    
    Returns path to the generated .docx file.
    """
    result = run_validation(file_path, original_filename)
    errors = result.errors

    cover_errors = [e for e in errors if e.col == "Cover"]
    data_errors = [e for e in errors if e.col != "Cover"]

    project_info = _extract_project_info(original_filename)

    # Copy template
    output_path = file_path.rsplit(".", 1)[0] + "_BC_THAM_DINH.docx"
    if os.path.exists(output_path):
        os.remove(output_path)
    shutil.copy2(TEMPLATE_PATH, output_path)

    doc = Document(output_path)

    # Fill header info
    header_map = {
        "Tên dự án": project_info.get("ten_du_an", ""),
        "Khu vực": project_info.get("khu_vuc", ""),
        "Nhóm dự án": project_info.get("nhom_du_an", ""),
    }

    rev_match = re.search(r'[Vv]er\s*(\d+)', original_filename)
    if rev_match:
        header_map["Lần thẩm định"] = rev_match.group(1)

    header_map["Ngày hoàn thành thẩm định"] = datetime.now().strftime("%d/%m/%Y")

    file_date_match = re.search(r'(\d{8})', original_filename)
    if file_date_match:
        try:
            dt = datetime.strptime(file_date_match.group(1), "%Y%m%d")
            header_map["Ngày yêu cầu thẩm định"] = dt.strftime("%d/%m/%Y")
        except ValueError:
            pass

    for p in doc.paragraphs:
        text = p.text.strip()
        for key, value in header_map.items():
            if text.startswith(key):
                for r in p.runs:
                    r.text = ""
                if p.runs:
                    p.runs[0].text = f"{key}\t: {value}"
                break

    # Build table rows
    table = doc.tables[0]

    # Keep rows 0 (header), 1 (Section A label)
    # Remove row 2 (template placeholder for Section A)
    # Insert cover rows after row 1
    # Keep Section B label
    # Remove template placeholder rows
    # Insert data rows

    cover_rows_data = _build_cover_rows(cover_errors)
    data_rows_data = _build_data_rows(data_errors)

    # Find Section A row (contains "A" in col 0)
    section_a_idx = None
    section_b_idx = None
    for ri, row in enumerate(table.rows):
        if ri == 0:
            continue
        text = row.cells[0].text.strip()
        if text == "A":
            section_a_idx = ri
        elif text == "B":
            section_b_idx = ri

    if section_a_idx is None:
        section_a_idx = 1
    if section_b_idx is None:
        section_b_idx = section_a_idx + len(cover_rows_data) + 2

    # Clear all existing data rows, keep header (row 0)
    _remove_rows_from(table, 1)

    # Add Section A row
    _add_row(table, [
        {"text": "A", "bold": True}, {"text": ""}, {"text": ""},
        {"text": "PHẦN CHUNG", "bold": True}, {"text": ""}, {"text": ""}, {"text": ""},
    ])

    # Add cover rows
    for row_data in cover_rows_data:
        _add_row(table, row_data)

    # Add Section B row
    _add_row(table, [
        {"text": "B", "bold": True}, {"text": ""}, {"text": ""},
        {"text": "CHI TIẾT", "bold": True}, {"text": ""}, {"text": ""}, {"text": ""},
    ])

    # Add data rows
    for row_data in data_rows_data:
        _add_row(table, row_data)

    # Set reviewer name if provided
    if reviewer_name:
        signoff_table = doc.tables[1] if len(doc.tables) > 1 else None
        if signoff_table:
            cell = signoff_table.rows[0].cells[0]
            if cell.paragraphs:
                p = cell.paragraphs[0]
                existing = p.text
                if "LẬP BÁO CÁO" in existing.upper():
                    for r in p.runs:
                        r.text = ""
                    if p.runs:
                        p.runs[0].text = f"LẬP BÁO CÁO (GMS)\n{reviewer_name}"

    doc.save(output_path)
    return output_path
