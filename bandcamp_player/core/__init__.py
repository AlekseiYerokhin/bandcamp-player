"""Core package.

Keep this package `__init__.py` free of heavy imports (PySide6, libvlc) so that
``core.bandcamp_api`` — the pure, Qt-free API client — stays importable in
environments without Qt. Import submodules directly instead.
"""
