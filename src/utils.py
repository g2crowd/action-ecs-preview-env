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


def validate_key(data, key, config_name):
    if data.get(key) is None:
        LOGGER.error("Invalid %s config, %s is not defined" % (config_name, key))
        exit(1)
    elif len(data[key]) == 0:
        LOGGER.error("Invalid %s config, %s is empty" % (config_name, key))
        exit(1)


def is_config_exists(filename):
    return os.path.isfile(filename)


def is_dns_config_exists(filename):
    data = load_config(filename)
    if data.get("dns") is None:
        return False
    return True


def load_config(filename):
    with open(filename) as file:
        data = json.load(file)
    return data


def get_ecs_config(filename):
    data = load_config(filename)
    validate_key(data, "subnet_ids", "ecs")
    validate_key(data, "security_groups", "ecs")
    validate_key(data, "cluster", "ecs")
    validate_key(data, "platform", "ecs")
    return (
        data["subnet_ids"],
        data["security_groups"],
        data["cluster"],
        data["platform"],
    )


def get_dns_config(filename):
    data = load_config(filename)
    validate_key(data, "dns", "dns")
    validate_key(data["dns"], "hosted_zone", "dns")
    validate_key(data["dns"], "domain", "dns")
    return data["dns"]["hosted_zone"], data["dns"]["domain"]


def compare_files(source_filename, target_filename):
    source = load_config(source_filename)
    target = load_config(target_filename)
    print(sorted(source.items()) == sorted(target.items()))


def assume_aws_role(role):
    LOGGER.info("Assuming AWS role")
    client = boto3.client("sts")
    response = client.assume_role(RoleArn=role, RoleSessionName="PrenvDNSSession")
    return response["Credentials"]
