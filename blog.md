# Debugging SQS Queues with mirrord

## 1. Introduction to debugging SQS queues with mirrord

### a. Introduction

Debugging distributed applications, especially those relying on messaging services like Amazon Simple Queue Service (SQS), presents unique challenges. These systems often involve asynchronous communication across multiple services running in the cloud. Traditional local debugging methods struggle to capture the context and interactions needed to diagnose issues effectively.

mirrord is a powerful tool designed to bridge this gap. It allows developers to debug cloud-native applications locally by mirroring remote context, including network traffic and environment variables, into their local process. This blog post will guide you through using mirrord to effectively debug applications built around AWS SQS.

### b. Prerequisites

Before diving in, ensure you have the following:

#### Development Environment
- A Kubernetes cluster (e.g., kind, minikube, Docker Desktop, or a remote cluster) OR Docker Compose setup locally.
- `kubectl` CLI (if using Kubernetes).
- Docker and Docker Compose (if using the Docker Compose setup).

#### Installing mirrord

Install the mirrord CLI. On macOS or Linux via Homebrew:
```bash
brew install metalbear-co/mirrord/mirrord
```
For other installation methods, see the [mirrord documentation](https://mirrord.dev/docs/overview/quick-start/).

#### Installing the mirrord Operator (Optional but Recommended for Queue Splitting)

For advanced features like queue splitting, the mirrord operator needs to be installed in your Kubernetes cluster.

Using Helm:
```bash
# Add the MetalBear Helm repository
helm repo add metalbear https://metalbear-co.github.io/charts

# Update the repository
helm repo update

# Install the chart (replace with your license key if you have one)
helm install mirrord-operator metalbear/mirrord-operator --set operator.license.key=your-license-key
```

Or using the CLI:
```bash
# Replace with your license key if you have one
mirrord operator setup --accept-tos --license-key your-license-key | kubectl apply -f -
```
*Note: Queue splitting for SQS relies on intercepting AWS SDK calls and doesn't require specific Helm flags like Kafka.*

### c. What is AWS SQS and when is it used?

Amazon Simple Queue Service (SQS) is a fully managed message queuing service that enables you to decouple and scale microservices, distributed systems, and serverless applications. Key features and use cases include:

- **Decoupling:** Allows components to send and receive messages without direct coupling, improving fault tolerance and scalability.
- **Asynchronous Communication:** Enables background processing, task offloading, and buffering.
- **Reliability:** Offers Standard (at-least-once delivery) and FIFO (exactly-once processing, first-in-first-out) queues.
- **Scalability:** Automatically scales to handle message volume.

SQS is commonly used for work queues, buffering requests between services, decoupling microservices, and enabling event-driven architectures.

### d. Popular queue services

Besides SQS, other popular queue/messaging services include:

1.  **Apache Kafka**: Distributed event streaming platform.
2.  **RabbitMQ**: Traditional message broker (AMQP).
3.  **Google Pub/Sub**: Google Cloud's asynchronous messaging service.
4.  **Azure Service Bus**: Microsoft's enterprise message broker.
5.  **NATS**: High-performance messaging system.

This guide focuses on debugging applications using AWS SQS with mirrord.

## 2. Scenarios while debugging an SQS queue

### a. Simple SQS producer-consumer application example

To illustrate debugging with mirrord, we'll use the application in this repository ([mirrord-sqs-debug-example](https://github.com/waveywaves/mirrord-sqs-debug-example)). It consists of:

- **LocalStack:** A local cloud service emulator providing an SQS endpoint.
- **Producer Service:** A Flask web application (`app.py` running in `producer` mode) that sends messages to an SQS queue via a web UI.
- **Consumer Service:** A Flask web application (`app.py` running in `consumer` mode) that receives messages from the SQS queue and displays them using WebSockets in a UI.

The services are orchestrated using `docker-compose.yml`.

The following diagram shows the basic setup running via Docker Compose without mirrord:

`![Placeholder Diagram - SQS Setup without mirrord]`

#### i. Understand the application consumer, producer, and SQS config

**Producer (`producer` service in `docker-compose.yml`):**
- Runs `app.py` with `APP_MODE=producer`.
- Serves `index.html` which provides a UI to send messages.
- Uses `boto3` (AWS SDK for Python) to send messages to SQS via the `/produce` endpoint.

**Consumer (`consumer` service in `docker-compose.yml`):**
- Runs `app.py` with `APP_MODE=consumer`.
- Polls the SQS queue using `boto3`.
- Uses Flask-SocketIO to push received messages to the `index.html` UI for display.

**SQS Configuration (via Environment Variables in `docker-compose.yml`):**
- The applications connect to the `localstack` service for SQS.
- Key environment variables configure `boto3`:
  - `AWS_ENDPOINT_URL=http://localstack:4566`
  - `AWS_DEFAULT_REGION=us-east-1`
  - `QUEUE_NAME=sample-queue` (default, used by `sqs_consumer.py` and `sqs_producer.py`)
  - Test credentials (`AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`) are used for LocalStack.

#### ii. Table of important values for the SQS endpoint and queue

| Parameter             | Value                       | Description                                     | Source                                    |
|-----------------------|-----------------------------|-------------------------------------------------|-------------------------------------------|
| `AWS_ENDPOINT_URL`    | `http://localstack:4566`    | The endpoint URL for the SQS service (LocalStack) | `docker-compose.yml`                      |
| `AWS_DEFAULT_REGION`  | `us-east-1`                 | The AWS region for the SQS queue                | `docker-compose.yml`                      |
| `AWS_ACCESS_KEY_ID`   | `test`                      | AWS Access Key (for LocalStack)                 | `docker-compose.yml`                      |
| `AWS_SECRET_ACCESS_KEY` | `test`                      | AWS Secret Key (for LocalStack)                 | `docker-compose.yml`                      |
| `QUEUE_NAME`          | `sample-queue` (default)    | The name of the SQS queue                       | `sqs_consumer.py`, `sqs_producer.py`      |
| Queue URL             | (Dynamically determined)    | The full URL of the queue, returned by SQS      | `boto3` client                            |

### b. Ideal scenario while debugging SQS queues

When debugging SQS-based applications, you ideally want:

1.  Full visibility into messages being sent and received.
2.  The ability to receive and process messages locally without disrupting the deployed application.
3.  To use your local debugger and development tools.
4.  Access to the same environment variables and configuration as the remote service.

mirrord helps achieve this by mirroring traffic and context from a remote target (like a Kubernetes pod) to your local process.

### c. Problems faced while debugging SQS queues

#### i. The remote consumer competes with the debug consumer

A common challenge arises when you run your consumer service locally to debug it while the same service is also running remotely (e.g., in Kubernetes or even another Docker container). Both the local and remote instances will poll the same SQS queue. SQS delivers a message to only *one* consumer instance per `VisibilityTimeout` period. This means your local debug instance might only receive *some* of the messages, or none at all, making it difficult to reproduce specific issues or test message handling reliably. The remote consumer "competes" for messages.

#### ii. Full data redirection from the main consumer to the debug consumer (when using copy_target + scaledown in Kubernetes)

If your application is running in Kubernetes, mirrord offers the `copy_target` feature with the `scale_down` option to solve the competition problem. This ensures *all* messages are directed only to your local debug consumer. It works like this:

1.  mirrord identifies the target pod (e.g., the pod running your consumer deployment).
2.  It creates an exact copy of this target pod's specification but doesn't run it yet.
3.  It scales down the original deployment to zero replicas, stopping the remote consumer.
4.  It starts the mirrord session targeting the *copied* pod specification (which now includes the mirrord agent).
5.  Your local process, running with mirrord, inherits the environment and network context of the copied pod and becomes the *only* consumer polling the queue.

`![Placeholder Diagram - SQS copy_target + scale_down]`

*(Note: `copy_target` is primarily a Kubernetes feature. For the Docker Compose setup in this example, you'd typically achieve exclusive consumption by simply stopping the remote consumer service: `docker-compose stop consumer`)*

## 3. Debugging an SQS topic with mirrord

*(The following examples assume your application is deployed in Kubernetes for features like `copy_target` and Operator-based queue splitting. For the Docker Compose example, mirrord primarily helps by mirroring environment variables and potentially outgoing traffic if needed.)*

### a. Simple Debug: Local consumer consumes the data exclusively (Kubernetes)

#### i. copy_target + scaledown

To ensure your local consumer gets all SQS messages without competition from the deployed version in Kubernetes:

**Configuration (`.mirrord/sqs_exclusive.json`):**
```json
{
  "target": {
    "deployment": "your-consumer-deployment-name", // Replace with your deployment name
    "container": "your-container-name" // Replace with your container name
  },
  "feature": {
    "copy_target": {
      "scale_down": true
    },
    "env": true,
    "network": {
      "incoming": "mirror",
      "outgoing": true
    }
  },
  "operator": true // Assumes operator is installed
}
```

**Execution:**
```bash
# Ensure your Kubernetes deployment exists
# kubectl apply -f your-deployment.yaml

# Run your local consumer application with mirrord
mirrord exec -f .mirrord/sqs_exclusive.json -- python app.py
```

`![Placeholder Screenshot - Kubernetes Apply Command]`
`![Placeholder Screenshot - mirrord exec copy_target output]`
`![Placeholder Screenshot - Producer UI sending messages]`
`![Placeholder Screenshot - Local Consumer UI receiving all messages]`

This setup directs all SQS messages meant for `your-consumer-deployment-name` exclusively to your local `python app.py` process.

### b. Queue Splitting: Local and Remote consumers consume the same data (Kubernetes)

#### i. Introduction to queue splitting for SQS

Sometimes, you want to debug message processing locally *without* stopping the remote consumer. mirrord's queue splitting feature (requires the mirrord Operator) enables this for SQS. It intercepts the messages received by the remote consumer and sends a *copy* of those messages to your local process as well.

`![Placeholder Diagram - SQS Queue Splitting Setup 1]`
`![Placeholder Diagram - SQS Queue Splitting Setup 2]`

#### ii. How does queue splitting work with SQS?

1.  The mirrord agent, injected into the remote target pod by the operator, monitors outgoing network calls.
2.  When it detects calls to the AWS SDK for `sqs:ReceiveMessage`, it intercepts the response containing the messages *before* it reaches the remote application code.
3.  It forwards a copy of these received messages over the mirrord connection to your local process.
4.  Your local mirrord layer makes these copied messages available as if your local code had called `sqs.receive_message`.
5.  The original messages continue to the remote application code, which processes them as usual (including deleting them). Your local copy does not affect the remote processing lifecycle.

#### iii. What local mirrord needs to know

You configure queue splitting in your local mirrord configuration file:

**Configuration (`.mirrord/sqs_split.json`):**
```json
{
  "target": {
    "deployment": "your-consumer-deployment-name", // Replace with your deployment name
    "container": "your-container-name" // Replace with your container name
  },
  "feature": {
    "split_queues": "sqs", // Enable SQS queue splitting globally
    // Or specify queues if needed, though often not necessary for SQS
    // "split_queues": {
    //   "my_explicit_queue_id": { // An identifier for logs/filtering
    //      "queue_type": "SQS"
    //      // Optional message filters can be added here
    //   }
    // },
    "env": true,
    "network": {
      "incoming": "mirror", // Mirror other incoming traffic if needed
      "outgoing": {         // Filter outgoing traffic if needed
         "filter": "block", // Block unnecessary outgoing calls locally
         "aws": true       // Allow AWS SDK calls to pass through mirrord
      }
    }
  },
  "operator": true // Requires operator
}
```
*Note: Simply enabling `"split_queues": "sqs"` often works, as mirrord intercepts based on the SDK calls.*

#### iv. What the operator needs to know

Unlike Kafka, SQS queue splitting generally doesn't require specific Custom Resource Definitions (CRDs) in the cluster. The operator facilitates the injection of the mirrord agent, which handles the SQS interception based on AWS SDK calls made by the targeted application. Ensure the operator is installed in your cluster.

#### v. How to use queue splitting to debug an SQS application (Kubernetes)

##### Prerequisites

- Kubernetes cluster with your application deployed.
- mirrord CLI installed locally.
- mirrord Operator installed in the cluster.

##### Configurations

- **Local:** Create a mirrord configuration file like `.mirrord/sqs_split.json` (see above).
- **Remote:** Ensure your consumer deployment exists in Kubernetes.

##### Debugging Steps

1.  **Target the remote consumer:**
    ```bash
    # Run your local app.py consumer with mirrord queue splitting
    mirrord exec -f .mirrord/sqs_split.json -- python app.py
    ```

2.  **Send Messages:** Use your producer (locally, remotely, or via AWS console/CLI) to send messages to the SQS queue being monitored by the remote deployment.

3.  **Observe:**
    *   The remote consumer application should receive and process messages as normal.
    *   Your local `python app.py` instance, running with mirrord, should *also* receive copies of the same messages.
    *   You can now set breakpoints and debug message processing locally without affecting the deployed service.

`![Placeholder Screenshot - mirrord exec Queue Splitting]`
`![Placeholder Screenshot - Producer UI sending messages]`
`![Placeholder Screenshot - Remote Consumer Logs showing processing]`
`![Placeholder Screenshot - Local Consumer UI/Debugger showing processing]`

## 4. Conclusion

Debugging applications using AWS SQS can be significantly simplified using mirrord. Whether you need exclusive access to messages for deep debugging or want to observe message flow alongside your deployed service without disruption, mirrord provides powerful solutions:

1.  **`copy_target` + `scale_down` (Kubernetes):** Grants your local debugger exclusive access to SQS messages intended for a remote deployment.
2.  **Queue Splitting (Kubernetes with Operator):** Delivers copies of messages received by your remote consumer to your local process, enabling non-disruptive debugging.
3.  **Environment Mirroring:** Provides your local process with the necessary AWS credentials and configuration from the remote environment.

By integrating mirrord into your workflow, you can:

- Accelerate bug fixing for SQS-related issues.
- Test changes locally against real cloud message flows.
- Gain better insight into asynchronous interactions.
- Debug production/staging issues more effectively.

Explore the [official mirrord documentation](https://mirrord.dev/docs/) to learn more about its features and configuration options. 