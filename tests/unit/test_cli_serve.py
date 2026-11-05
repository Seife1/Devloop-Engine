from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from learnloop.cli import main
from learnloop.integrator import LearnLoopIntegrator


def test_cli_serve_subcommand_invokes_cmd_serve():
    with patch("learnloop.cli.cmd_serve", return_value=0) as mock_serve:
        with pytest.raises(SystemExit) as exc_info:
            main(["serve"])
        assert exc_info.value.code == 0
        mock_serve.assert_called_once_with(transport="stdio", host="0.0.0.0", port=8000)


def test_cli_serve_subcommand_with_custom_transport_and_port():
    with patch("learnloop.cli.cmd_serve", return_value=0) as mock_serve:
        with pytest.raises(SystemExit) as exc_info:
            main(["serve", "--transport", "sse", "--port", "9090", "--host", "127.0.0.1"])
        assert exc_info.value.code == 0
        mock_serve.assert_called_once_with(transport="sse", host="127.0.0.1", port=9090)


def test_cmd_serve_emits_interactive_stderr_note_on_tty(capsys):
    from learnloop.cli import cmd_serve

    mock_server = MagicMock()
    with patch("learnloop.server.build_server", return_value=mock_server):
        with patch("sys.stdin.isatty", return_value=True):
            code = cmd_serve(transport="stdio")
            assert code == 0
            captured = capsys.readouterr()
            assert "LearnLoop MCP Server (stdio transport)" in captured.err
            assert "Press Ctrl+C to stop" in captured.err
            assert captured.out == ""  # Stdout must remain 100% clean for JSON-RPC


def test_integrator_emits_explicit_serve_args(tmp_path: Path):
    integrator = LearnLoopIntegrator(project_root=tmp_path)
    cfg = integrator.get_mcp_config("vscode")
    assert "mcpServers" in cfg
    assert "learnloop" in cfg["mcpServers"]
    server_entry = cfg["mcpServers"]["learnloop"]
    assert server_entry["args"] == ["serve"]

