import pytest

from slides2tutorial import client as client_module
from slides2tutorial.client import OpenAICompatibleNotesClient


class CongestionError(Exception):
    status_code = 429


class AuthError(Exception):
    status_code = 401


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise CongestionError("当前分组上游负载已饱和，请稍后再试")
        return {"ok": True, "kwargs": kwargs}


class FakeChat:
    def __init__(self) -> None:
        self.completions = FakeCompletions()


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.chat = FakeChat()


def make_client(fake_client: FakeOpenAIClient) -> OpenAICompatibleNotesClient:
    notes_client = OpenAICompatibleNotesClient.__new__(OpenAICompatibleNotesClient)
    notes_client._client = fake_client
    notes_client._model = "gemini-3.1-pro-preview"
    return notes_client


def test_upstream_congestion_retries_every_three_seconds(monkeypatch, capsys) -> None:
    sleeps: list[int] = []
    monkeypatch.setattr(client_module.time, "sleep", lambda seconds: sleeps.append(seconds))
    fake_client = FakeOpenAIClient()
    notes_client = make_client(fake_client)

    result = notes_client._create_chat_completion(model="m", messages=[])

    assert result == {"ok": True, "kwargs": {"model": "m", "messages": []}}
    assert fake_client.chat.completions.calls == 2
    assert sleeps == [3]
    assert "retrying in 3 seconds" in capsys.readouterr().err


def test_non_congestion_errors_are_not_retried(monkeypatch) -> None:
    sleeps: list[int] = []
    monkeypatch.setattr(client_module.time, "sleep", lambda seconds: sleeps.append(seconds))
    fake_client = FakeOpenAIClient()

    def raise_auth_error(**kwargs):
        raise AuthError("invalid api key")

    fake_client.chat.completions.create = raise_auth_error
    notes_client = make_client(fake_client)

    with pytest.raises(AuthError):
        notes_client._create_chat_completion(model="m", messages=[])

    assert sleeps == []


def test_detects_upstream_congestion_messages() -> None:
    assert client_module._is_upstream_congestion_error(
        RuntimeError("当前分组上游负载已饱和，请稍后再试")
    )
    assert not client_module._is_upstream_congestion_error(AuthError("invalid api key"))
