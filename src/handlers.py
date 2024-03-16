import datetime
import json
import typing
import telebot
import logging
from botocore import config as botocore_config, exceptions as botocore_exceptions
import boto3
from .config import bot, MY_CHAT_ID, BUCKET_NAME, FILE_NAME

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)


def load_birthdays_from_bucket() -> typing.List[typing.Tuple[str, datetime.date]]:
    s3_config = botocore_config.Config(connect_timeout=2, read_timeout=2)
    s3_client_with_timeout = boto3.client('s3', config=s3_config)
    try:
        logger.info("Loading birthdays from s3")
        response = s3_client_with_timeout.get_object(Bucket=BUCKET_NAME, Key=FILE_NAME)
        logger.info("Read object from s3")
        object_body = response['Body']
        content = object_body.read()
        content = content.decode(encoding='utf-8', errors='strict').strip()
        content = content.split("\n")

        birthdays: typing.List[typing.Tuple[str, datetime.date]] = []
        for row in content[1:]:
            row_items = row.split(',')
            person_name = row_items[0]
            date = datetime.datetime.strptime(row_items[1], "%d/%m/%Y").date()
            birthdays.append((person_name, date))

        return birthdays
    except botocore_exceptions.EndpointConnectionError as e:
        logger.error(f"Failed to connect to S3 endpoint: {e}")
        raise
    except botocore_exceptions.ReadTimeoutError as e:
        logger.error(f"Timeout while reading object from S3: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to read object from S3: {e}")
        raise


def remind(event, context):
    try:
        today = datetime.datetime.now().date()
        birthdays = load_birthdays_from_bucket()
        for person_name, birthday in birthdays:
            if birthday.month == today.month and birthday.day == today.day:
                text = "Its {} birthday today!".format(person_name)
                bot.send_message(chat_id=MY_CHAT_ID, text=text)
    except Exception as e:
        return {
            "statusCode": 500,
            'body': json.dumps({'error': str(e)})
        }
    return {"statusCode": 200}


def api(event, context):
    logger.info("Received event: {}".format(event))
    try:
        # content_length = int(event['headers']['Content-Length'])
        post_data_str = json.loads(event['body'])
        # post_data_str = post_data.decode('utf-8')
        update = telebot.types.Update.de_json(post_data_str)
        bot.process_new_updates([update])
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    return {"statusCode": 200}


@bot.message_handler(commands=['query'])
def handle_query(data):
    chat_id = data.json["chat"]["id"]
    try:
        person_name = str(data.json["text"][len("/query"):]).strip()
        birthdays = load_birthdays_from_bucket()
        for name, date in birthdays:
            if name.lower() == person_name.lower():
                text = "{}'s birthday is on {}".format(name, date.strftime("%d/%m/%Y"))
                bot.send_message(chat_id=chat_id, text=text)
                return {"statusCode": 200}
        bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))
        return {"statusCode": 200}
    except Exception as e:
        bot.send_message(chat_id=chat_id, text="Error: {}".format(str(e)))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
