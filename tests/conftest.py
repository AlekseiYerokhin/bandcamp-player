import os
import tempfile

# Headless Qt for widget tests (pytest-qt creates QApplication).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Isolate QSettings writes from the developer's real config.
os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp(prefix="bandcamp-test-"))
