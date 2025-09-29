#    Copyright (c) 2021 Ayush
#    
#    This program is free software: you can redistribute it and/or modify  
#    it under the terms of the GNU General Public License as published by  
#    the Free Software Foundation, version 3.
# 
#    This program is distributed in the hope that it will be useful, but 
#    WITHOUT ANY WARRANTY; without even the implied warranty of 
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
#    General Public License for more details.
# 
#    reference < https://github.com/Ayush7445/telegram-auto_forwarder/blob/main/License > .

# Import necessary modules
# Import necessary modules
from telethon import TelegramClient, events
from decouple import config
from telethon.sessions import StringSession
import logging
import os
import ast

# Configure logging
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.WARNING)

# Print starting message
print("Starting...")

# Read configuration from environment variables
APP_ID = config("APP_ID", default=0, cast=int)
API_HASH = config("API_HASH", default=None, cast=str)
SESSION = config("SESSION", default="", cast=str)

BLOCKED_TEXTS = config("BLOCKED_TEXTS", default="", cast=lambda x: [i.strip().lower() for i in x.split(',')])
MEDIA_FORWARD_RESPONSE = config("MEDIA_FORWARD_RESPONSE", default="yes").lower()

FROM_CHANNEL_STR = config("FROM_CHANNEL", default="[]", cast=str)
TO_CHANNEL_STR = config("TO_CHANNEL", default="[]", cast=str)

# Convert string representation of lists to actual lists
try:
    FROM_CHANNELS = ast.literal_eval(FROM_CHANNEL_STR)
    TO_CHANNELS = ast.literal_eval(TO_CHANNEL_STR)

    # Convert strings to integers
    FROM_CHANNELS = [int(ch) for ch in FROM_CHANNELS]
    TO_CHANNELS = [int(ch) for ch in TO_CHANNELS]

except (ValueError, SyntaxError) as e:
    print(f"Error parsing channel lists: {e}")
    exit(1)

# Validate that we have equal number of source and destination channels
if len(FROM_CHANNELS) != len(TO_CHANNELS):
    print(f"Error: Number of FROM_CHANNELS ({len(FROM_CHANNELS)}) must equal TO_CHANNELS ({len(TO_CHANNELS)})")
    exit(1)

# Create forwarding map (1-to-1 mapping based on index)
forwarding_map = dict(zip(FROM_CHANNELS, TO_CHANNELS))

print(f"Configured {len(forwarding_map)} forwarding pairs:")
for source, dest in forwarding_map.items():
    print(f"  {source} → {dest}")

# Define the database session file name
session_file = '/home/ubuntu/telegram/telegram-auto_forwarder/telethon.session'
os.makedirs('/home/ubuntu/telegram/telegram-auto_forwarder/downloads', exist_ok=True)

# Initialize Telethon client
try:
    clientAgent = TelegramClient(session_file, APP_ID, API_HASH)
    clientAgent.start()

except Exception as ap:
    print(f"ERROR - {ap}")
    exit(1)

# Event handler for incoming messages
@clientAgent.on(events.NewMessage(incoming=True, chats=FROM_CHANNELS))
async def sender_bH(event):
    source_chat = event.chat_id
    destination_chat = forwarding_map.get(source_chat)

    if not destination_chat:
        print(f"Warning: No destination found for source chat {source_chat}")
        return

    file_path = None
    try:
        message_text = event.raw_text

        # Check for blocked texts #"| [EDITED]"
        if BLOCKED_TEXTS and message_text:
            message_lower = message_text.lower()
            if any(blocked_text in message_lower for blocked_text in BLOCKED_TEXTS if blocked_text):
                print(f"Blocked message from {source_chat} containing blocked text")
                return

        if event.media:
            file_path = None
            try:
                # 1. Download the photo
                # The downloaded file path will be returned
                file_path = await event.download_media(file='/home/ubuntu/telegram/telegram-auto_forwarder/downloads/')

                # 2. Get the caption/text
                text_caption = event.text if event.text else ""

                # 3. Re-upload the photo with the caption to your channel
                await clientAgent.send_file(
                    destination_chat,
                    file=file_path,
                    caption=text_caption
                )
                print(f"Forwarded media message to channel {destination_chat}")

            finally:
                # 4. Clean up by deleting the downloaded file
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Clean up downloaded file")
                    except OSError as cleanup_error:
                        print(f"Warning: Could not delete file")

        else:
            await clientAgent.send_message(destination_chat, event.raw_text)
            print(f"Forwarded text message to channel {destination_chat}")

    except Exception as e:
        print(f"Error forwarding message to channel {destination_chat}: {e}")

# Run the bot
print("Bot has started.")
clientAgent.run_until_disconnected()
