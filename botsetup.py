import discord, os, random, db_manager, perms
from asyncio import TimeoutError
from discord import channel
from discord import message
from dotenv import load_dotenv
from math import ceil, floor
'''
Matthew Firmin [7/22/21]

TODO:
  - Add reaction functionality for favoriting quotes and for reporting bot breaking/bad quote
  - Make bot check for permissions on each command run
#   - Make -mqb quote <args> find a quote within enabled universes
  - Add ability to schedule messages
  - Setup prefixes to be dynamic
'''

load_dotenv()
TOKEN = os.getenv('TOKEN')

client = discord.Client()
TOTAL_UNIVERSES = 359       # global holding max number of universes
COLOR = 0x893a94            # global holding embed color
EMBED_PAGE = 1



async def set_pfp():
    with open('/pfp/MQB03.png', 'rb') as image:
        await client.user.edit(avatar=image)



'''
    Takes a list and builds an embed message of max 25 fields
    Used to generate embeds for universe lists
'''
async def create_embed(li, em_title, context, field_values=True, page=1, prev_embed=None):
    num_univ = len(li)
    desc = str(num_univ)

    if field_values:
        desc += ' Universes'
    else:
        desc += ' Characters'
    if num_univ != TOTAL_UNIVERSES:     # formatting since this is shared between ulist and alist
        desc += ' enabled'
    
    

    if field_values == False:
        num_per_page = 25
    else:
        num_per_page = 10 #24
    
    page_max = int(ceil(len(li)/num_per_page))    # Pages can only exist in fulls, ;)

    i = (page-1)*num_per_page
    super_increment = int(floor(page_max/5))     # Used for reaction emojis

    # fv = '\u200b'

    embed_var = discord.Embed(title=em_title+' Page '+str(page)+'/'+str(page_max), description=desc, color=COLOR)
    while i < page*num_per_page and i < num_univ: # iterate through maximum items that can be placed in the embed
        if field_values:
            embed_var.add_field(name=li[i][0], value=li[i][1], inline=not field_values)
        else:
            embed_var.add_field(name=li[i], value='\u200b', inline=not field_values)

        i += 1

    if field_values:
        footnote = ' Universes'
    else:
        footnote = ' Characters'
    footer_text = str(i) + '/' + str(num_univ) + footnote
    embed_var.set_footer(text=footer_text)
    
    ''' Old code used when bot took -next command instead of reactions
    # This next part waits for the -next command
    def check(m, context=context):
        return m.content == '-next' and m.channel == context.channel

    if page != 1:
        await prev_embed.edit(embed=embed_var)
        
    else:
        prev_embed = await context.channel.send(embed=embed_var)
    try:
        msg = await client.wait_for('message', check=check, timeout=30)
        await create_embed(li, em_title, context, field_values, page+1, prev_embed)
    except asyncio.TimeoutError:
            print('wait_for Timeout')
    '''
    if prev_embed is None:
        prev_embed = await context.channel.send(embed=embed_var)
    else:
        await prev_embed.edit(embed=embed_var)


    # Add reactions from bot, if/else to prevent people from pressing the wrong emoji and breaking loop
    if page == 1 and page != page_max:
        await prev_embed.add_reaction('▶️')
        await prev_embed.add_reaction('⏭️')
    elif page < page_max:
        await prev_embed.add_reaction('⏮️')
        await prev_embed.add_reaction('◀️')
        await prev_embed.add_reaction('▶️')
        await prev_embed.add_reaction('⏭️')
    elif page != 1:   # Last page
        await prev_embed.add_reaction('⏮️')
        await prev_embed.add_reaction('◀️')
        




    # Wait for user reaction
    try:    # reaction.messsage == prev_embed checks to make sure the message being reacted to is the same as the one to edit
        reaction, user = await client.wait_for('reaction_add', timeout=220, check=lambda reaction, user: reaction.message == prev_embed and user == context.author and reaction.emoji in ['▶️','◀️', '⏮️', '⏭️' ] )
    except TimeoutError:
        print('Timeout')
    else:
        if reaction.emoji == "▶️" and page < page_max:
            await prev_embed.clear_reaction('⏭️')
            await prev_embed.clear_reaction('▶️')
            await create_embed(li, em_title, context, field_values, page+1, prev_embed)
        elif reaction.emoji == "◀️" and page > 1:
            await prev_embed.clear_reaction('⏭️')
            await prev_embed.clear_reaction('▶️')
            await prev_embed.clear_reaction('◀️')
            await create_embed(li, em_title, context, field_values, page-1, prev_embed)

        # super_increment will now be used
        elif reaction.emoji == "⏭️" and page < page_max:
            await prev_embed.clear_reaction('⏭️')
            if page + super_increment > page_max:
                await create_embed(li, em_title, context, field_values, page_max, prev_embed)
            else:
                await create_embed(li, em_title, context, field_values, page+super_increment, prev_embed)

        elif reaction.emoji == "⏮️" and page > 1:
            await prev_embed.clear_reaction('⏭️')
            await prev_embed.clear_reaction('▶️')
            await prev_embed.clear_reaction('◀️')
            await prev_embed.clear_reaction('⏮️')
            if page - super_increment <= 0:
                await create_embed(li, em_title, context, field_values, 1, prev_embed)
            else:
                await create_embed(li, em_title, context, field_values, page-super_increment, prev_embed)

        

        



'''
    Builds quote message as an embed
'''
def constr_quote(quote_stream):
    if (len(quote_stream) == 0):    # Universe not found error
        # print('Universe not found')
        return None
    # [0] = quote, [1] = char, [2] = universe, [3] = link, [4] = _id, [5] = Suffix, [6] thumbnail (not guaranteed)
    if quote_stream[5] == '':   # If there isn't a suffix
        embed_var = discord.Embed(title=quote_stream[1]+' ('+quote_stream[2]+')', description=quote_stream[0] + '\n\n' + quote_stream[3], color=COLOR)
    else:
        embed_var = discord.Embed(title=quote_stream[1]+ ' (' + quote_stream[5] + ') '+' ('+quote_stream[2]+')', description=quote_stream[0] + '\n\n' + quote_stream[3], color=COLOR)

    if (len(quote_stream) >= 7):
        embed_var.set_thumbnail(url=quote_stream[6])
    return embed_var

'''
    Generates list of commands after a call to -mqb help
'''
def constr_help_page():
    ''' Original
    desc = 'I am a bot that generates quotes from just over 350 of Marvel\'s comic books, movies, and television universes. Currently I have gathered more than 11,000 quotes, with 83\u0025 coming from the mainline comic book universe Earth-616.'
    embed_var = discord.Embed(title="Marvel Quotes Bot", description=desc, color=COLOR)
    commands = db_manager.get_help_list()   # List of tuples: (command, details)
    for cmd in commands:
        embed_var.add_field(name=cmd[0], value='`'+cmd[1]+'`', inline=False)
    # Potentially add a footer saying -next if list grows
    return embed_var 
    '''
    desc = 'I am a bot that generates quotes from over 350 of Marvel\'s universes.\nType `-mqb help <command>` for more information about a command.'
    embed_var = discord.Embed(title='Marvel Quotes Bot', description=desc, color=COLOR)
    fields = db_manager.get_help_list()     # [0] = setup, [1] = lists, [2] = quotes, [3] = info
    for field in fields:
        val = ''
        i = 1
        while i < len(field)-1:
            val += field[i]+ ', '
            i += 1
        val += field[i]
        embed_var.add_field(name=field[0], value=val, inline=False)
    return embed_var


def constr_help_cmd(cmd):
    doc = db_manager.get_single_help(cmd)
    if doc is None:
        return None
    # embed_var = discord.Embed(title='Marvel Quotes Bot', description='\u200b', color=COLOR)
    embed_var = discord.Embed(title=cmd, description=doc['details'], color=COLOR)
    # embed_var.add_field(name=cmd, value=doc['details'], inline=False)
    embed_var.add_field(name='Use', value=doc['parameters'])
    return embed_var


'''
    Constructs embed that contains information about a character or universe
'''
def constr_about_embed(args):
    info = db_manager.get_about(args)     # [0] = Name, [1] = # references, [2] = % makeup, [3] universe/character, [4] info (NOT GUARANTEED)
    if info is None:
        return None

    about_len = len(info)
    
    if about_len < 5:
        desc = 'Marvel Comic Book ' + info[3]
    else:
        desc  = info[4]

    embed_var = discord.Embed(title=info[0], description=desc, color=COLOR)
    embed_var.add_field(name='Number of Quotes', value=info[1], inline=True)
    embed_var.add_field(name='Percent of all quotes', value=info[2], inline=True)

    return embed_var


''' TODO: db_manager function '''
def constr_about_bot():
    print('Nothing yet')
    about_bot = db_manager.get_about_bot()




@client.event
async def on_guild_join(guild):
    print('Joining guild ', guild)
    db_manager.add_guild(guild)

@client.event
async def on_ready():
    perms.establish_perms()     # Establishes local dictionary of perms
    print('Logged in as {0.user}'.format(client))



@client.event
async def on_message(message):
    command = None  # Set up for later check if None
    args = None
    if message.author == client.user:
        return
    
    # Sets up long if/else case to interpret commands
    elif message.content.startswith('-mqb'):   
        try:
            command = message.content.split(' ')[1]
            args = message.content.replace('-mqb', '')
            args = args.replace(command, '').strip()    # args holds what comes after command (ex: -mq command args)
        except IndexError:  # occurs when only one command is given "-mqb" which defaults to a quote
            pass

    else:
        return
    # message is now ensured to start with -mq and be a command
    guild_id = message.guild.id


    # Fetch random quote from universe specified or if none, from the list of enabled universes
    if command is None or command == '' or (len(command) >=5 and command[:5] == 'quote'):    
        if args is None or args == '':                                  # When args is empty, fetch random quote 
            quote = db_manager.get_quote(guild_id)
        elif args == 'all':                                             # Used keyword 'all', pull random quote from all
            # await set_pfp()
            quote = db_manager.get_random_quote(guild_id)

        else:                                                           # Specific universe called in args
            quote = db_manager.get_quote_from_arg(args, guild_id)
        
        if quote is None and (args is None or args == ''):          # Quote returned None when called with no extra arguments -> no universe list for guild 
            await message.channel.send('No universes to pull from.\nType \"-mqb add <universe>\" to add a specific universe or type \"-mqb add all\" to add all')
        elif quote is None:                                         # Quote returned None when a universe was specified
            await message.channel.send('Universe/Character not found, type \"-elist\" or \"clist\" for keywords')
        else:   # Quote exists, send it.
            quote_em = constr_quote(quote)
            await message.channel.send(embed=quote_em)

    elif command == 'all':
        quote = db_manager.get_random_quote(guild_id)
        await message.channel.send(embed=constr_quote(quote))

    # Adds specified universe to server's active universes
    elif command == 'add':
        if perms.check_perms(guild_id, message.author, is_uvm=True) == False:
            await message.channel.send('You do not have permission to use this command')

        else:
            success = db_manager.add_universe(args, guild_id)
            if success is not None and args != 'all':
                reply = 'Universe ' + success + ' successfully added'
            elif success is not None:   # add all case
                reply = 'All universes successfully added'
            else:
                reply = 'Universe ' + args + ' was unable to be added'
            # reply += db_manager.get_universe_list(guild_id)
            await message.channel.send(reply)
    
    # Removes specified universe from server's active universes
    elif command == 'remove':
        if perms.check_perms(guild_id, message.author, is_uvm=True) == False:
            await message.channel.send('You do not have permission to use this command')

            
        elif args.lower() == 'all':
            all_removed = db_manager.remove_all_universes(guild_id)
            if all_removed == True:
                await message.channel.send('All universes successfully removed')
            else:
                await message.channel.send('Something went wrong. Please make sure to use the \"-mqb\" command if you haven\'t already.')
        else:
            success = db_manager.remove_universe(args, guild_id)
            if success is not None:
                reply = 'Universe ' + success + ' successfully removed'
            else:
                reply = 'Universe ' + args + ' was unable to be removed'
            # reply += db_manager.get_universe_list(guild_id)
            await message.channel.send(reply)
    
    # Sends list of all universes
    elif command == 'ulist':
        ulist = db_manager.get_all_universes(guild_id)
        await create_embed(ulist, 'All Universes', context=message)

    # Sends list of enabled universes -- can only message 25 universes at a time, awaits "next" command
    elif command == 'elist':
        elist = db_manager.get_enabled_universes(guild_id)   # returns complete list of enabled universes

        if len(elist) == 0:
            await message.channel.send('No universes enabled, type \"-mqb add <universe>\" to add a specific universe. Type \"-mqb add all\" to add all')
        else:
            await create_embed(elist, 'Enabled Universes', context=message)

    # Sends list of characters    
    elif command == 'clist':
        clist = db_manager.get_character_list()
        await create_embed(clist, 'List of Characters', field_values=False, context=message)

    # Sends first page of help embed... Update so commands are shown within backticks <`command`>
    # TODO: Don't show information from command list instad show it when command is called as an arg with a help command (also give examples on how to use the command)
    elif command == 'help':
        if args == '':
            help_em = constr_help_page()
            await message.channel.send(embed=help_em)

        else:
            help_em = constr_help_cmd(args)
            if help_em is None:
                await message.channel.send('Invalid argument')
            else:
                await message.channel.send(embed=help_em)


    # Gives information about the specified universe
    # TODO: default about case should link to info
    elif command == 'about':
        if args == '':  # TODO: default case SHOULD INSTEAD link to -mqb info command
            about_bot = constr_about_bot()
        else:
            about_em = constr_about_embed(args)
            if about_em is not None:
                await message.channel.send(embed=about_em)
            else:
                await message.channel.send('Invalid argument')


    
    # Takes 'used quotes' as args, resets guild's used_quotes to a blank array
    elif command == 'clear':
        if perms.check_perms(guild_id, message.author, is_uvm=True) == False:
            await message.channel.send('You do not have permission to use this command')
        else:
            db_manager.clear_used_quotes(guild_id)
            await message.channel.send('Used quotes cleared')

    # Toggles quote exclusion on or off... does "-mqb quote Peter Parker" draw from ALL universes, or just those enabled
    elif command == 'exclude':
        if perms.check_perms(guild_id, message.author, is_excl=True) == False:
            await message.channel.send('You do not have permission to use this command')
        elif args == 'on' or args == 'off':
            db_manager.toggle_exclude(guild_id, args)
            await message.channel.send('Exclusion turned ' + args)
        else:
            await message.channel.send('Unrecognized argument, please use \"on\" or \"off\"')

    # Permission management
    # Syntax -mqb perms <set/unset> <cmd> <role>
    # TODO: Set up so it works with embeds
    elif command == 'perms':
        print('args = ', args)
        
        valid_perms = perms.check_perms(guild_id, message.author, is_perms=True)
        print('can use command:', valid_perms)
        if  valid_perms and args == 'reset':
            perms.reset_perms(guild_id)
            await message.channel.send('Perms reset, to view current permissions use the help command')
        elif valid_perms:
            full_args = args.split(' ')
            action = full_args[0]       # set
            if action == 'set':
                cmd = full_args[1].strip()
                if cmd == '':   # weird bug where 'perms' is replaced by an empty string
                    cmd = 'perms'
                role = full_args[2]
                if message.guild.get_role(role) is None:
                    await message.channel.send('Invalid Role')
                else:
                    perms.set_perms(message.guild, cmd, role)
                    await message.channel.send('Permission for command {0} set to {1}'.format(cmd, role))
        else:
            await message.channel.send('You do not have permission to use this command')
    
    

    else:
        await message.channel.send('I\'m sorry, I don\'t recognize that command, type \"-mqb help\" for a list of commands')

     



    



client.run(TOKEN)