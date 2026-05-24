from slides2tutorial.cli import main


def test_cli_reports_missing_api_key_without_leaking_secret(
    capsys, monkeypatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_BASE_URL", raising=False)

    exit_code = main(["missing.pdf", "--base-url", "https://example.test/v1"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing --api-key" in captured.err
    assert "GEMINI_API_KEY" in captured.err
