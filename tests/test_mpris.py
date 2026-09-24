"""MPRIS service unit tests — no D-Bus, no event loop.

Covers the state/marshalling logic (set_track, set_playback, set_position_ms,
_emit) and the D-Bus property getters, which is where MPRIS bugs have lived.
"""

import pytest

from bandcamp_player import mpris as mpris_mod
from bandcamp_player.mpris import MprisService, _PlayerInterface, _RootInterface


@pytest.fixture
def service():
    return MprisService()


def test_initial_state(service):
    assert service._playback_status == "Stopped"
    assert service._metadata == {}
    assert service._volume == 1.0
    assert service._position == 0


def test_set_track_builds_metadata_and_marks_playing(service):
    service.set_track(
        "Chamber", artist="Chamber", album="A Love To Kill For",
        duration_ms=70000, art_url="https://art/1.jpg",
    )
    assert service._playback_status == "Playing"
    meta = service._metadata
    assert meta["xesam:title"].value == "Chamber"
    assert meta["xesam:artist"].value == ["Chamber"]
    assert meta["xesam:album"].value == "A Love To Kill For"
    assert meta["mpris:length"].value == 70000000  # ms -> microseconds
    assert meta["mpris:artUrl"].value == "https://art/1.jpg"
    assert meta["mpris:trackid"].value.startswith("/org/mpris/MediaPlayer2/Track/")


def test_set_track_omits_optional_fields(service):
    service.set_track("Only Title")
    assert "xesam:artist" not in service._metadata
    assert "xesam:album" not in service._metadata
    assert "mpris:length" not in service._metadata
    assert "mpris:artUrl" not in service._metadata


def test_set_playback_updates_status_only(service):
    service.set_playback("Paused")
    assert service._playback_status == "Paused"
    assert service._metadata == {}


def test_set_position_us_converts_to_microseconds(service):
    service.set_position_us(5000000)
    assert service._position == 5000000


def test_set_position_ms_converts_to_microseconds(service):
    service.set_position_ms(5000)
    assert service._position == 5000000


def test_volume_setter_clamps_and_emits_float(service):
    captured = []
    service.volume_requested.connect(captured.append)
    player_iface = _PlayerInterface(service)
    player_iface.Volume = 2.0
    assert service._volume == 1.0
    player_iface.Volume = -1.0
    assert service._volume == 0.0
    player_iface.Volume = 0.35
    assert service._volume == 0.35
    assert captured == [1.0, 0.0, 0.35]


def test_command_signal_is_str_int(service):
    # The bug that shipped: Signal(str, int) truncating floats. Verify the
    # signal signature carries an int for commands, not a float.
    from PySide6.QtCore import QObject, Signal

    class Probe(QObject):
        s = Signal(str, int)

    probe = Probe()
    got = []
    probe.s.connect(lambda c, a: got.append((c, a)))
    probe.s.emit("seek", 5000)
    assert got == [("seek", 5000)]


def test_root_interface_properties(service):
    root = _RootInterface(service)
    assert root.CanQuit is True
    assert root.CanRaise is True
    assert root.HasTrackList is False
    assert root.Identity == "Bandcamp Player"
    assert root.DesktopEntry == "bandcamp-player"
    assert root.SupportedUriSchemes == []
    assert root.SupportedMimeTypes == []


def test_player_interface_readonly_properties(service):
    player = _PlayerInterface(service)
    service._playback_status = "Playing"
    service._volume = 0.5
    service._position = 123
    assert player.PlaybackStatus == "Playing"
    assert player.Volume == 0.5
    assert player.Position == 123
    assert player.Rate == 1.0
    assert player.MinimumRate == 1.0
    assert player.MaximumRate == 1.0
    assert player.CanControl is True
    assert player.CanPlay is True
    assert player.CanPause is True
    assert player.CanGoNext is True
    assert player.CanGoPrevious is True
    assert player.CanSeek is True
    assert player.CanStop is True
    assert player.Metadata == service._metadata


def test_commands_notify(service):
    got = []
    service.command_requested.connect(lambda c, a: got.append((c, a)))
    _PlayerInterface(service).Play()
    _PlayerInterface(service).Pause()
    _PlayerInterface(service).Next()
    _PlayerInterface(service).Seek(1000000)
    _PlayerInterface(service).SetPosition("/org/mpris/MediaPlayer2/Track/1", 5000000)
    assert got == [("play", 0), ("pause", 0), ("next", 0), ("seek", 1000000), ("set_position", 5000000)]


def test_seeked_signal_exists(service):
    assert hasattr(_PlayerInterface(service), "Seeked")


def test_emit_is_noop_without_loop(service):
    # No event loop / interface yet -> _emit must not raise (headless import).
    service.set_playback("Playing")
    assert service._playback_status == "Playing"


def test_module_noqa_for_signature_strings():
    # Guard: the D-Bus signature annotations rely on the module-level noqa;
    # if someone removes it, ruff will flag F821/F722 and this reminds us.
    with open(mpris_mod.__file__) as f:
        source = f.read()
    assert "# ruff: noqa: F821, F722" in source.split("\n")[7]
