import sys
import os
import logging

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.birthday_storage import build_storage, Birthday
from src.bot import commands, bot

USERS_TABLE_NAME = os.getenv('USERS_TABLE_NAME')
STORAGE_TYPE = os.getenv('STORAGE_TYPE')

birthday_storage = build_storage(storage_type=STORAGE_TYPE)

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)


def remove_command_prefix(text: str) -> str:
    return " ".join(text.split(" ", 1)[1:]).strip()


@bot.message_handler(commands=['start'])
def handle_start(message):
    text = "I can help you remember birthdays.\n"
    text += "You can store birthdays and I will remind you when they come.\n\n"
    text += "Use the following commands to interact with me:\n\n"
    for command in commands:
        text += "/{} - {}\n".format(command["command"], command["description"])
    bot.send_message(chat_id=message.chat.id, text=text)


@bot.message_handler(commands=['add'])
def handle_add(message):
    chat_id = str(message.chat.id)
    text = remove_command_prefix(message.text)
    try:
        data_parts = text.split(" ")
        data_parts = [d for d in data_parts if d != ""]
        if len(data_parts) < 2:
            bot.send_message(chat_id=chat_id, text="Invalid input. Please use /add <name> <date>")
            return
        person_name = " ".join([d.strip() for d in data_parts[0:len(data_parts) - 1]])
        date_str = data_parts[-1]
        birthday = Birthday(name=person_name, date_str=date_str)
        birthday_storage.store_birthday(chat_id, birthday)
        bot.send_message(chat_id=chat_id, text="Birthday for {} was correctly set".format(person_name))
    except ValueError:
        bot.send_message(chat_id=chat_id, text="Invalid date format. Please use dd/mm/yyyy or dd/mm")


@bot.message_handler(commands=['delete'])
def handle_delete(message):
    chat_id = str(message.chat.id)
    text = remove_command_prefix(message.text)
    if text == "":
        bot.send_message(chat_id=chat_id, text="Invalid input. Please use /delete <name>")
        return
    person_name = str(text).strip()
    deleted = birthday_storage.delete_birthday(chat_id, person_name)
    if deleted:
        bot.send_message(chat_id=chat_id, text="Birthday correctly deleted")
        return
    bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))


@bot.message_handler(commands=['get'])
def handle_get(message):
    chat_id = str(message.chat.id)
    text = remove_command_prefix(message.text)
    if text == "":
        bot.send_message(chat_id=chat_id, text="Invalid input. Please use /get <name>")
        return
    data_parts = text.split(" ")
    data_parts = [d for d in data_parts if d != ""]
    person_name = " ".join([d.strip() for d in data_parts[0:len(data_parts)]])
    birthday = birthday_storage.get_birthday(chat_id, person_name)
    if birthday is not None:
        bot.send_message(chat_id=chat_id, text=birthday.date_format())
    else:
        bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))


@bot.message_handler(commands=['list'])
def handle_list(message):
    chat_id = str(message.chat.id)
    birthdays = birthday_storage.load_birthdays_by_chat_id(chat_id)
    text = ""
    for birthday in birthdays:
        text += "{} - {}\n".format(birthday.name, birthday.date_format())
    if text == "":
        text = "No birthdays found"
    bot.send_message(chat_id=chat_id, text=text)


@bot.message_handler(func=lambda message: True)
def handle_command_not_found(message):
    chat_id = str(message.chat.id)
    bot.send_message(chat_id=chat_id, text="Command not found")
