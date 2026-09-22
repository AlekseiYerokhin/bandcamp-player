import os
import pathlib
import subprocess
import sys


def test_bandcamp_api_imports_without_qt():
    """bandcamp_api must be importable without PySide6/libvlc installed.

    Runs a subprocess with site-packages disabled (-S) so any Qt/vlc import in
    the chain would fail. Ensures the "Qt-free, unit-testable" invariant holds.
    """
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    code = "import src.core.bandcamp_api; print('OK')"
    result = subprocess.run(
        [sys.executable, "-S", "-c", code],
        cwd=repo_root,
        env={**dict(os.environ), "PYTHONPATH": str(repo_root)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
