import requests
import os

from src.bot import commands

TOKEN = os.getenv('TOKEN')

if __name__ == '__main__':
    url = f'https://api.telegram.org/bot{TOKEN}/setMyCommands'

    response = requests.post(url, json=commands)

    print(response.text)
