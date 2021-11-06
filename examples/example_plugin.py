from __future__ import annotations

import os

import lefi
from lefi.exts import commands


class MyPlugin(commands.Plugin):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @commands.Plugin.on("message_create")
    async def on_message(self, message: lefi.Message) -> None:
        print(f"[RECV MESSAGE]: {message.author.id}: {message.content}")

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        """
        Sends the current websocket latency

        Usage:
            !ping
        """
        embed: lefi.Embed = lefi.Embed(color=0x3455EB)
        embed.add_field(name="Websocket ping!", value=f"{self.bot.ws.latency:.2f}ms")

        await ctx.send(embeds=[embed])


bot = commands.Bot(
    prefix="!",
    token=os.getenv("DISCORD_TOKEN"),  # type: ignore
    intents=lefi.Intents.all(),
)


@bot.once("ready")
async def register_plugins(_: lefi.User) -> None:
    """
    You may add plugins inside of `READY` **ONLY** if you are using the `bot.once` decorator.
    As using `once` will cut the callback off the event after running once.

    FIRST RUN: --------->
    SECOND RUN: ---/ --->

    ===GOOD===

    bot.once("ready")
    async def register_plugins(_: lefi.User) -> None:
        bot.add_plugin(MyPlugin)

    ===BAD===

    @bot.on("ready")
    async def register_plugins(_: lefi.User) -> None:
        bot.add_plugin(MyPlugin)

    """
    print(f"[LOGGED IN]: {bot.user.id}")
    bot.add_plugin(MyPlugin)


# Or you can do
# bot.add_plugin(MyPlugin) outside of `bot.once("ready")`

bot.run()
