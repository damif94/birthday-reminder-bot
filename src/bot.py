import telebot
import os

TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

commands = [
    {
        "command": "start",
        "description": "Start the bot"
    },
    {
        "command": "set",
        "description": "Set a new birthday in the format <name> <dd/mm/yyyy>"
    },
    {
        "command": "query",
        "description": "Query a specific birthday by <name>"
    },
    {
        "command": "delete",
        "description": "Delete a birthday by <name>"
    },
    {
        "command": "query_all",
        "description": "Query all birthdays"
    },
    {
        "command": "set_reminders",
        "description": "Set reminders for birthdays in the list"
    },
    {
        "command": "unset_reminders",
        "description": "Unset reminders for birthdays in the list"
    }
]