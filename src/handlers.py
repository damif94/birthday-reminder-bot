import datetime
import json
import os
import logging
import boto3

from src.birthday_storage import S3BirthdayStorage
from src.bot import commands, bot

MY_CHAT_ID = os.getenv('MY_CHAT_ID')
BUCKET_NAME = os.getenv('BUCKET_NAME')
FILE_NAME = os.getenv('FILE_NAME')
USER_TABLE_NAME = os.getenv('USER_TABLE_NAME')

birthday_s3_storage = S3BirthdayStorage(**{"bucket_name": BUCKET_NAME, "file_name": FILE_NAME})

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

bot.set_my_commands(commands)


def remind(_event, _context):
    try:
        today = datetime.datetime.now().date()
        birthdays = birthday_s3_storage.load_birthdays()
        for person_name, birthday in birthdays:
            if birthday.month == today.month and birthday.day == today.day:
                text = "Its {} birthday today!".format(person_name)
                bot.send_message(chat_id=MY_CHAT_ID, text=text)
    except Exception as e:
        raise e
    return {"statusCode": 200}


def api(event, _context):
    logger.info("Received event: {}".format(event))
    post_data_str = json.loads(event['body'])
    if "message" not in post_data_str:
        return {"statusCode": 200}
    try:
        if post_data_str["message"]["text"] == "/start":
            return handle_start(post_data_str)
        elif post_data_str["message"]["text"].startswith("/set "):
            return handle_set(post_data_str)
        elif post_data_str["message"]["text"].startswith("/delete "):
            return handle_delete(post_data_str)
        elif post_data_str["message"]["text"].startswith("/query "):
            return handle_query(post_data_str)
        elif post_data_str["message"]["text"] == "/query_all":
            return handle_query_all(post_data_str)
        # elif post_data_str["message"]["text"] == "/set_reminders":
        #     return handle_set_reminders(post_data_str, True)
        # elif post_data_str["message"]["text"] == "/unset_reminders":
        #     return handle_set_reminders(post_data_str, False)
        else:
            return handle_command_not_found(post_data_str)
    except Exception as e:
        chat_id = post_data_str["message"]["chat"]["id"]
        bot.send_message(chat_id=chat_id, text='An error occurred while processing your request: {}'.format(str(e)))
        logger.error("An error occurred while processing the request: {}".format(e))
        return {
            'statusCode': 200,
            'body': json.dumps({'error': str(e)})
        }


def handle_start(data):
    chat_id = data["message"]["chat"]["id"]
    text = "I can help you remember birthdays.\n"
    text += "You can use the following commands to interact with me:\n\n"
    for command in commands:
        text += "/{} - {}\n".format(command["command"], command["description"])
    bot.send_message(chat_id=chat_id, text=text)
    return {"statusCode": 200}


def handle_set(data):
    chat_id = data["message"]["chat"]["id"]
    try:
        data = str(data["message"]["text"][len("/set"):]).strip()
        data_parts = data.split(" ")
        if len(data_parts) < 2:
            bot.send_message(chat_id=chat_id, text="Invalid input. Please use /set <name> <date>")
            return {"statusCode": 200}
        person_name = " ".join(data_parts[0:len(data_parts) - 1])
        date_str = data_parts[-1]
        date = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
        birthday_s3_storage.store_birthday(person_name, date)
        bot.send_message(chat_id=chat_id, text="Birthday for {} was correctly set".format(person_name))
        return {"statusCode": 200}
    except ValueError:
        bot.send_message(chat_id=chat_id, text="Invalid date format. Please use dd/mm/yyyy")
        return {"statusCode": 200}
    except Exception as e:
        raise e


def handle_delete(data):
    chat_id = data["message"]["chat"]["id"]
    try:
        person_name = str(data["message"]["text"][len("/delete"):]).strip()
        deleted = birthday_s3_storage.delete_birthday(person_name)
        if deleted:
            bot.send_message(chat_id=chat_id, text="Birthday correctly deleted")
            return {"statusCode": 200}
        bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))
        return {"statusCode": 200}
    except Exception as e:
        raise e


def handle_query(data):
    chat_id = data["message"]["chat"]["id"]
    try:
        person_name = str(data["message"]["text"][len("/query"):]).strip()
        birthday = birthday_s3_storage.get_birthday(person_name)
        if birthday is not None:
            text = birthday.strftime("%d/%m/%Y")
            bot.send_message(chat_id=chat_id, text=text)
            return {"statusCode": 200}
        bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))
        return {"statusCode": 200}
    except Exception as e:
        raise e


def handle_query_all(data):
    chat_id = data["message"]["chat"]["id"]
    try:
        birthdays = birthday_s3_storage.load_birthdays()
        text = ""
        for name, date in birthdays:
            text += "{} - {}\n".format(name, date.strftime("%d/%m/%Y"))
        bot.send_message(chat_id=chat_id, text=text)
        return {"statusCode": 200}
    except Exception as e:
        raise e


def handle_set_reminders(data, value: bool):
    chat_id = data["message"]["chat"]["id"]
    try:
        dynamodb_client = boto3.resource('dynamodb')
        table = dynamodb_client.Table(USER_TABLE_NAME)
        response = table.get_item(Key={"chat_id": str(chat_id)})
        new_item = {
            "chat_id": str(chat_id),
            "reminders": value
        }
        if 'Item' in response:
            new_item = response["Item"]
        table.put_item(Item=new_item)

        if value:
            bot.send_message(chat_id=chat_id, text="Reminders set")
        else:
            bot.send_message(chat_id=chat_id, text="Reminders unset")
    except Exception as e:
        raise e


def handle_command_not_found(data):
    chat_id = data["message"]["chat"]["id"]
    bot.send_message(chat_id=chat_id, text="Command not found")
    return {"statusCode": 200}


if __name__ == "__main__":
    f = open("../example_request.json", "r")
    d = json.loads(f.read())
    handle_set(d)
