import boto3
import telebot

MY_CHAT_ID = '1399764584'
TOKEN = '7176117100:AAHxaF5z6hbLZni4xb7DBN3vPoWHsg7VqKY'
BASE_URL = "https://api.telegram.org/bot{}".format(TOKEN)
BUCKET_NAME = "dferencz"
FILE_NAME = "birthdays.csv"

s3_client = boto3.client("s3")
bot = telebot.TeleBot(TOKEN)
