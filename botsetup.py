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
  - Add quote submission functionality - on command use user gets a google form submission to their DMs
#   - Make bot check for permissions on each command run
#   - Make -mqb quote <args> find a quote within enabled universes
  - Add ability to schedule messages
  - Setup prefixes to be dynamic (AKA mass-reformat botsetup.py to fully utilize API with @bot... methods)
  - Mass reformat botsetup.py to fully utilize API with @bot... methods, this will also allow use of dynamic prefixes
  - Setup dynamic prefixes (see one above)
'''

load_dotenv()
TOKEN = os.getenv('TOKEN')

client = discord.Client()
TOTAL_UNIVERSES = 528       # global holding max number of universes
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
        # await prev_embed.clear_reaction('⏭️')
        # await prev_embed.clear_reaction('▶️')
        # await prev_embed.clear_reaction('◀️')
        # await prev_embed.clear_reaction('⏮️')
        new_embed = embed_var
        new_embed.set_footer(text=footer_text + '  |  Timed Out')
        await prev_embed.edit(embed=new_embed)
        print('Reaction Timeout')
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
def constr_quote(quote_doc):
    if quote_doc['Suffix'] is None:
        desc = quote_doc['Quote'] + '\n\n' + '[Wiki]('+quote_doc['Link'] + ')'
    else:
        desc = quote_doc['Quote']

    embed_var = discord.Embed(title=quote_doc['Character']+' ('+quote_doc['Universe']+')', description=desc, color=COLOR)
    if quote_doc['Suffix'] is not None:
        try:
            embed_var.add_field(name='Alias/Associations', value='['+quote_doc['Suffix']+']'+'('+quote_doc['SLink']+')'+ '\n\n' + '[Wiki]('+quote_doc['Link'] + ')')
        except KeyError:
            embed_var.add_field(name='Alias/Associations', value=quote_doc['Suffix']+ '\n\n' + '[Wiki]('+quote_doc['Link'] + ')')
    
    if quote_doc['Thumbnail'] is not None:
        embed_var.set_thumbnail(url=quote_doc['Thumbnail'])

    return embed_var


def constr_mcu_quote(quote_doc):
    if quote_doc['sameName'] == True:
        char_name = quote_doc['name']
    else:
        char_name = quote_doc['name'] + ' (' + quote_doc['person'] +')'
    embed_var = discord.Embed(title=char_name, description=quote_doc['quote'], color=COLOR)


    if quote_doc['context'] is not None:
        embed_var.add_field(name='Context', value=quote_doc['name'] + ' ' +quote_doc['context'], inline=True)
    

    source = '['+quote_doc['sourceTitle']+']('+quote_doc['source']+')'
    if quote_doc['sourceType'] is not None:
        source += ' (' + quote_doc['sourceType'] + ')'
    embed_var.add_field(name='Source', value=source)
    

    if quote_doc['thumbnail'] is not None:
        embed_var.set_thumbnail(url=quote_doc['thumbnail'])

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
    embed_var.add_field(name='\u200b', value='[Bugs/Feedback/Suggestions](https://discord.gg/whf63z6YAF)')
    return embed_var


def constr_help_cmd(cmd, guild_id):
    doc = db_manager.get_single_help(cmd)
    if doc is None:
        return None
    # embed_var = discord.Embed(title='Marvel Quotes Bot', description='\u200b', color=COLOR)
    embed_var = discord.Embed(title=cmd, description=doc['details'], color=COLOR)
    # embed_var.add_field(name=cmd, value=doc['details'], inline=False)
    try:
        embed_var.add_field(name='Default Permissions', value=doc['default'], inline=False)
        embed_var.set_footer(text='Members able to kick other members can use all commands independent of perms use')
    except KeyError:
        pass
    embed_var.add_field(name='Use', value=doc['parameters'])

    if doc['group'] == 'Universe Management':
        embed_var.add_field(name='Perms', value=perms.get_perms(guild_id, 'universe'), inline=True)
    elif doc['command'] == 'exclude' or doc['command'] == 'perms':
        embed_var.add_field(name='Perms', value=perms.get_perms(guild_id, doc['command']), inline=True)

    return embed_var


'''
    Constructs embed that contains information about a character or universe
'''
def constr_about_embed(args):
    tupp = db_manager.get_about(args)     # [0] = Name, [1] = # references, [2] = % makeup, [3] universe/character, [4] info (NOT GUARANTEED)
    if tupp is None or tupp[1] is None:
        return None

    info = tupp[1]
    if tupp[0] == 'c':
        s = 'Character'
    else:
        s = 'Universe'
        
    try:
        embed_var = discord.Embed(title=info['name'], description=info['info'], color=COLOR)
    except KeyError:
        embed_var = discord.Embed(title=info['name'], description='Marvel Comic Book '+s, color=COLOR)
    try:
        embed_var.add_field(name='Association/Alias', value=info['suffix'], inline=False)
    except KeyError:
        pass
    embed_var.add_field(name='Number of Quotes', value=info['references'], inline=True)
    embed_var.add_field(name='Percent of all quotes', value=str(info['percent'])+'\u0025', inline=True)
    return embed_var




    # about_len = len(info)
    
    # if about_len < 5:
    #     desc = 'Marvel Comic Book ' + info[3]
    # else:
    #     desc  = info[4]

    # embed_var = discord.Embed(title=info[0], description=desc, color=COLOR)
    # embed_var.add_field(name='Number of Quotes', value=info[1], inline=True)
    # embed_var.add_field(name='Percent of all quotes', value=info[2], inline=True)

    # return embed_var


''' TODO: db_manager function '''
async def constr_about_bot():
    pass
    # print('Nothing yet')
    # about_bot = db_manager.get_about_bot()




'''
    Called when bot is added to a new guild, adds guild to guild database
'''
@client.event
async def on_guild_join(guild):
    print('Joining guild {0}, \tID = {1}'.format(guild, guild.id))
    num_servers = db_manager.add_guild(guild=guild)
    perms.add_guild(guild.id)

    bot_joins = client.get_channel(877640978700304455)

    # Creates embed to send in dev channel to notify me of new joins
    join_embed = discord.Embed(title='Joined '+guild.name, description='ID:'+ str(guild.id), color=COLOR)
    join_embed.add_field(name='Members', value=str(guild.member_count), inline=False )
    join_embed.add_field(name='Total Servers', value=num_servers[0], inline=True)
    join_embed.add_field(name='Total Members', value=num_servers[1], inline=True)
    await bot_joins.send(embed=join_embed)



    
@client.event
async def on_ready():
    perms.establish_perms()     # Establishes local dictionary of perms
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="-mqb help"))
    print('Logged in as {0.user}'.format(client))

    # db_manager.count_guilds()
    db_manager.check_guilds(client.guilds)  # Checks if any new guilds have been added while offline




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
            quote_doc = db_manager.get_quote(message.guild)
        elif args == 'all':                                             # Used keyword 'all', pull random quote from all
            quote_doc = db_manager.get_random_quote(guild_id)

        else:                                                           # Specific universe called in args
            quote_doc = db_manager.get_quote_from_arg(args, guild_id)
        
        if quote_doc is None and (args is None or args == ''):          # Quote returned None when called with no extra arguments -> no universe list for guild 
            await message.channel.send('No universes to pull from.\nType \"-mqb add <universe>\" to add a specific universe or type \"-mqb add all\" to add all')
        elif quote_doc is None:                                         # Quote returned None when a universe was specified
            await message.channel.send('Universe/Character not found.\nCheck exclusion setting, or use \"elist\" or \"clist\" commands for keywords')
        else:   # Quote exists, send it.
            quote_em = constr_quote(quote_doc)
            await message.channel.send(embed=quote_em)

    elif command == 'all':
        quote_doc = db_manager.get_random_quote(guild_id)
        await message.channel.send(embed=constr_quote(quote_doc))

    # Adds specified universe to server's active universes
    elif command == 'add':
        if perms.check_perms(message.guild, message.author, is_uvm=True) == False:
            await message.channel.send('You do not have permission to use this command')

        else:
            success = db_manager.add_universe(args, message.guild)
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
        if perms.check_perms(message.guild, message.author, is_uvm=True) == False:
            await message.channel.send('You do not have permission to use this command')

            
        elif args.lower() == 'all':
            all_removed = db_manager.remove_all_universes(message.guild)
            if all_removed == True:
                await message.channel.send('All universes successfully removed')
            else:
                await message.channel.send('Something went wrong. Please make sure to use the \"-mqb\" command if you haven\'t already.')
        else:
            success = db_manager.remove_universe(args, message.guild)
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
        elist = db_manager.get_enabled_universes(message.guild)   # returns complete list of enabled universes

        if elist is None or len(elist) == 0:
            await message.channel.send('No universes enabled, type \"-mqb add <universe>\" to add a specific universe. Type \"-mqb add all\" to add all')
        else:
            await create_embed(elist, 'Enabled Universes', context=message)

    # Sends list of characters    
    elif command == 'clist':
        clist = db_manager.get_character_list()
        await create_embed(clist, 'List of Characters', field_values=False, context=message)

    
    # MCU quote
    elif command.lower() == 'mcu':
        if args is None or args == '':
            quote_doc = db_manager.get_mcu_quote(message.guild)
        else:
            quote_doc = db_manager.get_mcu_quote(message.guild, args)
        
        if quote_doc is None:
            await message.channel.send('An error has occured')
        else:
            quote_embed = constr_mcu_quote(quote_doc)
            await message.channel.send(embed=quote_embed)

    # Sends first page of help embed... Update so commands are shown within backticks <`command`>
    # TODO: Don't show information from command list instad show it when command is called as an arg with a help command (also give examples on how to use the command)
    elif command == 'help':
        if args == '':
            help_em = constr_help_page()
            await message.channel.send(embed=help_em)

        else:
            help_em = constr_help_cmd(args, guild_id)
            if help_em is None:
                await message.channel.send('Invalid argument')
            else:
                await message.channel.send(embed=help_em)


    # Gives information about the specified universe
    # TODO: default about case should link to info
    elif command == 'about':
        if args == '':  # TODO: default case SHOULD INSTEAD link to -mqb info command
            # about_bot = constr_about_bot()
            await message.channel.send('Join the MQB discord server to make suggestions, report any issues, and submit your own quotes!\nhttps://discord.gg/d3q9jmxnuh')
        else:
            about_em = constr_about_embed(args)
            if about_em is not None:
                await message.channel.send(embed=about_em)
            else:
                await message.channel.send('Invalid argument')


    
    # Takes 'used quotes' as args, resets guild's used_quotes to a blank array
    elif command == 'clear':
        if perms.check_perms(message.guild, message.author, is_uvm=True) == False:
            await message.channel.send('You do not have permission to use this command')
        else:
            db_manager.clear_used_quotes(guild_id)
            await message.channel.send('Used quotes cleared')

    # Toggles quote exclusion on or off... does "-mqb quote Peter Parker" draw from ALL universes, or just those enabled
    elif command == 'exclude':
        if args == '':      # No arg, check what exclusion is set to (availible to everyone)
            await message.channel.send('Exclusion is {0}'.format(db_manager.check_exclusion(message.guild)))

        elif perms.check_perms(message.guild, message.author, is_excl=True) == False:
            await message.channel.send('You do not have permission to use this command')
        elif args == 'on' or args == 'off':
            db_manager.toggle_exclusion(guild_id, args)
            await message.channel.send('Exclusion turned ' + args)
        else:
            await message.channel.send('Unrecognized argument, please use \"on\" or \"off\"')

    # Permission management
    # Syntax -mqb perms <set/unset> <cmd> <role>
    # TODO: Set up so it works with embeds
    elif command == 'perms':      
        valid_perms = perms.check_perms(message.guild, message.author, is_perms=True)
        if  valid_perms and args == 'reset':
            perms.reset_perms(guild_id)
            await message.channel.send('Perms reset, to view current permissions use `help <command>`')
        elif valid_perms:
            full_args = args.split(' ')
            action = full_args[0]       # set
            if action == 'set' and len(full_args) <= 1:
                await message.channel.send("Invalid argument")
            elif action == 'set':
                cmd = full_args[1].strip()
                if cmd == '':   # weird bug where 'perms' is replaced by an empty string
                    cmd = 'perms'
                
                try:    # If role is given as expected
                    role_id = int(full_args[2][3:-1])
                    role = message.guild.get_role(role_id)
                    if role is None:
                        await message.channel.send('Invalid Role')
                    else:
                        perms.set_perms(message.guild, cmd, role_id)
                        await message.channel.send('Permission for command {0} set to {1}'.format(cmd, str(role)))
                except ValueError:  # Catches use of unofficial roles such as @everyone
                    if full_args[2] == '@everyone':
                        perms.set_perms(message.guild, cmd, 0)
                        await message.channel.send('Permission for command {0} set to @ everyone'.format(cmd))
                    else:
                        await message.channel.send('Invalid Role')
        

        else:
            await message.channel.send('You do not have permission to use this command')
    
    

    else:
        await message.channel.send('I\'m sorry, I don\'t recognize that command, type `-mqb help` for a list of commands')

     



    



client.run(TOKEN)