import datetime
import json
import os
import typing
import logging
from botocore import config as botocore_config, exceptions as botocore_exceptions
import boto3
from src.bot import commands, bot

MY_CHAT_ID = os.getenv('MY_CHAT_ID')
BUCKET_NAME = os.getenv('BUCKET_NAME')
FILE_NAME = os.getenv('FILE_NAME')
USER_TABLE_NAME = os.getenv('USER_TABLE_NAME')

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

bot.set_my_commands(commands)


def load_birthdays_from_bucket() -> typing.List[typing.Tuple[str, datetime.date]]:
    s3_config = botocore_config.Config(connect_timeout=2, read_timeout=2)
    s3_client_with_timeout = boto3.client('s3', config=s3_config)
    try:
        response = s3_client_with_timeout.get_object(Bucket=BUCKET_NAME, Key=FILE_NAME)
        logger.debug("Read object from s3")
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
        logger.error(f"Failed to read object from s3: {e}")
        raise


def store_birthdays_to_bucket(birthdays: typing.List[typing.Tuple[str, datetime.date]]):
    s3_config = botocore_config.Config(connect_timeout=2, read_timeout=2)
    s3_client_with_timeout = boto3.client('s3', config=s3_config)
    try:
        content = "name,birthday\n"
        for name, date in birthdays:
            content += f"{name},{date.strftime('%d/%m/%Y')}\n"
        s3_client_with_timeout.put_object(Bucket=BUCKET_NAME, Key=FILE_NAME, Body=content)
    except botocore_exceptions.EndpointConnectionError as e:
        logger.error(f"Failed to connect to S3 endpoint: {e}")
        raise
    except botocore_exceptions.ReadTimeoutError as e:
        logger.error(f"Timeout while reading object from S3: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to read object from s3: {e}")
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
        raise e
    return {"statusCode": 200}


def api(event, context):
    logger.info("Received event: {}".format(event))
    post_data_str = json.loads(event['body'])
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
        bot.send_message(chat_id=chat_id, text='An error occurred while processing your request')
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
        birthdays = load_birthdays_from_bucket()
        for i in range(len(birthdays)):
            name, _ = birthdays[i]
            if name.lower() == person_name.lower():
                birthdays[i] = (person_name, date)
                break
        else:
            birthdays.append((person_name, date))

        store_birthdays_to_bucket(birthdays)
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
        birthdays = load_birthdays_from_bucket()
        for i in range(len(birthdays)):
            name, _ = birthdays[i]
            if name.lower() == person_name.lower():
                birthdays.pop(i)
                store_birthdays_to_bucket(birthdays)
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
        birthdays = load_birthdays_from_bucket()
        for name, date in birthdays:
            if name.lower() == person_name.lower():
                text = date.strftime("%d/%m/%Y")
                bot.send_message(chat_id=chat_id, text=text)
                return {"statusCode": 200}
        bot.send_message(chat_id=chat_id, text="No birthday found for {}".format(person_name))
        return {"statusCode": 200}
    except Exception as e:
        raise e


def handle_query_all(data):
    chat_id = data["message"]["chat"]["id"]
    try:
        birthdays = load_birthdays_from_bucket()
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
    data = json.loads(f.read())
    handle_set(data)