import dataclasses
import typing
import boto3
import logging
import os

from botocore import config as botocore_config
from src import utils


logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

DEFAULT_UTC_OFFSET = -3


@dataclasses.dataclass
class User:
    chat_id: str
    utc_offset: int

    def __init__(self, chat_id: str, utc_offset=None):
        self.chat_id = chat_id
        if utc_offset is None:
            self.utc_offset = DEFAULT_UTC_OFFSET
        else:
            self.utc_offset = utc_offset


class UserStorage:
    name: str

    def load_users_by_utc_offset(self, utc_offset: int) -> typing.List[User]:
        pass

    def update_utc_offset(self, chat_id: str, utc_offset: int):
        pass


class DynamoDBUserStorage(UserStorage):
    table_name: str = None
    dynamodb: boto3.resource = None
    table: boto3.resource = None

    def __init__(self, table_name: str):
        self.table_name = table_name
        dynamodb_config = botocore_config.Config(connect_timeout=2, read_timeout=2)
        self.dynamodb_client = boto3.client('dynamodb', config=dynamodb_config, region_name='sa-east-1')

    def load_users_by_utc_offset(self, utc_offset: int) -> typing.List[User]:
        try:
            response = self.dynamodb_client.scan(
                TableName=self.table_name,
                IndexName='UtcOffsetIndex',
                FilterExpression='utc_offset = :utc_offset',
                ExpressionAttributeValues=utils.python_obj_to_dynamo_obj({
                    ':utc_offset': utc_offset
                })
            )
            users: typing.List[User] = []
            for item in response['Items']:
                item = utils.dynamo_obj_to_python_obj(item)
                users.append(User(chat_id=item['chat_id'], utc_offset=item['utc_offset']))

            return users
        except Exception as e:
            logger.error(f"Failed to read object from DynamoDB: {e}")
            raise

    def update_utc_offset(self, chat_id: str, utc_offset: int):
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.table_name,
                Key=utils.python_obj_to_dynamo_obj({'chat_id': chat_id})
            )
            if 'Item' in response:
                self.dynamodb_client.update_item(
                    TableName=self.table_name,
                    Key=utils.python_obj_to_dynamo_obj({
                        'chat_id': chat_id,
                        'utc_offset': utc_offset
                    }),
                    UpdateExpression='SET utc_offset = :utc_offset',
                    ExpressionAttributeValues=utils.python_obj_to_dynamo_obj({
                        ':utc_offset': int(utc_offset),
                    }),
                )
            else:
                self.dynamodb_client.put_item(
                    TableName=self.table_name,
                    Item=utils.python_obj_to_dynamo_obj({
                        'chat_id': chat_id,
                        'utc_offset': utc_offset,
                    }),
                )
        except Exception as e:
            logger.error(f"Failed to read object from DynamoDB: {e}")
            raise


def build_storage(storage_type: str) -> UserStorage:
    if storage_type == DynamoDBUserStorage.__name__:
        return DynamoDBUserStorage(table_name=os.getenv('USERS_TABLE_NAME'))
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
