import datetime
import json
import sys
import os
import logging
import telebot

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.birthday_storage import S3BirthdayStorage
from src.bot import commands, bot

MY_CHAT_ID = os.getenv('MY_CHAT_ID')
BUCKET_NAME = os.getenv('BUCKET_NAME')
FILE_NAME = os.getenv('FILE_NAME')
USER_TABLE_NAME = os.getenv('USER_TABLE_NAME')

birthday_storage = S3BirthdayStorage(**{"bucket_name": BUCKET_NAME, "file_name": FILE_NAME})

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)
telebot.logger.setLevel(logging.INFO)

def remove_command_prefix(text: str) -> str:
    return text.split(" ", 1)[1].strip()


def remind(_event, _context):
    try:
        today = datetime.datetime.now().date()
        birthdays = birthday_storage.load_birthdays()
        for person_name, birthday in birthdays:
            if birthday.month == today.month and birthday.day == today.day:
                text = "Its {} birthday today!".format(person_name)
                bot.send_message(chat_id=MY_CHAT_ID, text=text)
    except Exception as e:
        raise e
    return {"statusCode": 200}


@bot.message_handler(commands=['start'])
def handle_start(message):
    print("Reminding birthdays")
    text = "I can help you remember birthdays.\n"
    text += "You can use the following commands to interact with me:\n\n"
    for command in commands:
        text += "/{} - {}\n".format(command["command"], command["description"])
    bot.send_message(chat_id=message.chat.id, text=text)
    return {"statusCode": 200}


@bot.message_handler(commands=['set'])
def handle_set(message):
    chat_id = message.chat.id
    text = remove_command_prefix(message.text)
    try:
        data_parts = text.split(" ")
        if len(data_parts) < 2:
            bot.send_message(chat_id=chat_id, text="Invalid input. Please use /set <name> <date>")
            return {"statusCode": 200}
        person_name = " ".join(data_parts[0:len(data_parts) - 1])
        date_str = data_parts[-1]
        date = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
        birthday_storage.store_birthday(person_name, date)
        bot.send_message(chat_id=chat_id, text="Birthday for {} was correctly set".format(person_name))
        return {"statusCode": 200}
    except ValueError:
        bot.send_message(chat_id=chat_id, text="Invalid date format. Please use dd/mm/yyyy")
        return {"statusCode": 200}
    except Exception as e:
        raise e


@bot.message_handler(commands=['delete'])
def handle_delete(message):
    chat_id = message.chat.id
    text = remove_command_prefix(message.text)
    try:
        person_name = str(text).strip()
        deleted = birthday_storage.delete_birthday(person_name)
        if deleted:
            bot.send_message(chat_id=chat_id, text="Birthday correctly deleted")
            return {"statusCode": 200}
        bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))
        return {"statusCode": 200}
    except Exception as e:
        raise e


@bot.message_handler(commands=['query'])
def handle_query(message):
    chat_id = message.chat.id
    text = remove_command_prefix(message.text)
    try:
        person_name = text
        birthday = birthday_storage.get_birthday(person_name)
        if birthday is not None:
            text = birthday.strftime("%d/%m/%Y")
            bot.send_message(chat_id=chat_id, text=text)
            return {"statusCode": 200}
        bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))
        return {"statusCode": 200}
    except Exception as e:
        raise e


@bot.message_handler(commands=['query_all'])
def handle_query_all(message):
    chat_id = message.chat.id
    try:
        birthdays = birthday_storage.load_birthdays()
        text = ""
        for name, date in birthdays:
            text += "{} - {}\n".format(name, date.strftime("%d/%m/%Y"))
        bot.send_message(chat_id=chat_id, text=text)
        return {"statusCode": 200}
    except Exception as e:
        raise e


@bot.message_handler(func=lambda message: True)
def handle_command_not_found(data):
    chat_id = data["message"]["chat"]["id"]
    bot.send_message(chat_id=chat_id, text="Command not found")
    return {"statusCode": 200}


def api(event, _context):
    # logger.info("Received event: {}".format(event))
    post_data_str = json.loads(event['body'])
    if "message" not in post_data_str:
        logger.info("No message in post data")
        return {"statusCode": 200}
    try:
        logger.info("Processing message")
        update = telebot.types.Update.de_json(post_data_str)
        logger.info("Update: {}".format(update))
        bot.process_new_updates([update])
        return {'statusCode': 200}
    except Exception as e:
        chat_id = post_data_str["message"]["chat"]["id"]
        bot.send_message(chat_id=chat_id, text='An error occurred while processing your request: {}'.format(str(e)))
        logger.error("An error occurred while processing the request: {}".format(e))
        return {
            'statusCode': 200,
            'body': json.dumps({'error': str(e)})
        }
