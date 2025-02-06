import boto3
import json
import time
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

def get_queue_url():
    """Get queue URL, wait if queue doesn't exist yet"""
    while True:
        try:
            response = sqs.get_queue_url(QueueName=QUEUE_NAME)
            return response['QueueUrl']
        except Exception as e:
            print(f"Waiting for queue to be created... ({e})")
            time.sleep(5)

def process_message(message):
    """Process the received message"""
    try:
        body = json.loads(message['Body'])
        print(f"Processing message: {body}")
        # Add your message processing logic here
        return True
    except Exception as e:
        print(f"Error processing message: {e}")
        return False

def receive_messages(queue_url):
    try:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20  # Long polling
        )
        
        if 'Messages' in response:
            for message in response['Messages']:
                if process_message(message):
                    # Delete message after successful processing
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    print(f"Message deleted: {message['MessageId']}")
    
    except Exception as e:
        print(f"Error receiving messages: {e}")

def main():
    print("Starting consumer...")
    queue_url = get_queue_url()
    print(f"Connected to queue: {queue_url}")
    
    while True:
        receive_messages(queue_url)
        time.sleep(1)  # Small delay between polling

if __name__ == "__main__":
    main() 