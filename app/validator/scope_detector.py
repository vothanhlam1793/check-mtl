import openpyxl
from typing import List, Set, Dict
from dataclasses import dataclass, field

from config import TemplateConfig, SCOPE_DATA_COL_START, SCOPE_DATA_COL_END


@dataclass
class ScopeInfo:
    scope_wbs: Set[str] = field(default_factory=set)
    scope_root: str = ""
    scope_label: str = ""
    rows_to_validate: Set[int] = field(default_factory=set)
    rows_mandatory_missing: Dict[int, str] = field(default_factory=dict)
    rows_skipped: int = 0
    total_data_rows: int = 0


def detect_scope(ws: openpyxl.worksheet.worksheet.Worksheet,
                 template: TemplateConfig,
                 header_row: int) -> ScopeInfo:
    """Step C: detect employee scope and bold-mandatory rows."""
    info = ScopeInfo()
    total_rows = 0
    seen_wbs_labels = []

    wbs_col = template.col_wbs
    task_col = template.col_task
    start_col = template.col_start
    finish_col = template.col_finish
    status_col = template.col_status
    notes_col = template.col_notes

    data_cols = [start_col, finish_col, status_col, notes_col]
    if template.has_predecessors:
        data_cols.append(template.col_predecessors)

    for row in ws.iter_rows(min_row=header_row + 1, max_col=max(data_cols) + 1):
        row_num = row[0].row
        wbs = row[wbs_col].value if wbs_col < len(row) else None
        wbs_str = str(wbs).strip() if wbs else ""

        has_any = any(cell.value is not None and str(cell.value).strip() != "" for cell in row)
        if not has_any and not wbs_str:
            continue
        total_rows += 1

        has_data = False
        for ci in data_cols:
            if ci < len(row) and row[ci].value is not None:
                has_data = True
                break

        is_bold = any(cell.font and cell.font.bold for cell in row)

        if has_data:
            info.rows_to_validate.add(row_num)
            if wbs_str:
                info.scope_wbs.add(wbs_str)
                task = row[task_col].value if task_col < len(row) else None
                if task:
                    seen_wbs_labels.append(f"{wbs_str} {str(task)[:50]}")
                else:
                    seen_wbs_labels.append(wbs_str)

        if is_bold and not has_data:
            task_val = row[task_col].value if task_col < len(row) else None
            label = f"{wbs_str} {str(task_val)[:40]}".strip() if task_val else wbs_str
            info.rows_mandatory_missing[row_num] = label

    info.total_data_rows = total_rows
    info.rows_skipped = total_rows - len(info.rows_to_validate) - len(info.rows_mandatory_missing)

    root = _extract_scope_root(info.scope_wbs)
    info.scope_root = root
    info.scope_label = " | ".join(seen_wbs_labels[:5])
    if len(seen_wbs_labels) > 5:
        info.scope_label += f" +{len(seen_wbs_labels) - 5} mục"

    return info


def _extract_scope_root(wbs_set: Set[str]) -> str:
    if not wbs_set:
        return ""
    parts_list = [w.split(".") for w in wbs_set if w]
    if not parts_list:
        return ""
    min_len = min(len(p) for p in parts_list)
    root_parts = []
    for i in range(min_len):
        level_parts = {p[i] for p in parts_list}
        if len(level_parts) == 1:
            root_parts.append(list(level_parts)[0])
        else:
            break
    return ".".join(root_parts) if root_parts else ""
