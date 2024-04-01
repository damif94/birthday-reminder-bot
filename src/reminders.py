import datetime
import sys
import os
import logging
import math

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.birthday_storage import build_storage as build_birthday_storage
from src.user_storage import build_storage as build_user_storage
from src.bot import bot

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

STORAGE_TYPE = os.getenv('STORAGE_TYPE')
birthday_storage = build_birthday_storage(STORAGE_TYPE)
user_storage = build_user_storage(STORAGE_TYPE)


def reminder():
    now = datetime.datetime.now()
    today = now.date()

    users_to_remind = user_storage.load_users_by_reminder_hour(now.hour)
    chat_ids_to_remind = [user.chat_id for user in users_to_remind]
    birthdays_with_chat_id = birthday_storage.load_birthdays_by_day(today)
    for chat_id, birthday in birthdays_with_chat_id:
        if chat_id not in chat_ids_to_remind:
            continue
        text = "Its {} birthday today!".format(birthday.name)
        try:
            bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            text = 'An error occurred while processing your request: {}'.format(str(e))
            bot.send_message(chat_id=chat_id, text=text)
            logger.error(text.format(e))
    return {'statusCode': 200}


if __name__ == '__main__':
    reminder()
