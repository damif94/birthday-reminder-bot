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
        "command": "listupcoming (<n>)",
        "description": "List all upcoming birthdays up to <n> days from now. Default is 14 days"
    },
    {
        "command": "setreminderhour <hour>",
        "description": "Set <hour> for the reminder hour of the day (in UTC)"
    }
]
