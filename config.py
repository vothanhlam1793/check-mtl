import re
from datetime import datetime, timedelta
from typing import Optional

# ── WBS detection ──
WBS_PATTERN = re.compile(r"^\d+(\.\d+)*$")

# ── Duration patterns (try in order) ──
DURATION_PATTERNS = [
    re.compile(r"^\d+\s*d$", re.IGNORECASE),       # "30 d", "30 D", "1 d"
    re.compile(r"^\d+\s*days?$", re.IGNORECASE),    # "30 days", "30 day"
]

# ── Status detection: any short text that looks like a status ──
KNOWN_STATUS_LIKE = {
    "đóng", "hoàn thành", "chờ thực hiện", "đang thực hiện",
    "không thực hiện", "đang thi công", "chưa bắt đầu",
    "chậm tiến độ", "done", "completed", "in progress",
    "pending", "cancelled"
}

# ── Sheet detection ──
COVER_SHEET_NAMES = {"cover"}
SKIP_SHEET_SUBSTRINGS = ["mẫu", "m?u", "sheet3", "trình", "trinh", "so sánh"]

# ── Sentinel dates ──
EXCEL_EPOCH = datetime(1899, 12, 30)
SENTINEL_DATE_SERIAL = 11403  # 1931-03-21

# ── Base columns we always expect ──
CORE_COL_COUNT = 7  # A-G minimum
