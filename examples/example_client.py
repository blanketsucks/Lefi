from __future__ import annotations

import os

import lefi

client = lefi.Client(os.getenv("DISCORD_TOKEN"), intents=lefi.Intents.all())  # type: ignore


@client.on("ready")
async def on_ready(_: lefi.User) -> None:
    print(f"[LOGGED IN]: {client.user.id}")


@client.on("message_create")
async def on_message(message: lefi.Message) -> None:
    if message.content.startswith("!ping") and message.author is not client.user:

        embed: lefi.Embed = lefi.Embed(color=0x3455EB)
        embed.add_field(name="Websocket ping!", value=f"{client.ws.latency:.2f}ms")

        await message.channel.send(embeds=[embed])

    print(f"[RECV MESSAGE]: {message.author.id}: {message.content}")


client.run()
