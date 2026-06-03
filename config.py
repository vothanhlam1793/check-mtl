import re
from typing import Dict, Set, List, Optional
from dataclasses import dataclass, field


@dataclass
class TemplateConfig:
    name: str
    header_row_min: int = 1
    header_row_max: int = 6
    columns: Dict[str, str] = field(default_factory=dict)
    valid_statuses: Set[str] = field(default_factory=set)
    duration_pattern: re.Pattern = re.compile(r"^\d+\s*d$")
    date_format: str = "serial"        # "serial" | "datetime" | "string"
    col_wbs: int = 0
    col_task: int = 1
    col_duration: int = 2
    col_start: int = 3
    col_finish: int = 4
    col_status: int = 6       # G by default
    col_notes: int = 6
    has_predecessors: bool = False
    col_predecessors: int = 5


# ── Template A: NVLG-PMD.DN2-MTL-* (Phuoc Thien, Tai Tien, LA NGA) ──
TEMPLATE_A = TemplateConfig(
    name="TEMPLATE_A",
    header_row_min=3,
    header_row_max=6,
    columns={
        "A": "WBS",
        "B": "Tên công việc",
        "C": "Số ngày",
        "D": "Ngày bắt đầu",
        "E": "Ngày kết thúc",
        "F": "Predecessors",
        "G": "Trạng thái",
    },
    valid_statuses={"Hoàn thành", "Đang thực hiện", "Chờ thực hiện", "Đóng"},
    duration_pattern=re.compile(r"^\d+\s*days?$"),
    date_format="datetime",
    col_wbs=0, col_task=1, col_duration=2,
    col_start=3, col_finish=4,
    col_status=6, col_notes=6,
    has_predecessors=True, col_predecessors=5,
)

# ── Template B: NVW.HT.* + MTL-* + Morito (TROPICANA, Grand Mercure, HABANA) ──
TEMPLATE_B = TemplateConfig(
    name="TEMPLATE_B",
    header_row_min=1,
    header_row_max=3,
    columns={
        "A": "WBS",
        "B": "Hạng mục công việc",
        "C": "Số ngày",
        "D": "Ngày bắt đầu",
        "E": "Ngày hoàn thành",
        "F": "Trạng thái công việc",
        "G": "Ghi chú",
    },
    valid_statuses={"Đóng", "Hoàn thành", "Không thực hiện"},
    duration_pattern=re.compile(r"^\d+\s*d$"),
    date_format="serial",
    col_wbs=0, col_task=1, col_duration=2,
    col_start=3, col_finish=4,
    col_status=5, col_notes=6,
    has_predecessors=False,
)

ALL_TEMPLATES: List[TemplateConfig] = [TEMPLATE_A, TEMPLATE_B]

# Shared
WBS_PATTERN = re.compile(r"^\d+(\.\d+)*$")
COVER_SHEET_NAMES = {"Cover", "cover"}
TEMPLATE_SHEET_NAMES = {"Chi tiết MTL mẫu", "Chi ti?t MTL m?u"}

# Column indices for scope detection (D/E/F/G - start, finish, predecessors if any, status)
SCOPE_DATA_COL_START = 3
SCOPE_DATA_COL_END = 7
