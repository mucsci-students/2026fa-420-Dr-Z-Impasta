"""``zimpasta --gui``: argument handling, port choice, and startup, without a real server."""

import json
import socket

import pytest

from zimpasta import cli, gui
from zimpasta.gui import PortUnavailable, choose_port, port_is_free, serve


class Recorder:
    def __init__(self):
        self.lines = []
        self.servers = []

    def say(self, line):
        self.lines.append(line)

    def run(self, server):
        self.servers.append(server)

    @property
    def text(self):
        return "\n".join(self.lines)


# ------------------------------------------------------------------ arguments


def test_no_arguments_start_the_shell():
    arguments = cli.parse_arguments([])

    assert not arguments.gui


def test_gui_arguments():
    arguments = cli.parse_arguments(["--gui", "spring.json", "--port", "8123", "--no-browser"])

    assert arguments.gui
    assert (arguments.config, arguments.port, arguments.no_browser) == ("spring.json", 8123, True)


@pytest.mark.parametrize("argv", [["spring.json"], ["--port", "8123"], ["--no-browser"]])
def test_gui_options_need_gui(argv, capsys):
    with pytest.raises(SystemExit) as caught:
        cli.parse_arguments(argv)

    assert caught.value.code == 2
    assert "only apply with --gui" in capsys.readouterr().err


def test_main_with_gui_serves_and_exits_with_its_code(monkeypatch):
    calls = []

    def fake_serve(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(gui, "serve", fake_serve)

    with pytest.raises(SystemExit) as caught:
        cli.main(["--gui", "--port", "8123", "--no-browser"])

    assert caught.value.code == 0
    assert calls == [{"config": None, "port": 8123, "open_browser": False}]


# ----------------------------------------------------------------------- ports


def test_requested_port_is_used_if_free():
    assert choose_port(8123, is_free=lambda port: True) == 8123


def test_requested_port_that_is_busy_or_invalid_is_an_error():
    with pytest.raises(PortUnavailable, match="already in use"):
        choose_port(8123, is_free=lambda port: False)
    with pytest.raises(PortUnavailable, match="not a valid port"):
        choose_port(70000, is_free=lambda port: True)


def test_without_a_request_the_first_free_port_from_8000_is_used():
    busy = {8000, 8001}

    assert choose_port(None, is_free=lambda port: port not in busy) == 8002

    with pytest.raises(PortUnavailable, match="all in use"):
        choose_port(None, is_free=lambda port: False)


def test_port_is_free_sees_a_listening_socket():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        assert not port_is_free(port)
    assert port_is_free(port)


# ---------------------------------------------------------------------- serve


def test_serve_starts_uvicorn_on_localhost(monkeypatch, tmp_path):
    monkeypatch.setattr(gui, "choose_port", lambda requested: 8123)
    recorder = Recorder()

    code = serve(open_browser=False, static_dir=tmp_path, say=recorder.say, run=recorder.run)

    assert code == 0
    [server] = recorder.servers
    assert (server.config.host, server.config.port) == ("127.0.0.1", 8123)
    assert "http://127.0.0.1:8123/" in recorder.text
    assert "hasn't been built" in recorder.text


def test_serve_opens_the_config_file_first(monkeypatch, config_file):
    monkeypatch.setattr(gui, "choose_port", lambda requested: 8123)
    recorder = Recorder()

    serve(config=config_file, open_browser=False, say=recorder.say, run=recorder.run)

    controller = recorder.servers[0].config.app.state.controller
    assert controller.workspace.name == "config.json"


def test_serve_refuses_a_bad_config_file(tmp_path, config_data):
    config_data["limit"] = 0
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(config_data), encoding="utf-8")
    recorder = Recorder()

    code = serve(config=bad, open_browser=False, say=recorder.say, run=recorder.run)

    assert code == 2
    assert recorder.servers == []
    assert "Can't open" in recorder.lines[0]
    assert any("limit" in line for line in recorder.lines[1:])


def test_serve_reports_a_busy_port(monkeypatch):
    def busy(requested):
        raise PortUnavailable("Port 8123 is already in use.")

    monkeypatch.setattr(gui, "choose_port", busy)
    recorder = Recorder()

    assert serve(port=8123, open_browser=False, say=recorder.say, run=recorder.run) == 1
    assert recorder.lines == ["Port 8123 is already in use."]


def test_browser_opens_once_the_server_has_started(monkeypatch):
    opened = []
    monkeypatch.setattr(gui.webbrowser, "open", opened.append)

    class Started:
        started = True

    gui._open_when_ready(Started(), "http://127.0.0.1:8123/")

    assert opened == ["http://127.0.0.1:8123/"]

    class NeverStarts:
        started = False

    gui._open_when_ready(NeverStarts(), "http://127.0.0.1:8123/", timeout=0.1)
    assert opened == ["http://127.0.0.1:8123/"]
