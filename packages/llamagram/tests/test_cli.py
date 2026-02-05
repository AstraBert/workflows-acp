from pathlib import Path

import pytest
from dotenv import dotenv_values
from typer.testing import CliRunner

from llamagram.cli import app

runner = CliRunner()


def test_setup_command_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "setup",
            "--api-key",
            "secret-key",
            "--llama-cloud-key",
            "llama-cloud-key",
            "--telegram-token",
            "tok",
            "--no-interactive",
        ],
    )
    assert (tmp_path / ".env").is_file()
    assert result.exit_code == 0
    data = dotenv_values(dotenv_path=str((tmp_path / ".env")))
    assert data["LLAMAGRAM_LLM_MODEL"] == "gpt-4.1"
    assert data["LLAMAGRAM_LLM_PROVIDER"] == "openai"
    assert data["LLAMAGRAM_LLM_API_KEY"] == "secret-key"
    assert data["LLAMA_CLOUD_API_KEY"] == "llama-cloud-key"
    assert data["TELEGRAM_BOT_TOKEN"] == "tok"


def test_setup_command_custom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "setup",
            "--provider",
            "google",
            "--model",
            "gemini-3-flash-preview",
            "--api-key",
            "secret-key",
            "--llama-cloud-key",
            "llama-cloud-key",
            "--telegram-token",
            "tok",
            "--no-interactive",
        ],
    )
    assert (tmp_path / ".env").is_file()
    assert result.exit_code == 0
    data = dotenv_values(dotenv_path=str((tmp_path / ".env")))
    assert data["LLAMAGRAM_LLM_MODEL"] == "gemini-3-flash-preview"
    assert data["LLAMAGRAM_LLM_PROVIDER"] == "google"
    assert data["LLAMAGRAM_LLM_API_KEY"] == "secret-key"
    assert data["LLAMA_CLOUD_API_KEY"] == "llama-cloud-key"
    assert data["TELEGRAM_BOT_TOKEN"] == "tok"
