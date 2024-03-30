import datetime
import json
import sys
import os
import logging
import telebot

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.birthday_storage import build_storage
from src.bot import commands, bot

BUCKET_NAME = os.getenv('BUCKET_NAME')
FILE_NAME = os.getenv('FILE_NAME')
USER_TABLE_NAME = os.getenv('USER_TABLE_NAME')
STORAGE_TYPE = os.getenv('STORAGE_TYPE')

birthday_storage = build_storage(storage_type=STORAGE_TYPE)

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)


def remove_command_prefix(text: str) -> str:
    return " ".join(text.split(" ", 1)[1:]).strip()


@bot.message_handler(commands=['start'])
def handle_start(message):
    text = "I can help you remember birthdays.\n"
    text += "You can use the following commands to interact with me:\n\n"
    for command in commands:
        text += "/{} - {}\n".format(command["command"], command["description"])
    bot.send_message(chat_id=message.chat.id, text=text)


@bot.message_handler(commands=['set'])
def handle_set(message):
    chat_id = message.chat.id
    text = remove_command_prefix(message.text)
    try:
        data_parts = text.split(" ")
        if len(data_parts) < 2:
            bot.send_message(chat_id=chat_id, text="Invalid input. Please use /set <name> <date>")
            return
        person_name = " ".join(data_parts[0:len(data_parts) - 1])
        date_str = data_parts[-1]
        date = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
        birthday_storage.store_birthday(person_name, date)
        bot.send_message(chat_id=chat_id, text="Birthday for {} was correctly set".format(person_name))
    except ValueError:
        bot.send_message(chat_id=chat_id, text="Invalid date format. Please use dd/mm/yyyy")


@bot.message_handler(commands=['delete'])
def handle_delete(message):
    chat_id = message.chat.id
    text = remove_command_prefix(message.text)
    if text == "":
        bot.send_message(chat_id=chat_id, text="Invalid input. Please use /delete <name>")
        return
    person_name = str(text).strip()
    deleted = birthday_storage.delete_birthday(person_name)
    if deleted:
        bot.send_message(chat_id=chat_id, text="Birthday correctly deleted")
        return
    bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))


@bot.message_handler(commands=['query'])
def handle_query(message):
    chat_id = message.chat.id
    text = remove_command_prefix(message.text)
    if text == "":
        bot.send_message(chat_id=chat_id, text="Invalid input. Please use /query <name>")
        return
    person_name = text
    birthday = birthday_storage.get_birthday(person_name)
    if birthday is not None:
        text = birthday.strftime("%d/%m/%Y")
        bot.send_message(chat_id=chat_id, text=text)
        return
    bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))


@bot.message_handler(commands=['query_all'])
def handle_query_all(message):
    chat_id = message.chat.id
    birthdays = birthday_storage.load_birthdays()
    text = ""
    for name, date in birthdays:
        text += "{} - {}\n".format(name, date.strftime("%d/%m/%Y"))
    if text == "":
        text = "No birthdays found"
    bot.send_message(chat_id=chat_id, text=text)


@bot.message_handler(func=lambda message: True)
def handle_command_not_found(message):
    chat_id = message.chat.id
    bot.send_message(chat_id=chat_id, text="Command not found")


def webhook(event, _context):
    logger.debug("Received event: {}".format(event))
    event_body_str = json.loads(event['body'])
    if "message" not in event_body_str:
        logger.info("No message in post data")
        return {"statusCode": 200}
    try:
        update = telebot.types.Update.de_json(event_body_str)
        bot.process_new_updates([update])
        return {'statusCode': 200}
    except Exception as e:
        chat_id = event_body_str["message"]["chat"]["id"]
        bot.send_message(chat_id=chat_id, text='An error occurred while processing your request: {}'.format(str(e)))
        logger.error("An error occurred while processing the request: {}".format(e))
        return {
            'statusCode': 200,
            'body': json.dumps({'error': str(e)})
        }
