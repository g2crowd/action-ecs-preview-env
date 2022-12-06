import boto3
import logging


LOGGER = logging.getLogger("root")


def get_parameter(assumed_role, name):
    if assumed_role is None:
        client = boto3.client("ssm")
    else:
        client = boto3.client(
            "ssm",
            aws_access_key_id=assumed_role["AccessKeyId"],
            aws_secret_access_key=assumed_role["SecretAccessKey"],
            aws_session_token=assumed_role["SessionToken"],
        )

    result = client.get_parameter(Name=name, WithDecryption=True)

    return result["Parameter"]["Value"]
