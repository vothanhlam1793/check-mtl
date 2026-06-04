"""LLM renderer — tóm tắt lỗi thành nhận xét thẩm định tiếng Việt."""

import json
from typing import List, Optional
from collections import defaultdict

from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _client


def _build_prompt(section_label: str, error_summaries: List[str]) -> tuple:
    system = (
        "Bạn là chuyên viên GMS thẩm định tiến độ dự án. "
        "Viết nhận xét bằng tiếng Việt, chuyên nghiệp, NGẮN GỌN (2-3 câu). "
        "Nội dung phải rõ ràng, có thể hành động được. "
        "Ví dụ: 'Bổ sung tiến độ các đầu mục con tối thiểu theo email hướng dẫn của GMS ngày 16/01/2026' "
        "hoặc 'Điều chỉnh tiến độ hoàn thành theo vòng đời dự án' "
        "Không thêm lời chào. Không dùng ký tự đặc biệt."
    )
    items_text = "\n".join(f"  - {s}" for s in error_summaries)
    user = (
        f"Hạng mục: {section_label}\n"
        f"Kết quả kiểm tra:\n{items_text}\n"
        f"Viết nhận xét thẩm định ngắn gọn cho hạng mục này."
    )
    return system, user


def summarize_section(section_label: str, errors: List[dict]) -> str:
    """Gọi LLM viết nhận xét cho một section WBS.

    Args:
        section_label: Tên section (VD: "1.1 PLP")
        errors: List of {"wbs": str, "task": str, "severity": str, "reason": str, "received": str}

    Returns:
        Chuỗi nhận xét tiếng Việt 2-3 câu.
    """
    # Gom nhóm để dễ đọc
    groups = defaultdict(lambda: {"count": 0, "severity": "", "sample_wbs": [], "sample_received": ""})
    for e in errors:
        key = e.get("reason", "")[:80]
        groups[key]["count"] += 1
        groups[key]["severity"] = e.get("severity", "")
        if len(groups[key]["sample_wbs"]) < 3:
            groups[key]["sample_wbs"].append(e.get("wbs", "?"))
        if not groups[key]["sample_received"]:
            groups[key]["sample_received"] = e.get("received", "")

    summaries = []
    for reason, g in sorted(groups.items()):
        sev = g["severity"]
        cnt = g["count"]
        wbs_list = ", ".join(g["sample_wbs"])
        received = g["sample_received"]
        line = ""
        if received:
            line += f"Giá trị '{received}' — "
        line += reason
        if cnt > 1:
            line += f" ({cnt} mục, VD: {wbs_list})"
        else:
            line += f" (mục: {wbs_list})"
        summaries.append(line)

    system, user = _build_prompt(section_label, summaries)

    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        text = resp.choices[0].message.content.strip()
        if text:
            return text
    except Exception:
        pass

    return _fallback_summary(errors)


def _fallback_summary(errors: List[dict]) -> str:
    """Fallback: tóm tắt bằng text pattern (không LLM)."""
    sev_counts = defaultdict(int)
    reasons = []
    for e in errors:
        sev_counts[e.get("severity", "?")] += 1
        r = e.get("reason", "")[:60]
        if r not in reasons:
            reasons.append(r)

    parts = []
    if sev_counts.get("CRITICAL"):
        parts.append(f"{sev_counts['CRITICAL']} lỗi NGHIÊM TRỌNG")
    if sev_counts.get("ERROR"):
        parts.append(f"{sev_counts['ERROR']} lỗi")
    if sev_counts.get("WARNING"):
        parts.append(f"{sev_counts['WARNING']} nhắc nhở")

    summary = "; ".join(parts)
    if reasons:
        summary += f". Lý do chính: {reasons[0]}"
    return summary


def summarize_cover_errors(errors: List[dict]) -> str:
    """Viết nhận xét cho Cover errors (Section A)."""
    if not errors:
        return "Thông tin dự án trên Cover đầy đủ, không có lỗi."

    sev_counts = defaultdict(int)
    reasons = []
    for e in errors:
        sev_counts[e.get("severity", "?")] += 1
        reasons.append(f"{e.get('field', '?')}: {e.get('reason', '?')}")

    system = (
        "Bạn là chuyên viên GMS thẩm định. "
        "Viết nhận xét NGẮN GỌN (1-2 câu) bằng tiếng Việt về tình trạng Cover dự án. "
        "Không thêm lời chào."
    )
    user = (
        f"Lỗi phát hiện trên Cover:\n" + "\n".join(f"  - {r}" for r in reasons)
        + f"\nViết nhận xét."
    )

    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        text = resp.choices[0].message.content.strip()
        if text:
            return text
    except Exception:
        pass

    crit_count = sev_counts.get("CRITICAL", 0)
    warn_count = sev_counts.get("WARNING", 0)
    parts = []
    if crit_count:
        parts.append(f"{crit_count} lỗi NGHIÊM TRỌNG cần sửa gấp")
    if warn_count:
        parts.append(f"{warn_count} lưu ý nhỏ")
    if not parts:
        return "Cover OK."
    return f"Cover có {'; '.join(parts)}."
