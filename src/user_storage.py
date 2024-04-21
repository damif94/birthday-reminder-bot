import dataclasses
import typing
import boto3
import logging
import os

from botocore import config as botocore_config
from src import utils


logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)


@dataclasses.dataclass
class User:
    chat_id: str
    user_name: str
    first_name: str
    last_name: str
    reminder_hour: int

    def __init__(self, chat_id: str, user_name: str, first_name: str, last_name: str, reminder_hour: int):
        self.chat_id = chat_id
        self.user_name = user_name
        self.first_name = first_name
        self.last_name = last_name
        self.reminder_hour = reminder_hour


class UserStorage:
    name: str

    def load_users_by_reminder_hour(self, reminder_hour: int) -> typing.List[User]:
        pass

    def store_user(self, user: User):
        pass

    def update_reminder_hour(self, chat_id: str, reminder_hour: int):
        pass


class MemoryUserStorage(UserStorage):
    users: typing.List[User] = []

    def load_users_by_reminder_hour(self, reminder_hour: int) -> typing.List[User]:
        return [user for user in self.users if user.reminder_hour == reminder_hour]

    def store_user(self, user: User):
        self.users.append(user)

    def update_reminder_hour(self, chat_id: str, reminder_hour: int):
        user = next((user for user in self.users if user.chat_id == chat_id), None)
        if user:
            user.reminder_hour = reminder_hour

class DynamoDBUserStorage(UserStorage):
    table_name: str = None
    dynamodb: boto3.resource = None
    table: boto3.resource = None

    def __init__(self, table_name: str):
        self.table_name = table_name
        dynamodb_config = botocore_config.Config(connect_timeout=2, read_timeout=2)
        self.dynamodb_client = boto3.client('dynamodb', config=dynamodb_config, region_name='sa-east-1')

    def load_users_by_reminder_hour(self, reminder_hour: int) -> typing.List[User]:
        response = self.dynamodb_client.scan(
            TableName=self.table_name,
            IndexName='ReminderHourIndex',
            FilterExpression='reminder_hour = :reminder_hour',
            ExpressionAttributeValues=utils.python_obj_to_dynamo_obj({
                ':reminder_hour': reminder_hour
            })
        )
        users: typing.List[User] = []
        for item in response['Items']:
            item = utils.dynamo_obj_to_python_obj(item)
            user = User(
                chat_id=item['chat_id'],
                user_name=item['user_name'],
                first_name=item['first_name'],
                last_name=item['last_name'],
                reminder_hour=item['reminder_hour']
            )
            users.append(user)

        return users

    def store_user(self, user: User):
        self.dynamodb_client.put_item(
            TableName=self.table_name,
            Item=utils.python_obj_to_dynamo_obj({
                'chat_id': user.chat_id,
                'user_name': str(user.user_name),
                'first_name': str(user.first_name),
                'last_name': str(user.last_name),
                'reminder_hour': int(user.reminder_hour),
            }),
        )

    def update_reminder_hour(self, chat_id: str, reminder_hour: int):
        self.dynamodb_client.update_item(
            TableName=self.table_name,
            Key=utils.python_obj_to_dynamo_obj({'chat_id': chat_id}),
            UpdateExpression='SET reminder_hour = :reminder_hour',
            ExpressionAttributeValues=utils.python_obj_to_dynamo_obj({
                ':reminder_hour': int(reminder_hour),
            }),
        )


def build_storage(storage_type: str) -> UserStorage:
    if storage_type == "DynamoDB":
        return DynamoDBUserStorage(table_name=os.getenv('USERS_TABLE_NAME'))
    elif storage_type == "Memory":
        return MemoryUserStorage()
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
