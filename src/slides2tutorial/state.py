"""JSONL state and Markdown output helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class PageRecord:
    page_number: int
    model: str
    response: str
    context_summary_after_page: str
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        page_number: int,
        model: str,
        response: str,
        context_summary_after_page: str,
    ) -> "PageRecord":
        return cls(
            page_number=page_number,
            model=model,
            response=response,
            context_summary_after_page=context_summary_after_page,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def from_json(cls, data: dict) -> "PageRecord":
        return cls(
            page_number=int(data["page_number"]),
            model=str(data["model"]),
            response=str(data["response"]),
            context_summary_after_page=str(data.get("context_summary_after_page", "")),
            created_at=str(data.get("created_at", "")),
        )


def load_records(path: Path) -> list[PageRecord]:
    """Load state records. If a page appears more than once, the last record wins."""

    if not path.exists():
        return []

    records_by_page: dict[int, PageRecord] = {}
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = PageRecord.from_json(json.loads(stripped))
            except Exception as exc:
                raise ValueError(
                    f"Invalid JSONL state at {path}:{line_number}"
                ) from exc
            records_by_page[record.page_number] = record

    return [records_by_page[key] for key in sorted(records_by_page)]


def append_record(path: Path, record: PageRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def reset_state(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def write_markdown(
    path: Path,
    *,
    pdf_path: Path,
    model: str,
    records: Iterable[PageRecord],
) -> None:
    sorted_records = sorted(records, key=lambda record: record.page_number)
    lines = [
        "# PDF 逐页讲解笔记",
        "",
        f"- Source PDF: `{pdf_path}`",
        f"- Model: `{model}`",
        "- Format: Markdown + LaTeX (`$...$`, `$$...$$`)",
        "",
    ]

    for record in sorted_records:
        lines.extend(
            [
                f"## 第 {record.page_number} 页",
                "",
                record.response.strip(),
                "",
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
