from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from .command import Command
from .context import Context
from ..errors import CheckFailed, CommandOnCooldown

__all__ = ("Handler",)


class Handler:
    def __init__(self, ctx: Context):
        self.context = ctx

    async def invoke(self) -> Any:
        assert self.context.command is not None

        command: Command = self.context.command
        cooldown = getattr(command, "cooldown", None)
        ctx = self.context
        parser = ctx.parser
        parser.command = command

        kwargs, args = await parser.parse_arguments()
        if all(check(ctx) for check in command.checks):

            async def run_command(ctx: Context) -> Any:
                if command.parent is not None:
                    return await command(command.parent, ctx, *args, **kwargs)

                return await command(ctx, *args, **kwargs)

            if cooldown is not None:
                if cooldown.get_cooldown_reset(ctx.message) is None:
                    cooldown.set_cooldown_time(ctx.message)

                if cooldown._check_cooldown(ctx.message):
                    cooldown._update_cooldown(ctx.message)
                    return await run_command(ctx)

                cooldown_data = cooldown.get_cooldown_reset(ctx.message)
                return ctx.bot._state.dispatch(
                    "command_error", ctx, CommandOnCooldown(cooldown_data.retry_after)  # type: ignore
                )

            return await run_command(ctx)

        return ctx.bot._state.dispatch("command_error", ctx, CheckFailed)

    def __enter__(self) -> Handler:
        with contextlib.suppress():
            self.can_run = self.context.bot._check(self.context)

        return self

    def __exit__(self, *exception) -> bool:
        _, error, _ = exception

        if error is not None:
            self.context.bot._state.dispatch("command_error", self.context, error)

        return True
