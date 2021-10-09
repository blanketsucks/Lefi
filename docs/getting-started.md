## Getting started

# Table of contents
- [Installation](#installing)
- [Basic usage](#examples)

# Installing
To install the wrapper you can use `pip`, `poetry` or any other manager you use.
*Note: It is recommended to use poetry or any other venv when downloading*

* Poetry
    ```
    poetry add git+https://github.com/an-dyy/Lefi.git --no-dev
    ```
    *Note: If you plan on contributing, omit the `--no-dev` flag.*

* Pip
    ```
    pip install git+https://github.com/an-dyy/Lefi.git
    ```

# Examples

```py
import os
import asyncio

import lefi


async def main() -> None:
    token = os.getenv(
        "discord_token"
    )  # NOTE: I'm on linux so I can just export, windows might need a `.env`
    client = lefi.Client(token)  # type: ignore

    @client.once("ready")
    async def on_ready(client_user: lefi.User) -> None:
        print(f"LOGGED IN AS {client_user.id}")

    @client.on("message_create")
    async def message_create(message: lefi.Message) -> None:
        print(message)

    await client.start()


asyncio.run(main())
```
