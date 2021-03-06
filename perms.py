import discord, db_manager
from discord.utils import resolve_invite
from discord import guild
from pymongo.uri_parser import _parse_options
from discord.ext.commands import has_permissions
'''
  8/11/2021
  File for managing and tracking permissions.

  Permissions CAN ONLY BE SET ON Universe Management commands, the exclude command, and the perms command
  Stores set permissions in local dict to increase speed of role checking
  Note - Local data wiped on function termination which is why both the collection and local data is updated on each set/reset call

  TODO: make reset_perms() accept a command argument
'''

perms_dict = {}     # Keys = guild IDs, values = list/array of role IDs
UNIVERSE_MGMT = 0   # Indicates placement of commands in a guild's perms list
EXCLUDE       = 1
CHANGE_PERMS  = 2


''' 
  Called on startup, retrieves permission data from guild collection and stores it locally
'''
def establish_perms():
    global perms_dict

    perms_dict = db_manager.get_all_perms()
    print('Permissions Established')


'''
    Checks if the user can use a command, returns True/False
    Usage - is_XXX set to True for corresponding command call in botsetup.py
'''
def check_perms(guild, user, is_uvm=False, is_excl=False, is_perms=False):
    if user.guild_permissions.kick_members:  # Admins have access to all commands
        # print('User passed permissions via manage_role permission')
        return True

    global perms_dict
    # print('ENTERED PERMS CHECK')

    if is_uvm == True:
        cmd = UNIVERSE_MGMT
    elif is_excl == True:
        cmd = EXCLUDE
    elif is_perms == True:
        cmd = CHANGE_PERMS
    else:
        print('ERROR: no command type given in check_perms()')
        return False
    
    role_id = perms_dict[guild.id][cmd]    # immediately indexes role
    
    if role_id == -1:   # Specific roles have not been set, check via default
        return check_default(user, cmd)
    elif role_id == 0:  # @everyone case
        return True
    
    # Now check if the user has these roles
    # has_role = user.has_role(role)
    role = guild.get_role(role_id)
    if role in user.roles:
        return True
    else:
        return False
    # for item in user.roles:
        # if '<@&'+str(item.id)+'>' == role:    # Removed as set_perms now excludes chars 0-2 & -1
        # if str(item.id) == role:
            # return True
    # return False
    # print('has_role = {0}, type = {1}'.format(has_role, type(has_role)))
    # return has_role


''' Checks user's perms against default'''
def check_default(user, cmd):
    if cmd == UNIVERSE_MGMT:   # Default for universe management is @everyone
        return True
    else:                       # Default for exclusion and setting permissions is those who are able to manage the server
        return user.guild_permissions.manage_roles


''' Sets permission for a command to a roll '''
def set_perms(guild, command, role):
    global perms_dict
    cmd_index = get_index_from_str(command)
    if cmd_index == -1: # not a valid command
        return False
    db_manager.set_perms(guild.id, cmd_index, role)          #role[3:-1])
    perms_dict[guild.id][cmd_index] = role



''' 
Resets permissions to default, call with argument to set specific role to default 
TODO: make work with specific commands
'''
def reset_perms(guild_id, command=None):
    global perms_dict
    # if command is None: # reset all commands to default
    for x in perms_dict[guild_id]:              # local reset
        x = -1
    db_manager.set_perms(guild_id, reset=True)  # DB reset
    # else:
        # get_index_from_str(command)

def get_perms(guild_id, s):
    global perms_dict
    cmd = get_index_from_str(s)
    perm = perms_dict[guild_id][cmd]
    if perm != -1 and perm != 0:
        return '<@&'+str(perm)+'>'
    elif perm == 0 or cmd == UNIVERSE_MGMT:
        return '@everyone'


    return 'Permissions.manage_roles'



def add_guild(guild_id):
    global perms_dict
    perms_dict[guild_id] = [-1, -1, -1]





def get_index_from_str(str):
    if str == 'universe':
        return UNIVERSE_MGMT
    elif str == 'exclude':
        return EXCLUDE
    elif str == 'perms':
        return CHANGE_PERMS
    else:
        return -1


def remove_guild(guild):
    del perms_dict[guild.id]