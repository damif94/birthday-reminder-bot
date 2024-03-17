import os

import requests

TOKEN = os.getenv('TOKEN')

if __name__ == '__main__':
    webhook_url = ''
    url = f'https://api.telegram.org/bot{TOKEN}/setWebhook'

    response = requests.post(url, data={'url': webhook_url})

    print(response.text)
