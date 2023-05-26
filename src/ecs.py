import logging
import subprocess
import time

import boto3
import utils

LOGGER = logging.getLogger("root")
CLIENT = boto3.client("ecs")
WAITER_DELAY = 10
WAITER_MAXATTEMPTS = 60


def get_task_definition(name):
    response = CLIENT.describe_task_definition(taskDefinition=name)
    task_definition = response["taskDefinition"]
    if "taskDefinitionArn" in task_definition:
        del task_definition["taskDefinitionArn"]
    if "revision" in task_definition:
        del task_definition["revision"]
    if "status" in task_definition:
        del task_definition["status"]
    if "requiresAttributes" in task_definition:
        del task_definition["requiresAttributes"]
    if "compatibilities" in task_definition:
        del task_definition["compatibilities"]
    if "registeredAt" in task_definition:
        del task_definition["registeredAt"]
    if "registeredBy" in task_definition:
        del task_definition["registeredBy"]

    return task_definition


def register_task_definition(config):
    LOGGER.info("Registering task definition")
    command = "aws ecs register-task-definition --cli-input-json file://{0}".format(
        config
    )
    result = subprocess.call(command, shell=True, stdout=subprocess.DEVNULL)
    if result > 0:
        LOGGER.error("Failed to register task definition")
        exit(1)


def remove_task_definition(name):
    response = CLIENT.list_task_definitions(familyPrefix=name)
    for arn in response["taskDefinitionArns"]:
        CLIENT.deregister_task_definition(taskDefinition=arn)


def get_existing_deploy(cluster, started_by):
    response = CLIENT.list_tasks(
        cluster=cluster,
        startedBy=started_by,
        desiredStatus="RUNNING",
    )
    if len(response["taskArns"]) > 0:
        return response["taskArns"]
    return []


def get_task_ip(cluster, task_arn):
    response = CLIENT.describe_tasks(
        cluster=cluster,
        tasks=[
            task_arn,
        ],
    )
    return response["tasks"][0]["containers"][0]["networkInterfaces"][0][
        "privateIpv4Address"
    ]


def get_task_eni_id(cluster, task_arn):
    response = CLIENT.describe_tasks(
        cluster=cluster,
        tasks=[
            task_arn,
        ],
    )
    return response["tasks"][0]["containers"][0]["networkInterfaces"][0][
        "attachmentId"
    ]


def is_task_running(cluster, task_arn):
    attempt = 0
    response = None

    while attempt < WAITER_MAXATTEMPTS:

        response = CLIENT.describe_tasks(
            cluster=cluster,
            tasks=[
                task_arn,
            ],
        )
        if len(response["failures"]) > 0:
            LOGGER.error("Failed to deploy task")
            LOGGER.info("%s" % response["Failures"])
            break
        if response["tasks"][0]["lastStatus"] == "RUNNING":
            return True
        elif response["tasks"][0]["lastStatus"] == "STOPPED":
            return False
        time.sleep(WAITER_DELAY)
        attempt += 1

    return False


def stop_task(cluster, task_arn):
    CLIENT.stop_task(cluster=cluster, task=task_arn)


def run_task(
    cluster, subnets, security_groups, task_definition, started_by, platform, project, public_ip
):
    response = CLIENT.run_task(
        cluster=cluster,
        taskDefinition=task_definition,
        count=1,
        startedBy=started_by,
        launchType="FARGATE",
        platformVersion=platform,
        enableExecuteCommand=True,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnets,
                "securityGroups": security_groups,
                "assignPublicIp": public_ip,
            }
        },
        tags=[
            {"key": "environment", "value": "testing"},
            {"key": "project", "value": project},
            {"key": "owner", "value": "prenv"},
        ],
    )

    if len(response["failures"]) > 0:
        LOGGER.error("Failed to deploy task")
        LOGGER.info("%s" % response["Failures"])
        return None, False

    return response["tasks"][0]["taskArn"], is_task_running(
        cluster, response["tasks"][0]["taskArn"]
    )


def deploy(
    cluster, subnets, security_groups, task_definition, started_by, platform, project
):
    LOGGER.info("Deploying preview environment")
    existing_tasks = get_existing_deploy(cluster, started_by)
    deployed_task, ok = run_task(
        cluster,
        subnets,
        security_groups,
        task_definition,
        started_by,
        platform,
        project,
    )
    utils.export_env("TASK_ARN", deployed_task)

    if not ok:
        LOGGER.error("Deployment failed")
        return None

    LOGGER.info("Deployed successfully")

    if len(existing_tasks) > 0:
        LOGGER.info("Stopping previously deployed PR")
        for task in existing_tasks:
            stop_task(cluster, task)
    return deployed_task


def undeploy(cluster, started_by, task_family):
    LOGGER.info("Undeploying preview environment")
    ip = None
    existing_tasks = get_existing_deploy(cluster, started_by)
    remove_task_definition(task_family)

    if len(existing_tasks) > 0:
        for task in existing_tasks:
            ip = get_task_ip(cluster, task)
            stop_task(cluster, task)
    return ip
