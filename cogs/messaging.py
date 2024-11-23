import re
import time
import asyncio

import discord
from discord.ext import commands

from cogs.parent import ParentCog

class Messaging(ParentCog):
    
    def __init__(self, bot, db_handler):
        super().__init__(bot, db_handler)
        
    
    async def retrieve_quotes(self, ctx:commands.Context, person: str, search: str):
        
        member = self.get_mentioned_member(person, ctx) 
        if member is None or member.id == ctx.author.id:
            return
        
        if search is not None and re.match("<#\d+>", search):

            text_channel = ctx.guild.get_channel(int(search.strip("<#>")))
            if text_channel is None:
                asyncio.run_coroutine_threadsafe(ctx.send(f"{search} is not a text channel"), ctx.bot.loop)
                return
                
            history = [message async for message in text_channel.history(limit=50)]

            messages = []
            messages_datetime = None
            
            for msg in history:
                if msg.author.id == member.id:
                    messages.append(msg.content)
                    messages_datetime = msg.created_at
                elif messages:
                    break
            if not messages:
                return
        
            quote = {"message": '\n'.join(reversed(messages)),
                     "time":    int(messages_datetime.timestamp())}

            past_quote = self.db_handler.db["members"].find_one({"member_id": member.id, 
                                                                "quotes": {"$elemMatch": {"time": quote["time"]}} })
            if past_quote:
                self.db_handler.db["members"].update_one({"member_id": member.id, "quotes.time": quote["time"]},
                                                        {"$set": {"quotes.$.message": quote["message"]} })
            else:
                self.db_handler.db["members"].update_one({"member_id": member.id},
                                                        {"$push": {"quotes": quote} })
                
            return [ quote ]

        elif search is not None:

            member_quotes = self.db_handler.db["members"].find_one({"member_id": member.id}, {"quotes":1}).get("quotes")
            queried_quotes = [quote for quote in member_quotes if search in quote["message"]]

            return queried_quotes


    @commands.hybrid_command(name="quote", help="frame a person's greatest messages from a channel or previous list")
    async def quote(self, ctx:commands.Context, 
                    person: str = commands.parameter(description= "- the @person you want to quote.",
                                                     default=None, displayed_default=None),
                    search: str = commands.parameter(description= "- #channel if updating, or keywords if recalling.",
                                                     default=None, displayed_default=None)):
        
        quotes = await self.retrieve_quotes(ctx, person, search)
        
        if quotes:
            member = self.get_mentioned_member(person, ctx) 
            embed = discord.Embed(title=member.display_name, color=member.accent_color) 
            for quote in quotes:
                embed.add_field(name = f"\"{quote['message']}\"", value = time.ctime(quote['time']), inline = False)
            await ctx.send(embed = embed)