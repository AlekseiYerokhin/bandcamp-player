"""MPRIS D-Bus service so the desktop can control the player.

Exposes the ``org.mpris.MediaPlayer2`` and ``org.mpris.MediaPlayer2.Player``
interfaces on the session bus, giving system media keys and desktop applets
play/pause/next/previous control plus now-playing metadata.
"""

# ruff: noqa: F821, F722 - string annotations here are dbus_next D-Bus
# signature strings (e.g. "b", "x", "as", "a{sv}"), not forward references.

import asyncio
import threading

from dbus_next import Variant
from dbus_next.aio import MessageBus
from dbus_next.service import PropertyAccess, ServiceInterface, dbus_property, method, signal
from PySide6.QtCore import QObject, Signal

SERVICE_NAME = "org.mpris.MediaPlayer2.bandcamp_player"
OBJECT_PATH = "/org/mpris/MediaPlayer2"
_TRACK_ID_BASE = "/org/mpris/MediaPlayer2/Track"


class _RootInterface(ServiceInterface):
    def __init__(self, service):
        super().__init__("org.mpris.MediaPlayer2")
        self._service = service

    @dbus_property(access=PropertyAccess.READ)
    def CanQuit(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanRaise(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def HasTrackList(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> "s":
        return self._service._identity

    @dbus_property(access=PropertyAccess.READ)
    def DesktopEntry(self) -> "s":
        return "bandcamp-player"

    @dbus_property(access=PropertyAccess.READ)
    def SupportedUriSchemes(self) -> "as":
        return []

    @dbus_property(access=PropertyAccess.READ)
    def SupportedMimeTypes(self) -> "as":
        return []

    @method()
    def Raise(self):
        self._service._notify("raise")

    @method()
    def Quit(self):
        self._service._notify("quit")


class _PlayerInterface(ServiceInterface):
    def __init__(self, service):
        super().__init__("org.mpris.MediaPlayer2.Player")
        self._service = service

    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> "s":
        return self._service._playback_status

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> "a{sv}":
        return self._service._metadata

    @dbus_property()
    def Volume(self) -> "d":
        return self._service._volume

    @Volume.setter
    def Volume(self, value):
        self._service._volume = max(0.0, min(1.0, value))
        self._service.volume_requested.emit(self._service._volume)
        self.emit_properties_changed({"Volume": self._service._volume})

    @dbus_property(access=PropertyAccess.READ)
    def Position(self) -> "x":
        return self._service._position

    @dbus_property(access=PropertyAccess.READ)
    def Rate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def MinimumRate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def MaximumRate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def CanControl(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPlay(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPause(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanGoNext(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanGoPrevious(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanSeek(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanStop(self) -> "b":
        return True

    @method()
    def Play(self):
        self._service._notify("play")

    @method()
    def Pause(self):
        self._service._notify("pause")

    @method()
    def PlayPause(self):
        self._service._notify("play_pause")

    @method()
    def Next(self):
        self._service._notify("next")

    @method()
    def Previous(self):
        self._service._notify("previous")

    @method()
    def Stop(self):
        self._service._notify("stop")

    @method()
    def Seek(self, offset: "x"):
        self._service._notify("seek", offset)

    @method()
    def SetPosition(self, track_id: "o", position: "x"):
        self._service._notify("set_position", position)

    @signal()
    def Seeked(self, position: "x"):
        """Emitted when the playhead jumps without a direct seek request."""


class MprisService(QObject):
    """Owns the MPRIS D-Bus service in a background asyncio thread."""

    command_requested = Signal(str, int)
    volume_requested = Signal(float)

    def __init__(self, identity: str = "Bandcamp Player", parent=None):
        super().__init__(parent)
        self._identity = identity
        self._playback_status = "Stopped"
        self._metadata: dict[str, Variant] = {}
        self._volume = 1.0
        self._position = 0
        self._track_seq = 0
        self._ready = False
        self._error = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._bus = None
        self._player_iface: _PlayerInterface | None = None

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True, name="mpris")
        thread.start()

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        loop.run_until_complete(self._setup())
        loop.run_forever()  # serve D-Bus requests

    async def _setup(self):
        try:
            self._bus = await MessageBus().connect()
            self._player_iface = _PlayerInterface(self)
            self._bus.export(OBJECT_PATH, _RootInterface(self))
            self._bus.export(OBJECT_PATH, self._player_iface)
            await self._bus.request_name(SERVICE_NAME)
            self._ready = True
        except Exception as e:
            self._error = e

    # --- Qt thread -> D-Bus updates -------------------------------

    def set_track(self, title, artist="", album="", duration_ms=0, art_url=""):
        self._track_seq += 1
        metadata: dict[str, Variant] = {
            "mpris:trackid": Variant("o", f"{_TRACK_ID_BASE}/{self._track_seq}"),
            "xesam:title": Variant("s", title),
        }
        if artist:
            metadata["xesam:artist"] = Variant("as", [artist])
        if album:
            metadata["xesam:album"] = Variant("s", album)
        if duration_ms:
            metadata["mpris:length"] = Variant("x", duration_ms * 1000)
        if art_url:
            metadata["mpris:artUrl"] = Variant("s", art_url)
        self.set_playback("Playing", metadata)
        self.set_position_us(0)

    def set_playback(self, status, metadata: dict | None = None):
        changes = {}
        if status != self._playback_status:
            self._playback_status = status
            changes["PlaybackStatus"] = status
        if metadata is not None and metadata != self._metadata:
            self._metadata = metadata
            changes["Metadata"] = metadata
        self._emit(changes)

    def set_position_us(self, position_us: int):
        self._position = position_us
        if self._loop is not None and self._player_iface is not None:
            self._loop.call_soon_threadsafe(
                lambda: self._player_iface.Seeked(position_us))

    def set_position_ms(self, position_ms: int):
        self.set_position_us(position_ms * 1000)  # MPRIS uses microseconds

    def _emit(self, changes: dict):
        if changes and self._loop is not None and self._player_iface is not None:
            self._loop.call_soon_threadsafe(
                lambda: self._player_iface.emit_properties_changed(changes))

    def _notify(self, command: str, arg: int = 0):
        self.command_requested.emit(command, arg)
