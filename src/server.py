import os
import logging
import datetime
import sys
import telebot

from flask import Flask, request

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.birthday_storage import MemoryBirthdayStorage
from src.bot import commands, bot

MY_CHAT_ID = os.getenv('MY_CHAT_ID')
birthday_storage = MemoryBirthdayStorage()

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

bot.set_my_commands(commands)
app = Flask(__name__)


@bot.message_handler(commands=['start'])
def handle_start(message):
    text = "I can help you remember birthdays.\n"
    text += "You can use the following commands to interact with me:\n\n"
    for command in commands:
        text += "/{} - {}\n".format(command["command"], command["description"])
    bot.send_message(chat_id=message.chat.id, text=text)


@bot.message_handler(commands=['query_all'])
def handle_query_all(message):
    birthdays = birthday_storage.load_birthdays()
    text = ""
    for name, date in birthdays:
        text += "{} - {}\n".format(name, date.strftime("%d/%m/%Y"))
    bot.send_message(chat_id=message.chat.id, text=text)


@bot.message_handler(commands=['set'])
def handle_set(message):
    try:
        text = remove_command_prefix(message.text)
        message_parts = text.split(" ")
        if len(message_parts) < 2:
            bot.reply_to(message, text="Invalid input. Please use /set <name> <date>")
        person_name = " ".join(message_parts[0:len(message_parts) - 1])
        date_str = message_parts[-1]
        date = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
        birthday_storage.store_birthday(person_name, date)
        bot.send_message(chat_id=message.chat.id, text="Birthday for {} was correctly set".format(person_name))
    except ValueError:
        bot.send_message(chat_id=message.chat.id, text="Invalid date format. Please use dd/mm/yyyy")


@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return '', 200


def remove_command_prefix(text: str) -> str:
    return text.split(" ", 1)[1]


if __name__ == '__main__':
    app.run(debug=True, port=8000)

# def remind(_event, _context):
#     try:
#         today = datetime.datetime.now().date()
#         birthdays = birthday_storage.load_birthdays()
#         for person_name, birthday in birthdays:
#             if birthday.month == today.month and birthday.day == today.day:
#                 text = "Its {} birthday today!".format(person_name)
#                 bot.reply_to(chat_id=MY_CHAT_ID, text=text)
#     except Exception as e:
#         raise e
#     return {"statusCode": 200}
