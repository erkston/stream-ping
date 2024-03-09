# ResidentStalker
A Discord bot designed to check if a Twitch streamer is playing a specific game, and if so send a Discord notification.
## Discord and Twitch Developer set-up
From Discord Developer Portal you will need your bot token. From the Twitch Developer console you will need your Client ID and Client Secret. These can be provided via a .env file (see .env.example) or directly using docker ENV or similar.
With either method you need to set the following environment variables:
- DISCORDBOTTOKEN
- TWITCHCLIENTID
- TWITCHCLIENTSECRET
## Discord Server set-up
The bot requires the following permissions: Send Messages, Manage Messages, Read Message History, Embed Links. It also requires permission to mention roles.
The server should also have a dedicated role for the @notification mention (see config below).
## Configuration
Rename config.json.example to config.json and edit settings as needed:
- BotTimezone - Timezone used for timestamps in console output. Will use this timezone instead of system time
- BotActivity* - Actvity the bot should be "Watching" in its Discord presence
- BotAdminRole - Name of the role whose members can change config options via /rs
- AlertChannelName - The Channel name the bot should use to send messages
- AlertRole - The Role name the bot should mention when alerting
- AllowDiscordEmbed* - The alert message contains a link to the twitch stream, this setting controls whether or not the message will be shown with a large discord embed and thumbnail
- DeleteOldAlerts* - When starting up and shutting down the bot removes its old messages unless this is false
- OfflineCheckInterval* - Interval the bot will check the stream status while the channel is not live. Must have units attached (1m, 10m, 1h, etc) 
- OnlineCheckInterval* - Interval the bot will check the stream status while the channel is live. Must have units attached (10s, 30s, 1m, etc) 
- AlertCooldown* - After alerting the bot will wait for this amount of time before beginning to check the stream status again. Must have units attached (3h, 12h, 2d, etc) 
- Streams - List of channels to check and their associated games. Can be any number of streams as long as syntax is preserved. **The game names are case-sensitive so it's recommended to copy directly from the Twitch category page**
## Slash Command Configuration (/rs)
Any option listed with an asterisk(*) above can be modified on the fly by anyone who has BotAdminRole by using "/rs SETTING VALUE". Tab completion also works for those settings that are settable using the command.
Any changes made using the command are temporary until the next restart, permanent changes must be made in the config file.

Examples:
- /rs BotActivity paint dry
- /rs OfflineCheckInterval 2m
- /rs AlertCooldown 12h

Additionaly you can use this command to get a new auth token from Twitch:
- /rs TwitchReAuth anyvalue

Setting names are not case-sensitive, however the setting values need to follow the same format as in the config or things will start breaking.
Cooldowns/timers need to have units (s, m, or h) and boolean options are true/false.
## Docker Images
See [DockerHub](https://hub.docker.com/r/erkston/residentstalker) for installation instructions