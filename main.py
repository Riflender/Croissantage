import json
from typing import Optional, Union
from functools import partialmethod
import inspect

import discord
from discord.ext.commands import Bot

intents = discord.Intents.default()
intents.message_content = True
bot = Bot(command_prefix="&", intents=intents)

discord.Embed.add_field = partialmethod(discord.Embed.add_field, inline=False)

# database_type = dict[str, dict[str, dict[str, int], list[dict[str, int]]]]
database_type = dict[str, dict[str]]


async def get_admin() -> discord.User:
    return await bot.fetch_user(290190195846807553)


async def get_member(info: Union[None, int, str], guild: discord.Guild) -> Optional[discord.Member]:
    if info is not None:
        if isinstance(info, int):
            return await guild.fetch_member(info)
        elif isinstance(info, str):
            return await guild.fetch_member(int(info[2:-1]))
        else:
            raise TypeError("Cannot find member id in argument")

    return None


async def embed_croissant(victim: discord.Member, author: discord.Member = None) -> discord.Embed:
    admin = await get_admin()

    e = discord.Embed(title=f"Croissantage !!",
                      color=0xffc119,
                      description=f"{victim.mention} a été croissanté !\n\n"
                                  "Si vous voulez qu'il vous offre un croissant, "
                                  "réagissez avec l'emote croissant. :croissant:\n\n"
                                  f"Si tu es la victime, tape la commande : __**{bot.command_prefix}stop**__\n",
                      )

    has_author = author is not None

    if has_author:
        e.set_author(name=f"Auteur : {author}", icon_url=author.avatar.url)
    e.set_thumbnail(url=victim.avatar.url)
    e.set_footer(text="Bot fait avec amour (et malice) par Rémi ;)", icon_url=admin.avatar.url)

    e.add_field(name="Liste des profiteurs", value=f"{author.mention if has_author else 'Personne...'}")

    return e


def read_json() -> database_type:
    with open("croissants.json", "r") as c:
        data = json.load(c)

    return data


def msg_to_dict_id(msg: discord.Message) -> dict[str, int]:
    return {"guild": msg.guild.id, "channel": msg.channel.id, "message": msg.id}


def write_json(data: database_type) -> None:
    with open("croissants.json", "w") as c:
        json.dump(data, c, indent="\t", sort_keys=True)


async def get_message(channel_id: int, message_id: int) -> discord.Message:
    return await (await bot.fetch_channel(channel_id)).fetch_message(message_id)


def get_all_profiteurs(fields):
    return [x for y in list(map(lambda x: x.value.split("\n"), fields)) for x in y]


@bot.event
async def on_ready():
    print("\n--------")
    print(f"Connecté en tant que '{bot.user}'")
    print(f"ID : {bot.user.id}")
    print("bot développé par Rémi Le Hénaff, promotion 2024")
    print("""Pour les étudiants de l'ESIEA et l'amour du croissantage <3""")
    print(f"API {discord.__title__} {discord.__version__}")
    print(discord.__copyright__)
    print("--------\n")


@bot.command()
async def croissant(ctx, author: Union[None, str, int] = None):
    victim = ctx.author
    author = await get_member(author, ctx.guild)

    e = await embed_croissant(victim, author)

    msg = await ctx.send(embed=e)
    await msg.add_reaction("🥐")  # \U0001F950

    data = read_json()

    if str(victim.id) not in data:
        data[victim.id] = {}
        data[victim.id]["debts"] = {}
        data[victim.id]["ongoings"] = []

    data[str(victim.id)]["ongoings"].append(msg_to_dict_id(msg))

    write_json(data)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Si l'emoji n'est pas un croissant, on ignore
    if payload.emoji.name != "🥐":
        return

    # Récupère le message
    msg = await get_message(payload.channel_id, payload.message_id)

    # Quitte la fonction si la réaction vient du bot
    if msg.author == payload.member:
        return

    e = msg.embeds[0]

    # S'il n'y a pas de profiteurs, ajoute le 1er
    if e.fields[0].value == "Personne...":
        e.clear_fields()
        e.add_field(name="Liste des profiteurs", value=payload.member.mention)

        await msg.edit(embed=e)

    # S'il y a déjà des profiteurs, on ajoute le nouveau
    elif payload.member.mention not in get_all_profiteurs(e.fields):
        value = e.fields[-1].value + "\n" + payload.member.mention

        if len(value) <= 1024:
            name = e.fields[-1].name
            e.clear_fields()
            e.add_field(name=name, value=value)

        else:
            nb_list = len(e.fields) + 1
            e.add_field(name=f"Liste des profiteurs ({nb_list})", value=payload.member.mention)

        await msg.edit(embed=e)


@bot.command()
async def stop(ctx):
    data = read_json()

    if str(ctx.author.id) not in data or len(data[str(ctx.author.id)]["ongoings"]) == 0:
        await ctx.send("Tu n'as aucun croissantage en cours rassure toi :D")

    for d in data[str(ctx.author.id)]["ongoings"]:
        msg = await get_message(d["channel"], d["message"])

        people = []
        for p in get_all_profiteurs(msg.embeds[0].fields):
            people.append(p)

            if p[2:-1] not in data[str(ctx.author.id)]["debts"]:
                data[str(ctx.author.id)]["debts"][p[2:-1]] = 0

            data[str(ctx.author.id)]["debts"][p[2:-1]] += 1

        cheh_msg = await msg.channel.send("Loading...")
        await cheh_msg.edit(content="Dommage, dommage...\n\nTu dois désormais un croissant à ces personnes :\n" +
                                    "\n".join(people) +
                                    f"\n\nTu peux voir les dettes avec la commande __**{bot.command_prefix}debts**__")

        await msg.delete()

    data[str(ctx.author.id)]["ongoings"] = []

    write_json(data)


@bot.command()
async def debts(ctx, member: Union[None, str, int] = None):
    data = read_json()

    member = await get_member(member, ctx.guild)

    g = (str(member.id), data[str(member.id)]) if member is not None else data.items()
    s = [""]

    for k, i in g:
        tmp = f"----- Dettes de <@{k}> -----\n"

        for l, j in i["debts"].items():
            tmp += f"<@{l}> : {j} croissant{'s' if j > 1 else ''}\n"
        tmp += "\n"

        if len(s[-1]) > 2000:
            s.append(tmp)
        else:
            s[-1] += tmp

    for i in s:
        msg = await ctx.send("Loading...")
        await msg.edit(content=i)


@bot.command()
async def rembourse(ctx: discord.ext.commands.Context, member: Union[None, str, int] = None, nb: Union[None, str, int] = None):
    member = await get_member(member, ctx.guild)
    if member is None or nb is None:
        await ctx.send(":warning: Erreur de saisie :warning:\n"
                       f"Le bon prototype est `{bot.command_prefix}rembourse <créancier> <nb. croissant (ou 'all')>`")
        return

    data = read_json()

    m = str(member.id)
    a = str(ctx.author.id)

    if (m not in data) or (a not in data[m]["debts"]) or (data[m]["debts"][a] <= 0):
        msg = await ctx.send("Loading...")
        await msg.edit(content=f"{member.mention} n'a pas de dettes envers toi")

        return




bot.run("NTU3MzM0MjYxMjY3NDMxNDQw.GKcIIu.zJu6UPxXWbFzcae44qt0vRhjyVmQF6PmzW_tK4")
