import json
import yaml
import pytest

from pathlib import Path
from typer.testing import CliRunner
from workflows_acp.cli import app

runner = CliRunner()


def test_model_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["model", "--model", "gemini-3-flash-preview"])
    assert result.exit_code == 0
    with open(tmp_path / "agent_config.yaml") as f:
        data = yaml.safe_load(f)
    assert data["model"] == "gemini-3-flash-preview"


def test_add_tool_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["add-tool", "--tool", "read_file"])
    assert result.exit_code == 0
    with open(tmp_path / "agent_config.yaml") as f:
        data = yaml.safe_load(f)
    assert "read_file" in data["tools"]


def test_rm_tool_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Add tool first
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["add-tool", "--tool", "read_file"])
    # Remove tool
    result = runner.invoke(app, ["rm-tool", "--tool", "read_file"])
    assert result.exit_code == 0
    with open(tmp_path / "agent_config.yaml") as f:
        data = yaml.safe_load(f)
    assert "read_file" not in data.get("tools", [])


def test_mode_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["mode", "--mode", "ask"])
    assert result.exit_code == 0
    with open(tmp_path / "agent_config.yaml") as f:
        data = yaml.safe_load(f)
    assert data["mode"] == "ask"


def test_task_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["task", "--task", "Assist with python coding"])
    assert result.exit_code == 0
    with open(tmp_path / "agent_config.yaml") as f:
        data = yaml.safe_load(f)
    assert data["agent_task"] == "Assist with python coding"


def test_add_mcp_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "add-mcp",
            "--name",
            "test",
            "--transport",
            "stdio",
            "--command",
            "npx @mcp/server start",
            "--env",
            "PORT=3000",
        ],
    )
    assert result.exit_code == 0
    with open(tmp_path / ".mcp.json") as f:
        data = json.load(f)
    assert "test" in data["mcpServers"]
    assert data["mcpServers"]["test"]["command"] == "npx"
    assert data["mcpServers"]["test"]["args"] == ["@mcp/server", "start"]
    assert data["mcpServers"]["test"]["env"]["PORT"] == "3000"


def test_add_mcp_http_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "add-mcp",
            "--name",
            "search",
            "--transport",
            "http",
            "--url",
            "https://search.com/mcp",
            "--header",
            "Authorization=Bearer token",
        ],
    )
    assert result.exit_code == 0
    with open(tmp_path / ".mcp.json") as f:
        data = json.load(f)
    assert "search" in data["mcpServers"]
    assert data["mcpServers"]["search"]["url"] == "https://search.com/mcp"
    assert data["mcpServers"]["search"]["headers"]["Authorization"] == "Bearer token"


def test_rm_mcp_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    # Add MCP server first
    runner.invoke(
        app,
        [
            "add-mcp",
            "--name",
            "test",
            "--transport",
            "stdio",
            "--command",
            "npx @mcp/server start",
        ],
    )
    # Remove MCP server
    result = runner.invoke(app, ["rm-mcp", "--name", "test"])
    assert result.exit_code == 0
    with open(tmp_path / ".mcp.json") as f:
        data = json.load(f)
    assert "test" not in data["mcpServers"]
