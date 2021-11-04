from __future__ import annotations

import os
import textwrap

import lefi
from lefi.exts import commands

bot = commands.Bot(
    prefix="!",
    token=os.getenv("DISCORD_TOKEN"),  # type: ignore
    intents=lefi.Intents.all(),
)


@bot.on("ready")
async def on_ready(_: lefi.User) -> None:
    print(f"[LOGGED IN]: {bot.user.id}")


@bot.command()
async def ping(ctx: commands.Context) -> None:
    """
    Sends the current websocket latency

    Usage:
        !ping
    """
    embed: lefi.Embed = lefi.Embed(color=0x3455EB)
    embed.add_field(name="Websocket ping!", value=f"{bot.ws.latency:.2f}ms")

    await ctx.send(embeds=[embed])


@bot.command()
@commands.cooldown(1, 1, commands.CooldownType.user)
async def echo(ctx: commands.Context, *, message: str) -> None:
    """
    Echo's the passed in string
    Cooldown is set so a user may only use this once per second.

    Usage:
        !echo <Hello world!>
    """
    await ctx.send(message)


@bot.command()
@commands.check(lambda ctx: ctx.author.id == 270700034985558017)
async def eval(ctx: commands.Context, *, code: str) -> None:
    """
    Evaluates python code

    Usage:
        !eval ```py
        return 2+2
        ```
    """
    cleaned: str = code.strip("```").removeprefix("py")
    final: str = textwrap.indent(cleaned, prefix="\t")

    env: dict = {"_": ctx, "lefi": lefi, "commands": commands, **globals()}

    exec(f"async def eval_():\n{final}", env)

    embed: lefi.Embed = lefi.Embed(color=0x3455EB)
    embed.add_field(name="Evaluating...", value=f"```py\n{await env['eval_']()}```")  # type: ignore

    await ctx.send(embeds=[embed])


bot.run()
