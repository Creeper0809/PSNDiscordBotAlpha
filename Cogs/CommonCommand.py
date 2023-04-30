import datetime

import discord
from discord.ext import commands

import Datamodel


class CommonCommand(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="회원가입")
    async def 회원가입(self,ctx : discord.ext.commands.Context):
        user = Datamodel.get_user(ctx.message.author.id)
        if user is None:
            Datamodel.add_user(ctx.message.author.id,ctx.message.author.name)
            await ctx.send(content = f"{ctx.message.author.name}의 가입을 정말 축하합니다.")
            return
        await ctx.send(content=f"{ctx.message.author.name}님은 이미 가입한 회원입니다.")

    @commands.command(name="유저정보")
    async def 유저정보(self, ctx, user: discord.User):
        print()

    @commands.command()
    async def 출석체크(self, ctx):
        user: Datamodel.User = Datamodel.get_user(ctx.message.author.id)
        if user is None:
            await ctx.send('회원가입부터 해주십시오.')
            return
        attendance_check = datetime.datetime.strptime(user.attendance_check.strftime('%Y-%m-%d'), '%Y-%m-%d')
        current_date = datetime.datetime.now()
        delta = (current_date - attendance_check).days
        if delta == 0:
            temp = attendance_check.strftime('%m월-%d일')
            await ctx.send(f'다음날에 다시 출석체크를 시도해주세요 \n{temp}에 출석하셨습니다')
        else:
            user.PWN += 1000
            user.attendance_check = current_date
            Datamodel.update_datamodel(user)
            await ctx.send(f'오늘도 출석해주셔서 감사합니다 계좌로 1000원 입급해드렸습니다 ')

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        CommonCommand(bot),
    )