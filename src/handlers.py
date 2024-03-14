import datetime
import json
import typing
import telebot

from .config import s3_client, bot, MY_CHAT_ID, BUCKET_NAME, FILE_NAME


def load_birthdays_from_bucket() -> typing.List[typing.Tuple[str, datetime.date]]:
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=FILE_NAME)
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

    return {"statusCode": 200}
