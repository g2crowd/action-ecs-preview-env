import json
import logging

import boto3

LOGGER = logging.getLogger("root")


def init_client(assumed_role):
    if assumed_role is None:
        session = boto3.Session()
    else:
        session = boto3.Session(
            aws_access_key_id=assumed_role["AccessKeyId"],
            aws_secret_access_key=assumed_role["SecretAccessKey"],
            aws_session_token=assumed_role["SessionToken"],
        )

    return session.resource("s3")


def parse_outputs(data):
    result = {}
    for item in data:
        result[item] = data[item]["value"]
    return result


def get_outputs(assumed_role, state_file):
    client = init_client(assumed_role)
    state_file = state_file.split("/", 1)
    object = client.Object(state_file[0], state_file[1])
    content = object.get()["Body"].read().decode("utf-8")
    data = json.loads(content)
    return parse_outputs(data["outputs"])
