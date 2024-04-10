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


@dataclasses.dataclass
class Birthday:
    name: str
    day: int
    month: int
    year: typing.Optional[int] = None

    def date_format(self) -> str:
        if self.year is None:
            return datetime.date(1900, self.month, self.day).strftime("%d/%m")
        return datetime.date(self.year, self.month, self.day).strftime("%d/%m/%Y")

    def __init__(self, name: str, date_str: str):
        date_parts = date_str.split("/")
        if len(date_parts) == 2:
            day, month = date_parts
            year = None
        elif len(date_parts) == 3:
            day, month, year = date_parts
        else:
            raise ValueError("Invalid date format")
        self.name = name
        self.day = int(day)
        self.month = int(month)
        self.year = int(year) if year is not None else None
        try:
            self.date_format()
        except ValueError:
            raise ValueError("Invalid date value")


class BirthdayStorage:
    name: str

    def load_birthdays_by_chat_id(self, chat_id: str) -> typing.List[Birthday]:
        pass

    def load_birthdays_by_day(self, day: datetime.date) -> typing.List[typing.Tuple[str, Birthday]]:
        pass

    def store_birthday(self, chat_id: str, birthday: Birthday):
        pass

    def get_birthday(self, chat_id: str, name: str) -> typing.Optional[Birthday]:
        pass

    def delete_birthday(self, chat_id: str, name: str):
        pass


class MemoryBirthdayStorage(BirthdayStorage):
    birthdays: typing.Dict[str, typing.List[Birthday]]

    def __init__(self):
        self.birthdays = {}

    def load_birthdays_by_chat_id(self, chat_id: str) -> typing.List[Birthday]:
        return self.birthdays[chat_id]

    def load_birthdays_by_day(self, day: datetime.date) -> typing.List[typing.Tuple[str, Birthday]]:
        birthday_list: typing.List[typing.Tuple[str, Birthday]] = []
        for chat_id, birthday in self.birthdays:
            if day.day == birthday.day and day.month == birthday.month:
                birthday_list.append((chat_id, birthday))
        return birthday_list

    def store_birthday(self, chat_id: str, birthday: Birthday):
        if chat_id not in self.birthdays:
            self.birthdays[chat_id] = []
        for i in range(len(self.birthdays[chat_id])):
            b = self.birthdays[chat_id][i]
            if b.name.lower() == birthday.name.lower():
                self.birthdays[chat_id][i] = birthday
                break
        else:
            self.birthdays[chat_id].append(birthday)

    def get_birthday(self, chat_id: str, name: str) -> typing.Optional[Birthday]:
        for birthday in self.birthdays[chat_id]:
            if birthday.name.lower() == name.lower():
                return birthday
        return None

    def delete_birthday(self, chat_id: str, name: str) -> bool:
        for i in range(len(self.birthdays)):
            birthday = self.birthdays[chat_id][i]
            if birthday.name.lower() == name.lower():
                self.birthdays[chat_id].pop(i)
                return True
        return False


class RedisBirthdayStorage(BirthdayStorage):
    # redis: redis.Redis

    def __init__(self, host: str, port: int, db: int):
        self.redis = redis.Redis(host=host, port=port, db=db)

    def load_birthdays_by_chat_id(self, chat_id: str) -> typing.List[Birthday]:
        birthdays: typing.List[Birthday] = []
        for key in self.redis.scan_iter(match=f"birthday:{chat_id}:*"):
            name = key.decode("utf-8").split(":")[2]
            date = self.redis.get(key).decode("utf-8")
            birthdays.append(Birthday(name, date))
        return birthdays

    def load_birthdays_by_day(self, day: datetime.date) -> typing.List[typing.Tuple[str, Birthday]]:
        birthdays: typing.List[typing.Tuple[str, Birthday]] = []
        for key in self.redis.scan_iter(match=f"birthday:*:{day.day}/{day.month}*"):
            chat_id = key.decode("utf-8").split(":")[1]
            name = key.decode("utf-8").split(":")[2]
            date = self.redis.get(key).decode("utf-8")
            birthdays.append((chat_id, Birthday(name, date)))
        return birthdays

    def store_birthday(self, chat_id: str, birthday: Birthday):
        self.redis.set(f"birthday:{chat_id}:{birthday.name}", birthday.date_format())

    def get_birthday(self, chat_id: str, name: str) -> typing.Optional[Birthday]:
        date: bytes = self.redis.get(f"birthday:{chat_id}:{name}")
        if date is not None:
            return Birthday(name, date.decode("utf-8"))
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

    def load_birthdays_by_chat_id(self, chat_id: str) -> typing.List[Birthday]:
        response = self.dynamodb_client.scan(
            TableName=self.table_name,
            IndexName='UserBirthdaysIndex',
            FilterExpression='chat_id = :chat_id',
            ExpressionAttributeValues=utils.python_obj_to_dynamo_obj({
                ':chat_id': chat_id
            })
        )
        birthdays: typing.List[Birthday] = []
        for item in response['Items']:
            item = utils.dynamo_obj_to_python_obj(item)
            date_str = "/".join([
                str(item[k]) for k in ['birthday_day', 'birthday_month', 'birthday_year']
                if k in item and item[k] is not None
            ])
            birthdays.append(Birthday(item['name'], date_str))

        sorted_birthdays = sorted(birthdays, key=lambda day: (day.month, day.day))

        return sorted_birthdays

    def load_birthdays_by_day(self, day: datetime.date) -> typing.List[typing.Tuple[str, Birthday]]:
        response = self.dynamodb_client.scan(
            TableName=self.table_name,
            FilterExpression='birthday_day = :day AND birthday_month = :month',
            ExpressionAttributeValues=utils.python_obj_to_dynamo_obj({
                ':day': day.day,
                ':month': day.month,
            })
        )
        birthdays: typing.List[typing.Tuple[str, Birthday]] = []
        for item in response['Items']:
            item = utils.dynamo_obj_to_python_obj(item)
            date_str = "/".join([
                str(item[k]) for k in ['birthday_day', 'birthday_month', 'birthday_year']
                if k in item and item[k] is not None
            ])
            birthdays.append((item['chat_id'], Birthday(item['name'], date_str)))
        return birthdays

    def store_birthday(self, chat_id: str, birthday: Birthday):
        response = self.dynamodb_client.get_item(
            TableName=self.table_name,
            Key=utils.python_obj_to_dynamo_obj({'chat_id': chat_id, 'name': birthday.name})
        )
        if 'Item' in response:
            self.dynamodb_client.update_item(
                TableName=self.table_name,
                Key=utils.python_obj_to_dynamo_obj({
                    'chat_id': chat_id,
                    'name': birthday.name
                }),
                UpdateExpression='SET birthday_day = :day, birthday_month = :month, birthday_year = :year',
                ExpressionAttributeValues=utils.python_obj_to_dynamo_obj({
                    ':day': int(birthday.day),
                    ':month': int(birthday.month),
                    ':year': int(birthday.year) if birthday.year is not None else None
                }),
            )
        else:
            self.dynamodb_client.put_item(
                TableName=self.table_name,
                Item=utils.python_obj_to_dynamo_obj({
                    'chat_id': chat_id,
                    'name': birthday.name,
                    'birthday_day': int(birthday.day),
                    'birthday_month': int(birthday.month),
                    'birthday_year': int(birthday.year) if birthday.year is not None else None
                }),
            )

    def get_birthday(self, chat_id: str, name: str) -> typing.Optional[Birthday]:
        response = self.dynamodb_client.get_item(
            TableName=self.table_name,
            Key=utils.python_obj_to_dynamo_obj({'chat_id': chat_id, 'name': name})
        )
        if 'Item' in response:
            item = utils.dynamo_obj_to_python_obj(response['Item'])
            date_str = "/".join([
                str(item[k]) for k in ['birthday_day', 'birthday_month', 'birthday_year']
                if k in item and item[k] is not None
            ])
            return Birthday(name, date_str)
        else:
            return None

    def delete_birthday(self, chat_id: str, name: str) -> bool:
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


def build_storage(storage_type: str) -> BirthdayStorage:
    if storage_type == "Memory":
        return MemoryBirthdayStorage()
    if storage_type == "Redis":
        return RedisBirthdayStorage(**{"host": os.getenv('REDIS_HOST'), "port": os.getenv('REDIS_PORT'), "db": 0})
    if storage_type == "DynamoDB":
        return DynamoDBBirthdayStorage(table_name=os.getenv('BIRTHDAYS_TABLE_NAME'))
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
