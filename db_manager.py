# Test
from discord import guild
import pymongo, os
from dotenv import load_dotenv
from bson.son import SON

load_dotenv()
DB_CLIENT = os.getenv('DB_CLIENT')

db_client = pymongo.MongoClient(DB_CLIENT)
DB          = db_client["marvelQuotes"]
QUOTES_DB   = DB['all_marvel_quotes']
UNIVERSE_DB = DB['all_universes']
CHARS_DB    = DB['all_characters']
GUILDS_DB   = DB["guilds"]

def add_guild(guild_id, universe_list=None):
    universes = []
    if universe_list is not None:
        for univ in universe_list:
            universes.append(univ)
    GUILDS_DB.insert_one({'_id': guild_id, 'universes': universes, 'used_quotes': [], 'exclusion': False, 'perms': [-1, -1, -1]})


''' Returns dictionary of perms for use in perms.py '''
def get_all_perms():
    cursor = GUILDS_DB.find()
    dict = {}   # key = guild ID, value = guild['perms']
    for doc in cursor:
        try:
            dict[doc['_id']] = doc['perms']
        except KeyError:    # Occurs on alpha:omega, beta:gamma, and theta:iota fake/setup guilds
            # print('KeyError on ', doc['_id'])
            pass

    return dict


''' Sets one specific value '''
def set_perms(guild_id, command_index=0, role=None, reset = False):
    if reset:
        GUILDS_DB.update(
            { '_id': guild_id },
            { '$set': { "perms" : [-1, -1, -1] } })
    else:
        GUILDS_DB.update(
            { '_id': guild_id },
            { '$set': { "perms."+str(command_index) : role } })





def get_character_list():
    doc = GUILDS_DB.find_one({ 'beta': 'gamma'})
    return doc['characters']

''' 
    Returns full list of universes by iterating through UNIVERSE_DB
'''
def get_all_universes(page=0):
    url = 'https://marvel.fandom.com/wiki/'
    cursor = UNIVERSE_DB.find()
    univ_tupp = []
    univ_name = ''
    for doc in cursor:
        univ_info = ''
        try:
            univ_name = doc['alt'] 
        except KeyError:
            univ_name = doc['name'] 
        try:
            univ_info = doc['info'] # + '\n[link](' + url + univ_name + ')'
        except KeyError:
            univ_info = '\u200b'    # '[Nothing yet](' + url + univ_name + ')'
        univ_tupp.append((univ_name, univ_info))
    return univ_tupp

'''
    Returns list of all universes
'''
def get_enabled_universes(guild_id):
    the_guild = GUILDS_DB.find_one({ '_id': guild_id })
    if the_guild is None:
        add_guild(guild_id)
        get_enabled_universes(guild_id)
    
    univ_tupp = []
    univ_name = ''
    univ_info = ''
    cursor = UNIVERSE_DB.find({'name': the_guild['universes']})
    for universe in the_guild['universes']:
        
        try:
            doc = UNIVERSE_DB.find_one({'alt': universe})
            univ_name = doc['alt'] 
        except TypeError or KeyError:
            doc = UNIVERSE_DB.find_one({'name': universe})
            univ_name = doc['name'] 
        try:
            univ_info = doc['info'] # + '\n[link](' + url + univ_name + ')'
        except KeyError:
            univ_info = '\u200b'    # '[Nothing yet](' + url + univ_name + ')'
        univ_tupp.append((univ_name, univ_info))
    return univ_tupp
    



'''
    Returns number of universes enabled
'''
def get_num_universes(guild_id):
    doc = GUILDS_DB.find_one({'_id': guild_id})
    return len(doc['universes'])

'''
    Returns the list of commands from collection 'commands"
'''
def get_help_list():
    ''' Version 1
    commands = []
    doc = DB['commands'].find()     # Returns cursor
    for item in doc:
        commands.append((item['command'], item['details']))
    return commands
    '''
    
    comm_list   = []
    univ_mgmt_comms = [ 'Universe Management' ]
    lists_comms = [ 'Lists' ]
    quo_comms   = [ 'Quotes']
    info_comms  = [ 'Info'  ]
    setup_comms = [ 'Setup' ]


    doc = DB['command-info'].find()
    for item in doc:
        group = item['group']
        if group == 'Universe Management':
            univ_mgmt_comms.append('`' + item['command'] + '`')
        elif group == 'Lists':
            lists_comms.append('`' + item['command'] + '`')
        elif group == 'Quotes':
            quo_comms.append('`' + item['command'] + '`')
        elif group == 'Info':
            info_comms.append('`' + item['command'] + '`')
        elif group == 'Setup':
            setup_comms.append('`' + item['command'] + '`')
        else:
            print('ERROR NEW QUOTE TYPE')
    
    comm_list.append(quo_comms)
    comm_list.append(lists_comms)
    comm_list.append(univ_mgmt_comms)
    comm_list.append(info_comms)
    comm_list.append(setup_comms)

    return comm_list        # [0] = setup, [1] = lists, [2] = quotes, [3] = info


''' Gets info about a specific command, returns none if none found, must be indexed using var['whatever'] '''
def get_single_help(cmd):
    return DB['command-info'].find_one({ 'command': cmd })
    


''' Enables all universes for selected guild '''
def enable_all_universes(guild_id):
    ao = GUILDS_DB.find_one({ 'alpha': 'omega' })   # Establish master universe list
    GUILDS_DB.update_one(
        { '_id': guild_id },
        { '$addToSet': { 'universes': { '$each': ao['universes']}}}
    )
    


'''
    Takes string and turns it into the proper syntax to be used by the database
    Used by add_universe(), remove_universe(), and get_quote_from_arg()
'''
def format_univ(universe):
    is_valid_univ = UNIVERSE_DB.find_one({'name': universe})
    univ_f = universe

    if is_valid_univ is not None and UNIVERSE_DB.find_one({'alt': 'Earth-'+universe}) is not None:
        univ_f = 'Earth-' + universe
    elif is_valid_univ is None and len(universe) > 1:
        univ_f = universe[0].upper() + universe[1:].lower()
        is_valid_univ = UNIVERSE_DB.find_one({'name': univ_f})
    if is_valid_univ is None and len(universe) > 5:
        is_valid_univ = UNIVERSE_DB.find_one({'name': universe[5:]})    #earthXXXX case
        univ_f = 'Earth-' + universe[5:]
    if is_valid_univ is None and len(universe) > 6:
        is_valid_univ = UNIVERSE_DB.find_one({'name': universe[6:]})    #earth-XXXX case
        univ_f = 'Earth-' + universe[6:]
    
    
    if is_valid_univ is None:
        return None
    return univ_f


'''
    adds to guild's active uiverses
     - Can take universe as an array or string
'''
def add_universe(universe, guild_id):
    if universe == 'all':               # If the enable all command was given
        enable_all_universes(guild_id)
        return universe

    # Check to see if universe is valid
    univ_f = format_univ(universe)
    if univ_f is None:
        return None
    
    GUILDS_DB.update(
        { '_id': guild_id },
        { '$addToSet': { 'universes': univ_f } }
    )
    return univ_f


'''
    Removes ALL universes from server's enabled universe list
'''
def remove_all_universes(guild_id):
    if GUILDS_DB.find_one({'_id': guild_id}) is not None:       # I want to remove this to make it faster... should I add a -mqb setup command?
        GUILDS_DB.update(
                { '_id': guild_id },
                { '$set': { 'universes': [] }}
            )
        return True
    else:   # guild has not been established yet
        add_guild(guild_id)
        remove_all_universes(guild_id)
        return True


'''
    Removes specific universe from server's enabled universe list
'''
def remove_universe(universe, guild_id):
    # Check to see if universe is valid
    univ_f = format_univ(universe)
    if univ_f is None:
        return None
    

    GUILDS_DB.update(
        { '_id': guild_id},
        { '$pull': { 'universes': univ_f } }
    )
    return univ_f
    
    

'''
    Builds list from cursor object that is returned from pymongo's aggregate() function
    Returns in form [Quote, Character, Universe, Link, Thumbnail]
    Used by get_quote_from_univ() and get_quote()
'''
def list_from_cursor(cursor):
    quo_char_univ_link = []
    for item in cursor:          # aggregate() mathod returns a cursor
        quo_char_univ_link.append(item['Quote'])
        quo_char_univ_link.append(item['Character'])
        quo_char_univ_link.append(item['Universe'])        
        quo_char_univ_link.append(item['Link'])
        quo_char_univ_link.append(item['_id'])
        try:
            quo_char_univ_link.append(item['Suffix'])
        except KeyError:
            quo_char_univ_link.append('')
        try:
            quo_char_univ_link.append(item['Thumbnail'])
        except KeyError:
            print('Thumbnail value = Null')
    return quo_char_univ_link

'''
    Retrieves quote from a single specific universe
    Note: potential for case-sensitive errors or incorrect formatting/spelling
    TODO: Fix case-sensitive and formatting errors to new standard (format_univ())
'''
def get_quote_from_arg(args, guild_id):
    args = args.strip()
    guild_info = GUILDS_DB.find_one( {'_id': guild_id })
    exclusion = guild_info['exclusion']     # boolean representing exclusion
    enabled_univ = guild_info['universes']

    # Check if the character exists
    if QUOTES_DB.find_one({ 'Character': args}) is not None:
        if exclusion:
            items = QUOTES_DB.aggregate([   
                { '$match': { '$and': [{'Character': args}, {'Universe': {'$in': enabled_univ}}]}},   # Exclusive to enabled universes
                { "$sample": {"size": 1}}
        ])
        else:
            items = QUOTES_DB.aggregate([   
                { '$match': {'Character': args}},
                { "$sample": {"size": 1}}
            ])

    else:   # Now check if args is a universe param
        # Check to see if universe is valid
        univ_f = format_univ(args)
        if univ_f is None:
            return None

        # Does not check for exclusion as user is specifically requesting this universe
        items = QUOTES_DB.aggregate([   
                { "$match": {"Universe": { '$in': univ_f}}},
                { "$sample": {"size": 1}}
        ])
    quo_char_univ_link = list_from_cursor(items)


    if len(quo_char_univ_link) == 0:
        return None

    GUILDS_DB.update(
            { '_id': guild_id },
            { '$push': { 'used_quotes': quo_char_univ_link[4] } }
        )
   
    return quo_char_univ_link


''' Get quote from ENTIRE database (no exclusion) '''
def get_random_quote(guild_id):
    items = QUOTES_DB.aggregate([{ "$sample": {"size": 1}}])
    quo_char_univ_link = list_from_cursor(items)
    # add quote to list of quotes pulled
    GUILDS_DB.update(
            { '_id': guild_id },
            { '$push': { 'used_quotes': quo_char_univ_link[4] } }
        )
    return quo_char_univ_link


'''
    Retrieves a quote from server's enabled universes
    TODO:
      - Exclude any results that have already been pulled
      - Fix adding server document to database
      - Ensure universe search is working correctly
'''
def get_quote(guild_id):
    guild_data = GUILDS_DB.find_one({'_id': guild_id})
    if guild_data is None:      # Guild has not been added to system, add it with default values, return None
        add_guild(guild_id)
        return None
    
    universe_list = guild_data['universes']

    # If no universes are selected, return None
    if len(universe_list) == 0:
        return None

    # Otherwise Pull from selected databases
    else:
        items = QUOTES_DB.aggregate([
            { "$match": {"Universe": { "$in": universe_list }}},
            { "$sample": {"size": 1}}
        ])
        
    quo_char_univ_link = list_from_cursor(items)
    GUILDS_DB.update(
            { '_id': guild_id },
            { '$push': { 'used_quotes': quo_char_univ_link[4] } }
        )
    
    return quo_char_univ_link

    

'''
    Called from bot for <-mqb about>. 
    Figures out if argument is a character or universe and returns info
    [0] = Name, [1] = # references, [2] = % makeup, [3] info (NOT GUARANTEED)
    Note: Does not attempt spell check
'''
def get_about(args):
    info_list = []
    char_doc = CHARS_DB.find_one({'name': args})
    if char_doc is not None:
        info_list.append(char_doc['name'])
        info_list.append(char_doc['references'])
        info_list.append(char_doc['percent'])
        info_list.append('character ')
        try:
            info_list.append(char_doc['info'])
        except KeyError:
            print('No info value for character', info_list[0])
        return info_list

    univ_f = format_univ(args)
    univ_doc = UNIVERSE_DB.find_one({'alt': univ_f})
    if (univ_doc is None):
        univ_doc = UNIVERSE_DB.find_one({'name': univ_f})
    


    if univ_doc is not None:
        try:        # Because I messed up setting up the database and don't feel like fixing it
            info_list.append(univ_doc['alt'])
        except KeyError:
            info_list.append(univ_doc['name'])
        info_list.append(univ_doc['references'])
        info_list.append(univ_doc['percent'])
        info_list.append('universe ')
        try:
            info_list.append(univ_doc['info'])
        except KeyError:
            print('No info value for universe', info_list[0])

        return info_list

    return None


''' Returns information about the bot '''
def get_about_bot():
    pass



def clear_used_quotes(guild_id):
    GUILDS_DB.update_one({'_id': guild_id}, {'$set': {'used_quotes': []}})


''' Toggles exclusion --> whether quote fetch requests with arguments pull from enabled universes or all universes '''
def toggle_exclusion(guild_id, args):
    if args == 'on':
        io_bool = True
    else:
        io_bool = False
    GUILDS_DB.update_one({'_id': guild_id}, {'$set': {'exclusion': io_bool}})
