# Debugging SQS Consumers with mirrord

<div align="center">
  <a href="https://mirrord.dev">
    <img src="images/mirrord.svg" width="150" alt="mirrord Logo"/>
  </a>
  <a href="https://aws.amazon.com/sqs/">
    <img src="images/sqs.png" width="150" alt="SQS Logo"/>
  </a>
</div>

A sample application demonstrating how to debug SQS consumers using mirrord. This application features a producer service that publishes messages to an SQS queue and a consumer service that reads and processes these messages.

## Tech Stack

- Python 3.9
- Flask
- Amazon SQS (LocalStack for local development)
- boto3 Python library
- Kubernetes

## Features

- Producer service with a web UI for publishing messages
- Consumer service that processes SQS messages, these messages can be seen in the terminal
- Kubernetes-ready deployment
- mirrord configuration for debugging SQS consumers with two different approaches

## Prerequisites

- Python 3.9 or higher
- Kubernetes cluster
- kubectl
- mirrord CLI
- helm (for alternative mirrord operator installation)

## Setup Options

### 1. Local Development with Docker Compose

For testing locally without Kubernetes:

```bash
docker compose up --build
```

This will start the LocalStack SQS emulator, producer, and consumer services in Docker containers.

### 2. Local Python Environment

If you prefer running the Python application directly:

```bash
conda create -n sqs-debug python=3.9 -y && conda activate sqs-debug && pip install -r requirements.txt
conda activate sqs-debug
```

### 3. Kubernetes Deployment

Deploy the application to your Kubernetes cluster:

```bash
kubectl apply -f kube/
```

## Debugging with mirrord

mirrord offers two powerful approaches for debugging SQS consumers:

### Approach 1: Copy Target with Scale Down

Debug with your local consumer as the only active consumer:

```bash
mirrord exec --config .mirrord/copytarget_plus_scaledown.json -- python app.py
```

This configuration:
- Creates a copy of the target deployment's pod
- Scales down the original deployment to zero replicas
- Ensures your local application receives all messages

### Approach 2: Queue Splitting

Debug without disrupting existing consumers:

```bash
APP_MODE=consumer PYTHONUNBUFFERED=1 mirrord exec -f .mirrord/mirrord.json -- python app.py
```

This configuration:
- Allows both your local application and remote consumers to receive the same messages
- Uses the mirrord operator to intercept and duplicate SQS messages
- Supports message filtering for targeted debugging

## How it Works

mirrord allows you to run your SQS consumer locally while connecting to your Kubernetes cluster:

- Your local consumer can receive messages from SQS queues in the cluster
- You can debug your consumer code with local tools while processing real SQS messages
- Choose between exclusive access to messages or non-disruptive debugging

## Configuration Files

This project includes several mirrord configuration files:

- `.mirrord/mirrord.json`: Configuration for queue splitting
- `.mirrord/copytarget_plus_scaledown.json`: Configuration for copy target with scale down

## Additional Documentation

For more detailed information about debugging SQS consumers with mirrord, refer to the [BLOG.md](BLOG.md) file in this repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
