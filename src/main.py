import argparse
import os
import parser

import database
import ecs
import git
import route53
import utils

LOGGER = utils.setup_custom_logger("root")


CONFIG_FILE_PATH = ".prenv/"
ECS_CONFIG = "ecs_config.json"
TASK_DEFINITION_CONFIG = "task_definition.json"
DATABASE_CONFIG = "database_config.json"
DEPLOYMENT_CONFIG = "deployment_config.json"


def deploy(org, repo, branch, pr, author, image, sha, assume):
    ecs_config = CONFIG_FILE_PATH + ECS_CONFIG
    task_definition_config = CONFIG_FILE_PATH + TASK_DEFINITION_CONFIG
    deployment_config = CONFIG_FILE_PATH + DEPLOYMENT_CONFIG
    database_config = CONFIG_FILE_PATH + DATABASE_CONFIG
    dns_name = None
    stack_name = repo + pr
    task_family = "prenv-" + repo + "-" + pr

    os.environ["PRENV_ORG"] = org
    os.environ["PRENV_REPO"] = repo
    os.environ["PRENV_BRANCH"] = branch
    os.environ["PRENV_PR"] = pr
    os.environ["PRENV_AUTHOR"] = author
    os.environ["PRENV_IMAGE"] = image
    os.environ["PRENV_SHA"] = sha
    os.environ["PRENV_TASK_FAMILY"] = task_family

    if utils.is_config_exists(ecs_config):
        subnet_ids, security_groups, cluster, platform = utils.get_ecs_config(
            ecs_config
        )
    else:
        LOGGER.error("ECS configuration file is not available")
        exit(1)

    if utils.is_dns_config_exists(ecs_config):
        hosted_zone, domain = utils.get_dns_config(ecs_config)
        dns_name = stack_name + "." + domain
        os.environ["PRENV_DNS_NAME"] = dns_name
    else:
        LOGGER.info("Recordset configuration file is not available")
        LOGGER.info("The DNS reocord will not be created")

    repo_obj = git.get_repo(org, repo)

    if utils.is_config_exists(database_config):
        db = database.get_database(database_config, repo_obj, pr)
        for item in db:
            if item != "share":
                os.environ["PRENV_" + item.upper()] = db[item]
    else:
        LOGGER.info("Database configuration file is not available")

    parser.update_placeholders(task_definition_config, deployment_config)
    ecs.register_task_definition(deployment_config)

    git_deploys = git.get_deployment(repo_obj, sha, stack_name)
    if git_deploys.totalCount == 0:
        git.create_environment(org, repo, stack_name)
        git_deployment = git.create_deployment(repo_obj, sha, stack_name, author)
    else:
        for deploy in git_deploys:
            git_deployment = deploy

    ip = ecs.deploy(
        cluster, subnet_ids, security_groups, task_family, stack_name, platform, repo
    )

    env_url = "" if dns_name is None else str(dns_name)
    deployment_status = "success"

    if ip is None:
        deployment_status = "failure"
    LOGGER.info("Updating github deployment")
    git.update_deployment(git_deployment, deployment_status, "https://" + env_url)

    assumed_creds = None
    if dns_name is not None:
        if assume is not None:
            assumed_creds = utils.assume_aws_role(assume)
        route53.update_recordset(assumed_creds, hosted_zone, dns_name, ip)


def undeploy(org, repo, pr, sha, assume):
    task_family = "prenv-" + repo + "-" + pr
    stack_name = repo + pr
    ecs_config = CONFIG_FILE_PATH + ECS_CONFIG

    subnet_ids, security_groups, cluster, platform = utils.get_ecs_config(ecs_config)
    if utils.is_dns_config_exists(ecs_config):
        hosted_zone, domain = utils.get_dns_config(ecs_config)
        dns_name = stack_name + "." + domain
    repo_obj = git.get_repo(org, repo)

    ip = ecs.undeploy(cluster, stack_name, task_family)

    label = git.get_pr_label(repo_obj, pr)
    if label is not None:
        git.remove_label(repo_obj, pr, label)
    git_deploys = git.get_deployment(repo_obj, sha, stack_name)
    LOGGER.info("Updating github deployment")
    for deploy in git_deploys:
        git.update_deployment(deploy, "inactive", "")
        git.delete_environment(org, repo, stack_name)
        git.delete_deployment(org, repo, deploy.id)

    assumed_creds = None
    if assume is not None:
        assumed_creds = utils.assume_aws_role(assume)
    if ip is None:
        route53.check_and_remove_recordset(assumed_creds, hosted_zone, dns_name)
    route53.remove_recordset(assumed_creds, hosted_zone, dns_name, str(ip))


def cleanup():
    pass


def main(command_line=None):
    parser = argparse.ArgumentParser(
        description="Deploy preview environment on AWS ECS"
    )
    subparsers = parser.add_subparsers(dest="command")
    prenv_deploy = subparsers.add_parser("deploy")
    prenv_undeploy = subparsers.add_parser("undeploy")

    prenv_deploy.add_argument("-o", "--org", required=True)
    prenv_deploy.add_argument("-r", "--repo", required=True)
    prenv_deploy.add_argument("-b", "--branch", required=True)
    prenv_deploy.add_argument("-p", "--pr", required=True)
    prenv_deploy.add_argument("-a", "--author", required=True)
    prenv_deploy.add_argument("-i", "--image", required=True)
    prenv_deploy.add_argument("-s", "--sha", required=True)
    prenv_deploy.add_argument("-x", "--assume")

    prenv_undeploy.add_argument("-o", "--org", required=True)
    prenv_undeploy.add_argument("-r", "--repo", required=True)
    prenv_undeploy.add_argument("-p", "--pr", required=True)
    prenv_undeploy.add_argument("-s", "--sha", required=True)
    prenv_undeploy.add_argument("-x", "--assume")

    args = parser.parse_args(command_line)

    if args.command == "deploy":
        deploy(
            args.org,
            args.repo,
            args.branch,
            args.pr,
            args.author,
            args.image,
            args.sha,
            args.assume,
        )
    elif args.command == "undeploy":
        undeploy(args.org, args.repo, args.pr, args.sha, args.assume)
    elif args.command == "cleanup":
        cleanup()


if __name__ == "__main__":
    main()
