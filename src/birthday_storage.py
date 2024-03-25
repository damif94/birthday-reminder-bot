import typing
from botocore import config as botocore_config, exceptions as botocore_exceptions
import boto3
import logging
import datetime

logger = logging.getLogger("root")
logging.getLogger().setLevel(logging.INFO)


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


class S3BirthdayStorage(BirthdayStorage):
    file_name: str
    bucket_name: str
    birthdays: typing.Optional[typing.List[typing.Tuple[str, datetime.date]]] = None
    s3_client: boto3.client
    name: "S3BirthdayStorage"

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
            name, _ = self.birthdays[i]
            if name.lower() == name.lower():
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


def build_storage(storage_type: str, **kwargs) -> BirthdayStorage:
    if storage_type == S3BirthdayStorage.name:
        return S3BirthdayStorage(**kwargs)
