import typing
import boto3
import logging
import datetime
import redis
import os

from botocore import config as botocore_config, exceptions as botocore_exceptions

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)

S3_BUCKET_NAME = os.getenv('BUCKET_NAME')
S3_FILE_NAME = os.getenv('FILE_NAME')
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')


class BirthdayStorage:
    name: str

    def load_birthdays(self) -> typing.List[typing.Tuple[str, datetime.date]]:
        pass

    def store_birthday(self, name: str, date: datetime.date):
        pass

    def get_birthday(self, name: str) -> typing.Optional[datetime.date]:
        pass

    def delete_birthday(self, name: str):
        pass


class MemoryBirthdayStorage(BirthdayStorage):
    birthdays: typing.List[typing.Tuple[str, datetime.date]]

    def __init__(self):
        self.birthdays = []

    def load_birthdays(self) -> typing.List[typing.Tuple[str, datetime.date]]:
        return self.birthdays

    def store_birthday(self, name: str, date: datetime.date):
        for i in range(len(self.birthdays)):
            n, _ = self.birthdays[i]
            if n.lower() == name.lower():
                self.birthdays[i] = (name, date)
                break
        else:
            self.birthdays.append((name, date))

    def get_birthday(self, name: str) -> typing.Optional[datetime.date]:
        for n, d in self.birthdays:
            if n.lower() == name.lower():
                return d
        return None

    def delete_birthday(self, name: str) -> bool:
        for i in range(len(self.birthdays)):
            n, _ = self.birthdays[i]
            if n.lower() == name.lower():
                self.birthdays.pop(i)
                return True
        return False


class S3BirthdayStorage(BirthdayStorage):
    file_name: str
    bucket_name: str
    birthdays: typing.Optional[typing.List[typing.Tuple[str, datetime.date]]]
    s3_client: boto3.client

    def __init__(self, bucket_name: str, file_name: str):
        self.bucket_name = bucket_name
        self.file_name = file_name
        s3_config = botocore_config.Config(connect_timeout=2, read_timeout=2)
        self.s3_client = boto3.client('s3', config=s3_config)

    def load_birthdays(self) -> typing.List[typing.Tuple[str, datetime.date]]:
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self.file_name)
            logger.debug("Read object from s3")
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
        except botocore_exceptions.EndpointConnectionError as e:
            logger.error(f"Failed to connect to S3 endpoint: {e}")
            raise
        except botocore_exceptions.ReadTimeoutError as e:
            logger.error(f"Timeout while reading object from S3: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to read object from s3: {e}")
            raise

    def store_birthday(self, name: str, date: datetime.date):
        if self.birthdays is None:
            self.birthdays = self.load_birthdays()
        for i in range(len(self.birthdays)):
            if name.lower() == self.birthdays[i][0].lower():
                self.birthdays[i] = (name, date)
                break
        else:
            self.birthdays.append((name, date))
        self._store_birthdays(self.birthdays)

    def get_birthday(self, name: str) -> typing.Optional[datetime.date]:
        if self.birthdays is None:
            self.birthdays = self.load_birthdays()
        for n, d in self.birthdays:
            if n.lower() == name.lower():
                return d
        return None

    def delete_birthday(self, name: str) -> bool:
        if self.birthdays is None:
            self.birthdays = self.load_birthdays()
        for i in range(len(self.birthdays)):
            n, _ = self.birthdays[i]
            if n.lower() == name.lower():
                self.birthdays.pop(i)
                self._store_birthdays(self.birthdays)
                return True
        return False

    def _store_birthdays(self, birthdays: typing.List[typing.Tuple[str, datetime.date]]):
        try:
            content = "name,birthday\n"
            for name, date in birthdays:
                content += f"{name},{date.strftime('%d/%m/%Y')}\n"
            self.s3_client.put_object(Bucket=self.bucket_name, Key=self.file_name, Body=content)
        except botocore_exceptions.EndpointConnectionError as e:
            logger.error(f"Failed to connect to S3 endpoint: {e}")
            raise
        except botocore_exceptions.ReadTimeoutError as e:
            logger.error(f"Timeout while reading object from S3: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to read object from s3: {e}")
            raise


class RedisBirthdayStorage(BirthdayStorage):
    redis: redis.Redis

    def __init__(self, host: str, port: int, db: int):
        self.redis = redis.Redis(host=host, port=port, db=db)

    def load_birthdays(self) -> typing.List[typing.Tuple[str, datetime.date]]:
        birthdays = []
        for key in self.redis.scan_iter(match="birthday:*"):
            name = key.split(":")[1]
            date = self.redis.get(key)
            date = datetime.datetime.strptime(date, "%d/%m/%Y").date()
            birthdays.append((name, date))
        return birthdays

    def store_birthday(self, name: str, date: datetime.date):
        self.redis.set(f"birthday:{name}", date.strftime("%d/%m/%Y"))

    def get_birthday(self, name: str) -> typing.Optional[datetime.date]:
        date = self.redis.get(f"birthday:{name}")
        if date is not None:
            return datetime.datetime.strptime(date, "%d/%m/%Y").date()
        return None

    def delete_birthday(self, name: str) -> bool:
        return self.redis.delete(f"birthday:{name}") == 1


def build_storage(storage_type: str) -> BirthdayStorage:
    if storage_type == S3BirthdayStorage.__name__:
        return S3BirthdayStorage(**{"bucket_name": S3_BUCKET_NAME, "file_name": S3_FILE_NAME})
    if storage_type == MemoryBirthdayStorage.__name__:
        return MemoryBirthdayStorage()
    if storage_type == RedisBirthdayStorage.__name__:
        return RedisBirthdayStorage(**{"host": REDIS_HOST, "port": REDIS_PORT, "db": 0})
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
