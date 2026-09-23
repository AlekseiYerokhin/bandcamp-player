---
name: qt-integration
description: Use when working on PySide6 UI code, Qt threading, signals, async image loads, or desktop-integration services (MPRIS/D-Bus) — covers the Qt threading model, signal type pitfalls, widget-lifecycle guards, and the dbus-next pattern used in this project.
---

# Qt Integration Patterns

PySide6 (Qt6) app. This skill captures the threading and object-lifecycle
rules that have repeatedly caused subtle bugs here.

## Threading model

There are four threads in this app:

1. **GUI thread** — runs the Qt event loop (`app.exec()`). The ONLY thread
   allowed to touch `QWidget` and `QTimer`.
2. **Engine worker threads** (daemon, one per API call) — emit results via
   Qt signals.
3. **libVLC event callbacks** — fire on VLC's own thread.
4. **MPRIS asyncio thread** — serves D-Bus in the background.

**Golden rule:** non-GUI threads never call methods on widgets, `QTimer`, or
other QObjects directly. They marshal back to the GUI via Qt signals with an
auto/queued connection.

## Signal type pitfalls

- `Signal(int, ...)` is a **32-bit C++ int**. Bandcamp IDs (`band_id`,
  `tralbum_id`, e.g. `4199458029`) overflow it. Use
  `Signal('qint64')` for any signal carrying an ID.
- Queued signals only deliver while the GUI thread runs `app.exec()`. In a
  test or probe that never starts the event loop, connected slots will never
  fire.

## Widget-lifecycle guards

- After any async work (image load, worker result), the widget may have been
  deleted. Check `shiboken6.isValid(obj)` before calling methods on it.
- Abort/ignore in-flight loads when a view is cleared (keep a set of pending
  reply/render ids and drop results for cleared views).
- `QPointer` is **not** importable from `PySide6.QtCore` — use `shiboken6`.

## Async image loading pattern

1. Start loading on a background thread.
2. When the image bytes arrive, emit a Qt signal carrying the bytes + a
   token identifying the target widget.
3. In the GUI-thread slot: ignore if the view was cleared (stale token),
   check `shiboken6.isValid(widget)`, then `setPixmap`.
4. Clearing a view marks its pending tokens stale so late results are dropped.

## dbus-next service pattern (MPRIS)

`bandcamp_player/mpris.py` is the reference implementation.

- Run the service in a **background asyncio thread**.
- After `request_name()`, call `loop.run_forever()` — `run_until_complete`
  returns immediately after setup and the service is never served.
- Read-only D-Bus properties need `access=PropertyAccess.READ` on the
  `@dbus_property` decorator; writable ones get a setter.
- D-Bus signature strings (`"x"`, `"a{sv}"`, ...) in annotations trigger
  `F821`/`F722` — add a module-level `# ruff: noqa: F821, F722`.
- `Position` must be exported in **microseconds** (multiply ms by 1000).
- Commands from D-Bus cross into the GUI thread as queued Qt signals.

## Verification

- Headless UI runs: `QT_QPA_PLATFORM=offscreen`.
- Widget-signal tests: `pytest-qt` (`qtbot`).
- Cross-thread behavior: prefer small fakes over mocks for controller tests
  so queued-signal delivery is exercised.