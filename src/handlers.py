import sys
import os
import logging
import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.birthday_storage import build_storage as build_birthday_storage, Birthday
from src.user_storage import build_storage as build_user_storage, User
from src.bot import commands, bot
from src import utils

USERS_TABLE_NAME = os.getenv('USERS_TABLE_NAME')
STORAGE_TYPE = os.getenv('STORAGE_TYPE')

birthday_storage = build_birthday_storage(storage_type=STORAGE_TYPE)
user_storage = build_user_storage(storage_type=STORAGE_TYPE)

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)


def remove_command_prefix(text: str) -> str:
    return " ".join(text.split(" ", 1)[1:]).strip()


@bot.message_handler(commands=['start'])
def handle_start(message):
    text = "I can help you remember birthdays.\n"
    text += "You can store birthdays and I will remind you when they come.\n\n"
    text += "Use the following commands to interact with me:\n\n"
    chat_id = str(message.chat.id)
    user = User(
        chat_id=chat_id,
        user_name=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        reminder_hour=0,
    )
    user_storage.store_user(user)
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


@bot.message_handler(commands=['listupcoming'])
def handle_listupcoming(message):
    chat_id = str(message.chat.id)
    text = remove_command_prefix(message.text)
    if text == "":
        text = "14"
    elif not utils.represents_int(text):
        bot.send_message(chat_id=chat_id, text="Invalid number format. Please use an integer")
        return
    elif int(text) < 0 or int(text) > 365:
        bot.send_message(chat_id=chat_id, text="Invalid number input. Please use a integer between 0 and 365")
        return

    birthdays = birthday_storage.load_birthdays_by_chat_id(chat_id)

    today = datetime.datetime.now()
    today_plus_days = today + datetime.timedelta(days=int(text))

    today_plus_days_this_year = today_plus_days
    today_plus_days_next_year = None
    if today_plus_days.year > today.year:
        today_plus_days_this_year = datetime.date(year=today.year, month=12, day=31)
        today_plus_days_next_year = today_plus_days

    filtered_birthdays = [
        b for b in birthdays
        if all([
            b.month > today.month
            or (b.month == today.month and b.day >= today.day),
            (b.month < today_plus_days_this_year.month
             or (b.month == today_plus_days_this_year.month and b.day < today_plus_days_this_year.day))
        ])
    ]

    if today_plus_days_next_year is not None:
        filtered_birthdays += [
            b for b in birthdays
            if b.month < today_plus_days_next_year.month
               or (b.month == today_plus_days_next_year.month and b.day < today_plus_days_next_year.day)
        ]

    text = ""
    for birthday in filtered_birthdays:
        text += "{} - {}\n".format(birthday.name, birthday.date_format())
    if text == "":
        text = "No birthdays found"
    bot.send_message(chat_id=chat_id, text=text)


@bot.message_handler(commands=['setreminderhour'])
def handle_set_hour(message):
    chat_id = str(message.chat.id)
    text = remove_command_prefix(message.text)
    if text == "":
        bot.send_message(chat_id=chat_id, text="Invalid input. Please use /setreminderhour <hour>")
        return
    if not utils.represents_int(text):
        bot.send_message(chat_id=chat_id, text="Invalid hour format. Please use an integer")
        return
    if int(text) < 0 or int(text) > 23:
        bot.send_message(chat_id=chat_id, text="Invalid hour format. Please use a integer between 0 and 23")
        return
    user_storage.update_reminder_hour(chat_id, int(text))
    text = "Hour for reminder correctly set"
    bot.send_message(chat_id=chat_id, text=text)


@bot.message_handler(func=lambda message: True)
def handle_command_not_found(message):
    chat_id = str(message.chat.id)
    bot.send_message(chat_id=chat_id, text="Command not found")
