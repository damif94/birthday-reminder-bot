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
        "command": "set <name> <dd/mm/yyyy>",
        "description": "Set a new birthday in the format <name> <dd/mm/yyyy>"
    },
    {
        "command": "query <name>",
        "description": "Query a specific birthday by <name>"
    },
    {
        "command": "delete <name>",
        "description": "Delete a birthday by <name>"
    },
    {
        "command": "query_all",
        "description": "Query all birthdays"
    }
]
