from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, BinaryIO, List, Optional, Protocol, Union
import time
import audioop

from . import _opus
from .wsclient import SpeakingState

__all__ = (
    "AudioStream",
    "BaseAudioStream",
    "PCMAudioStream",
    "FFmpegAudioStream",
    "AudioPlayer",
)

if TYPE_CHECKING:
    from .protocol import VoiceProtocol


class AudioStream(Protocol):
    async def read(self) -> bytes:
        ...

    async def close(self) -> None:
        ...

    def __aiter__(self) -> AudioStream:
        ...

    async def __anext__(self) -> bytes:
        ...

    async def __aenter__(self) -> AudioStream:
        ...

    async def __aexit__(self, *args) -> None:
        ...


class BaseAudioStream(AudioStream):
    async def read(self) -> bytes:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        data = await self.read()
        if not data:
            raise StopAsyncIteration
        return data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


class PCMAudioStream(BaseAudioStream):
    def __init__(self, source: BinaryIO) -> None:
        self.source = source
        self.loop = asyncio.get_running_loop()

    async def read(self) -> bytes:
        data = await asyncio.to_thread(self.source.read, _opus.PACKET_SIZE)
        if len(data) != _opus.PACKET_SIZE:
            return b""

        return data

    async def close(self) -> None:
        self.source.close()


class FFmpegAudioStream(BaseAudioStream):
    def __init__(
        self,
        source: Union[str, BinaryIO],
        ffmpeg_options: Optional[List[str]] = None,
    ) -> None:
        self.pipe = False
        if not isinstance(source, str):
            self.pipe = True

        self.source = source
        self.process: Optional[asyncio.subprocess.Process] = None
        self.options = ffmpeg_options or []
        self.loop = asyncio.get_running_loop()

    async def create_process(self):
        kwargs = {
            "-i": "-" if self.pipe else self.source,
            "-f": "s16le",
            "-ar": "48000",
            "-ac": "2",
            "-loglevel": "warning",
        }

        args = []
        for k, v in kwargs.items():
            args.extend([k, v])

        args.extend(self.options)
        args.append("pipe:1")

        stdin = self.source if self.pipe else asyncio.subprocess.DEVNULL
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stdin=stdin,  # type: ignore
        )

        return process

    async def read(self) -> bytes:
        if self.process is None:
            self.process = await self.create_process()

        if self.process.stdout is None:
            return b""

        data = await self.process.stdout.read(_opus.PACKET_SIZE)
        if len(data) != _opus.PACKET_SIZE:
            return b""

        return data

    async def close(self) -> None:
        if self.process:
            try:
                self.process.kill()
                await self.process.wait()
            except ProcessLookupError:
                pass

            self.process = None


class AudioPlayer:
    def __init__(self, protocol: VoiceProtocol, stream: AudioStream) -> None:
        self.stream = stream
        self.protocol = protocol
        self.loop = protocol._loop
        self.delay = _opus.FRAME_DURATION / 1000

        self._volume = 1.0
        self._resumed = asyncio.Event()
        self._resumed.set()
        self._waiter: Optional[asyncio.Task] = None

    async def _play(self) -> None:
        self._start = time.perf_counter()
        self.loops = 0

        await self.protocol.websocket.speak(state=SpeakingState.VOICE)

        async with self.stream:
            async for packet in self.stream:
                self.loops += 1

                if self.is_paused():
                    await self._resumed.wait()

                transformed = audioop.mul(packet, 2, self._volume)
                await self.protocol.send_voice_packet(transformed)

                # Shamelessly copied from discord.py
                next_time = self._start + self.delay * self.loops
                delay = max(0, self.delay + (next_time - time.perf_counter()))

                await asyncio.sleep(delay)

        await self.protocol.websocket.speak(state=SpeakingState.NONE)

    def play(self) -> AudioPlayer:
        """
        Starts playing the audio stream.
        """
        self._waiter = self.loop.create_task(self._play())
        return self

    def is_playing(self) -> bool:
        """
        Checks if the stream is currently playing.
        """
        return self._waiter is not None and not self._waiter.done()

    async def stop(self) -> None:
        """
        Stops the player.
        """
        if self._waiter is not None:
            if not self._waiter.done():
                self._waiter.cancel()

            self._waiter = None

        await self.protocol.websocket.speak(state=SpeakingState.NONE)

    async def wait(self) -> None:
        """
        Waits for the player to finish.

        """
        if self._waiter is not None:
            try:
                await self._waiter
            except asyncio.CancelledError:
                pass

    def pause(self) -> AudioPlayer:
        """
        Pauses the player.

        """
        self._resumed.clear()
        return self

    def resume(self) -> AudioPlayer:
        """
        Resumes the player.

        """
        self._resumed.set()
        return self

    def is_paused(self) -> bool:
        """
        Whether the player is paused.

        """
        return not self._resumed.is_set()

    def set_volume(self, volume: float) -> AudioPlayer:
        """
        Sets the volume. The volume passed in must be between 0.0 and 2.0.

        Parameters:
            volume (float): The volume to set the player to.

        """
        self._volume = min(max(0.0, volume), 2.0)
        return self

    @property
    def volume(self) -> float:
        """
        The current volume of the player.

        """
        return self._volume
