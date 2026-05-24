"""Core tutorial generation workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .client import NotesClient
from .pdf import open_pdf, render_page_to_png_data_url
from .prompts import build_page_prompt
from .state import (
    PageRecord,
    append_record,
    load_records,
    reset_state,
    write_markdown,
)


@dataclass(slots=True)
class TutorialConfig:
    pdf_path: Path
    output_path: Path
    state_path: Path
    model: str
    dpi: int = 180
    limit_pages: int | None = None
    force: bool = False
    keep_recent_pages: int = 3


@dataclass(slots=True)
class GenerationResult:
    total_pages: int
    generated_pages: int
    skipped_pages: int
    output_path: Path
    state_path: Path


class TutorialGenerator:
    def __init__(
        self,
        *,
        config: TutorialConfig,
        client: NotesClient,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config
        self.client = client
        self.progress = progress

    def run(self) -> GenerationResult:
        if not self.config.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.config.pdf_path}")
        if self.config.dpi <= 0:
            raise ValueError("--dpi must be greater than 0")
        if self.config.limit_pages is not None and self.config.limit_pages <= 0:
            raise ValueError("--limit-pages must be greater than 0")
        if self.config.keep_recent_pages < 1:
            raise ValueError("keep_recent_pages must be at least 1")

        if self.config.force:
            reset_state(self.config.state_path)

        existing_records = [] if self.config.force else load_records(self.config.state_path)
        existing_by_page = {
            record.page_number: record for record in existing_records
        }

        generated_pages = 0
        skipped_pages = 0
        processed_records: list[PageRecord] = []
        current_summary = ""

        with open_pdf(self.config.pdf_path) as document:
            total_pages = document.page_count
            if self.config.limit_pages is not None:
                total_pages = min(total_pages, self.config.limit_pages)

            for page_number in range(1, total_pages + 1):
                existing_record = existing_by_page.get(page_number)
                if existing_record is not None:
                    self._progress(f"Skipping page {page_number}/{total_pages} from state.")
                    processed_records.append(existing_record)
                    current_summary = existing_record.context_summary_after_page
                    skipped_pages += 1
                    write_markdown(
                        self.config.output_path,
                        pdf_path=self.config.pdf_path,
                        model=self.config.model,
                        records=processed_records,
                    )
                    continue

                self._progress(f"Generating page {page_number}/{total_pages}.")
                previous_context = build_previous_context(
                    current_summary,
                    processed_records[-self.config.keep_recent_pages :],
                )
                prompt = build_page_prompt(previous_context)
                image_data_url = render_page_to_png_data_url(
                    document,
                    page_number - 1,
                    self.config.dpi,
                )

                response = self.client.generate_page_notes(prompt, image_data_url)

                if len(processed_records) >= self.config.keep_recent_pages:
                    page_to_summarize = processed_records[-self.config.keep_recent_pages]
                    self._progress(
                        f"Updating rolling summary with page {page_to_summarize.page_number}."
                    )
                    current_summary = self.client.update_context_summary(
                        current_summary,
                        page_to_summarize.response,
                    )

                record = PageRecord.create(
                    page_number=page_number,
                    model=self.config.model,
                    response=response,
                    context_summary_after_page=current_summary,
                )
                append_record(self.config.state_path, record)
                processed_records.append(record)
                generated_pages += 1

                write_markdown(
                    self.config.output_path,
                    pdf_path=self.config.pdf_path,
                    model=self.config.model,
                    records=processed_records,
                )

        write_markdown(
            self.config.output_path,
            pdf_path=self.config.pdf_path,
            model=self.config.model,
            records=processed_records,
        )

        return GenerationResult(
            total_pages=total_pages,
            generated_pages=generated_pages,
            skipped_pages=skipped_pages,
            output_path=self.config.output_path,
            state_path=self.config.state_path,
        )

    def _progress(self, message: str) -> None:
        if self.progress is not None:
            self.progress(message)


def build_previous_context(summary: str, recent_records: list[PageRecord]) -> str:
    parts: list[str] = []
    if summary.strip():
        parts.extend(["# 之前较早页面的滚动摘要", summary.strip()])

    if recent_records:
        parts.append("# 最近页面的完整讲解")
        for record in recent_records:
            parts.extend(
                [
                    f"## 第 {record.page_number} 页讲解",
                    record.response.strip(),
                ]
            )

    return "\n\n".join(parts)
