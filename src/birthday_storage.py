import dataclasses
import typing
import boto3
import logging
import datetime
import redis
import os

from botocore import config as botocore_config
from src import utils

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')


@dataclasses.dataclass
class BirthdayItem:
    chat_id: str
    name: str
    day: int
    month: int
    year: typing.Optional[int] = None


class BirthdayStorage:
    name: str

    def load_birthdays(self, chat_id: str) -> typing.List[BirthdayItem]:
        pass

    def store_birthday(self, chat_id: str, name: str, date: datetime.date):
        pass

    def get_birthday(self, chat_id: str, name: str) -> typing.Optional[datetime.date]:
        pass

    def delete_birthday(self, chat_id: str, name: str):
        pass


class MemoryBirthdayStorage(BirthdayStorage):
    birthdays: typing.Dict[str, typing.List[typing.Tuple[str, datetime.date]]]

    def __init__(self):
        self.birthdays = {}

    def load_birthdays(self, chat_id: str) -> typing.List[typing.Tuple[str, datetime.date]]:
        return self.birthdays[chat_id]

    def store_birthday(self, chat_id: str, name: str, date: datetime.date):
        for i in range(len(self.birthdays[chat_id])):
            n, _ = self.birthdays[chat_id][i]
            if n.lower() == name.lower():
                self.birthdays[chat_id][i] = (name, date)
                break
        else:
            self.birthdays[chat_id].append((name, date))

    def get_birthday(self, chat_id: str, name: str) -> typing.Optional[datetime.date]:
        for n, d in self.birthdays[chat_id]:
            if n.lower() == name.lower():
                return d
        return None

    def delete_birthday(self, chat_id: str, name: str) -> bool:
        for i in range(len(self.birthdays)):
            n, _ = self.birthdays[chat_id][i]
            if n.lower() == name.lower():
                self.birthdays[chat_id].pop(i)
                return True
        return False


class RedisBirthdayStorage(BirthdayStorage):
    # redis: redis.Redis

    def __init__(self, host: str, port: int, db: int):
        self.redis = redis.Redis(host=host, port=port, db=db)

    def load_birthdays(self, chat_id: str) -> typing.List[typing.Tuple[str, datetime.date]]:
        birthdays = []
        for key in self.redis.scan_iter(match=f"birthday:{chat_id}:*"):
            name = key.decode("utf-8").split(":")[1]
            date = self.redis.get(key).decode("utf-8")
            date = datetime.datetime.strptime(date, "%d/%m/%Y").date()
            birthdays.append((name, date))
        return birthdays

    def store_birthday(self, chat_id: str, name: str, date: datetime.date):
        self.redis.set(f"birthday:{chat_id}:{name}", date.strftime("%d/%m/%Y"))

    def get_birthday(self, chat_id: str, name: str) -> typing.Optional[datetime.date]:
        date: bytes = self.redis.get(f"birthday:{chat_id}:{name}")
        if date is not None:
            return datetime.datetime.strptime(date.decode("utf-8"), "%d/%m/%Y").date()
        return None

    def delete_birthday(self, chat_id: str, name: str) -> bool:
        return self.redis.delete(f"birthday:{chat_id}:{name}") == 1


class DynamoDBBirthdayStorage(BirthdayStorage):
    table_name: str = None
    dynamodb: boto3.resource = None
    table: boto3.resource = None

    def __init__(self, table_name: str):
        self.table_name = table_name
        dynamodb_config = botocore_config.Config(connect_timeout=2, read_timeout=2)
        self.dynamodb_client = boto3.client('dynamodb', config=dynamodb_config, region_name='sa-east-1')

    def load_birthdays(self, chat_id: str) -> typing.List[typing.Tuple[str, datetime.date]]:
        try:
            response = self.dynamodb_client.scan(
                TableName=self.table_name,
                FilterExpression='chat_id = :chat_id',
                ExpressionAttributeValues=utils.python_obj_to_dynamo_obj({
                    ':chat_id': chat_id
                })
            )
            birthdays = []
            for item in response['Items']:
                item = utils.dynamo_obj_to_python_obj(item)
                birthday = datetime.date(int(item['birthday_year']), int(item['birthday_month']), int(item['birthday_day']))
                birthdays.append((item['name'], birthday))
            return birthdays
        except Exception as e:
            logger.error(f"Failed to read object from DynamoDB: {e}")
            raise

    def store_birthday(self, chat_id: str, name: str, date: datetime.date):
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.table_name,
                Key=utils.python_obj_to_dynamo_obj({'chat_id': chat_id, 'name': name})
            )
            if 'Item' in response:
                self.dynamodb_client.update_item(
                    TableName=self.table_name,
                    Key=utils.python_obj_to_dynamo_obj({
                        'chat_id': chat_id,
                        'name': name
                    }),
                    UpdateExpression='SET birthday_day = :day, birthday_month = :month, birthday_year = :year',
                    ExpressionAttributeValues=utils.python_obj_to_dynamo_obj({
                        ':day': int(date.day),
                        ':month': int(date.month),
                        ':year': int(date.year)
                    }),
                )
            else:
                self.dynamodb_client.put_item(
                    TableName=self.table_name,
                    Item=utils.python_obj_to_dynamo_obj({
                        'chat_id': chat_id,
                        'name': name,
                        'birthday_day': int(date.day),
                        'birthday_month': int(date.month),
                        'birthday_year': int(date.year)
                    }),
                )
        except Exception as e:
            logger.error(f"Failed to read object from DynamoDB: {e}")
            raise

    def get_birthday(self, chat_id: str, name: str) -> typing.Optional[datetime.date]:
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.table_name,
                Key=utils.python_obj_to_dynamo_obj({'chat_id': chat_id, 'name': name})
            )
            if 'Item' in response:
                item = utils.dynamo_obj_to_python_obj(response['Item'])
                birthday = datetime.date(int(item['birthday_year']), int(item['birthday_month']), int(item['birthday_day']))
                return birthday
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to get birthday from DynamoDB: {e}")
            raise

    def delete_birthday(self, chat_id: str, name: str) -> bool:
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.table_name,
                Key=utils.python_obj_to_dynamo_obj({'chat_id': chat_id, 'name': name})
            )
            if 'Item' not in response:
                return False
            self.dynamodb_client.delete_item(
                TableName=self.table_name,
                Key=utils.python_obj_to_dynamo_obj({'chat_id': chat_id, 'name': name})
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete object from DynamoDB: {e}")
            raise


def build_storage(storage_type: str) -> BirthdayStorage:
    if storage_type == MemoryBirthdayStorage.__name__:
        return MemoryBirthdayStorage()
    if storage_type == RedisBirthdayStorage.__name__:
        return RedisBirthdayStorage(**{"host": REDIS_HOST, "port": REDIS_PORT, "db": 0})
    if storage_type == DynamoDBBirthdayStorage.__name__:
        return DynamoDBBirthdayStorage(table_name=os.getenv('TABLE_NAME'))
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
