import boto3
import json
import time
import random
import os

# Initialize SQS client with LocalStack endpoint
sqs = boto3.client('sqs',
    endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566'),
    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
)

# Queue name for local development
QUEUE_NAME = 'sample-queue'

def ensure_queue_exists():
    """Create queue if it doesn't exist and return its URL"""
    try:
        response = sqs.create_queue(QueueName=QUEUE_NAME)
        queue_url = response['QueueUrl']
        print(f"Queue URL: {queue_url}")
        return queue_url
    except Exception as e:
        print(f"Error creating queue: {e}")
        raise

def send_message(queue_url, message):
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        print(f"Message sent. MessageId: {response['MessageId']}")
        return response
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def main():
    queue_url = ensure_queue_exists()
    
    while True:
        # Generate a sample message
        message = {
            'id': random.randint(1, 1000),
            'timestamp': time.time(),
            'data': f'Sample message {random.randint(1, 100)}'
        }
        
        send_message(queue_url, message)
        
        # Wait for a few seconds before sending the next message
        time.sleep(2)

if __name__ == "__main__":
    main() 