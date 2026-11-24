"""General commands: /help, /ping, /about."""
from __future__ import annotations

import platform
import time

import discord
from discord import app_commands
from discord.ext import commands


def _duration(seconds: float) -> str:
    seconds = int(seconds)
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    parts = [f"{days}d"] if days else []
    parts += [f"{hours}h"] if hours or days else []
    return " ".join(parts + [f"{minutes}m", f"{secs}s"])


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="List the bot's commands")
    async def help(self, interaction: discord.Interaction) -> None:
        lines = []
        for command in sorted(self.bot.tree.get_commands(), key=lambda c: c.name):
            if isinstance(command, app_commands.Group):
                for sub in command.commands:
                    lines.append(f"`/{command.name} {sub.name}` - {sub.description}")
            else:
                lines.append(f"`/{command.name}` - {command.description}")
        embed = discord.Embed(title="Commands", description="\n".join(lines), color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check the bot's latency and database")
    async def ping(self, interaction: discord.Interaction) -> None:
        gateway_ms = self.bot.latency * 1000
        db_text = "not configured"
        pool = getattr(self.bot, "pool", None)
        if pool is not None:
            start = time.perf_counter()
            await pool.fetchval("SELECT 1")
            db_text = f"{(time.perf_counter() - start) * 1000:.1f} ms"
        await interaction.response.send_message(
            f"Pong! Gateway {gateway_ms:.0f} ms, database {db_text}.", ephemeral=True
        )

    @app_commands.command(name="about", description="Uptime and version of this bot")
    async def about(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title=str(self.bot.user), color=discord.Color.blurple())
        embed.add_field(name="Uptime", value=_duration(time.time() - self.bot.started_at))
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(
            name="Runtime",
            value=f"discord.py {discord.__version__}, Python {platform.python_version()}",
            inline=False,
        )
        embed.set_footer(text=f"Starter v{self.bot.version} on Railway")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
