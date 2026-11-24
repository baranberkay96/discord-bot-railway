"""/tag: saved snippets per server (FAQ answers, rules, links), stored in Postgres."""
from __future__ import annotations

import re

import discord
from discord import app_commands
from discord.ext import commands

NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
MAX_TAGS_PER_SERVER = 500


def _can_manage(interaction: discord.Interaction, owner_id: int) -> bool:
    perms = getattr(interaction.user, "guild_permissions", None)
    return interaction.user.id == owner_id or bool(perms and perms.manage_messages)


@app_commands.guild_only()
class Tags(commands.GroupCog, group_name="tag", group_description="Saved snippets for this server"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    async def _need_db(self, interaction: discord.Interaction) -> bool:
        if self.bot.pool is None:
            await interaction.response.send_message("Tags need the database (DATABASE_URL).", ephemeral=True)
            return False
        return True

    async def _names(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        if self.bot.pool is None or interaction.guild_id is None:
            return []
        rows = await self.bot.pool.fetch(
            "SELECT name FROM tags WHERE guild_id = $1 AND name LIKE $2 ORDER BY uses DESC, name LIMIT 25",
            interaction.guild_id, current.lower().replace("%", "").replace("_", r"\_") + "%",
        )
        return [app_commands.Choice(name=r["name"], value=r["name"]) for r in rows]

    @app_commands.command(name="show", description="Post a saved tag in this channel")
    @app_commands.describe(name="Tag name")
    async def show(self, interaction: discord.Interaction, name: str) -> None:
        if not await self._need_db(interaction):
            return
        content = await self.bot.pool.fetchval(
            "UPDATE tags SET uses = uses + 1 WHERE guild_id = $1 AND name = $2 RETURNING content",
            interaction.guild_id, name.lower(),
        )
        if content is None:
            await interaction.response.send_message(f"No tag named `{name}`.", ephemeral=True)
            return
        await interaction.response.send_message(content, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="set", description="Create or update a tag")
    @app_commands.describe(name="Lowercase letters, digits, - and _ (max 32)", content="What the tag posts")
    async def set_(
        self, interaction: discord.Interaction, name: str, content: app_commands.Range[str, 1, 2000]
    ) -> None:
        if not await self._need_db(interaction):
            return
        name = name.lower()
        if not NAME.match(name):
            await interaction.response.send_message(
                "Tag names use lowercase letters, digits, - and _ (max 32 characters).", ephemeral=True
            )
            return
        pool = self.bot.pool
        owner = await pool.fetchval("SELECT owner_id FROM tags WHERE guild_id = $1 AND name = $2",
                                    interaction.guild_id, name)
        if owner is not None and not _can_manage(interaction, owner):
            await interaction.response.send_message("Only the tag's creator or moderators can change it.",
                                                    ephemeral=True)
            return
        if owner is None:
            total = await pool.fetchval("SELECT count(*) FROM tags WHERE guild_id = $1", interaction.guild_id)
            if total >= MAX_TAGS_PER_SERVER:
                await interaction.response.send_message("This server has reached the tag limit.", ephemeral=True)
                return
        await pool.execute(
            "INSERT INTO tags (guild_id, name, content, owner_id) VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (guild_id, name) DO UPDATE SET content = EXCLUDED.content, updated_at = now()",
            interaction.guild_id, name, content, interaction.user.id,
        )
        verb = "updated" if owner is not None else "created"
        await interaction.response.send_message(f"Tag `{name}` {verb}.", ephemeral=True)

    @app_commands.command(name="list", description="All tags of this server")
    async def list_(self, interaction: discord.Interaction) -> None:
        if not await self._need_db(interaction):
            return
        rows = await self.bot.pool.fetch(
            "SELECT name, uses FROM tags WHERE guild_id = $1 ORDER BY name LIMIT 200", interaction.guild_id
        )
        if not rows:
            await interaction.response.send_message("No tags yet. Create one with `/tag set`.", ephemeral=True)
            return
        text = ", ".join(f"`{r['name']}` ({r['uses']})" for r in rows)
        await interaction.response.send_message(text[:1990], ephemeral=True)

    @app_commands.command(name="delete", description="Delete a tag you created (moderators: any tag)")
    @app_commands.describe(name="Tag name")
    async def delete(self, interaction: discord.Interaction, name: str) -> None:
        if not await self._need_db(interaction):
            return
        pool = self.bot.pool
        owner = await pool.fetchval("SELECT owner_id FROM tags WHERE guild_id = $1 AND name = $2",
                                    interaction.guild_id, name.lower())
        if owner is None:
            await interaction.response.send_message(f"No tag named `{name}`.", ephemeral=True)
            return
        if not _can_manage(interaction, owner):
            await interaction.response.send_message("Only the tag's creator or moderators can delete it.",
                                                    ephemeral=True)
            return
        await pool.execute("DELETE FROM tags WHERE guild_id = $1 AND name = $2", interaction.guild_id, name.lower())
        await interaction.response.send_message(f"Tag `{name.lower()}` deleted.", ephemeral=True)

    @show.autocomplete("name")
    async def _show_names(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._names(interaction, current)

    @delete.autocomplete("name")
    async def _delete_names(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self._names(interaction, current)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tags(bot))
