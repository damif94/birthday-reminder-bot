import datetime
import sys
import os
import logging

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.birthday_storage import build_storage
from src.bot import bot

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

STORAGE_TYPE = os.getenv('STORAGE_TYPE')
birthday_storage = build_storage(STORAGE_TYPE)


def reminder():
    today = datetime.datetime.now().date()
    birthdays_with_chat_id = birthday_storage.load_birthdays_by_day(today)
    for chat_id, birthday in birthdays_with_chat_id:
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
