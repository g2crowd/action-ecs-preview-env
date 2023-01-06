import logging
import random

import git
import utils

LOGGER = logging.getLogger("root")


def is_db_shareble(database):
    if database.get("share") is None:
        return True
    if database["share"]:
        return True
    return False


def get_shareble_dbs(databases):
    dbs = {}
    for db in databases:
        if is_db_shareble(databases[db]):
            dbs[db] = databases[db]
    return dbs


def get_non_shareble_dbs(databases):
    dbs = {}
    for db in databases:
        if not is_db_shareble(databases[db]):
            dbs[db] = databases[db]
    return dbs


def select_random_db(databases):
    dbs = [db for db in databases]
    result = random.choice(dbs)
    return result


def get_shared_database(databases, repo, pr):
    databases = get_shareble_dbs(databases)
    if len(databases) == 0:
        LOGGER.error("Sharable databases are not available")
        exit(1)
    db = select_random_db(databases)
    git.set_label(repo, pr, db)
    return databases[db]


def get_available_database(databases, repo, pr):
    available_dbs = {}

    for database in databases:
        if not git.is_label_assigned(repo, database, False):
            if not git.is_label_exists(repo, database):
                LOGGER.info("Adding missing label to corrospoding db:%s" % database)
                git.create_label(repo, database)
            available_dbs[database] = databases[database]

    available_dbs = utils.merge_dicts(available_dbs, get_shareble_dbs(databases))
    if len(available_dbs) == 0:
        LOGGER.error("Databases are not available")
        exit(1)

    db = select_random_db(available_dbs)
    git.set_label(repo, pr, db)
    return databases[db]


def get_labeled_database(databases, repo, pr_label):
    if databases.get(pr_label) is None:
        LOGGER.error("Attached label database is not avaialble in the config")
        exit(1)

    if git.is_label_assigned_to_current(repo, pr_label, True):
        return databases[pr_label]

    if is_db_shareble(databases[pr_label]):
        LOGGER.error("Attached label database is already assigned to another PR")
        LOGGER.info(
            "With db share setting set to False, database can not be shared with multiple PRs"
        )
        exit(1)

    return databases[pr_label]


def get_database(data, repo, pr):
    pr_label = git.get_pr_label(repo, pr)

    if data.get("databases") is None:
        LOGGER.error("Databases config is not defined")
        exit(1)

    databases = data["databases"]
    if len(databases) == 0:
        LOGGER.error("Databases are not available in the config")
        exit(1)

    if pr_label is not None:
        return get_labeled_database(databases, repo, pr_label)
    return get_available_database(databases, repo, pr)
