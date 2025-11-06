import boto3
import uuid
from config import Config

def upload_file_to_s3(file):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=Config.AWS_ACCESS_KEY,
        aws_secret_access_key=Config.AWS_SECRET_KEY,
        region_name=Config.AWS_REGION
    )

    ext = file.filename.split(".")[-1]
    key = f"events/{uuid.uuid4()}.{ext}"

    s3.upload_fileobj(
        file,
        Config.AWS_BUCKET_NAME,
        key,
        ExtraArgs={
            "ACL": "public-read",
            "ContentType": file.content_type
        }
    )

    return f"https://{Config.AWS_BUCKET_NAME}.s3.{Config.AWS_REGION}.amazonaws.com/{key}"
