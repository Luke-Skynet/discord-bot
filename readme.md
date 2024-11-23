# My Discord Bot
This is the code for the discord bot that runs on our server.
Some things that it can do are play music, look up pokemon/animals, and (by popular request) facilitate peer-to-peer bonking.
Currently, it only supports one client per server. If you would like to run it on your own server, you can follow these steps:

## Getting Started
1. Set up an application on the Discord Developer Portal (https://discord.com/developers/applications)  
    Under Settings - Bot: Enable PRESENCE, SERVER MEMBERS, MESSAGE CONTENT Privileged Gateway Intents   
    Under Settings - Oauth2 - URL Generator: Select 'Bot' under Scopes with the following Permissions:
    - Read Messages / View Channels
    - Send Messages
    - Send Messages in Threads
    - Embed Links
    - Attach Files
    - Read Message History
    - Use Slash Commands
    - Voice Connect
    - Voice Speak
    - Use Voice Activity

2. Make sure you have docker downloaded (https://docs.docker.com/get-docker/)   
   Download the MongoDB container image with the following command:  
   &nbsp;&nbsp;&nbsp;&nbsp;`docker pull mongo`

3. Clone this repository
4. Create a .env file with the following fields:    
&nbsp;&nbsp;&nbsp;&nbsp;`guild_id= (found by right clicking server name in the top left of your server in discord)`     
&nbsp;&nbsp;&nbsp;&nbsp;`commands_channel_id= (found by right clicking the channel in your server in discord)`      
&nbsp;&nbsp;&nbsp;&nbsp;`bot_key= (found by generating a secret key in the Discord Dev Portal)`     
&nbsp;&nbsp;&nbsp;&nbsp;`owner_id= (found by clicking on your profile picture in Discord)`    
5. After completing these steps, run the bot with the following command inside the repository directory:    
&nbsp;&nbsp;&nbsp;&nbsp;`docker-compose up`
