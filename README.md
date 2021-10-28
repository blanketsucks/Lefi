# Lefi
[![Documentation Status](https://readthedocs.org/projects/lefi/badge/?version=latest)](https://lefi.readthedocs.io/en/latest/?badge=latest)
![Pytest](https://github.com/an-dyy/Lefi/actions/workflows/run-pytest.yml/badge.svg?event=push)
![Mypy](https://github.com/an-dyy/Lefi/actions/workflows/mypy.yml/badge.svg?event=push)

A discord API wrapper focused on clean code, and usability

## Installation

1. Poetry

   ```
   poetry add lefi
   ```

2. Pip
   ```
   pip install lefi
   ```

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
    async def on_ready(user: lefi.User) -> None:
        print(f"LOGGED IN AS {client_user.id}") # You can also access `client.user`

    @client.on("message_create")
    async def on_message_create(message: lefi.Message) -> None:
        print(message)

    await client.start()


asyncio.run(main())
```

## Documentation
[Here!](https://lefi.readthedocs.io/en/latest/)

## Contributing
1. If you plan on contributing please open an issue beforehand
2. Fork the repo, and setup the poetry env (with dev dependencies)
3. Install pre-commit hooks (*makes it a lot easier for me*)
    ```
    pre-commit install
    ```

## Contributors

- [blanketsucks](https://github.com/blanketsucks) - collaborator
- [an-dyy](https://github.com/an-dyy) - creator and maintainer

