import argparse
import os

import config
import database
import ec2
import ecs
import git
import route53
import tf
import utils

LOGGER = utils.setup_custom_logger("root")


CONFIG_FILE_PATH = ".prenv/"
ECS_CONFIG = "ecs_config.json"
TASK_DEFINITION_CONFIG = "task_definition.json"
DATABASE_CONFIG = "database_config.json"
DEPLOYMENT_CONFIG = "deployment_config.json"


def deploy(ecs_data, org, repo, branch, pr, author, image, sha, assume, tf_outputs, stackname):
    task_definition_config = CONFIG_FILE_PATH + TASK_DEFINITION_CONFIG
    deployment_config = CONFIG_FILE_PATH + DEPLOYMENT_CONFIG
    database_config = CONFIG_FILE_PATH + DATABASE_CONFIG
    dns_name = None
    stack_name = repo + pr if stackname is None else stackname + pr
    task_family = "prenv-" + repo + "-" + pr
    assumed_creds = None
    os.environ["PRENV_ORG"] = org
    os.environ["PRENV_REPO"] = repo
    os.environ["PRENV_BRANCH"] = branch
    os.environ["PRENV_PR"] = pr
    os.environ["PRENV_AUTHOR"] = author
    os.environ["PRENV_IMAGE"] = image
    os.environ["PRENV_SHA"] = sha
    os.environ["PRENV_TASK_FAMILY"] = task_family
    os.environ["PRENV_STACK_NAME"] = stack_name

    for item, value in os.environ.items():
        print("{}: {}".format(item, value))

    if ecs_data.get("public_ip") is None:
        ecs_data["public_ip"] = "DISABLED"

    if ecs_data.get("dns") is not None:
        hosted_zone, domain = config.get_dns_config(ecs_data)
        dns_name = stack_name + "." + domain
        os.environ["PRENV_DNS_NAME"] = dns_name
    else:
        LOGGER.info("Recordset configuration file is not available")
        LOGGER.info("The DNS reocord will not be created")

    env_url = "" if dns_name is None else str(dns_name)
    repo_obj = git.get_repo(org, repo)
    git_deploys = git.get_deployment(repo_obj, sha, stack_name)
    if git_deploys.totalCount == 0:
        git.create_environment(org, repo, stack_name)
        git_deployment = git.create_deployment(repo_obj, sha, stack_name, author)
    else:
        for deploy in git_deploys:
            git_deployment = deploy

    if config.is_config_exists(database_config):
        db_data = config.load_config(database_config)
        db_data = config.parse_config(db_data, tf_outputs, assumed_creds)
        db = database.get_database(db_data, repo_obj, pr)
        if db is None:
            LOGGER.error("Databases are not available")
            deployment_status = "failure"
            LOGGER.info("Updating github deployment")
            git.update_deployment(
                git_deployment, deployment_status, "https://" + env_url
            )
            exit(1)

        for item in db:
            if item != "share":
                os.environ["PRENV_" + item.upper()] = db[item]
    else:
        LOGGER.info("Database configuration file is not available")

    td_data = config.load_config(task_definition_config)
    td_data = config.parse_config(td_data, tf_outputs, assumed_creds)
    config.generate_task_def_config_file(td_data, deployment_config)
    ecs.register_task_definition(deployment_config)

    deployed_task = ecs.deploy(
        ecs_data["cluster"],
        ecs_data["subnet_ids"],
        ecs_data["security_groups"],
        task_family,
        stack_name,
        ecs_data["platform"],
        repo,
        ecs_data["public_ip"],
    )

    if ecs_data["public_ip"] == "ENABLED":
        eni_id = ecs.get_task_eni_id(ecs_data["cluster"], deployed_task)
        ip = ec2.get_public_ip(eni_id)
    else:
        ip = ecs.get_task_ip(ecs_data["cluster"], deployed_task)

    deployment_status = "success"
    if ip is None:
        deployment_status = "failure"
    LOGGER.info("Updating github deployment")
    git.update_deployment(git_deployment, deployment_status, "https://" + env_url)

    if dns_name is not None and ip is not None:
        if assume is not None:
            assumed_creds = utils.assume_aws_role(assume)
        route53.update_recordset(assumed_creds, hosted_zone, dns_name, ip)


def undeploy(ecs_data, org, repo, pr, sha, assume, tf_outputs, stackname):
    task_family = "prenv-" + repo + "-" + pr
    stack_name = repo + pr if stackname is None else stackname + pr
    assumed_creds = None

    if ecs_data.get("dns") is not None:
        hosted_zone, domain = config.get_dns_config(ecs_data)
        dns_name = stack_name + "." + domain
        os.environ["PRENV_DNS_NAME"] = dns_name

    cluster = ecs_data["cluster"]

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
    prenv_deploy.add_argument("-t", "--tfstate")
    prenv_deploy.add_argument("-t", "--stackname")

    prenv_undeploy.add_argument("-o", "--org", required=True)
    prenv_undeploy.add_argument("-r", "--repo", required=True)
    prenv_undeploy.add_argument("-p", "--pr", required=True)
    prenv_undeploy.add_argument("-s", "--sha", required=True)
    prenv_undeploy.add_argument("-x", "--assume")
    prenv_undeploy.add_argument("-t", "--tfstate")
    prenv_undeploy.add_argument("-t", "--stackname")

    args = parser.parse_args(command_line)

    tf_outputs = {}
    if args.tfstate is not None:
        tf_outputs = tf.get_outputs(None, args.tfstate)

    ecs_config = CONFIG_FILE_PATH + ECS_CONFIG
    if not config.is_config_exists(ecs_config):
        LOGGER.error("ECS configuration file is not available")
        exit(1)
    ecs_data = config.load_config(ecs_config)
    ecs_data = config.parse_config(ecs_data, tf_outputs, None)

    if args.command == "deploy":
        deploy(
            ecs_data,
            args.org,
            args.repo,
            args.branch,
            args.pr,
            args.author,
            args.image,
            args.sha,
            args.assume,
            tf_outputs,
            args.stackname
        )
    elif args.command == "undeploy":
        undeploy(
            ecs_data, args.org, args.repo, args.pr, args.sha, args.assume, tf_outputs, args.stackname
        )
    elif args.command == "cleanup":
        cleanup()


if __name__ == "__main__":
    main()
