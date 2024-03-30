import os
import sys

from flask import Flask, request

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.birthday_storage import MemoryBirthdayStorage
from handlers import *

MY_CHAT_ID = os.getenv('MY_CHAT_ID')
birthday_storage = MemoryBirthdayStorage()

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

bot.set_my_commands(commands)
app = Flask(__name__)


@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return '', 200


def remove_command_prefix(text: str) -> str:
    return text.split(" ", 1)[1]


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
