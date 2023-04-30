import asyncio
import random
from collections import deque
from typing import Any

import discord
from discord import ButtonStyle, Interaction, SelectOption, InteractionType
from discord.ext import commands
from discord.ui import Button, View, Select

import Datamodel
import Skills


class RPGCommand(commands.Cog):
    combat_user = {}

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.group(aliases=["ㄷㅈ", "던전"])
    async def dungeon(self, ctx):
        user: Datamodel.User = Datamodel.get_userInfo(ctx.message.author.id)
        if user is None:
            await ctx.send('이 컨텐츠를 즐기기전에 회원가입부터 하십시오')
            return
        if ctx.invoked_subcommand is not None:
            return
        embed = discord.Embed(title="PWN봇의 RPG!",
                              description="더 자세한 명령어는 //던전 {도움말,도움,help}")
        await ctx.send(embed=embed)

    @dungeon.command(aliases=["도움말", "도움", "help"])
    async def dungeon_help(self, ctx):
        embed = discord.Embed(title="RPG 명령어")
        commands = "던전은 ㄷㅈ으로 생략 가능.\n"
        commands += "던전 입장 - 던전에 입장합니다.\n"
        commands += "던전 스탯 - 내 정보를 엽니다.\n"
        commands += "던전 설명 {아이템 이름} - 아이템의 대한 설명을 보여줍니다.\n"
        commands += "던전 장착 {아이템 이름} - 선택한 아이템을 장착합니다.\n"
        commands += "던전 해제 - 아이템을 장착해제합니다.\n"
        commands += "던전 이름짓기 {이름} - 이름을 변경합니다.\n"
        debug_command = "던전 디버그아이템추가 {아이템 이름} - 디버그의 힘을 빌어 아이템을 추가합니다.\n"
        debug_command += "던전 디버그아이템강화 {아이템 이름} - 디버그의 힘을 빌어 아이템을 강화합니다.\n"
        debug_command += "던전 디버그체력회복 - 디버그의 힘을 빌어 체력을 회복합니다.\n"
        embed.add_field(name="명령어 목록", value=commands, inline=False)
        embed.add_field(name="디버그 명령어", value=debug_command, inline=False)
        embed.add_field(name="미완성 명령어", value="")
        await ctx.send(embed=embed)

    @dungeon.command(name="입장")
    async def dungeon_join(self, ctx):
        userinfo: Datamodel.User = Datamodel.get_userInfo(ctx.message.author.id)
        if userinfo.id in self.combat_user:
            await ctx.send('이미 전투중입니다')
            return
        if userinfo.now_hp == 0:
            await ctx.send('체력회복부터 해주십시오')
            return
        self.combat_user[userinfo.id] = {
            "나가기": False,
            "선택던전": None,
            "임베드": None,
            "전투텍스트": deque(maxlen=5),
            "이벤트중": False
        }
        dungeons = Datamodel.get_all_dungeon()
        view = View(timeout=60)
        dungeon_list = list()
        for temp_dungeon in dungeons:
            dungeon_list.append(SelectOption(
                label=temp_dungeon.name,
                description=f"출입가능레벨:{temp_dungeon.min_level}",
                value=temp_dungeon.name
            ))
        selects = Select(options=dungeon_list, min_values=1, max_values=1)

        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            dungeon = Datamodel.get_dungeon_by_name(selects.values[0])
            view.on_timeout = View.on_timeout
            view.add_item(enter)
            self.combat_user[userinfo.id]["선택던전"] = dungeon
            await interaction.response.edit_message(view=view, embed=dungeon.get_description())

        selects.callback = select_callback

        enter = Button(label="입장하기", style=ButtonStyle.green)

        async def enter_callback(interaction: Interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            select_dungeon = self.combat_user[userinfo.id]["선택던전"]
            if select_dungeon is None:
                await ctx.send('던전부터 선택해주십시오.')
                return
            await interaction.response.defer()
            await deleteEmbed(interaction.message, 0)
            await self.explore_dungeon(ctx, userinfo)

        enter.callback = enter_callback
        button2 = Button(label="취소", style=ButtonStyle.red)

        async def close_callback(interaction: Interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            await deleteEmbed(interaction.message, 1)
            del self.combat_user[userinfo.id]
            await interaction.response.defer()

        async def close():
            await ctx.send("응답시간 초과")
            await deleteEmbed(self.combat_user[userinfo.id]["임베드"], 1)
            del self.combat_user[userinfo.id]

        button2.callback = close_callback
        view.add_item(selects)
        view.add_item(button2)
        view.on_timeout = close
        self.combat_user[userinfo.id]["임베드"] = await ctx.send(view=view)

    @dungeon.command(name="스탯")
    async def my_info(self, ctx):
        await ctx.send(view=RPGInfo(ctx.message.author.id, ctx.message.author.id))

    @dungeon.command(name="도감")
    async def item_dic(self, ctx,page : int):
        if page < 1:
            await ctx.send("1 이상의 숫자를 입력해주십시오")
            return
        a = list(Datamodel.ItemTable.values())
        length = min(len(a),page*10)
        items = ""
        for i in range((page-1) * 10,length):
            items += a[i]["name"] + '\n'
        embed = discord.Embed(title="아이템 목록",description=items)
        embed.set_footer(text=f"page : {page}")
        await ctx.send(embed = embed)
    @dungeon.command(name="유저보기")
    async def check_another_user(self, ctx, user: discord.User):
        await ctx.send(view=RPGInfo(ctx.message.author.id, user.id))

    @dungeon.command(name="이름짓기")
    async def change_name(self, ctx, *, message):
        user: Datamodel.User = Datamodel.get_userInfo(ctx.message.author.id)
        user.name = message
        Datamodel.update_datamodel(user)
        await ctx.send(f"{message}로 이름 변경 완료")

    @dungeon.command(name="장착")
    async def use_item(self, ctx, *, message):
        item_name = message.replace(" ", "")
        if Datamodel.getItem(item_name) is None:
            return
        item_list = Datamodel.get_inv_item_by_item_name(item_name, ctx.message.author.id)
        if len(item_list) == 0:
            await ctx.send("가지고 있는 아이템이 아닙니다.")
            return
        view = View(timeout=60)
        item_selection_option = list()
        for item in item_list:
            if item.quantity - Datamodel.is_equiped(item.id) == 0:
                continue
            item_selection_option.append(SelectOption(
                label=item.item.name,
                description=f"강화 횟수: {item.item.get_upgrade_point_and_caculate_spac()}번",
                value=item.id
            ))
        selects = Select(options=item_selection_option, min_values=1, max_values=1)
        enter = Button(label="장착", style=ButtonStyle.green)
        button2 = Button(label="취소", style=ButtonStyle.red)

        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            item = Datamodel.get_inv_item_by_id(selects.values[0])
            view.on_timeout = View.on_timeout
            await interaction.response.edit_message(embed=item.get_description_is_hanced(ctx.message.author.id))

        selects.callback = select_callback

        async def enter_callback(interaction: Interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            text = Datamodel.get_inv_item_by_id(selects.values[0]).use(ctx.message.author.id)
            await interaction.response.send_message(text)
            await deleteEmbed(interaction.message, 0)

        enter.callback = enter_callback

        async def close_callback(interaction: Interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            await deleteEmbed(interaction.message, 0)
            await interaction.response.defer()

        button2.callback = close_callback
        view.add_item(selects)
        view.add_item(enter)
        view.add_item(button2)
        await ctx.send(view=view)

    @dungeon.command(name="설명")
    async def show_item_description(self, ctx, *, message):
        item = Datamodel.getItem(message.replace(" ", ""))
        if item is None:
            await ctx.send("없는 아이템입니다.")
            return
        await ctx.send(embed=item.get_description())

    @dungeon.command(name="디버그강화")
    async def debug_upgrade(self, ctx, *, message):
        item_name = message.replace(" ", "")
        if Datamodel.getItem(item_name) is None:
            return
        item_list = Datamodel.get_inv_item_by_item_name(item_name, ctx.message.author.id)
        if len(item_list) == 0:
            await ctx.send("가지고 있는 아이템이 아닙니다.")
            return
        view = View(timeout=60)
        item_selection_option = list()
        for item in item_list:
            if item.quantity - Datamodel.is_equiped(item.id) == 0:
                continue
            item_selection_option.append(SelectOption(
                label=item.item.name,
                description=f"강화 횟수: {item.item.get_upgrade_point_and_caculate_spac()}번",
                value=item.id
            ))

        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            item = Datamodel.get_inv_item_by_id(selects.values[0])
            view.on_timeout = View.on_timeout
            await interaction.response.edit_message(embed=item.get_description_is_hanced(ctx.message.author.id))

        async def select2_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            view.on_timeout = View.on_timeout
            item = Datamodel.get_inv_item_by_id(selects.values[0])
            embed = item.get_description_is_hanced(ctx.message.author.id)
            embed.add_field(name="적용하려는 주문서", value=selects2.values[0])
            await interaction.response.edit_message(embed=embed)

        async def yes_callback(interaction):
            id = Datamodel.upgrade_equip(selects.values[0], selects2.values[0])
            item = Datamodel.get_inv_item_by_id(id)
            await ctx.send(f"아이템 {item.name}가 {selects2.values[0]}으로 인해 강화 되었습니다.")
            await interaction.response.defer()
            await deleteEmbed(embed_message, 1)

        async def no_callback(interaction):
            await deleteEmbed(embed_message, 1)
            await ctx.send("강화하지 않기로 했다")
            await interaction.response.defer()

        async def interaction_check(interaction: discord.Interaction):
            if ctx.message.author.id != interaction.user.id:
                return False
            return True

        selects = Select(options=item_selection_option, min_values=1, max_values=1)
        selects.callback = select_callback
        selects2 = Select(options=[SelectOption(label="올스탯 증가", description="모든 스탯이 5씩 증가한다", value="올스탯증가")],
                          min_values=1, max_values=1)
        selects2.callback = select2_callback
        button_yes = Button(label="강화", style=ButtonStyle.green)
        button_no = Button(label="취소", style=ButtonStyle.red)
        button_yes.callback = yes_callback
        button_no.callback = no_callback
        view.interaction_check = interaction_check
        view.add_item(selects)
        view.add_item(selects2)
        view.add_item(button_yes)
        view.add_item(button_no)
        embed_message = await ctx.send(view=view)

    @dungeon.command(name="디버그아이템추가")
    async def debug_item_add(self, ctx, *, message):
        item_name = message.replace(" ", "")
        if Datamodel.getItem(item_name) is None:
            return
        Datamodel.add_new_item_to_inventory(ctx.message.author.id, item_name, 1)
        await ctx.send(f"디버그의 힘으로 아이템 {message}가 추가 되었다.")

    @dungeon.command(name="디버그체력회복")
    async def debug_full_condition(self, ctx):
        user: Datamodel.User = Datamodel.get_userInfo(ctx.message.author.id)
        user.now_hp = 1
        Datamodel.update_instance_datamodel(user)
        await ctx.send(f"디버그의 힘으로 체력이 회복 되었다")

    @dungeon.command(name="해제")
    async def unequip_item(self, ctx):
        equiped_items = Datamodel.get_user_equipinv(ctx.message.author.id)
        if len(equiped_items) > 0:
            await ctx.send("장착하신 장비가 없습니다")
            return
        item_selection_option = list()
        for item in equiped_items:
            if item.item.type == "스킬":
                continue
            item_selection_option.append(SelectOption(
                label=item.item.name,
                description=f"강화 횟수: {item.item.get_upgrade_point_and_caculate_spac()}번 장착위치:{Datamodel.EquipPos[item.item.equip_pos]}",
                value=item.id
            ))

        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            Datamodel.remove_equip_info(selects.values[0])
            await interaction.response.send_message("장착해제 완료")
            await deleteEmbed(interaction.message, 1)

        selects = Select(options=item_selection_option, min_values=1, max_values=1)
        selects.callback = select_callback
        view = View()
        view.add_item(selects)
        await ctx.send(view=view)

    async def explore_dungeon(self, ctx, userinfo):
        dungeon = self.combat_user[userinfo.id]["선택던전"]
        user_combat_data = userinfo.get_combatStat()
        user_dm = self.bot.get_user(int(ctx.message.author.id))

        embed = discord.Embed(title=f"던전: {dungeon.name}", description=f"{dungeon.description}")
        embed.add_field(name="내 정보",
                        value=":heart: 체력:%20s\n" % f"{user_combat_data.get_now_hp()}/{user_combat_data.hp}",
                        inline=False)
        embed.add_field(name="진행 상황", value="", inline=False)
        view = View()
        exitButton = Button(label="나가기", style=ButtonStyle.red)

        async def exit_dungeon(interaction):
            if interaction.user.id != ctx.message.author.id:
                return
            self.combat_user[userinfo.id]["나가기"] = True
            exitButton.label = "나가기(예약됨)"
            await embedMessage.edit(view=view)
            await interaction.response.defer()
            return

        exitButton.callback = exit_dungeon
        view.add_item(exitButton)

        embedMessage = await user_dm.send(embed=embed, view=view)

        events = [self.fightEvent, self.nothing_happend]
        weight = [70, 15]
        queue = deque(maxlen=5)
        while user_combat_data.get_now_hp() != 0 and not self.combat_user[userinfo.id]["나가기"]:
            random_sleep = random.randint(0, 10)
            await asyncio.sleep(random_sleep)
            event = random.choices(events, weight)[0]
            dm_message = await user_dm.send(".")
            random_dot = random.randint(4,7)
            for i in range(random_dot):
                await asyncio.sleep(0.4)
                await dm_message.edit(content="." * ((i%3)+1))
            await asyncio.sleep(0.4)
            await dm_message.edit(content="....!")
            await deleteEmbed(dm_message,1)
            queue.append(await event(ctx, user_combat_data, dungeon, user_dm))
            combat_text = "```"
            for i in range(len(queue)):
                combat_text += queue[i] + '\n'
            combat_text += "```"
            embed.set_field_at(0, name="내 정보",
                               value=":heart: 체력:%20s\n" % f"{user_combat_data.get_now_hp()}/{user_combat_data.hp}",
                               inline=False)
            embed.set_field_at(1, name="진행 상황", value=combat_text, inline=False)
            await embedMessage.edit(embed=embed, view=view)
        await ctx.send(f"{user_dm.display_name}이(가) 던전에서 나왔다.")
        await user_dm.send("던전에서 나왔다.")
        del self.combat_user[userinfo.id]

    async def nothing_happend(self, ctx, user: Datamodel.User, dungeon: Datamodel.Dungeon, user_dm):
        lists = [
            "오늘은 날씨가 좋다",
            "돌맹이를 관찰 했다.",
            "갑자기 비가 오려 한다.",
            "넘어졌다"
        ]
        return random.choice(lists)

    async def fightEvent(self, ctx, user: Datamodel.CombatData, dungeon: Datamodel.Dungeon, user_dm: discord.User):
        monster: Datamodel.Monster = Datamodel.get_monster(random.choice(dungeon.spawn_monster))
        view = CheckYesNo(ctx.message.author.id)
        embed_message = await user_dm.send(view=view, embed=monster.get_Discription())
        try:
            await self.bot.wait_for("interaction", timeout=10.0,
                                    check=lambda interaction: interaction.user.id == ctx.message.author.id)
        except asyncio.TimeoutError:
            await deleteEmbed(embed_message, 1)
            return '도망을 선택했다'
        else:
            if not view.user_response:
                await deleteEmbed(embed_message, 1)
                return "도망을 선택했다"
        monster_combat = monster.get_combatStat()
        combat_text = ""
        embed = discord.Embed(title="전투 시작!", color=discord.Color.red())
        embed.add_field(name=f"{monster_combat.name} 체력", value=f"{monster_combat.get_now_hp()} / {monster_combat.hp}")
        embed.add_field(name=f"{user.name} 체력", value=f"{user.get_now_hp()} / {user.hp}")
        embed.add_field(name="전투 텍스트", value=combat_text, inline=False)
        await embed_message.edit(embed=embed, view=View())

        def attack_each(who, target):
            text = ""
            damage = random.randint(int(who.attack * 0.9), int(who.attack * 1.1))
            target.attacked(damage, who)
            text += f"{target.name}이 {who.name}에 의해 {damage}의 대미지를 받았다 \n"
            text += f"현재 {target.name}의 체력은 {target.get_now_hp()}\n"
            if target.get_now_hp() == 0:
                return text
            damage = random.randint(int(target.attack * 0.9), int(target.attack * 1.1))
            who.attacked(damage, target)
            text += f"{who.name}이 {target.name}에 의해 {damage}의 대미지를 받았다 \n"
            text += f"현재 {who.name}의 체력은 {who.get_now_hp()}\n"
            return text

        while user.get_now_hp() > 0 and monster_combat.get_now_hp() > 0:
            await asyncio.sleep(1)
            user_speed = random.randint(user.speed, 30 + user.speed)
            monster_speed = random.randint(monster_combat.speed, 30 + monster_combat.speed)
            combat_text = attack_each(user, monster_combat) if user_speed > monster_speed else attack_each(
                monster_combat, user)
            embed.set_field_at(0, name=f"{monster_combat.name} 체력",
                               value=f"{monster_combat.get_now_hp()} / {monster.hp}")
            embed.set_field_at(1, name=f"{user.name} 체력", value=f"{user.get_now_hp()} / {user.hp}")
            embed.set_field_at(2, name="전투 텍스트", value=combat_text, inline=False)
            await embed_message.edit(embed=embed)
        temp = Datamodel.get_user(user.id)
        result_embed = discord.Embed(title="전투 결과")
        result_embed.add_field(name=f"{user.name}", value="", inline=True)
        result_embed.add_field(name=f"{monster.name}", value="", inline=True)
        if user.get_now_hp() == 0:
            combat_text = f"{user.name}은 {monster.name}에 의해 쓰러졌다.\n"
            result_embed.color = 0xfe0101
            result_embed.add_field(name="패")
        else:
            combat_text = f"{user.name}은 {monster.name}에게서 승리를 가져왔다! {monster.dropPWN}원 획득.\n"
            for i in monster.drop_item:
                random_num = random.uniform(0, 100)
                if random_num <= i["확률"]:
                    item = Datamodel.getItem(i["아이템"])
                    Datamodel.add_new_item_to_inventory(user.id, i["아이템"], 1)
                    combat_text += f"{item.name}을 획득했다!\n"
            temp.PWN += monster.dropPWN
            result_embed.color = 0x12fe01
            result_embed.add_field(name="승",value="")
        await deleteEmbed(embed_message, 1)
        result_embed.set_footer(text=f"{user_dm.display_name}의 전투")
        await ctx.send(embed=result_embed)
        userinf = Datamodel.get_userInfo(user.id)
        userinf.now_hp = user.now_hp_percentage
        Datamodel.update_datamodel(temp)
        Datamodel.update_instance_datamodel(userinf)
        return combat_text


class RPGInfo(discord.ui.View):
    command_call_user = ""
    want_user = ""
    user: Datamodel.User = None
    inv_next_page = Button(label="다음페이지", style=ButtonStyle.secondary)
    inv_filter = Button(label="필터", style=ButtonStyle.red)
    inv_previous_page = Button(label="이전페이지", style=ButtonStyle.secondary)
    child_item = None
    footer_name = None
    page = 1

    def __init__(self, command_call_user, want_user):
        super().__init__()
        self.command_call_user = command_call_user
        self.want_user = want_user
        self.value = None
        self.child_item = self.children
        self.inv_next_page.callback = self.next_page
        self.inv_previous_page.callback = self.previous_page

    async def interaction_check(self, interaction: discord.Interaction):
        if self.command_call_user != interaction.user.id:
            return False
        self.user = Datamodel.get_userInfo(self.want_user)
        for i in interaction.guild.members:
            if int(self.want_user) == i.id:
                self.footer_name = i.display_name
        return True

    # async def on_error(self, interaction: discord.Interaction, error: Exception, item, /) -> None:
    #     await interaction.response.defer()

    @discord.ui.button(label="정보", style=discord.ButtonStyle.blurple)
    async def my_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.set_normal_menu()
        embed = self.user.get_Discription()
        embed.set_footer(text=f"{self.footer_name}의 소유")
        await interaction.response.edit_message(view=self, embed=embed)

    @discord.ui.button(label="인벤토리", style=discord.ButtonStyle.blurple)
    async def my_inv(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.command_call_user != self.want_user:
            return
        self.set_inv_menu()
        self.page = 1
        if self.user.get_inv_len_byPage(self.page) < 10:
            self.inv_next_page.disabled = True
        if self.page == 1:
            self.inv_previous_page.disabled = True
        await interaction.response.edit_message(view=self, embed=self.user.get_inv_info(self.page))

    @discord.ui.button(label="장비창", style=discord.ButtonStyle.blurple)
    async def my_equip(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.set_normal_menu()
        await interaction.response.edit_message(view=self, embed=self.user.get_equip_item_info())

    async def next_page(self, interaction: discord.Interaction):
        lenth = self.user.get_inv_len_byPage(self.page + 1)
        if lenth < 10:
            self.inv_next_page.disabled = True
        self.page += 1
        self.inv_previous_page.disabled = False
        await interaction.response.edit_message(view=self, embed=self.user.get_inv_info(self.page))

    async def previous_page(self, interaction: discord.Interaction):
        if self.page - 1 == 1:
            self.inv_previous_page.disabled = True
        self.inv_next_page.disabled = False
        self.page -= 1
        await interaction.response.edit_message(view=self, embed=self.user.get_inv_info(self.page))

    def set_inv_menu(self):
        self.clear_items()
        self.add_item(self.child_item[0])
        self.add_item(self.inv_previous_page)
        self.add_item(self.inv_filter)
        self.add_item(self.inv_next_page)
        self.add_item(self.child_item[2])

    def set_normal_menu(self):
        self.clear_items()
        [self.add_item(item) for item in self.child_item]


class CheckYesNo(discord.ui.View):
    command_call_user = ""
    user_response = None

    def __init__(self, command_call_user, ):
        super().__init__()
        self.command_call_user = command_call_user
        self.value = None

    def change_label(self, yes, no):
        a = self.children
        for item in a:
            if item.label == "예":
                item.label = yes
            elif item.label == "아니오":
                item.label = no
        self.clear_items()
        [self.add_item(i) for i in a]

    def insert_item(self, index, item):
        a = self.children
        a.insert(index, item)
        self.clear_items()
        [self.add_item(i) for i in a]

    async def interaction_check(self, interaction: discord.Interaction):
        if self.command_call_user != interaction.user.id:
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item, /) -> None:
        await interaction.response.defer()

    @discord.ui.button(label="예", style=discord.ButtonStyle.blurple)
    async def response_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.user_response = True
        await interaction.response.defer()

    @discord.ui.button(label="아니오", style=discord.ButtonStyle.red)
    async def response_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.user_response = False
        await interaction.response.defer()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        RPGCommand(bot),
    )


async def deleteEmbed(embed_message, second):
    await asyncio.sleep(second)
    await embed_message.delete()
