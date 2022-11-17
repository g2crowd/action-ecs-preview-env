import fileinput
import logging
import os

LOGGER = logging.getLogger("root")


def get_env_vars():
    LOGGER.info("Fetching environment variables:")
    envs = {}
    for name, value in os.environ.items():
        if name.startswith("PRENV_"):
            envs[name] = value
            LOGGER.info("%s: %s" % (name, value))
    return envs


def update_placeholders(input_filename, output_filename):
    envs = get_env_vars()
    out_file = open(output_filename, "w")
    for content in fileinput.input(files=input_filename):
        for env in envs:
            content = content.replace(env, envs[env])
        out_file.write(content)
