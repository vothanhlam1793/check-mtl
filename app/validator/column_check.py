import openpyxl
from typing import List

from config import TemplateConfig


def check_columns(ws: openpyxl.worksheet.worksheet.Worksheet, template: TemplateConfig, header_row: int) -> List[str]:
    """Step B: validate column headers match the detected template."""
    errors = []
    col_letters = ["A", "B", "C", "D", "E", "F", "G"]

    for letter in col_letters:
        cell = ws.cell(row=header_row, column=ord(letter) - 64)
        actual = (cell.value or "").strip()
        expected = template.columns[letter]
        if actual != expected:
            errors.append(f"Cột {letter}: nhận '{actual}', mong đợi '{expected}' (template {template.name})")

    return errors
