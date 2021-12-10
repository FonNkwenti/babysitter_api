from aws_lambda_powertools import Logger, Tracer
import boto3
import os
from entities.Job import Job
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
logger = Logger(service="list_all_jobs")
tracer = Tracer()

table = dynamodb.Table(os.environ["TABLE_NAME"])

@tracer.capture_method
def listAllJobs(jobStatus: str = ""):
    logger.debug(f'jobStatus is:{jobStatus}')

    try:
        response = table.query(
            IndexName="getJobsByStatus",
            KeyConditionExpression=Key('jobStatus').eq(jobStatus),
            ScanIndexForward=False

        )

        logger.info(f'response is {response["Items"]}')
        jobs = [Job(item).job_dict() for item in response['Items']]

        logger.debug({"job_functions list is": jobs})
        return jobs


    except ClientError as err:
        logger.debug(f"Error occured when getting applications per job_functions{err.response['Error']}")
        raise err