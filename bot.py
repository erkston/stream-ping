# ResidentStalker
import asyncio
import datetime
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import distutils
import discord
from discord.ext import tasks
import dotenv
import json
import os
import re
import requests

# importing config and reading variables
with open("config/config.json", "r") as jsonfile:
    config = json.load(jsonfile)
BotTimezone = config['BotTimezone']
BotActivity = config['BotActivity']
BotAdminRole = config['BotAdminRole']
AlertChannelName = config['AlertChannelName']
AlertRole = config['AlertRole']
AllowDiscordEmbed = config['AllowDiscordEmbed']
EnableStartupMessage = config['EnableStartupMessage']
AlertAdminOnError = config['EnableStartupMessage']
DeleteOldAlerts = config['DeleteOldAlerts']
OldMessagesToCheck = config['OldMessagesToCheck']
OfflineCheckInterval = config['OfflineCheckInterval']
OnlineCheckInterval = config['OnlineCheckInterval']
AlertCooldown = config['AlertCooldown']
Streams = config['Streams']

dotenv.load_dotenv()
DiscordBotToken = str(os.getenv("DISCORDBOTTOKEN"))
TwitchClientID = str(os.getenv("TWITCHCLIENTID"))
TwitchClientSecret = str(os.getenv("TWITCHCLIENTSECRET"))

# declaring other stuff
version = "v0.0.4"
Units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days', 'w': 'weeks'}
laststatus_time = datetime.now(timezone.utc)
laststatus = []
statusmessage = []
rsCommandList = ["BotActivity", "AllowDiscordEmbed", "AlertAdminOnError", "DeleteOldAlerts", "OfflineCheckInterval", "OnlineCheckInterval",
                 "AlertCooldown", "TwitchReAuth", "Status"]


# convert config time intervals into seconds
def convert_to_seconds(s):
    return int(timedelta(**{
        Units.get(m.group('unit').lower(), 'seconds'): float(m.group('val'))
        for m in re.finditer(r'(?P<val>\d+(\.\d+)?)(?P<unit>[smhdw]?)', s, flags=re.I)
    }).total_seconds())


OfflineCheckIntervalSeconds = convert_to_seconds(OfflineCheckInterval)
OnlineCheckIntervalSeconds = convert_to_seconds(OnlineCheckInterval)
AlertCooldownSeconds = convert_to_seconds(AlertCooldown)


class BOT(discord.Bot):
    async def cleanup(self):
        print('------------------------------------------------------')
        await delete_old_messages()

    async def close(self):
        await self.cleanup()
        print("Goodbye...")
        await super().close()


allowed_mentions = discord.AllowedMentions(roles=True)
intents = discord.Intents.default()
bot = BOT(intents=intents)


@bot.command(name="rs", description="Change ResidentStalker options")
async def rs(ctx, setting: discord.Option(autocomplete=discord.utils.basic_autocomplete(rsCommandList)), value):
    if bot_admin_role in ctx.author.roles:
        print(f'Received command from {ctx.author.display_name}, executing command...')
        global OfflineCheckInterval
        global OfflineCheckIntervalSeconds
        global OnlineCheckInterval
        global OnlineCheckIntervalSeconds
        global AlertCooldown
        global AlertCooldownSeconds
        global token_expiry_time
        global laststatus
        if setting.casefold() == "botactivity":
            global BotActivity
            BotActivity = value
            await bot.change_presence(status=discord.Status.online,
                                      activity=discord.Activity(type=discord.ActivityType.watching,
                                                                name=f"{BotActivity}"))
            await ctx.respond(f'BotActivity has been set to "{BotActivity}"')
            print(f'BotGame changed to {BotActivity} by {ctx.author.display_name}')

        elif setting.casefold() == "allowdiscordembed":
            global AllowDiscordEmbed
            AllowDiscordEmbed = value
            await ctx.respond(f'AllowDiscordEmbed has been set to "{AllowDiscordEmbed}"')
            print(f'AllowDiscordEmbed changed to {AllowDiscordEmbed} by {ctx.author.display_name}')

        elif setting.casefold() == "deleteoldalerts":
            global DeleteOldAlerts
            DeleteOldAlerts = value
            await ctx.respond(f'DeleteOldAlerts has been set to "{DeleteOldAlerts}"')
            print(f'DeleteOldAlerts changed to {DeleteOldAlerts} by {ctx.author.display_name}')

        elif setting.casefold() == "offlinecheckinterval":
            OfflineCheckInterval = value
            OfflineCheckIntervalSeconds = convert_to_seconds(OfflineCheckInterval)
            await ctx.respond(f'OfflineCheckInterval has been set to {OfflineCheckInterval}')
            print(f'OfflineCheckInterval changed to {OfflineCheckInterval} ({OfflineCheckIntervalSeconds}s) by {ctx.author.display_name}')

        elif setting.casefold() == "onlinecheckinterval":
            OnlineCheckInterval = value
            OnlineCheckIntervalSeconds = convert_to_seconds(OnlineCheckInterval)
            await ctx.respond(f'OnlineCheckInterval has been set to {OnlineCheckInterval}')
            print(f'OnlineCheckInterval changed to {OnlineCheckInterval} ({OnlineCheckIntervalSeconds}s) by {ctx.author.display_name}')

        elif setting.casefold() == "alertcooldown":
            AlertCooldown = value
            AlertCooldownSeconds = convert_to_seconds(AlertCooldown)
            await ctx.respond(f'AlertCooldown has been set to {AlertCooldown}')
            print(f'AlertCooldown changed to {AlertCooldown} ({AlertCooldownSeconds}s) by {ctx.author.display_name}')

        elif setting.casefold() == "alertadminonerror":
            global AlertAdminOnError
            AlertAdminOnError = value
            await ctx.respond(f'AlertAdminOnError has been set to {AlertAdminOnError}')
            print(f'AlertAdminOnError changed to {AlertAdminOnError} by {ctx.author.display_name}')

        elif setting.casefold() == "twitchreauth":
            await twitch_auth()
            await ctx.respond(f'New Twitch Auth token retrieved, expires at ' + token_expiry_time.strftime("%Y-%m-%d %H:%M:%S"))
            print(f'Twitch token renewed by {ctx.author.display_name}')

        elif setting.casefold() == "status":
            statusmessage.clear()
            statusmessage.append('Twitch Auth token expires at ' + token_expiry_time.strftime("%Y-%m-%d %H:%M:%S"))
            statusmessage.append("Current status of all watchers:")
            for i in range(len(Streams)):
                statusmessage.append(f'{Streams[i][0]}/{Streams[i][1]} {laststatus[i]}')
            statusmessagejoin = '\n'.join(statusmessage)
            await ctx.respond(f'{statusmessagejoin}')
            print(f'Status queried by {ctx.author.display_name}')

        else:
            await ctx.respond("I don't have that setting, please try again")
            print(f'Received command from {ctx.author.display_name} but I did not understand it :(')
    else:
        await ctx.respond('You do not have appropriate permissions! Leave me alone!!')
        print(f'Received command from {ctx.author.display_name} who does not have admin role "{bot_admin_role}"!')


@bot.event
async def on_ready():
    print('------------------------------------------------------')
    print(f'erkston/residentstalker {version}')
    systemtime = datetime.now()
    bottime = datetime.now(ZoneInfo(BotTimezone))
    print(f'System Time: {systemtime.strftime("%Y-%m-%d %H:%M:%S")} Bot Time: {bottime.strftime("%Y-%m-%d %H:%M:%S")} (Timezone: {BotTimezone})')
    print('Config options:')
    print(f'BotActivity: {BotActivity}')
    print(f'BotAdminRole: {BotAdminRole}')
    print(f'AlertChannelName: {AlertChannelName}')
    print(f'AlertRole: {AlertRole}')
    print(f'AllowDiscordEmbed: {AllowDiscordEmbed}')
    print(f'EnableStartupMessage: {EnableStartupMessage}')
    print(f'AlertAdminOnError: {AlertAdminOnError}')
    print(f'DeleteOldAlerts: {DeleteOldAlerts}')
    print(f'OldMessagesToCheck: {OldMessagesToCheck}')
    print(f'OfflineCheckInterval: {OfflineCheckInterval}')
    print(f'OnlineCheckInterval: {OnlineCheckInterval}')
    print(f'AlertCooldown: {AlertCooldown}')
    for i in range(len(Streams)):
        print(f'Streams[{i}]: {Streams[i]}')
    print('------------------------------------------------------')
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'{bot.user} is connected to the following guild(s):')
    for guild in bot.guilds:
        print(f'{guild.name} (id: {guild.id})')

    global alert_channel
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name == AlertChannelName:
                alert_channel = channel
                print(f'Alert Channel found: #{alert_channel.name}')

    global alert_role
    global bot_admin_role
    for guild in bot.guilds:
        for role in guild.roles:
            if role.name == AlertRole:
                alert_role = role
                print(f'Alert Role found: "{alert_role.name}"')
            if role.name == BotAdminRole:
                bot_admin_role = role
                print(f'Bot Admin Role found: "{bot_admin_role.name}"')

    await bot.change_presence(status=discord.Status.online,
                              activity=discord.Activity(type=discord.ActivityType.watching,
                                                        name=f"{BotActivity}"))
    print('Updated discord presence')

    await delete_old_messages()

    print('------------------------------------------------------')

    twitch_auth_renew.start()
    await asyncio.sleep(3)

    am_i_alive.start()
    await asyncio.sleep(3)

    print('------------------------------------------------------')

    await main()


async def twitch_auth():
    print('twitchauth: Beginning Twitch Authorization...')
    global headers
    global token_expiry_time
    authendpoint = 'https://id.twitch.tv/oauth2/token'
    params = {'client_id': TwitchClientID,
              'client_secret': TwitchClientSecret,
              'grant_type': 'client_credentials'
              }
    authcall = requests.post(url=authendpoint, params=params)
    access_token = authcall.json()['access_token']

    token_expiry_time = datetime.now(ZoneInfo(BotTimezone)) + timedelta(seconds=authcall.json()['expires_in'])
    print(f'twitchauth: Access token acquired! Expires at ' + token_expiry_time.strftime("%Y-%m-%d %H:%M:%S"))

    headers = {
        'Client-ID': TwitchClientID,
        'Authorization': "Bearer " + access_token
    }


async def main():
    async with asyncio.TaskGroup() as task_group:
        for i in range(len(Streams)):
            task_group.create_task(watch(Streams[i], i))
            await asyncio.sleep(3)


@tasks.loop(minutes=1)
async def am_i_alive():
    global AlertCooldownSeconds
    global laststatus_time
    print('amialive: Beginning alive check...')
    now = datetime.now(timezone.utc)
    if (now - laststatus_time).seconds > AlertCooldownSeconds:
        print(f'amialive: Last update time ({laststatus_time.strftime("%Y-%m-%d %H:%M:%S")}) is longer ago than AlertCooldown ({AlertCooldown}), I think something may be wrong!')
        if distutils.util.strtobool(AlertAdminOnError):
            print(f'amialive: AlertAdminOnError is {AlertAdminOnError}, sending discord message to bot admins')
            await alert_channel.send(f"\n {bot_admin_role.mention}\n I haven't been able to check Twitch in a while, please check my console!", allowed_mentions=allowed_mentions)
        else:
            print(f'amialive: AlertAdminOnError is {AlertAdminOnError}, not sending discord alert')
        await asyncio.sleep(AlertCooldownSeconds)
    else:
        print(f'amialive: Last update time ({laststatus_time.strftime("%Y-%m-%d %H:%M:%S")}) is more recent than AlertCooldown ({AlertCooldown})')


@tasks.loop(hours=24)
async def twitch_auth_renew():
    await twitch_auth()
    print('twitchauth: Twitch auth renew completed, will renew in 24 hours')


async def watch(stream, index):
    global laststatus
    global laststatus_time
    if len(laststatus) < index+1:
        laststatus_time = datetime.now(timezone.utc)
        laststatus.append(f'initilized (Updated <t:' + str(int(laststatus_time.timestamp())) + ':R>)')
    print(f'watcher-{index} spawned for {stream}')
    if distutils.util.strtobool(EnableStartupMessage):
        print(f'watcher-{index}: EnableStartupMessage is {EnableStartupMessage}, sending discord message')
        await alert_channel.send(f"I'm watching to see if {stream[0]} is playing {stream[1]}")
    islive = await is_user_live(stream[0], index)
    while True:
        while not islive:
            print(f'watcher-{index}: {stream[0]} is not live, sleeping for {OfflineCheckInterval} before next check')
            laststatus_time = datetime.now(timezone.utc)
            laststatus[index] = f'not live, {OfflineCheckInterval} check (Updated <t:' + str(int(laststatus_time.timestamp())) + ':R>)'
            await asyncio.sleep(OfflineCheckIntervalSeconds)
            islive = await is_user_live(stream[0], index)
        while islive:
            print(f'watcher-{index}: {stream[0]} live! Checking their game...')
            gamematch = await does_game_match(stream)
            while gamematch == 0:
                print(
                    f'watcher-{index}: {stream[0]} is live but not playing {stream[1]}, sleeping for {OnlineCheckInterval} before next check')
                laststatus_time = datetime.now(timezone.utc)
                laststatus[index] = f'live but playing different game, {OnlineCheckInterval} check (Updated <t:' + str(int(laststatus_time.timestamp())) + ':R>)'
                await asyncio.sleep(OnlineCheckIntervalSeconds)
                gamematch = await does_game_match(stream)
            while gamematch == 1:
                print(
                    f'watcher-{index}: {stream[0]} live and playing {stream[1]}! Sending alert (AllowDiscordEmbed = {AllowDiscordEmbed})')
                if distutils.util.strtobool(AllowDiscordEmbed):
                    link_string = "".join(["https://twitch.tv/", str(stream[0])])
                else:
                    link_string = "".join(["<https://twitch.tv/", str(stream[0]), ">"])
                await alert_channel.send(
                    f'\n {alert_role.mention}\n{stream[0]} is playing {stream[1]}! Get in here!\n{link_string}',
                    allowed_mentions=allowed_mentions)
                print(f'watcher-{index}: Alert message sent! Sleeping for {AlertCooldown}')
                laststatus_time = datetime.now(timezone.utc)
                laststatus[index] = f'alert was sent and currently in {AlertCooldown} cooldown (Updated <t:' + str(int(laststatus_time.timestamp())) + ':R>)'
                await asyncio.sleep(AlertCooldownSeconds)
            if gamematch == 2:
                print(f'watcher-{index}: {stream[0]} was live but stopped streaming...')
                islive = False


async def is_user_live(username, index):
    global headers
    endpoint = 'https://api.twitch.tv/helix/streams'
    params = {'user_login': username}
    try:
        response = requests.get(endpoint, headers=headers, params=params)
    except Exception as exc:
        print(f'Exception: "{exc}" while checking live status for {username}!')
        if distutils.util.strtobool(AlertAdminOnError):
            await alert_channel.send(f'\n {bot_admin_role.mention}\n Exception occured, please check my console!',
                    allowed_mentions=allowed_mentions)
    data = response.json()['data']
    if len(data) == 0:
        return False
    else:
        print(f'watcher-{index}: Received API response, {username} is live!')
        return True


async def does_game_match(stream):
    global headers
    endpoint = 'https://api.twitch.tv/helix/streams'
    params = {'user_login': stream[0]}
    try:
        response = requests.get(endpoint, headers=headers, params=params)
    except Exception as exc:
        print(f'Exception: "{exc}" while checking game for {stream}!')
    data = response.json()['data']
    if len(data) == 0:
        return 2
    elif data[0]['game_name'] != stream[1]:
        return 0
    else:
        return 1


async def delete_old_messages():
    global DeleteOldAlerts
    global OldMessagesToCheck
    if distutils.util.strtobool(DeleteOldAlerts):
        print(f'DeleteOldAlerts is {DeleteOldAlerts}, Checking {OldMessagesToCheck} messages for old alerts to delete...')
        async for message in alert_channel.history(limit=int(OldMessagesToCheck)):
            if message.author == bot.user:
                print(f'Found old message from {bot.user}, deleting it')
                await message.delete()
        print('Finished checking for old messages')
    else:
        print(f'DeleteOldAlerts is {DeleteOldAlerts}, not deleting any old messages...')


bot.run(DiscordBotToken)
