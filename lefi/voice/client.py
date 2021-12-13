from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Callable, Optional, Dict


from ..errors import VoiceException
from .wsclient import VoiceWebSocketClient, UserVoiceData
from .protocol import VoiceProtocol
from .player import AudioPlayer, AudioStream
from .listeners import AudioDestination, AudioListener

if TYPE_CHECKING:
    from ..state import State
    from ..objects import VoiceChannel


class VoiceClient:
    """
    Represents a voice client.

    """

    def __init__(self, state: State, channel: VoiceChannel) -> None:
        self._state = state
        self._received_state_update = asyncio.Event()
        self._player: Optional[AudioPlayer] = None
        self._connected = False
        self._received_server_update = asyncio.Event()

        self.channel = channel
        self.session_id: Optional[str] = None
        self.endpoint: Optional[str] = None
        self.token: Optional[str] = None
        self.ws: VoiceWebSocketClient = VoiceWebSocketClient(self, self.channel.guild.id, self._state.client.user.id)
        self.protocol: VoiceProtocol = VoiceProtocol(self)
        self._listener: Optional[AudioListener] = None

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._state.loop

    @property
    def player(self) -> Optional[AudioPlayer]:
        """
        Returns the current player. If no player is playing, returns None.
        """
        return self._player

    @property
    def listener(self) -> Optional[AudioListener]:
        return self._listener

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

        self.protocol.encoder.destroy()

    def is_connected(self) -> bool:
        """
        Whether the client is connected to the voice channel.

        """
        return self._connected

    def is_playing(self) -> bool:
        """
        Whether the client is playing.

        """
        return self._player is not None and self._player.is_playing()

    def is_listening(self) -> bool:
        """
        Whether the client is listening.
        """
        return self._listener is not None and self._listener.is_listening()

    def play(self, stream: AudioStream, *, volume: float = 1.0) -> AudioPlayer:
        """
        Plays an audio stream. If the client is either connected or already playing it raises an error.

        Parameters:
            stream (AudioStream): The audio stream to play.
            volume (float): The volume to play the stream at.

        """
        if not self.is_connected():
            raise VoiceException("Client not connected")

        if self.is_playing():
            raise VoiceException("Client is already playing")

        self._player = player = AudioPlayer(self.protocol, stream)
        player.set_volume(volume)

        return player.play()

    async def listen(
        self,
        destination: AudioDestination,
        duration: int,
        *,
        timeout: Optional[float] = None,
        filter: Optional[Callable[[UserVoiceData], bool]] = None
    ) -> None:
        """
        Listens for an audio stream. If the client is either connected or already listening it raises an error.

        Parameters:
            destination (AudioDestination): The destination to listen to.
            duration (int): The duration to listen for.
            timeout (float): The timeout to listen for.

        """

        if self.is_listening():
            raise VoiceException("Client is already listening")

        self._listener = listener = AudioListener(self.protocol, destination)
        if filter:
            listener.filter = filter

        await listener.listen(duration, timeout=timeout)
        self._listener = None
