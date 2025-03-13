import boto3
import json
import os
import time
import random
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_producer():
    """Create an SQS producer instance"""
    aws_endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID', 'test')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
    queue_name = os.getenv('QUEUE_NAME', 'sample-queue')

    logger.info(f"Connecting to SQS at {aws_endpoint_url}")
    
    # Initialize SQS client
    sqs = boto3.client('sqs',
        endpoint_url=aws_endpoint_url,
        region_name=aws_region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    # Create queue if it doesn't exist
    try:
        response = sqs.create_queue(QueueName=queue_name)
        queue_url = response['QueueUrl']
        logger.info(f"Connected to queue: {queue_url}")
        return sqs, queue_url
    except Exception as e:
        logger.error(f"Error creating/connecting to queue: {e}")
        raise

def send_message(sqs, queue_url, message):
    """Send a message to SQS queue"""
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        logger.info(f"Message sent successfully")
        logger.info(f"Message ID: {response['MessageId']}")
        logger.info(f"Value: {message}")
        return response['MessageId']
    except ClientError as e:
        logger.error(f"Error sending message: {e}")
        return None

def main():
    sqs, queue_url = create_producer()
    
    logger.info("Starting to send random numbers...")
    try:
        while True:
            # Generate a random number between 1 and 1000
            random_number = random.randint(1, 1000)
            message = {
                'timestamp': time.time(),
                'value': random_number
            }
            send_message(sqs, queue_url, message)
            time.sleep(1)  # Wait 1 second between messages
    except KeyboardInterrupt:
        logger.info("Stopping producer...")

if __name__ == '__main__':
    main() 