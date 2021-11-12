from typing import Any, Dict, Optional, Tuple
import youtube_dl
import asyncio
import os

import lefi
import lefi.voice  # make sure to have PyNaCl installed
from lefi.exts import commands

youtube_dl_options = {
    "format": "bestaudio/best",
    "quite": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
}


class MusicPlugin(commands.Plugin):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ytdl = youtube_dl.YoutubeDL(youtube_dl_options)

    def extract(self, url: str, *, download: bool = False) -> Tuple[str, str]:
        data: Dict[str, Any] = self.ytdl.extract_info(url, download=download)  # type: ignore

        if entries := data.get("entries", []):
            data = entries[0]

        if download:
            return self.ytdl.prepare_filename(data), data["title"]  # type: ignore

        return data["url"], data["title"]

    async def ensure_voice(
        self, ctx: commands.Context
    ) -> Optional[lefi.voice.VoiceClient]:
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return None

        voice = ctx.guild.voice_client
        if not voice:
            await ctx.send("Not connected to a voice channel.")
            return None

        return voice

    @commands.command()
    async def join(self, ctx: commands.Context):
        if not ctx.guild or not isinstance(ctx.author, lefi.Member):
            return await ctx.send("This command can only be used in a server.")

        if ctx.guild.voice_client:
            return await ctx.send("Already connected to a voice channel.")

        voice = ctx.author.voice
        if voice:
            if not voice.channel:
                return await ctx.send("Failed to join the voice channel.")

            await voice.channel.connect()
        else:
            await ctx.send("You are not connected to a voice channel.")

    @commands.command()
    async def leave(self, ctx: commands.Context):
        voice = await self.ensure_voice(ctx)
        if not voice:
            return

        if voice.player:
            await voice.player.stop()

        await voice.channel.disconnect()

    @commands.command()
    async def play(self, ctx: commands.Context, url: str):
        voice = await self.ensure_voice(ctx)
        if not voice:
            return

        if voice.is_playing():
            return await ctx.send("Already playing.")

        source, title = await asyncio.to_thread(self.extract, url)
        stream = lefi.voice.FFmpegAudioStream(source)

        player = voice.play(stream)
        await player.wait()

        await ctx.send(f"Finished playing {title}.")

    @commands.command()
    async def volume(self, ctx: commands.Context, volume: int):
        voice = await self.ensure_voice(ctx)
        if not voice:
            return

        if not voice.player:
            return await ctx.send("Nothing is playing.")

        voice.player.set_volume(volume / 100)

    @commands.command()
    async def pause(self, ctx: commands.Context):
        voice = await self.ensure_voice(ctx)
        if not voice:
            return

        if not voice.player:
            return await ctx.send("Nothing is playing.")

        if voice.player.is_paused():
            return await ctx.send("Already paused.")

        voice.player.pause()

    @commands.command()
    async def resume(self, ctx: commands.Context):
        voice = await self.ensure_voice(ctx)
        if not voice:
            return

        if not voice.player:
            return await ctx.send("Nothing is playing.")

        if not voice.player.is_paused():
            return await ctx.send("Already resumed.")

        voice.player.resume()

    @commands.command()
    async def stop(self, ctx: commands.Context):
        voice = await self.ensure_voice(ctx)
        if not voice:
            return

        if not voice.player:
            return await ctx.send("Nothing is playing.")

        await voice.player.stop()


bot = commands.Bot(
    prefix="!",
    token=os.getenv("DISCORD_TOKEN"),  # type: ignore
    intents=lefi.Intents.all(),
)

bot.add_plugin(MusicPlugin)
bot.run()
