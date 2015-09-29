# -*- coding: utf-8 -*-

import requests
import functools
from threading import Timer
import datetime
from collections import Counter, namedtuple
try:
    from urllib.parse import quote as urlquote
except ImportError:
    from urllib import quote as urlquote
import shlex
import datetime
import json
import traceback
import random as rng
from discord.permissions import Permissions
import math
import sys

commands = {}
config = {}

authority_prettify = {
    -1: 'Banned',
    0: 'User',
    1: 'Moderator',
    2: 'Admin',
    3: 'Creator'
}

help_prolog = """
Note that <argument> means the argument is required and [argument] means it is optional.
Also, having the argument name be in ellipsis means it takes 1 or more. e.g. <arguments...>
You do not type the brackets. If spaces are needed, put them in quotes. e.g. "Tentatek Splattershot"."""

def load_config():
    with open('config.json') as f:
        global config
        config = json.load(f)

def save_config():
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

def find_from(l, predicate):
    for element in l:
        if predicate(element):
            return element
    return None


def _get_help_text(name, help_text, params):
    result = '{prefix}{name}'
    if params:
        result = result + ' {params}'
    if help_text:
        result = result + ' -- {help}'
    return result.format(prefix=config.get('command_prefix'), name=name, params=params, help=help_text)


def command(authority=0, hidden=False, help=None, params=None):
    """A decorator used to register a simple command.

    :param authority: The authority required to execute the command.
    :param hidden: Specifies that the command is hidden from help output.
    :param help: The help text when !help is called.
    :param params: The text that comes before the help output.
    """

    def actual_decorator(function):
        function.hidden = hidden
        function.authority = authority
        function.help = help
        function.params = params

        @functools.wraps(function)
        def wrapped(bot, message):
            # check authority
            user_authority = config['authority'].get(message.author.id, 0)
            if user_authority < authority:
                bot.send_message(message.channel, "Sorry, you're not authorised to do this command.")
                return

            # check !command help
            if len(message.args) != 0 and message.args[0] == 'help':
                prefix = function.__name__
                output = [
                    _get_help_text(prefix, help, params),
                    _get_help_text(prefix + ' help', 'shows this message', None)
                ]

                for subcommand in getattr(function, 'subcommands', []):
                    data = function.subcommands[subcommand]
                    name = prefix + ' ' + subcommand
                    output.append(_get_help_text(name, data['help'], data['params']))

                bot.send_message(message.channel, '\n'.join(output) + '\n' + help_prolog)
                return

            function(bot, message)

        commands[function.__name__] = wrapped
        return wrapped
    return actual_decorator

def subcommand(name, help=None, params=None):
    """A decorator that registers a subcommand to a command.

    This allows you to do e.g. !random map and give it help text and what not.
    Which gives more detailed output on ``!command help`` .

    :param help: The help text for the subcommand.
    :param params: The prefixed help text for the subcommand.
    """
    def actual_decorator(command):
        if not hasattr(command, 'subcommands'):
            command.subcommands = {}

        command.subcommands[name] = {
            'help': help,
            'params': params
        }
        return command
    return actual_decorator


@command(help='shows this message')
def help(bot, message):
    output = ['available commands for you:']
    authority = config['authority'].get(message.author.id, 0)
    for name in commands:
        func = commands[name]
        if func.hidden == True:
            continue
        if func.authority > authority:
            continue
        output.append(_get_help_text(name, func.help, func.params))
    output.append('')
    output.append('If you want more info, you can do !command help, e.g. !hello help')
    bot.send_message(message.author, '\n'.join(output) + help_prolog)


def try_parse(s, default=None, cls=int):
    try:
        return cls(s)
    except Exception as e:
        return default

@command(help='displays my intro message')
def hello(bot, message):
    bot.send_message(message.channel, "Hello! I'm a robot! I am currently **version 2.0.0**. Danny made me.")


@command(help='displays a random weapon, map, mode, or number')
@subcommand('weapon', help='displays a random Splatoon weapon')
@subcommand('map', help='displays a random Splatoon map')
@subcommand('mode', help='displays a random Splatoon mode')
@subcommand('lenny', help='displays a random lenny face')
@subcommand('game', help='displays a random map/mode combination (without Turf War)')
@subcommand('number', help='displays a random number with an optional range', params='[range]')
def random(bot, message):
    error_message = 'Random what? weapon, map, mode, or number? (e.g. !random weapon)'
    if len(message.args) == 0:
        bot.send_message(message.channel, error_message)
        return

    random_type = message.args[0].lower()
    if random_type not in random.subcommands:
        bot.send_message(message.channel, error_message)
        return

    splatoon = config['splatoon']
    if random_type == 'weapon':
        weapon = rng.choice(splatoon['weapons'])
        name = weapon.get('name')
        sub = weapon.get('sub')
        special = weapon.get('special')
        bot.send_message(message.channel, '{} (sub: {}, special: {})'.format(name, sub, special))
    elif random_type == 'map':
        bot.send_message(message.channel, rng.choice(splatoon['maps']))
    elif random_type == 'lenny':
        lenny = rng.choice([
            "( ͡° ͜ʖ ͡°)", "( ͠° ͟ʖ ͡°)", "ᕦ( ͡° ͜ʖ ͡°)ᕤ", "( ͡~ ͜ʖ ͡°)",
            "( ͡o ͜ʖ ͡o)", "͡(° ͜ʖ ͡ -)", "( ͡͡ ° ͜ ʖ ͡ °)﻿", "(ง ͠° ͟ل͜ ͡°)ง",
            "ヽ༼ຈل͜ຈ༽ﾉ"
        ])
        bot.send_message(message.channel, lenny)
    elif random_type == 'mode':
        mode = rng.choice(['Turf War', 'Splat Zones', 'Rainmaker', 'Tower Control'])
        bot.send_message(message.channel, mode)
    elif random_type == 'number':
        maximum = 100
        minimum = 0
        if len(message.args) == 2:
            maximum = try_parse(message.args[1], default=100)
        elif len(message.args) > 2:
            minimum = try_parse(message.args[1], default=0)
            maximum = try_parse(message.args[2], default=100)
        bot.send_message(message.channel, rng.randrange(minimum, maximum + 1))
    elif random_type == 'game':
        mode = rng.choice(['Splat Zones', 'Rainmaker', 'Tower Control'])
        stage = rng.choice(splatoon['maps'])
        bot.send_message(message.channel, '{} on {}'.format(mode, stage))

@command(help='displays weapon info from a query', params='<query>')
def weapon(bot, message):
    if len(message.args) != 1:
        bot.send_message(message.channel, 'No query given. Try e.g. !weapon "disruptor" or !weapon "Aerospray RG"')
        return

    query = message.args[0].lower()
    if len(query) < 3:
        bot.send_message(message.channel, 'The query must be at least 3 characters long')
        return

    weapons = config['splatoon']['weapons']
    def query_handler(weapon):
        tup = [weapon[attr].lower() for attr in weapon]
        return any(query in x for x in tup)
    result = list(filter(query_handler, weapons))
    output = []
    if len(result):
        output.append('Found {} weapon(s):'.format(len(result)))
        for weapon in result:
            output.append('Name: {}, Sub: {}, Special: {}'.format(weapon['name'], weapon['sub'], weapon['special']))
    else:
        output.append('Sorry. The query "{}" returned nothing.'.format(message.args[0]))

    bot.send_message(message.channel if len(result) <= 10 else message.author, '\n'.join(output))

def get_profile_reply(profile):
    output = ['Profile for **{}**:'.format(profile.get('name'))]
    output.append('NNID: {}'.format(profile.get('nnid', '*None found*')))
    output.append('Rank: {}'.format(profile.get('rank', '*None found*')))
    output.append('Squad: {}'.format(profile.get('squad', '*None found*')))
    weapon = profile.get('weapon')
    if weapon:
        output.append('Weapon: {} (sub: {}, special: {})'.format(weapon['name'], weapon['sub'], weapon['special']))
    else:
        output.append('Weapon: *None Found*')

    return '\n'.join(output)

def create_profile_if_none_exists(user, force=False):
    profiles = config['splatoon']['profiles']
    if force or user.id not in profiles:
        profiles[user.id] = {
            'name': user.name,
            'nnid': None,
            'rank': None,
            'squad': None,
            'weapon': None,
        }
        save_config()

@command(help='manages your profile', params='<action>')
@subcommand('get', help="retrieves your profile or someone else's profile", params='[username]')
@subcommand('stats', help="retrieves some statistics on the profile database")
@subcommand('nnid', help='sets your NNID of your profile', params='<NNID>')
@subcommand('rank', help='sets your Splatoon rank of your profile', params='<rank-title>')
@subcommand('squad', help='sets your Splatoon squad of your profile', params='<squad-name>')
@subcommand('weapon', help='sets your Splatoon weapon of your profile', params='<weapon-name>')
@subcommand('delete', help='clears an element of your profile or the entire thing', params='[element]')
@subcommand('username', help='updates the username of your profile', params='[name]')
def profile(bot, message):
    create_profile_if_none_exists(message.author)
    profiles = config['splatoon']['profiles']
    userid = message.author.id
    profile = profiles[userid]
    action = None if len(message.args) == 0 else message.args[0].lower()

    if action is None:
        return bot.send_message(message.channel, get_profile_reply(profile))
    if action == 'get':
        if len(message.args) == 1:
            # !profile get alone
            return bot.send_message(message.channel, get_profile_reply(profile))
        # !profile get <username>
        username = message.args[1]
        found_id = None
        for profile_id in profiles:
            value = profiles[profile_id]
            if value['name'] == username:
                found_id = profile_id
                break

        if found_id is None:
            return bot.send_message(message.channel, 'User not found. Note this is case sensitive or they do not have a profile set up yet.')
        bot.send_message(message.channel, get_profile_reply(profiles[profile_id]))
    elif action == 'nnid':
        # !profile nnid <nnid>
        if len(message.args) == 1:
            return bot.send_message(message.author, 'Missing your NNID to set to your profile.')
        nnid = message.args[1]
        profile['nnid'] = nnid
        save_config()
        bot.send_message(message.author, 'Your profile NNID is now set to "{}"'.format(nnid))
    elif action == 'delete':
        # !profile delete [element]
        if len(message.args) == 1:
            create_profile_if_none_exists(message.author, force=True)
            return bot.send_message(message.author, 'Your profile has successfully been deleted.')
        element = message.args[1].lower()
        if element not in profile:
            return bot.send_message(message.author, 'Invalid delete action given.')
        profile[element] = None
        save_config()
    elif action == 'rank':
        # !profile rank <rank>
        valid_ranks = ['C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+', 'S', 'S+']
        if len(message.args) == 1:
            return bot.send_message(message.author, 'No Splatoon rank given.')
        rank = message.args[1].upper()
        if rank not in valid_ranks:
            return bot.send_message(message.author, 'Invalid rank provided.')
        profile['rank'] = rank
        save_config()
        bot.send_message(message.author, 'Your rank has successfully been set to "{}".'.format(rank))
    elif action == 'squad':
        # !profile squad <squad>
        if len(message.args) == 1:
            return bot.send_message(message.author, 'No squad given.')
        squad = message.args[1]
        profile['squad'] = squad
        save_config()
        bot.send_message(message.author, 'Your squad was successfully set to "{}"'.format(squad))
    elif action == 'weapon':
        # !profile weapon <name>
        if len(message.args) == 1:
            return bot.send_message(message.author, 'No weapon given.')
        query = message.args[1].lower()
        weapon = find_from(config['splatoon']['weapons'], lambda wep: wep['name'].lower() == query)
        if weapon is not None:
            profile['weapon'] = weapon
            save_config()
            bot.send_message(message.author, 'Your main weapon was successfully set to "{}"'.format(weapon['name']))
        else:
            bot.send_message(message.author, 'Invalid weapon given.')
    elif action == 'stats':
        # rank statistics
        rank_counter = Counter((x['rank'] for x in profiles.values() if x.get('rank') is not None))
        rank_count = sum(rank_counter.values())
        rank_intro = 'From {} players, {} are ranked with the following distribution:\n'.format(len(profiles), rank_count)
        rank_stats = []
        for rank in rank_counter:
            value = rank_counter[rank]
            rank_stats.append('{0}: {1} ({2:.2%})'.format(rank, value, float(value) / rank_count))

        # weapon statistics
        weapon_counter = Counter((x['weapon']['name'] for x in profiles.values() if x.get('weapon') is not None))
        weapon_count = sum(weapon_counter.values())
        weapon_topcut = 3
        weapon_intro = '\nAlso {} players have their weapons set to something. The top {} are:\n'.format(weapon_count, weapon_topcut)
        weapon_stats = []
        for stat in weapon_counter.most_common(weapon_topcut):
            weapon_stats.append('{}: {} players'.format(stat[0], stat[1]))

        reply = rank_intro + ', '.join(rank_stats) + weapon_intro + ', '.join(weapon_stats)
        bot.send_message(message.channel, reply)
    elif action == 'username':
        # !profile username [name]
        name = message.author.name
        if len(message.args) > 1:
            name = message.args[1]
        profile['name'] = name
        save_config()
        bot.send_message(message.author, 'Profile username successfully changed to "{}".'.format(name))
    else:
        bot.send_message(message.channel, 'Invalid profile action given. Type !profile help for more info.')


class SplatoonMap(object):
    """Represents a Splatoon Map entry in the future."""
    def __init__(self, **data):
        self.start_time = datetime.datetime.utcfromtimestamp(data.get('startTime', 0.0) / 1000.0)
        self.end_time = datetime.datetime.utcfromtimestamp(data.get('endTime', 0.0) / 1000.0)
        regular_maps = data.get('regular', {}).get('maps', [])
        self.regular = [m.get('nameEN') for m in regular_maps]

        ranked_data = data.get('ranked', {})
        ranked_maps = ranked_data.get('maps', [])
        self.ranked = [m.get('nameEN') for m in ranked_maps]
        self.mode = ranked_data.get('rulesEN', 'Unknown')

        # check if the map date is over
        self.is_over = self.end_time < datetime.datetime.utcnow()

    def __str__(self):
        now = datetime.datetime.utcnow()
        prefix = ''
        if self.start_time > now:
            minutes_delta = int((self.start_time - now) / datetime.timedelta(minutes=1))
            hours = int(minutes_delta / 60)
            minutes = minutes_delta % 60
            prefix = '**In {0} hours and {1} minutes**:\n'.format(hours, minutes)
        else:
            prefix = '**Current Rotation**:\n'

        fmt = 'Turf War is {0[0]} and {0[1]}\n{1} is {2[0]} and {2[1]}'
        return prefix + fmt.format(self.regular, self.mode, self.ranked)

def get_splatoon_maps():
    response = requests.get(config['splatoon']['schedule_url'])
    if response.status_code == 502:
        raise RuntimeError('Request took too long. Try again later.')
    elif response.status_code != 200:
        raise RuntimeError('An error occurred. Status code {}. Tell Danny'.format(response.status_code))

    data = response.json()
    sched = data.get('schedule', [])
    if sched is None or len(sched) == 0:
        raise RuntimeError('No map data could be found.')

    result = []
    for element in sched:
        m = SplatoonMap(**element)
        if m.is_over:
            continue
        result.append(m)
    return result

def send_splatoon_map_message(bot, message, index):
    try:
        maps = get_splatoon_maps()
        bot.send_message(message.channel, maps[index])
    except RuntimeError as e:
        bot.send_message(message.channel, e)
    except Exception as e:
        bot.send_message(message.channel, 'No map data found.')

@command(help='shows the current Splatoon maps in rotation')
def maps(bot, message):
    send_splatoon_map_message(bot, message, 0)

@command(help='shows the next Splatoon maps in rotation')
def nextmaps(bot, message):
    send_splatoon_map_message(bot, message, 1)

@command(help='shows the last Splatoon maps in rotation', hidden=True)
def lastmaps(bot, message):
    send_splatoon_map_message(bot, message, 2)

@command(help='shows the current Splatoon map schedule')
def schedule(bot, message):
    try:
        maps = get_splatoon_maps()
        bot.send_message(message.channel, '\n'.join(map(str, maps)))
    except RuntimeError as e:
        bot.send_message(message.channel, e)

@command(help='echoes text', authority=2)
def echo(bot, message):
    bot.send_message(message.channel, message.content)

@command(help='helps you choose between multiple choices')
def choose(bot, message):
    if len(message.args) < 2:
        return bot.send_message(message.channel, 'Not enough choices to choose from.')
    bot.send_message(message.channel, rng.choice(message.args))

@command(help='shows info about a Splatoon brand', params='<name>')
@subcommand('list', help='shows all the available brands')
def brand(bot, message):
    if len(message.args) == 0:
        return bot.send_message(message.channel, 'No brand given')
    query = message.args[0].lower()
    brands = config['splatoon']['brands']
    if query == 'list':
        return bot.send_message(message.channel, ', '.join(map(lambda x: x['name'], brands)))

    brand = find_from(brands, lambda x: x['name'].lower() == query)
    if brand is None:
        return bot.send_message(message.channel, 'Could not find brand "{}".'.format(message.args[0]))

    buffed = brand['buffed']
    nerfed = brand['nerfed']
    if buffed is None or nerfed is None:
        bot.send_message(message.channel, 'The brand "{}" is neutral!'.format(brand['name']))
    else:
        fmt = 'The brand "{}" has buffed {} and nerfed {} ability probabilities'
        abilities = config['splatoon']['abilities']
        bot.send_message(message.channel, fmt.format(brand['name'], abilities[buffed - 1], abilities[nerfed - 1]))

# Some creator only commands
@command(authority=3)
def quit(bot, message):
    bot.logout()

@command(authority=3)
def reloadconfig(bot, message):
    load_config()

@command(help='cleans up past messages from the bot', params='[number-of-messages]', authority=1)
def cleanup(bot, message):
    limit = 100
    if len(message.args) > 0:
        limit = try_parse(message.args[0], default=100)
    count = 0
    done = bot.send_message(message.channel, 'Cleaning up...')
    for entry in bot.logs_from(message.channel, limit=limit):
        if entry.author == bot.user:
            count += 1
            bot.delete_message(entry)
    bot.delete_message(done)
    bot.send_message(message.channel, 'Clean up has completed. {} message(s) were deleted.'.format(count))

@command(help='manages the authority of a user', authority=1, params='<username> <new_authority>')
@subcommand('list', help='lists all the currently available authority')
def authority(bot, message):
    server = message.channel.server
    if len(message.args) == 0:
        return bot.send_message(message.channel, 'No username or authority given.')
    if len(message.args) == 1:
        if message.args[0].lower() == 'list':
            generator = (str(key) + ' => ' + authority_prettify[key] for key in authority_prettify)
            return bot.send_message(message.channel, '\n'.join(generator))
        return bot.send_message(message.channel, 'No authority given for the user.')

    # at this point we have two arguments..
    authority = try_parse(message.args[1], default=0)
    author_authority = config['authority'].get(message.author.id, 0)
    user = find_from(server.members, lambda x: x.name == message.args[0])
    if user is None:
        return bot.send_message(message.channel, 'User not found. Note this is case sensitive or they might be offline.')
    if authority > author_authority or author_authority < config['authority'].get(user.id, 0):
        return bot.send_message(message.channel, "You can't give someone authority higher than yours.")

    if authority not in authority_prettify:
        return bot.send_message(message.channel, 'This authority does not exist.')

    config['authority'][user.id] = authority
    save_config()
    bot.send_message(message.channel, '{} now has an authority of **{}**.'.format(user.name, authority_prettify[authority]))


@command(help='reminds you after a certain amount of time', params='<seconds> [reminder]')
def timer(bot, message):
    if len(message.args) == 0:
        return bot.send_message(message.channel, 'Missing the amount of seconds to remind you from.')

    time = try_parse(message.args[0], default=None, cls=float)
    if time is None:
        return bot.send_message(mesage.channel, message.author.mention() + ', your time is incorrect.')

    reminder = ''
    complete = ''
    if len(message.args) >= 2:
        reminder = message.author.mention() + ", I'll remind you to _\"{}\"_ in {} seconds.".format(message.args[1], time)
        complete = message.author.mention() + ':\nTime is up! You asked to be reminded for _\"{}\"_.'.format(message.args[1])
    else:
        reminder = message.author.mention() + ", You've set a reminder in {} seconds.".format(time)
        complete = message.author.mention() + ':\nTime is up! You asked to be reminded about something...'

    bot.send_message(message.channel, reminder)
    t = Timer(time, lambda: bot.send_message(message.channel, complete))
    t.start()

@command(help='are you cool?')
def coolkids(bot, message):
    bot.send_message(message.channel, ', '.join(config['cool_kids']))

@command(hidden=True)
def marie(bot, message):
    return bot.send_message(message.channel, 'http://i.stack.imgur.com/0OT9X.png')

@command(help='shows a page from the Inkipedia', params='<title>')
def splatwiki(bot, message):
    if len(message.args) == 0:
        return bot.send_message(message.channel, 'A title is required to search.')
    params = {
        'title': message.args[0]
    }
    response = requests.get('http://splatoonwiki.org/w/index.php', params=params)
    if response.status_code == 404:
        search = 'http://splatoonwiki.org/wiki/Special:Search/' + urlquote(message.args[0])
        bot.send_message(message.channel, 'Could not find a page with the specified title.\nTry searching at ' + search)
    elif response.status_code == 200:
        bot.send_message(message.channel, response.url)
    elif response.status_code == 502:
        bot.send_message(message.channel, 'It seems that Inkipedia is taking too long to response. Try again later.')
    else:
        bot.send_message(message.channel, 'An error has occurred of status code {} happened. Tell Danny.'.format(response.status_code))

@command(help='allows you tag text for later retrieval', params='<name>')
@subcommand('create', help='creates a new tag under your ID', params='<name> <text>')
@subcommand('edit', help='edits a new tag under your ID', params='<name> <text>')
@subcommand('remove', help='removes a tag if it belongs to you', params='<name>')
@subcommand('list', help='lists all tags that belong to you')
def tag(bot, message):
    if 'tags' not in config:
        config['tags'] = {}

    tags = config['tags']
    if len(message.args) == 1:
        # !tag <name> (retrieval)
        name = message.args[0].lower()
        if name in tags:
            return bot.send_message(message.channel, tags[name]['content'])
        elif name == 'list':
            # !tag list
            auth = config['authority'].get(message.author.id, 0)
            my_tags = []
            for tagname in tags:
                if auth >= 2 or tags[tagname]['owner_id'] == message.author.id:
                    my_tags.append('"' + tagname + '"')

            if len(my_tags) > 0:
                return bot.send_message(message.author, ', '.join(my_tags))
            else:
                return bot.send_message(message.author, 'You have no tag ownership. Create some with !tag create.')
        else:
            return bot.send_message(message.channel, 'Could not find a tag with the name "{}".'.format(name))

    action = message.args[0]
    if action not in tag.subcommands:
        return bot.send_message(message.channel, 'Invalid action given. Type !tag help for more info.')

    if action == 'create':
        if len(message.args) < 3:
            return bot.send_message(message.channel, 'Missing name or text for the created tag. e.g. !tag create "test" "hello"')
        name = message.args[1].lower()
        content = message.args[2]
        if name in tag.subcommands:
            return bot.send_message(message.channel, 'That tag name is reserved and cannot be used.')
        if name in tags:
            return bot.send_message(message.channel, 'Tag already exists. If you are the owner of the tag, do !tag edit.')
        tags[name] = {
            'content': content,
            'owner_id': message.author.id
        }
        save_config()
        bot.send_message(message.channel, 'Tag "{}" successfully created.'.format(name))

    elif action == 'remove':
        if len(message.args) < 2:
            return bot.send_message(message.channel, 'Missing the name of the tag to remove.')

        name = message.args[1].lower()
        if name not in tags:
            return bot.send_message(message.channel, 'Tag "{}" does not exist.'.format(name))

        found_tag = tags[name]
        auth = config['authority'].get(message.author.id, 0)
        if auth >= 1 or message.author.id == found_tag['owner_id']:
            # proper permission met to delete a tag
            del tags[name]
            save_config()
            bot.send_message(message.channel, 'Tag successfully deleted.')
        else:
            bot.send_message(message.channel, 'You do not have the proper permissions to delete this tag.')
    elif action == 'edit':
        if len(message.args) < 3:
            return bot.send_message(message.channel, 'Missing name or text for the created tag. e.g. !tag edit "test" "hello"')

        name = message.args[1].lower()
        content = message.args[2]

        if name not in tags:
            return bot.send_message(message.channel, 'Tag "{}" does not exist.'.format(name))

        found_tag = tags[name]
        auth = config['authority'].get(message.author.id, 0)
        if auth >= 1 or message.author.id == found_tag['owner_id']:
            tags[name]['content'] = content
            save_config()
            bot.send_message(message.channel, 'Tag successfully edited.')
        else:
            bot.send_message(message.channel, 'You do not have the proper permissions to edit this tag.')

@command(help='shows you my changelog for my current version')
def changelog(bot, message):
    with open('changelog.txt') as f:
        bot.send_message(message.author, f.read())

@command(help='shows you info about you or someone else as a member of a server', params='[username]')
def info(bot, message):
    if message.channel.is_private:
        return bot.send_message(message.channel, 'You cannot use this via PMs. Sorry.')

    username = message.author.name if len(message.args) == 0 else message.args[0]
    server = message.channel.server
    members = server.members
    member = find_from(members, lambda m: m.name == username)
    if member is None:
        return bot.send_message(message.channel, 'User not found. You might have misspelled their name. The name is case sensitive.')


    roles = list(map(lambda x: x.name, member.roles))
    output = []
    output.append('Info about **{}**:'.format(username))
    if len(roles) > 0:
        output.append('Their roles are {}.'.format(', '.join(roles)))
    else:
        output.append('They have no roles!')
    output.append('They joined this server at {}.'.format(member.joined_at.isoformat()))
    output.append('Their authority on me is **{}**.'.format(authority_prettify.get(config['authority'].get(member.id, 0))))
    output.append('We are currently in server {}, channel {}.'.format(server.name, message.channel.name))
    output.append('This server is owned by {} and has {} members.'.format(server.owner.name, len(members)))
    bot.send_message(message.channel, '\n'.join(output))

@command(hidden=True, help='shows you your permissions in the channel')
def permissions(bot, message):
    if message.channel.is_private:
        return bot.send_message(message.author, 'You have no permissions in private messages.')
    member = next((m for m in message.channel.server.members if m.id == message.author.id), None)
    if member is None:
        return bot.send_message(message.author, 'Apparently I cannot find you in my list.')

    perm = find_from(member.server.roles, lambda r: r.name == '@everyone').permissions
    for role in member.roles:
        perm.value = perm.value | role.permissions.value

    output = ['Your Permissions Are:']
    for attr in dir(perm):
        if attr.startswith('can_'):
            output.append('{} -> {}'.format(attr, getattr(perm, attr)))

    bot.send_message(message.author, '\n'.join(output))

@command(help='shows the current tournament bracket')
def bracket(bot, message):
    bot.send_message(message.channel, 'http://hypest.challonge.com/BooyahBattle/')

@command(help='shows the tournament rules')
def rules(bot, message):
    bot.send_message(message.channel, 'https://docs.google.com/document/d/1TyPFEaFOb1zbRRImQHJ_Er4N5IKNy5RN4y9Ej9mFMoU')

@command(help='shows the tournament squads')
def squidsquads(bot, message):
    bot.send_message(message.channel, 'https://docs.google.com/spreadsheets/d/1uOO3yktxj9fP7pNZArfpjnChDQYRqevHSnrJ_TfppRc')

def nested_get(data, attrs):
    return functools.reduce(lambda d, k: d[k], attrs, data)

def nested_set(data, attrs, value):
    nested_get(data, attrs[:-1])[attrs[-1]] = value

@command(authority=3, help='edits the config file', params='<action> <key> <value>')
@subcommand('append', help='appends the value to the key if the key value is a list')
@subcommand('remove', help='removes the value to the key if the key value is a list')
@subcommand('delete', help='deletes the key entirely')
@subcommand('set', help='sets the value to the specified key (this also creates the key if needed)')
@subcommand('get', help='gets the value to the specified key')
@subcommand('debug', help='calculates a command and executes it on a key')
def conf(bot, message):
    # !conf <action> <key> [value]
    if len(message.args) < 2:
        return bot.send_message(message.channel, 'Not enough arguments given.')

    action = message.args[0]
    keys = message.args[1].split('.')
    key = None
    if action != 'set':
        try:
            key = nested_get(config, keys)
        except KeyError as e:
            return bot.send_message(message.channel, 'Key not found.')

    if action == 'delete':
        del key
        save_config()
        return bot.send_message(message.channel, 'Key "{}" successfully deleted.'.format(message.args[1]))
    elif action == 'get':
        return bot.send_message(message.author, key)

    # rest require a value
    if len(message.args) < 3:
        return bot.send_message(message.channel, 'Value is required.')

    try:
        value = eval(message.args[2]) # dangerous but YOLO
        if action == 'append':
            key.append(value)
        elif action == 'remove':
            key.remove(value)
        elif action == 'set':
            nested_set(config, keys, value)
        elif action == 'debug':
            return bot.send_message(message.channel, value)
        save_config()
        return bot.send_message(message.channel, 'Key "{}" successfully updated.'.format(message.args[1]))
    except Exception as e:
        return bot.send_message(message.channel, 'An error occurred: {}: {}'.format(type(e).__name__, str(e)))


@command(hidden=True, authority=2, help='calculates a python expression subset')
def calculate(bot, message):
    env = {
        'locals': None,
        'globals': None,
        '__name__': None,
        '__file__': None,
        '__builtins__': None,
    }

    safe_functions = {
        'max': max,
        'min': min,
        'round': round,
        'range': range,
        'sum': sum,
        'filter': filter,
        'map': map,
        'abs': abs
    }

    for index, argument in enumerate(message.args):
        try:
            result = eval(argument, env, safe_functions)
            bot.send_message(message.channel, '[{}]: {}'.format(index, result))
        except Exception as e:
            bot.send_message(message.channel, 'An error happened: {}.'.format(e))


@command(hidden=True, authority=3)
def debug(bot, message):
    try:
        bot.send_message(message.channel, eval(message.args[0]))
    except Exception as e:
        bot.send_message(message.channel, 'Error: {}.'.format(e))

def dispatch_messages(bot, message, debug=True):
    """Handles the dispatching of the messages to commands.

    :param bot: The discord client.
    :param message: The message class from on_message event.
    :param debug: If True, adds some debug text to stdout.
    """

    command_prefix = config.get('command_prefix')
    prefix = message.content.partition(' ')[0][len(command_prefix):]

    if message.content.startswith(command_prefix) and prefix in commands and message.author != bot.user:
        if debug:
            print('On {} {} has said {}'.format(message.timestamp.isoformat(), message.author.name.encode('utf-8'), message.content.encode('utf-8')))
        try:
            args = shlex.split(message.content)
        except Exception as e:
            return bot.send_message(message.channel, 'An error occurred in your message: ' + str(e))
        message.args = args[1:]
        func = commands[prefix]
        try:
            func(bot, message)
        except Exception as e:

            if debug:
                print('An error happened:')
                traceback.print_exc(limit=4)
