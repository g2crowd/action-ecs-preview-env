import logging

import boto3

LOGGER = logging.getLogger("root")


def init_client(assumed_creds):
    if assumed_creds is None:
        client = boto3.client("route53")
    else:
        client = boto3.client(
            "route53",
            aws_access_key_id=assumed_creds["AccessKeyId"],
            aws_secret_access_key=assumed_creds["SecretAccessKey"],
            aws_session_token=assumed_creds["SessionToken"],
        )
    return client


def update_recordset(assumed_creds, hosted_zone, dns_name, ip):
    LOGGER.info("Setting DNS recordset")

    client = init_client(assumed_creds)
    client.change_resource_record_sets(
        HostedZoneId=hosted_zone,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": dns_name,
                        "Type": "A",
                        "TTL": 300,
                        "ResourceRecords": [
                            {"Value": ip},
                        ],
                    },
                }
            ]
        },
    )


def remove_recordset(assumed_creds, hosted_zone, dns_name, ip):
    LOGGER.info("Removing DNS recordset")

    client = init_client(assumed_creds)
    client.change_resource_record_sets(
        HostedZoneId=hosted_zone,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": dns_name,
                        "Type": "A",
                        "TTL": 300,
                        "ResourceRecords": [
                            {"Value": ip},
                        ],
                    },
                }
            ]
        },
    )


def check_and_remove_recordset(assumed_creds, hosted_zone, dns_name):
    client = init_client(assumed_creds)
    response = client.list_resource_record_sets(
        HostedZoneId=hosted_zone,
        StartRecordName=dns_name,
        StartRecordType="A",
    )

    if len(response["ResourceRecordSets"]) == 0:
        exit(0)

    record = response["ResourceRecordSets"][0]["Name"]
    dns_name = dns_name + "."
    if record == dns_name:
        ip = response["ResourceRecordSets"][0]["ResourceRecords"][0]["Value"]
        remove_recordset(assumed_creds, hosted_zone, dns_name, ip)
