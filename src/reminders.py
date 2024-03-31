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

MY_CHAT_ID = os.getenv('MY_CHAT_ID')
STORAGE_TYPE = os.getenv('STORAGE_TYPE')
birthday_storage = build_storage(STORAGE_TYPE)


def reminder():
    try:
        today = datetime.datetime.now().date()
        birthdays = birthday_storage.load_birthdays(chat_id=MY_CHAT_ID)
        for person_name, birthday in birthdays:
            if birthday.month == today.month and birthday.day == today.day:
                text = "Its {} birthday today!".format(person_name)
                bot.send_message(chat_id=MY_CHAT_ID, text=text)
    except Exception as e:
        text = 'An error occurred while processing your request: {}'.format(str(e))
        bot.send_message(chat_id=MY_CHAT_ID, text=text)
        logger.error(text.format(e))
    finally:
        return {'statusCode': 200}

if __name__ == '__main__':
    reminder()