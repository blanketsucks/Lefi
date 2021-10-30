from __future__ import annotations

import asyncio
from typing import IO, TYPE_CHECKING, Optional, Protocol, Union
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
    def __init__(self, source: IO[bytes]) -> None:
        self.source = source
        self.loop = asyncio.get_running_loop()

    async def read(self) -> bytes:
        data = await self.loop.run_in_executor(
            None, self.source.read, _opus.PACKET_SIZE
        )

        if len(data) != _opus.PACKET_SIZE:
            return b""

        return data

    async def close(self) -> None:
        self.source.close()


class FFmpegAudioStream(BaseAudioStream):
    def __init__(self, source: Union[str, IO[bytes]]):
        self.source = source
        self.process: Optional[asyncio.subprocess.Process] = None

    async def create_process(self):
        kwargs = {
            "-i": self.source,
            "-f": "s16le",
            "-ar": "48000",
            "-ac": "2",
            "-loglevel": "warning",
        }

        args = []
        for k, v in kwargs.items():
            args.extend([k, v])

        args.append("pipe:1")
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
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
            self.process.terminate()
            await self.process.wait()


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
        await self.protocol.websocket.speak(state=SpeakingState.VOICE)

        async with self.stream:
            async for packet in self.stream:
                if self.is_paused():
                    await self._resumed.wait()

                await self.protocol.send_voice_packet(packet)
                await asyncio.sleep(_opus.FRAME_DURATION / 1000)

        await self.protocol.websocket.speak(state=SpeakingState.NONE)

    def play(self) -> AudioPlayer:
        self._waiter = self.loop.create_task(self._play())
        return self

    async def stop(self) -> None:
        if self._waiter is not None:
            if not self._waiter.done():
                self._waiter.cancel()

            self._waiter = None

        await self.protocol.websocket.speak(state=SpeakingState.NONE)

    async def wait(self) -> None:
        if self._waiter is not None:
            await self._waiter

    def pause(self) -> AudioPlayer:
        self._resumed.clear()
        return self

    def resume(self) -> AudioPlayer:
        self._resumed.set()
        return self

    def is_paused(self) -> bool:
        return not self._resumed.is_set()

    def set_volume(self, volume: float) -> AudioPlayer:
        self._volume = min(max(0.0, volume), 5.0)
        return self

    @property
    def volume(self) -> float:
        return self._volume