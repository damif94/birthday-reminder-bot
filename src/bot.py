import os
import telebot

TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN, threaded=False)

commands = [
    {
        "command": "start",
        "description": "Start the bot"
    },
    {
        "command": "add <name> <dd/mm(/yyyy)>",
        "description": "Add a birthday to your list in the format <name> <dd/mm(/yyyy)>"
    },
    {
        "command": "get <name>",
        "description": "Get a birthday from your list by <name>"
    },
    {
        "command": "delete <name>",
        "description": "Delete a birthday from your list by <name>"
    },
    {
        "command": "list",
        "description": "List all your birthdays"
    },
    {
        "command": "setoffset",
        "description": "Set utc offset for the reminder"
    }
]
