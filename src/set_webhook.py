import requests
from .config import TOKEN

if __name__ == '__main__':
    webhook_url = 'https://1ak35r29n0.execute-api.sa-east-1.amazonaws.com/prod/'
    url = f'https://api.telegram.org/bot{TOKEN}/setWebhook'

    response = requests.post(url, data={'url': webhook_url})

    print(response.text)
