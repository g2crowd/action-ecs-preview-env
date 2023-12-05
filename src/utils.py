import logging

import boto3

LOGGER = logging.getLogger("root")
ENV_FILE = ".prenv_vars"

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


def assume_aws_role(role):
    LOGGER.info("Assuming AWS role")
    client = boto3.client("sts")
    response = client.assume_role(RoleArn=role, RoleSessionName="PrenvDNSSession")
    return response["Credentials"]


def export_env(key, value):
    env_file = open(ENV_FILE, "a")
    env = "{}={}".format(key, value)
    print(env, file=env_file)
    env_file.close()
