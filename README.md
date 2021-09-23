# Lefi
Work in progress discord API wrapper made in Python

# Example(s)
```py
import os
import asyncio

import lefi


async def main() -> None:
    token = os.getenv(
        "discord_token"
    )  # NOTE: I'm on linux so I can just export, windows might need a `.env`
    client = lefi.Client(token)  # type: ignore

    @client.on("message_create")
    async def message_create(message: lefi.Message) -> None:
        print(message)

    await client.start()


asyncio.run(main())
```

*Note: this is not a serious project*
