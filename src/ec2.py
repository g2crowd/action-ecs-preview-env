import logging

import boto3

LOGGER = logging.getLogger("root")

def get_public_ip(eni_id):
    eni = boto3.resource('ec2').NetworkInterface(eni_id)
    return eni.association_attribute['PublicIp']
