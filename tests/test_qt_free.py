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
    site_packages = str(pathlib.Path(sys.executable).parent.parent / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages")
    code = "import bandcamp_player.core.bandcamp_api; print('OK')"
    result = subprocess.run(
        [sys.executable, "-S", "-c", code],
        cwd=repo_root,
        # -S still blocks PySide6/vlc; PYTHONPATH restores the declared
        # third-party deps (curl_cffi) so the Qt-free invariant is what's tested.
        env={**dict(os.environ), "PYTHONPATH": os.pathsep.join([str(repo_root), site_packages])},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
