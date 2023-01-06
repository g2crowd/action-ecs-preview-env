import json
import logging
import os.path

import boto3

LOGGER = logging.getLogger("root")


def setup_custom_logger(name):
    formatter = logging.Formatter(fmt="[%(levelname)s] %(message)s")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def merge_dicts(source, target):
    result = source.copy()
    result.update(target)
    return result


def compare_files(source_filename, target_filename):
    source = load_config(source_filename)
    target = load_config(target_filename)
    print(sorted(source.items()) == sorted(target.items()))


def assume_aws_role(role):
    LOGGER.info("Assuming AWS role")
    client = boto3.client("sts")
    response = client.assume_role(RoleArn=role, RoleSessionName="PrenvDNSSession")
    return response["Credentials"]
