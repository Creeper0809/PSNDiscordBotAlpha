import os

import discord.utils
from discord import Intents, Game, Status
from dotenv import load_dotenv

import Datamodel
from discord.ext import commands


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="",
            intents=Intents.all(),
            sync_command=True,
            application_id=os.environ.get("APPLIOCATIONCODE")
        )
        self.initial_extension = [
            "Cogs.CommonCommand",
            "Cogs.RPGCommand"
        ]

    async def setup_hook(self):
        for ext in self.initial_extension:
            await self.load_extension(ext)
        await bot.tree.sync()
    async def on_command_error(self, context, exception):
        if isinstance(exception, commands.CommandNotFound):
            pass
    async def on_ready(self):
        print("login")
        print(self.user.name)
        print(self.user.id)
        print("===============")
        game = Game("....")
        await self.change_presence(status=Status.online, activity=game)
        all_guild_emojis = {}
        for guild in self.guilds:
            emojis = await guild.fetch_emojis()
            for emoji in emojis:
                all_guild_emojis[emoji.name] = discord.utils.get(bot.emojis,name = emoji.name)
        Datamodel.set_emoji(all_guild_emojis)

Datamodel.makeJson()
load_dotenv()
Datamodel.makeDB()
bot = MyBot()
bot.run(os.environ.get("TOKEN"))
