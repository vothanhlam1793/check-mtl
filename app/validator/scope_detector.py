import openpyxl
from typing import List, Set, Dict
from dataclasses import dataclass, field

from app.validator.infer import InferredLayout


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
                 layout: InferredLayout) -> ScopeInfo:
    """Detect employee scope and bold-mandatory rows using inferred column layout."""
    info = ScopeInfo()
    total_rows = 0
    seen_wbs_labels = []

    # Data columns to check: start, finish, status (+ any between them)
    data_cols = sorted(set([
        layout.start_col, layout.finish_col,
        layout.status_col, layout.notes_col
    ]))
    # Also include duration column if it has non-formula values
    if layout.duration_col >= 0:
        data_cols.append(layout.duration_col)
    data_cols = sorted(set(c for c in data_cols if c >= 0))
    max_col = max(data_cols) + 1 if data_cols else 8

    for row in ws.iter_rows(min_row=layout.header_row + 1, max_col=max_col):
        row_num = row[0].row
        wbs = row[layout.wbs_col].value if layout.wbs_col < len(row) else None
        wbs_str = str(wbs).strip() if wbs else ""

        # Skip completely empty rows (no data, no WBS)
        has_any = any(cell.value is not None and str(cell.value).strip() != "" for cell in row)
        if not has_any and not wbs_str:
            continue
        total_rows += 1

        # Check if row has actual data in key columns (skip formula-only data)
        has_data = False
        for ci in data_cols:
            if ci < len(row) and row[ci].value is not None:
                raw = str(row[ci].value).strip()
                if raw and not raw.startswith("="):
                    has_data = True
                    break
            # Also consider non-formula datetime/numbers as data
            if ci < len(row) and row[ci].value is not None:
                v = row[ci].value
                if isinstance(v, (datetime, int, float)) and not (isinstance(v, (int, float)) and v < 2000):
                    has_data = True
                    break

        is_bold = any(cell.font and cell.font.bold for cell in row)

        if has_data:
            info.rows_to_validate.add(row_num)
            if wbs_str:
                info.scope_wbs.add(wbs_str)
                task = row[layout.task_col].value if layout.task_col < len(row) else None
                if task:
                    seen_wbs_labels.append(f"{wbs_str} {str(task)[:50]}")
                else:
                    seen_wbs_labels.append(wbs_str)

        if is_bold and not has_data:
            task_val = row[layout.task_col].value if layout.task_col < len(row) else None
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
