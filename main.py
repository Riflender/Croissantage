import json
from typing import Optional, Union
from functools import partialmethod
import inspect

import discord
from discord.ext.commands import Bot

intents = discord.Intents.default()
intents.message_content = True
bot = Bot(command_prefix="!", intents=intents)

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

    has_author = author is not None

    e = discord.Embed(title=f"Croissants !!",
                      color=0xffc119,
                      description=f"{victim.mention} a été croissanté{' par ' + author.mention if has_author else ''} !\n\n"
                                  "Si vous voulez qu'il vous offre un croissant, "
                                  "réagissez avec l'emote croissant. :croissant:\n\n"
                                  f"Si tu es la victime, tape la commande : __**{bot.command_prefix}stop**__\n",
                      )

    if has_author:
        e.set_author(name=f"Auteur : {author}", icon_url=author.avatar.url)
    e.set_thumbnail(url=victim.avatar.url)
    e.set_footer(text="Bot fait avec amour (et malice) par Rémi ;)", icon_url=admin.avatar.url)

    e.add_field(name="Liste des profiteurs", value=f"{author.mention if has_author else 'Personne...'}")

    return e


async def embed_stop(victim: discord.Member, people: list[str], author: discord.Member = None) -> discord.Embed:
    admin = await get_admin()

    desc = ""
    if people[0] == "Personne...":
        desc = f"Bien joué {victim.mention} ! Tu n'as laissé le temps à personne de te croissanté !\n\n" \
               f"Tu peux tout de même voir tes dettes avec la commande __**{bot.command_prefix}debts**__"
    else:
        desc = f"Dommage, dommage {victim.mention}...\n\nTu dois désormais un croissant à ces personnes :\n" + \
               "\n".join(people) + \
               f"\n\nTu peux voir tes dettes avec la commande __**{bot.command_prefix}debts**__"

    e = discord.Embed(title="Fin du croissantage :kissing_heart:",
                      color=0xffc119,
                      description=desc
                      )

    has_author = author is not None
    if has_author:
        e.set_author(name=f"Auteur : {author}", icon_url=author.avatar.url)
    e.set_thumbnail(url=victim.avatar.url)
    e.set_footer(text="Bot fait avec amour (et malice) par Rémi ;)", icon_url=admin.avatar.url)

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


@bot.command(name="croissant",
             brief="Miam, miam les bons croissants",
             aliases=["CROISSANT", "c", "C"])
async def croissant(ctx, author: Union[None, str, int] = None):
    victim = ctx.author
    author = await get_member(author, ctx.guild)

    e = await embed_croissant(victim, author)

    msg = await ctx.send(embed=e)
    await msg.add_reaction("🥐")  # \U0001F950

    data = read_json()

    if str(victim.id) not in data:
        data[str(victim.id)] = {}
        data[str(victim.id)]["debts"] = {}
        data[str(victim.id)]["ongoings"] = []
        data[str(victim.id)]["occurrences"] = 0

    data[str(victim.id)]["ongoings"].append(msg_to_dict_id(msg))
    data[str(victim.id)]["occurrences"] += 1

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


@bot.command(name="stop",
             brief="Dommage, dommage...",
             aliases=["STOP", "s", "S"])
async def stop(ctx):
    data = read_json()

    if str(ctx.author.id) not in data or len(data[str(ctx.author.id)]["ongoings"]) == 0:
        await ctx.send("Tu n'as aucun croissantage en cours rassure toi :D")
        return

    # Pour chaque croissantage en cours pour la victime...
    for d in data[str(ctx.author.id)]["ongoings"]:
        # On récupère le message
        msg = await get_message(d["channel"], d["message"])

        people = []
        for p in get_all_profiteurs(msg.embeds[0].fields):
            people.append(p)

            # Ajoute le profiteur aux dettes de la victime
            if p[2:-1] not in data[str(ctx.author.id)]["debts"]:
                data[str(ctx.author.id)]["debts"][p[2:-1]] = 0

            # Ajoute une dette envers le profiteur
            data[str(ctx.author.id)]["debts"][p[2:-1]] += 1

        # Affiche un premier message à éditer pour éviter de mentionner tout le monde
        cheh_msg = await msg.channel.send("Loading...")

        # Récupère l'auteur directement depuis le croisantage
        author = None
        if len(msg.embeds[0].description.split("\n")[0].split(" ")) > 5:
            author = await get_member(msg.embeds[0].description.split(" ")[5], msg.guild)

        # Affiche le message par modification
        await cheh_msg.edit(content=None, embed=await embed_stop(ctx.author, people, author))

        # Supprime le message de croissantage
        await msg.delete()

    # Vide la liste des croissantages de l'auteur de la commande
    data[str(ctx.author.id)]["ongoings"] = []

    #Actualise la base de données
    write_json(data)


@bot.command(name="dettes",
             brief="À qui vous devez des croissants",
             aliases=["DETTES", "d", "D"])
async def dettes(ctx, member: Union[None, str, int] = None):
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


@bot.command()
async def source(ctx):
    await ctx.send("Le lien du Github est accessible ici :\nhttps://github.com/Riflender/Croissantage")


bot.run("NTU3MzM0MjYxMjY3NDMxNDQw.GX8wtt.9RKK0cX3pV4U-e6N9PnVSidONwKGQYlMc31L9g")
