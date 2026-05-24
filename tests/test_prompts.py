from slides2tutorial.prompts import build_page_prompt, build_summary_prompt


def test_page_prompt_rejects_boilerplate_openings() -> None:
    prompt = build_page_prompt("")

    assert "严格禁止输出的内容" in prompt
    assert "同学们好" in prompt
    assert "以下是本页的详细课堂笔记" in prompt
    assert "评价性形容词" in prompt
    assert "客观列举" in prompt
    assert "第一句话应直接进入本页知识点" in prompt
    assert "第 X 页讲解" in prompt


def test_page_prompt_keeps_explanations_readable_not_overly_compact() -> None:
    prompt = build_page_prompt("前文讲过物理层负责透明传输比特流。")

    assert "概念跳转时用 1-2 句自然过渡" in prompt
    assert "直观解释、生活类比或小例子" in prompt
    assert "为什么要从 A 讲到 B" in prompt
    assert "700-1200 中文字" in prompt


def test_summary_prompt_drops_non_reusable_talk() -> None:
    prompt = build_summary_prompt("", "页面讲解")

    assert "不要保留寒暄" in prompt
    assert "页面评价" in prompt
    assert "以下是笔记" in prompt
