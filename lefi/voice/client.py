from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional, Dict

from ..errors import PyNaClNotFound, VoiceException
from .wsclient import VoiceWebSocketClient
from .protocol import VoiceProtocol, has_nacl
from .player import AudioPlayer, AudioStream

if TYPE_CHECKING:
    from ..state import State
    from ..objects import VoiceChannel


class VoiceClient:
    """
    Represents a voice client.

    """

    def __init__(self, state: State, channel: VoiceChannel) -> None:
        if not has_nacl:
            raise PyNaClNotFound("PyNaCl is required for voice")

        self._state = state
        self._received_state_update = asyncio.Event()
        self._player: Optional[AudioPlayer] = None
        self._connected = False
        self._received_server_update = asyncio.Event()

        self.channel = channel
        self.session_id: Optional[str] = None
        self.endpoint: Optional[str] = None
        self.token: Optional[str] = None
        self.ws: VoiceWebSocketClient = VoiceWebSocketClient(
            self, self.channel.guild.id, self._state.client.user.id
        )
        self.protocol: VoiceProtocol = VoiceProtocol(self)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._state.loop

    @property
    def player(self) -> Optional[AudioPlayer]:
        """
        Returns the current player. If no player is playing, returns None.
        """
        return self._player

    async def voice_state_update(self, data: Dict) -> None:
        self.session_id = data["session_id"]
        self._received_state_update.set()

    async def voice_server_update(self, data: Dict) -> None:
        self.endpoint = data["endpoint"]
        self.token = data["token"]

        self._received_server_update.set()

    async def connect(self) -> None:
        """
        Connects the voice client.

        """
        await self.channel.guild.change_voice_state(channel=self.channel)

        futures = [
            self._received_server_update.wait(),
            self._received_state_update.wait(),
        ]

        await asyncio.wait(futures, return_when=asyncio.ALL_COMPLETED)
        await self.ws.connect()

        self._connected = True

    async def disconnect(self) -> None:
        """
        Disconnects the voice client.

        """
        if self._player:
            await self._player.stop()

        await self.channel.guild.change_voice_state(channel=None)
        await self.ws.close()

        self._connected = False

        self._received_server_update.clear()
        self._received_state_update.clear()

    def is_connected(self) -> bool:
        """
        Wether the client is connected to the voice channel.

        """
        return self._connected

    def is_playing(self) -> bool:
        """
        Wether the client is playing.

        """
        return self._player is not None

    def play(self, stream: AudioStream, *, volume: float = 1.0) -> AudioPlayer:
        """
        Plays an audio stream. If the client is either connected or already playing it raises an error.

        Parameters:
            stream (AudioStream): The audio stream to play.

        """
        if not self.is_connected():
            raise VoiceException("Client not connected")

        if self.is_playing():
            raise VoiceException("Client is already playing")

        self._player = player = AudioPlayer(self.protocol, stream)
        player.set_volume(volume)

        return player.play()

    def pause(self) -> None:
        """
        A shortcut for VoiceClient.player.pause().
        If not player is playing, raises an error.

        """
        if not self.is_playing() or self._player is None:
            raise VoiceException("Client is not playing")

        self._player.pause()

    def resume(self) -> None:
        if not self.is_playing() or self._player is None:
            raise VoiceException("Client is not playing")

        self._player.resume()

    async def stop(self) -> None:
        if not self.is_playing() or self._player is None:
            raise VoiceException("Client is not playing")

        await self._player.stop()
        self._player = None

    def is_paused(self) -> bool:
        if not self.is_playing() or self._player is None:
            raise VoiceException("Client is not playing")

        return self._player.is_paused()
