import socket
import subprocess
import time
import urllib.request

from collections.abc import Iterator

import pytest

from zimpasta.controller.static import BUILT_GUI


pytestmark = pytest.mark.skipif(
    not (BUILT_GUI / "index.html").exists(),
    reason="Run npm run build in frontend first."
)

RUN_SERVER = ["uv", "run", "zimpasta", "--gui", "--no-browser"]


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def site() -> Iterator[str]:
    port = free_port()
    url = f"http://127.0.0.1:{port}"

    server = subprocess.Popen(
        [*RUN_SERVER, "--port", str(port)]
    )

    try:
        deadline = time.time() + 30

        while time.time() < deadline:
            if server.poll() is not None:
                raise RuntimeError("Server stopped unexpectedly.")

            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Server failed to start.")

        yield url

    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
