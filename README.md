# Lefi
A discord API wrapper focused on clean code, and usability

## Installation

1. Poetry

   ```
   poetry add git+https://github.com/an-dyy/Lefi.git --no-dev
   ```
    *Note: if you plan on contributing, omit the `--no-dev` flag.*

2. Pip
   ```
   pip install git+https://github.com/an-dyy/Lefi.git
   ```
   *Note: After stable the wrapper will get a pip package rather then requiring to install from git*

## Example(s)
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

## Documentation
[Here!](https://an-dyy.github.io/Lefi)

## Contributing
1. If you plan on contributing please open an issue beforehand
2. Install pre-commit hooks (*makes it a lot easier for me*)
    ```
    pre-commit install
    ```

## Contributors

- [blanketsucks](https://github.com/blanketsucks) - Contributor
- [an-dyy](https://github.com/an-dyy) - creator and maintainer
