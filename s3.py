import logging, os, json
from flask import current_app
import boto3
from botocore.config import Config

from config import config

_current_env = os.getenv("FLASK_ENV")
print(_current_env)
_current_config = config[_current_env]

S3_CLIENT = boto3.client(
    's3',
    config=Config(signature_version='s3v4'),
    region_name=_current_config.AWS_REGION,
    aws_access_key_id=_current_config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=_current_config.AWS_SECRET_ACCESS_KEY
)

def generate_presigned_post(filename, type):
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.generate_presigned_post

    Returns
    A dictionary with two elements: url and fields. Url is the url to post to.
    Fields is a dictionary filled with the form fields and respective values to use when submitting the post. For example:

    {
        'url': 'https://mybucket.s3.amazonaws.com
        'fields': {
            'acl': 'public-read',
            'key': 'mykey', 'signature': 'mysignature', 'policy': 'mybase64 encoded policy'
        }
    }
    """
    return S3_CLIENT.generate_presigned_post(
        _current_config.AWS_BUCKET_NAME,
        filename
    )



def create_presigned_url(bucket_name: str, object_name: str, expiration=30):
    """
    Generate a presigned URL to share an S3 object

    :param bucket_name: str
    :param object_name: str
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    try:
        response = S3_CLIENT.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_name
            },
            ExpiresIn=expiration
        )

    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response

