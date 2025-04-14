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
- Consumer service that processes SQS messages
- LocalStack integration for local SQS development
- Kubernetes-ready deployment
- mirrord configuration for debugging SQS consumers with two different approaches:
  - Queue splitting for non-disruptive debugging
  - Copy target with scale down for exclusive debugging

## Prerequisites

- Python 3.9 or higher
- Kubernetes cluster
- kubectl
- mirrord CLI
- helm (for mirrord operator installation)
- LocalStack (for local development)

## Setup Options

### 1. Local Development with Docker Compose

For testing locally without Kubernetes:

```bash
docker compose up --build
```

This will start:
- LocalStack SQS emulator
- Producer service with web UI
- Consumer service
- All services are configured to work together with LocalStack

### 2. Local Python Environment

If you prefer running the Python application directly:

```bash
# Create and activate conda environment
conda create -n sqs-debug python=3.9 -y
conda activate sqs-debug

# Install dependencies
pip install -r requirements.txt
```

### 3. Kubernetes Deployment

Deploy the application to your Kubernetes cluster:

```bash
# Apply all Kubernetes manifests
kubectl apply -f kube/
```

This will deploy:
- LocalStack service for SQS emulation in the `default` namespace
- Producer deployment with web UI in the `default` namespace
- Consumer deployment in the `default` namespace
- mirrord operator configuration in the `mirrord` namespace
- Queue registry in the `mirrord` namespace

Note: The consumer deployment is annotated with `mirrord.metalbear.co/enabled: "true"` for mirrord integration.

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
- Perfect for isolated debugging sessions

### Approach 2: Queue Splitting

Debug without disrupting existing consumers:

```bash
APP_MODE=consumer PYTHONUNBUFFERED=1 mirrord exec -f .mirrord/mirrord.json -- python app.py
```

This configuration:
- Allows both your local application and remote consumers to receive the same messages
- Uses the mirrord operator to intercept and duplicate SQS messages
- Supports message filtering for targeted debugging
- Ideal for production debugging without disruption

## How it Works

### LocalStack Integration

The application uses LocalStack to emulate SQS in local development:
- LocalStack runs on port 4566
- All services are configured to use LocalStack's endpoint
- Test AWS credentials are used for authentication
- The SQS queue is automatically created by an init container in the LocalStack deployment

### mirrord Queue Splitting

When using queue splitting:
1. mirrord operator intercepts SQS messages
2. Messages are duplicated and sent to both:
   - Original consumer in the cluster
   - Your local debugging environment
3. Message filtering can be applied to focus on specific patterns

### Message Flow

1. Producer sends messages to SQS queue
2. mirrord operator intercepts messages
3. Messages are delivered to:
   - Original consumer (if using queue splitting)
   - Your local debugging environment
4. You can debug the message processing in real-time

## Configuration Files

This project includes several configuration files:

- `.mirrord/mirrord.json`: Configuration for queue splitting
- `.mirrord/copytarget_plus_scaledown.json`: Configuration for copy target with scale down


## Additional Documentation

For more detailed information about debugging SQS consumers with mirrord, refer to the [BLOG.md](BLOG.md) file in this repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
