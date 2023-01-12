import json
import logging
import os
import re

import ssm

LOGGER = logging.getLogger("root")


def get_env_vars():
    LOGGER.info("Fetching environment variables:")
    envs = {}
    for name, value in os.environ.items():
        if name.startswith("PRENV_"):
            envs[name] = value
            LOGGER.info("%s: %s" % (name, value))
    return envs


def validate_key(data, key, config_name):
    if data.get(key) is None:
        LOGGER.error("Invalid %s config, %s is not defined" % (config_name, key))
        exit(1)
    elif len(data[key]) == 0:
        LOGGER.error("Invalid %s config, %s is empty" % (config_name, key))
        exit(1)


def generate_task_def_config_file(data, output_filename):
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_config(value, tf_outputs, assume_role):
    if type(value) == str:
        pattern = re.compile(r"\${(.+):(.+)}")
        result = pattern.search(value)
        if result is None:
            return value
        if result.group(1) == "tf":
            if tf_outputs.get(result.group(2)) is None:
                LOGGER.error("%s does not exists in TF state" % result.group(2))
            value = tf_outputs[result.group(2)]
        elif result.group(1) == "ssm":
            value = ssm.get_parameter(assume_role, result.group(2))
        elif result.group(1) == "env":
            if os.environ.get(result.group(2)) is None:
                LOGGER.error(
                    "%s environment variable does not exists" % result.group(2)
                )
            value = os.environ[result.group(2)]
        return value
    elif type(value) == list:
        return [parse_config(i, tf_outputs, assume_role) for i in value]
    elif type(value) == dict:
        return {k: parse_config(i, tf_outputs, assume_role) for k, i in value.items()}
    return value


def is_config_exists(filename):
    return os.path.isfile(filename)


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


def get_dns_config(data):
    validate_key(data, "dns", "dns")
    validate_key(data["dns"], "hosted_zone", "dns")
    validate_key(data["dns"], "domain", "dns")
    return data["dns"]["hosted_zone"], data["dns"]["domain"]
