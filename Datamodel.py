import Skills
import json
import os
from abc import abstractmethod, ABCMeta
from enum import Enum

import discord
from sqlalchemy import String, Column, Integer, Date, create_engine, ForeignKey, Text, Float, and_, Double, delete
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, joinedload
from sqlalchemy.types import Enum as EnumType

# 변수들
Base = declarative_base()
RequireExperimentTable = None
ItemTable = None
MonsterTable = None
DungeonTable = None
EquipPos = [
    "",
    "슬롯1",
    "슬롯2",
    "슬롯3",
    "슬롯4",
    "슬롯5",
    "슬롯6",
    "슬롯7",
    "슬롯8",
    "슬롯9",
    "슬롯10",
    "상의",
    "무기"
]

# 데이터 모델
class DB_PSNUser(Base):
    __tablename__ = 'User'
    id = Column(String, primary_key=True)
    discord_name = Column(String)
    PWN = Column(Integer, default=0)
    baekjoon_id = Column(String, default="")
    attendance_check = Column(Date, default="2020-04-21")


class DB_UserInventory(Base):
    __tablename__ = 'UserInventory'
    id = Column(Integer, primary_key=True)
    discord_id = Column(String)
    item_id = Column(String)
    quantity = Column(Integer)


class DB_UserEquipInventory(Base):
    __tablename__ = 'UserEquipInventory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    inv_id = Column(Integer)
    discord_id = Column(String)
    slot = Column(Integer)


class DB_UserInfo(Base):
    __tablename__ = 'UserSpec'
    id = Column(String, primary_key=True)
    name = Column(String, default="무명")
    level = Column(Integer, default=1)
    accumulated_exp = Column(Integer, default=0)
    hp = Column(Integer, default=50)
    now_hp = Column(Double, default=1)
    attack = Column(Integer, default=10)
    ap_attack = Column(Integer, default=0)
    accuracy = Column(Integer, default=3)
    defense = Column(Integer, default=0)
    speed = Column(Integer, default=10)
    stats_remaining = Column(Integer, default=0)
    STR = Column(Integer, default=1)
    DEX = Column(Integer, default=1)
    INT = Column(Integer, default=1)
    LUK = Column(Integer, default=1)

class DB_EnhancedEquipment(Base):
    __tablename__ = 'EnhancedEquipment'
    id = Column(Integer, primary_key=True,autoincrement=True)
    inv_id = Column(Integer)
    scroll_id = Column(Integer)
    used_time = Column(Integer,default=1)

# UTIL
def makeDB():
    global connection_pool
    db_url = f'mysql+pymysql://{os.environ.get("USER")}:{os.environ.get("PASSWORD")}@{os.environ.get("HOST")}' \
             f':{os.environ.get("PORT")}/{os.environ.get("DATABASE")}'
    connection_pool = create_engine(db_url, pool_size=15, max_overflow=15, echo=False, pool_recycle=10)


def set_emoji(emoji):
    global emoji_list
    emoji_list = emoji


def session_decorator(func):
    def wrapper(*args, **kwargs):
        Session = sessionmaker(bind=connection_pool)
        session = Session()
        result = func(session, *args, **kwargs)
        session.close()
        return result

    return wrapper


def dbdata_to_instance(instance_class, *args):
    for db_data in args:
        for key, value in db_data.__dict__.items():
            if key != '_sa_instance_state':
                setattr(instance_class, key, value)
    return instance_class


def makeJson():
    global RequireExperimentTable
    global ItemTable
    global MonsterTable
    global DungeonTable
    with open('json\\RequireExperiment.json', 'r') as f:
        RequireExperimentTable = json.load(f)["rows"]
    with open('json\\PSNBotItemTable.json', 'r', encoding='utf-8') as f:
        ItemTable = json.load(f)
    with open('json\\PSNMonsterTable.json', 'r', encoding='utf-8') as f:
        MonsterTable = json.load(f)
    with open('json\\PSNDungeon.json', 'r', encoding='utf-8') as f:
        DungeonTable = json.load(f)


# READ
@session_decorator
def get_user(session, id):
    return session.query(DB_PSNUser).filter(DB_PSNUser.id == id).first()


@session_decorator
def get_userInfo(session, id):
    result = session.query(DB_UserInfo).filter(DB_UserInfo.id == id).first()
    if result is None:
        return None
    user = dbdata_to_instance(User(), result)
    return user


def get_experimentTable(user):
    for i in range(len(RequireExperimentTable)):
        if RequireExperimentTable[i]["accumulated_experience"] > user.accumulated_exp:
            return RequireExperimentTable[i - 1]
    return None


@session_decorator
def get_userinv_using_paging(session, id,page):
    tables = session.query(DB_UserInventory) \
        .filter(DB_UserInventory.discord_id == id) \
        .limit(10) \
        .offset((page-1) * 10)
    user_inv = list()
    for table in tables:
        inv = dbdata_to_instance(InvItem(), table)
        inv.item = getItem(table.item_id)
        inv.item.inv_id = table.id
        user_inv.append(inv)
    return user_inv

@session_decorator
def get_userinv(session, id):
    tables = session.query(DB_UserInventory) \
        .filter(DB_UserInventory.discord_id == id) \
        .all()
    user_inv = list()
    for table in tables:
        inv = dbdata_to_instance(InvItem(), table)
        inv.item = getItem(table.item_id)
        inv.item.inv_id = table.id
        user_inv.append(inv)
    return user_inv

@session_decorator
def get_inv_item_by_id(session, id):
    item = session.query(DB_UserInventory).filter(DB_UserInventory.id == id).first()
    inv = getItem(item.item_id)
    inv.inv_id = id
    return inv

@session_decorator
def get_inv_item_by_item_name(session,name,userid):
    user_inv = list()
    for table in session.query(DB_UserInventory).filter(and_(DB_UserInventory.item_id == name,DB_UserInventory.discord_id == userid)).all():
        inv = dbdata_to_instance(InvItem(), table)
        inv.item = getItem(table.item_id)
        inv.item.inv_id = table.id
        user_inv.append(inv)
    return user_inv

@session_decorator
def is_equiped(session, id):
    item = session.query(DB_UserEquipInventory).filter(DB_UserEquipInventory.inv_id == id).all()
    return len(item)


@session_decorator
def get_user_equipinv(session, id):
    tables = session.query(DB_UserEquipInventory) \
        .filter(DB_UserEquipInventory.discord_id == id) \
        .all()
    user_inv = list()
    for table in tables:
        inv = dbdata_to_instance(InvEquipItem(), table)
        inv.item = get_inv_item_by_id(table.inv_id)
        inv.item.inv_id = table.inv_id
        user_inv.append(inv)
    return user_inv


def getItem(item_name):
    if item_name not in ItemTable:
        return None
    item = ItemTable[item_name]
    item_type = item["type"]
    if item_type == "장비":
        item = EquipableItem(item)
    elif item_type == "소모품":
        item = ConsumableItem(item)
    elif item_type == "스킬":
        item = SkillItem(item)
    else:
        item = Item(item)
    return item

def get_monster(id):
    id = id.replace(" ", "")
    return Monster(MonsterTable[id])


def get_dungeon_by_name(id):
    id = id.replace(" ", "")
    return Dungeon(DungeonTable[id])


def get_all_dungeon():
    dungeon_list = list()
    for i in DungeonTable:
        dungeon_list.append(Dungeon(DungeonTable[i]))
    return dungeon_list
@session_decorator
def get_enhanced_info(session,inv_id):
    return session.query(DB_EnhancedEquipment).filter(DB_EnhancedEquipment.inv_id == inv_id).all()


# CREATE
@session_decorator
def add_user(session, id, discord_name):
    inv = DB_UserInventory(discord_id=id, item_id="기본공격", quantity=10)
    session.add(DB_PSNUser(id=id, discord_name=discord_name))
    session.add(DB_UserInfo(id=id))
    session.add(inv)
    session.commit()
    for i in range(1, 11):
        session.add(DB_UserEquipInventory(discord_id=id, inv_id=inv.id, slot=i))
    session.commit()

@session_decorator
def add_new_item_to_inventory(session,user_id, item_code, quantity):
    inventory_items = session.query(DB_UserInventory).filter_by(discord_id=user_id, item_id=item_code).all()
    inventory_item = None
    for items in inventory_items:
        if session.query(DB_EnhancedEquipment).filter(DB_EnhancedEquipment.inv_id == items.id).first() is None:
            print("없음")
            inventory_item = items
    if inventory_item is None:
        inventory_item = DB_UserInventory(item_id=item_code, quantity=quantity, discord_id=user_id)
        session.add(inventory_item)
    else:
        inventory_item.quantity += quantity
        if inventory_item.quantity <= 0:
            session.delete(inventory_item)
    session.commit()
    return True

# UPDATE
@session_decorator
def update_instance_datamodel(session, db_model):
    existing_data = session.query(type(db_model.db_type)).get(db_model.id)
    for key, value in db_model.__dict__.items():
        if key != '_sa_instance_state':
            setattr(existing_data, key, value)
    print(existing_data.now_hp,db_model.now_hp)
    session.commit()


@session_decorator
def update_datamodel(session, db_model):
    existing_data = session.query(type(db_model)).get(db_model.id)
    for key, value in db_model.__dict__.items():
        if key != '_sa_instance_state':
            setattr(existing_data, key, value)
    session.commit()

@session_decorator
def upgrade_equip(session,item,used_scroll):
    item_already_upgrade = session.query(DB_EnhancedEquipment).filter(and_(DB_EnhancedEquipment.inv_id == item,DB_EnhancedEquipment.scroll_id == used_scroll)).first()
    if item_already_upgrade is not None:
        item_already_upgrade.used_time += 1
    else:
        items = session.query(DB_UserInventory).filter(DB_UserInventory.id == item).first()
        items.quantity -= 1
        new_upgraded_item = DB_UserInventory(item_id = items.item_id,discord_id = items.discord_id,quantity = 1)
        session.add(new_upgraded_item)
        session.commit()
        new_upgrade_info = DB_EnhancedEquipment(inv_id = new_upgraded_item.id,scroll_id = used_scroll)
        session.add(new_upgrade_info)
        if items.quantity == 0:
            session.delete(items)
    session.commit()
    return new_upgraded_item.id

# REMOVE
@session_decorator
def remove_equip_info(session,inv_id):
    session.execute(delete(DB_UserEquipInventory).where(DB_UserEquipInventory.id == inv_id))
    session.commit()

# RPGGAME

class CombatData:

    def __init__(self,data):
        self.id = data.id
        self.name = data.name
        self.attack = data.attack
        self.hp = data.hp
        self.ap_attack = data.ap_attack
        self.defense = data.defense
        self.speed = data.speed
        self.now_hp_percentage = data.now_hp

    def set_plus_spac(self,attack,hp,ap_attack,defense):
        self.attack += attack
        self.hp += hp
        self.ap_attack += ap_attack
        self.defense += defense

    def get_now_hp(self):
        return int(self.hp * self.now_hp_percentage)
    def attacked(self,damage,attacker):
        self.now_hp_percentage = Skills.clamp(self.get_now_hp() - damage, 0, self.hp)/ self.hp

    def attack_target(self):
        pass

class Character(metaclass=ABCMeta):
    id: str
    name: str
    level: int
    hp: int
    now_hp: int
    attack: int
    ap_attack: int
    defense: int
    speed: int
    skill = list()
    passive = list()
    def get_spac(self):
        spac = ""
        spac += ":heart: 체력:%20s\n" % f"{self.hp}"
        spac += ":crossed_swords: 공격력:%20s\n" % f"{self.attack}"
        spac += ":magic_wand: 마법공격력:%20s\n" % f"{self.ap_attack}"
        spac += ":shield: 방어력:%20s\n" % f"{self.defense}"
        spac += ":boot: 민첩도:%20s" % f"{self.speed}"
        return spac

    def get_Discription(self):
        embed = discord.Embed()
        embed.set_author(name=f"{self.name}의 정보")
        embed.add_field(name="레벨", value=self.level)
        embed.add_field(name="스펙", value=self.get_spac(), inline=True)
        return embed

    def get_combatStat(self):
        return CombatData(self)


class User(Character):
    db_type = DB_UserInfo()
    accumulated_exp: int
    accuracy: int
    stats_remaining: int
    plus_attack : int = 0
    plus_hp: int= 0
    plus_ap_attack: int= 0
    plus_defense: int= 0
    def caculate_plus_spac(self):
        equipment = get_user_equipinv(self.id)
        for i in equipment:
            if i.item.type == "스킬":
                continue
            i.item.get_upgrade_point_and_caculate_spac()
            self.plus_attack += i.item.total_attack
            self.plus_hp += i.item.total_hp
            self.plus_defense += i.item.total_defense
            self.plus_ap_attack += i.item.total_ap_attack


    def get_combatStat(self):
        self.caculate_plus_spac()
        combat = CombatData(self)
        combat.set_plus_spac(self.plus_attack,self.plus_hp,self.ap_attack,self.defense)
        return combat

    def get_Discription(self):
        embed = discord.Embed()
        level = get_experimentTable(self)
        now = self.accumulated_exp - level["accumulated_experience"]
        self.caculate_plus_spac()
        spac = ""
        spac += f":heart: 체력: {int((self.hp + self.plus_hp)*self.now_hp)}/{self.hp + self.plus_hp}({self.hp}+{self.plus_hp}) \n"
        spac += f":crossed_swords: 공격력: {self.attack + self.plus_attack}({self.attack}+{self.plus_attack})\n"
        spac += f":magic_wand: 마법공격력: {self.ap_attack + self.plus_ap_attack}({self.ap_attack}+{self.plus_ap_attack})\n"
        spac += f":shield: 방어력: {self.defense + self.plus_defense}({self.defense}+{self.plus_defense})\n"
        spac += f":boot: 민첩도:{self.speed}"

        embed.set_author(name=f"{self.name}의 정보")
        embed.add_field(name="레벨", value=f"{self.level} (EXP:{now}/%d)"% level["required_experience"], inline=False)
        embed.add_field(name="스펙", value=spac, inline=True)
        return embed
    def get_inv_len_byPage(self,page):
        return len(get_userinv_using_paging(self.id,page))

    def get_inv_info(self,page):
        items = ""
        value = ""
        embed = discord.Embed(title=f"{self.name}의 인벤토리")
        tables = get_userinv_using_paging(self.id,page)
        for inv_item in tables:
            equiped_count = is_equiped(inv_item.id)
            if inv_item.quantity - equiped_count == 0:
                continue
            else:
                items += inv_item.item.name
                upgrade = inv_item.item.get_upgrade_point_and_caculate_spac()
                if upgrade > 0:
                    items += f" + {upgrade}({inv_item.item.type})\n"
                else:
                    items += f"({inv_item.item.type})\n"
                value += f"{inv_item.quantity - equiped_count}\n"
        embed.add_field(name="아이템", value=items.rstrip())
        embed.add_field(name="개수", value=value.rstrip())
        embed.set_footer(text=f"page:{page}")
        return embed

    def get_equip_item_info(self):
        items = ""
        value = ""
        equip_items = get_user_equipinv(self.id)
        embed = discord.Embed(title=f"{self.name}의 장착 장비")
        skill_item = ""
        count = 0
        for invitem in equip_items:
            if invitem.item.type == "스킬":
                emoji = emoji_list[invitem.item.emoji_id]
                skill_item += str(emoji)
                count += 1
                if count % 5 == 0:
                    skill_item += '\n'
            else:
                items += invitem.item.name
                upgrade = invitem.item.get_upgrade_point_and_caculate_spac()
                if upgrade > 0:
                    items += f" + {upgrade}\n"
                else:
                    items += f"\n"
                value += f"{EquipPos[invitem.item.equip_pos]}\n"
        embed.add_field(name="아이템", value=items.rstrip(),inline=True)
        embed.add_field(name="장착 위치", value=value.rstrip(),inline=True)
        embed.add_field(name="스킬", value=skill_item.rstrip(),inline=False)
        return embed

class Bundle:
    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)

    def __str__(self):
        attr = ""
        for key, value in self.__dict__.items():
            attr += f"{key} : {value}\n"
        return attr


class UserInv:
    id: str
    discord_id: str


class InvItem(UserInv):
    quantity: int


class InvEquipItem(UserInv):
    slot: int


class Item(Bundle):
    @abstractmethod
    def use(self):
        pass


class ConsumableItem(Item):
    def use(self):
        pass


class EquipableItem(Item):
    plus_attack : int = 0
    plus_hp: int= 0
    plus_ap_attack: int= 0
    plus_defense: int= 0
    total_attack: int = 0
    total_hp: int = 0
    total_ap_attack: int = 0
    total_defense: int = 0
    def use(self,user):
        Session = sessionmaker(bind=connection_pool)
        session = Session()
        equiped_item = session.query(DB_UserEquipInventory).filter(and_(DB_UserEquipInventory.slot == self.equip_pos,DB_UserEquipInventory.discord_id == user)).first()
        text = f"{self.name} 장착 완료"
        if equiped_item is not None:
            item = get_inv_item_by_id(equiped_item.inv_id)
            text = f"{item.name} -> {self.name} 교환 완료"
            session.delete(equiped_item)
            session.commit()
        session.add(DB_UserEquipInventory(discord_id=user, inv_id=self.inv_id, slot=self.equip_pos))
        session.commit()
        session.close()
        return text

    def get_description(self):
        embed = discord.Embed(title=f"{self.name}의 정보",
                              description=self.description)
        if self.image_link is not None:
            embed.set_thumbnail(url=self.image_link)
        embed.add_field(name="등급", value=self.grade)
        embed.add_field(name="분류", value=self.type)
        embed.add_field(name="장착위치", value=EquipPos[self.equip_pos])
        if len(self.ability) > 0:
            ability_info = ', '.join(self.ability)
            embed.add_field(name="능력", value=ability_info, inline=False)
        spac = ""
        if self.hp > 0:
            spac += ":heart: 체력: +%20s\n" % f"{self.hp}"
        if self.attack > 0:
            spac += ":crossed_swords: 공격력: +%20s\n" % f"{self.attack}"
        if self.ap_attack > 0:
            spac += ":magic_wand: 마법공격력: +%20s\n" % f"{self.ap_attack}"
        if self.defense > 0:
            spac += ":shield: 방어력: +%20s\n" % f"{self.defense}"
        embed.add_field(name="스펙", value=spac, inline=False)
        return embed

    def get_upgrade_point_and_caculate_spac(self):
        enhanced_info = get_enhanced_info(self.inv_id)
        upgrade_count = 0
        for i in enhanced_info:
            # 스크롤 종류에 따라 다시 능력치 추가하기
            self.plus_hp += 5 * i.used_time
            self.plus_attack += 5 * i.used_time
            self.plus_ap_attack += 5 * i.used_time
            self.plus_defense += 5 * i.used_time
            upgrade_count += i.used_time
        self.total_hp = self.plus_hp + self.hp
        self.total_defense = self.plus_defense + self.defense
        self.total_ap_attack = self.plus_ap_attack + self.ap_attack
        self.total_attack = self.plus_attack + self.attack
        return upgrade_count

    def get_description_is_hanced(self,user_id):
        user = get_userInfo(user_id)
        title = f"{user.name}의 {self.name}"
        upgrade_count = self.get_upgrade_point_and_caculate_spac()
        if upgrade_count != 0:
            title += f"+ {upgrade_count}"
        title+= " 정보"
        embed = discord.Embed(title= title,
                              description=self.description)
        if self.image_link is not None:
            embed.set_thumbnail(url=self.image_link)
        embed.add_field(name="등급", value=self.grade)
        embed.add_field(name="분류", value=self.type)
        embed.add_field(name="장착위치", value=EquipPos[self.equip_pos])
        if len(self.ability) > 0:
            ability_info = ', '.join(self.ability)
            embed.add_field(name="능력", value=ability_info, inline=False)
        spac = ""
        if self.total_hp > 0:
            spac += f":heart: 체력: +{self.total_hp} ({self.hp} + {self.plus_hp})\n"
        if self.total_attack > 0:
            spac += f":crossed_swords: 공격력 +{self.total_attack} ({self.attack} + {self.plus_attack})\n"
        if self.total_ap_attack > 0:
            spac += f":magic_wand: 마법공격력: +{self.total_ap_attack} ({self.ap_attack} + {self.plus_ap_attack})\n"
        if self.total_defense > 0:
            spac += f":shield: 방어력: +{self.total_defense} ({self.defense} + {self.plus_defense})\n"
        embed.add_field(name="스펙", value=spac, inline=False)
        return embed

class SkillItem(Item):
    def use(self):
        pass

    def get_description(self):
        embed = discord.Embed(title=f"{self.name}의 정보")
        if self.image_link is not None:
            embed.set_thumbnail(url=self.image_link)
        embed.add_field(name="아이템 분류", value=self.type)
        embed.add_field(name="스킬 분류", value=self.skilltype)
        embed.add_field(name="스킬 설명", value=self.description, inline=False)
        return embed


class Dungeon(Bundle):
    def get_description(self):
        embed = discord.Embed(title=f"던전: {self.name}",
                              description=f"{self.description}")
        embed.add_field(name="입장 최소 레벨", value=self.min_level)
        appearances = ", ".join(self.spawn_monster)
        embed.add_field(name="출현 몬스터", value=appearances, inline=False)
        return embed

class Monster(Bundle,Character):
    def __init__(self,data):
        self.now_hp = 1
        super().__init__(data)
        self.id = self.name