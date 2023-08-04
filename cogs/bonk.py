import logging
import time

import discord
from discord.ext import commands

from cogs.parent import ParentCog

class Bonk(ParentCog):
    
    def __init__(self, bot, db_handler):
        super().__init__(bot, db_handler)
    
    @commands.command(name = "bonk", help="bonk a person being indecorous", aliases = ("b",))
    async def bonk(self, ctx:commands.Context,
                   person: str = commands.parameter(description="- the @person you want to bonk.",
                                                    default=None, displayed_default=None),
                *, reason: str = commands.parameter(description="- why they deserve to be bonked.",
                                                    default="no reason")):

        bonk_time = round(time.time())
        bonk_reason = reason
        
        if person == self.bot.user.mention:
            await ctx.send(f"{ctx.message.author.mention} tried to bonk the bot!")
            return
        
        member = ParentCog.get_mentioned_member(person, ctx)
        if member is None:
            return

        self.db_handle.db["members"].update_one(
            {"member_id": ctx.message.author.id},
            {"$inc": {"bonks_given": 1},
            "$set": {"last_bonk_given": member.id,
                    "last_bonk_given_time": bonk_time,
                    "last_bonk_given_reason": bonk_reason}
            }
        )
        bonked_result = self.db_handle.db["members"].find_one_and_update(
            {"member_id": member.id},
            {"$inc": {"bonks_received": 1},
            "$set": {"last_bonked_by": ctx.message.author.id,
                    "last_bonked_by_time": bonk_time,
                    "last_bonked_by_reason": bonk_reason},
            "$push":{"bonk_reasons": bonk_reason}
            }
        )

        bonks = bonked_result["bonks_received"] + 1
        await ctx.send(f"{member.mention} has been bonked {str(bonks)} time{'s' if bonks != 1 else ''}!")


    @commands.command(name = "bonkinfo", help="view a person's bonk statistics (last bonk and reason)")
    async def bonkinfo(self, ctx:commands.Context,
                       person: str = commands.parameter(description="- the @person you want to look up. Leave blank to look up yourself.",
                                                        default=None, displayed_default=None)):
        
        member_id = ctx.author.id
        if person is not None: 
            if person == self.bot.user.mention:
                await ctx.send("I cannot be bonked")
                return
            else:
                member = ParentCog.get_mentioned_member(person, ctx)
                if member is None:
                    return
                member_id = member.id

        doc = self.db_handle.db["members"].find_one({"member_id":member_id})

        string = f"Bonk statistics for <@{member_id}>: \n" + \
                f"\t They have been bonked {doc['bonks_received']} time{'s' if doc['bonks_received'] != 1 else ''}\n"
        if doc['last_bonked_by']:
            string = string + f"\t They were last bonked by <@{doc['last_bonked_by']}> on {time.ctime(doc['last_bonked_by_time'])}\n"
            string = string + f"\t This was because: \"{doc['last_bonked_by_reason']}\"\n"
        
        await ctx.send(string)