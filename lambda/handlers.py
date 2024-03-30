import json
import os
import sys
import logging
import telebot

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.bot import bot
from src.reminders import reminder
from src.handlers import * # for side effects

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

def remind(_event, _context):
    reminder()
    return {'statusCode': 200}

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
