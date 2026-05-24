from pathlib import Path

import fitz

from slides2tutorial.generator import TutorialConfig, TutorialGenerator


class FakeNotesClient:
    def __init__(self) -> None:
        self.page_prompts: list[str] = []
        self.image_urls: list[str] = []
        self.summary_calls: list[tuple[str, str]] = []

    def generate_page_notes(self, prompt: str, image_data_url: str) -> str:
        self.page_prompts.append(prompt)
        self.image_urls.append(image_data_url)
        page_number = len(self.page_prompts)
        return f"第 {page_number} 页讲解\n\n重要公式：\n\n$$x_{page_number}=1$$"

    def update_context_summary(self, old_summary: str, new_page_response: str) -> str:
        self.summary_calls.append((old_summary, new_page_response))
        marker = new_page_response.splitlines()[0]
        return f"{old_summary}\n摘要包含：{marker}".strip()


def create_sample_pdf(path: Path, pages: int) -> None:
    document = fitz.open()
    for page_number in range(1, pages + 1):
        page = document.new_page(width=320, height=180)
        page.insert_text((40, 80), f"Page {page_number}: TCP throughput")
    document.save(path)
    document.close()


def make_config(tmp_path: Path, pdf_path: Path, *, limit_pages: int | None = None) -> TutorialConfig:
    return TutorialConfig(
        pdf_path=pdf_path,
        output_path=tmp_path / "output" / "tutorial.md",
        state_path=tmp_path / "output" / "state.jsonl",
        model="gemini-3.1-pro",
        dpi=72,
        limit_pages=limit_pages,
    )


def test_generates_markdown_state_and_uses_previous_page_context(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_sample_pdf(pdf_path, pages=2)
    client = FakeNotesClient()

    result = TutorialGenerator(config=make_config(tmp_path, pdf_path), client=client).run()

    markdown = (tmp_path / "output" / "tutorial.md").read_text(encoding="utf-8")
    state = (tmp_path / "output" / "state.jsonl").read_text(encoding="utf-8")

    assert result.generated_pages == 2
    assert result.skipped_pages == 0
    assert "## 第 1 页" in markdown
    assert "## 第 2 页" in markdown
    assert "$$x_1=1$$" in markdown
    assert '"page_number": 1' in state
    assert client.image_urls[0].startswith("data:image/png;base64,")
    assert "之前内容为空" in client.page_prompts[0]
    assert "第 1 页讲解" in client.page_prompts[1]


def test_summarizes_older_pages_and_keeps_recent_pages_verbatim(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_sample_pdf(pdf_path, pages=5)
    client = FakeNotesClient()

    TutorialGenerator(config=make_config(tmp_path, pdf_path), client=client).run()

    assert len(client.summary_calls) == 2
    assert "第 1 页讲解" in client.summary_calls[0][1]
    assert "第 2 页讲解" in client.summary_calls[1][1]
    fifth_prompt = client.page_prompts[4]
    assert "摘要包含：第 1 页讲解" in fifth_prompt
    assert "第 2 页讲解" in fifth_prompt
    assert "第 3 页讲解" in fifth_prompt
    assert "第 4 页讲解" in fifth_prompt


def test_resume_skips_completed_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_sample_pdf(pdf_path, pages=2)

    first_client = FakeNotesClient()
    TutorialGenerator(config=make_config(tmp_path, pdf_path), client=first_client).run()

    second_client = FakeNotesClient()
    result = TutorialGenerator(config=make_config(tmp_path, pdf_path), client=second_client).run()

    assert result.generated_pages == 0
    assert result.skipped_pages == 2
    assert second_client.page_prompts == []


def test_force_regenerates_existing_state(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_sample_pdf(pdf_path, pages=1)
    config = make_config(tmp_path, pdf_path)

    TutorialGenerator(config=config, client=FakeNotesClient()).run()

    force_config = TutorialConfig(
        pdf_path=config.pdf_path,
        output_path=config.output_path,
        state_path=config.state_path,
        model=config.model,
        dpi=config.dpi,
        force=True,
    )
    second_client = FakeNotesClient()
    result = TutorialGenerator(config=force_config, client=second_client).run()

    assert result.generated_pages == 1
    assert result.skipped_pages == 0
    assert len(second_client.page_prompts) == 1
