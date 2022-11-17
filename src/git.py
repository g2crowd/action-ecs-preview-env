import logging
import os

import requests
from github import Github

LOGGER = logging.getLogger("root")
DB_LABEL_PREFIX = "db:"
LABEL_COLOR = "0E8A16"


def init_git():
    return Github(os.environ["GITHUB_TOKEN"])


def get_repo(org, repo):
    git = init_git()
    repo = git.get_repo(org + "/" + repo)
    return repo


def get_issue(repo, pr):
    issue = repo.get_issue(int(pr))
    return issue


def get_labels(repo):
    labels = repo.get_labels()
    db_labels = []
    for label in labels:
        if label.name.startswith(DB_LABEL_PREFIX):
            db_labels.append(label.name)
    return db_labels


def get_unassigned_label(repo, labels):
    for label in labels:
        if not is_label_assigned(repo, label, True):
            return label[label.startswith(DB_LABEL_PREFIX) and len(DB_LABEL_PREFIX) :]
    return None


def is_label_assigned(repo, label, prefixed):
    git = init_git()
    if not prefixed:
        label = DB_LABEL_PREFIX + label
    query = "state:open label:" + label
    issues = git.search_issues(query)
    if issues.totalCount == 0:
        return False
    return True


def is_label_assigned_to_current(repo, label, prefixed):
    git = init_git()
    if not prefixed:
        label = DB_LABEL_PREFIX + label
    query = "state:open label:" + label
    issues = git.search_issues(query)
    if issues.totalCount <= 1:
        return True
    return False


def is_label_exists(repo, name):
    name = DB_LABEL_PREFIX + name
    labels = repo.get_labels()
    for label in labels:
        if label.name.startswith(DB_LABEL_PREFIX) and label.name == name:
            return True
    return False


def get_pr_label(repo, pr):
    issue = get_issue(repo, pr)
    labels = issue.get_labels()
    attached_label = None
    for label in labels:
        label = label.name
        if label.startswith(DB_LABEL_PREFIX):
            if attached_label is None:
                attached_label = label[
                    label.startswith(DB_LABEL_PREFIX) and len(DB_LABEL_PREFIX) :
                ]
            else:
                LOGGER.error("Multile database label are attached to the PR")
                exit(1)
    return attached_label


def create_label(repo, db_name):
    name = DB_LABEL_PREFIX + db_name
    repo.create_label(name, LABEL_COLOR)


def set_label(repo, pr, label):
    issue = get_issue(repo, pr)
    if not label.startswith(DB_LABEL_PREFIX):
        label = DB_LABEL_PREFIX + label
    issue.set_labels(label)


def remove_label(repo, pr, label):
    issue = get_issue(repo, pr)
    if not label.startswith(DB_LABEL_PREFIX):
        label = DB_LABEL_PREFIX + label
    issue.remove_from_labels(label)


def create_deployment(repo, sha, env, author):
    LOGGER.info("Creating github deployment")
    git_deploy_id = repo.create_deployment(
        ref=sha,
        environment=env,
        required_contexts=[],
        payload={"owner": author},
        description="Preview environment",
        auto_merge=False,
        transient_environment=True,
        production_environment=False,
    )
    return git_deploy_id


def update_deployment(deployment, status, env_url):
    deployment.create_status(state=status, environment_url=env_url)


def get_deployment(repo, sha, env):
    return repo.get_deployments(sha=sha, environment=env)


def create_environment(org, repo, env):
    token = os.environ["GITHUB_TOKEN"]
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
    }

    url = "https://api.github.com/repos/{0}/{1}/environments/{2}".format(org, repo, env)
    requests.put(url, headers=headers)


def delete_environment(org, repo, env):
    token = os.environ["GITHUB_TOKEN"]
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
    }

    url = "https://api.github.com/repos/{0}/{1}/environments/{2}".format(org, repo, env)
    requests.delete(url, headers=headers)


def delete_deployment(org, repo, deploy_id):
    token = os.environ["GITHUB_TOKEN"]
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
    }

    url = "https://api.github.com/repos/{0}/{1}/deployments/{2}".format(
        org, repo, deploy_id
    )
    requests.delete(url, headers=headers)
