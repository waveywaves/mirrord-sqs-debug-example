#!/bin/bash

# Wait for LocalStack to be ready
until curl -s http://localhost:4566/_localstack/health | grep -q '"sqs": "running"'; do
    echo "Waiting for LocalStack SQS to be ready..."
    sleep 1
done

# Create the SQS queue
echo "Creating SQS queue..."
aws --endpoint-url=http://localhost:4566 sqs create-queue \
    --queue-name sample-queue \
    --region us-east-1 \
    --attributes '{
        "VisibilityTimeout": "30",
        "MessageRetentionPeriod": "345600",
        "ReceiveMessageWaitTimeSeconds": "20"
    }'

echo "SQS queue created successfully!" 