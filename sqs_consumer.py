import boto3
import json
import os
import time
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_consumer():
    """Create an SQS consumer instance"""
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

def process_message(message):
    """Process a received message"""
    try:
        message_body = json.loads(message['Body'])
        logger.info(f"Processing message: {message_body}")
        logger.info(f"Message ID: {message['MessageId']}")
        return True
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return False

def main():
    sqs, queue_url = create_consumer()
    
    logger.info("Starting to consume messages...")
    try:
        while True:
            try:
                # Receive message
                response = sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20,
                    VisibilityTimeout=30
                )
                
                if 'Messages' in response:
                    for message in response['Messages']:
                        if process_message(message):
                            # Delete message after successful processing
                            try:
                                sqs.delete_message(
                                    QueueUrl=queue_url,
                                    ReceiptHandle=message['ReceiptHandle']
                                )
                                logger.info(f"Deleted message: {message['MessageId']}")
                            except ClientError as e:
                                logger.error(f"Error deleting message: {e}")
                
            except Exception as e:
                logger.error(f"Error receiving messages: {e}")
                time.sleep(5)
                
    except KeyboardInterrupt:
        logger.info("Stopping consumer...")

if __name__ == '__main__':
    main() 