import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import boto3
import json
import threading
import os
import logging
import time
import random
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
# Update Socket.IO configuration for better compatibility
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e8,
    manage_session=False,
    namespace='/'
)

# SQS configuration
AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'test')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
QUEUE_NAME = os.getenv('QUEUE_NAME', 'sample-queue')
APP_MODE = os.getenv('APP_MODE', 'producer')  # 'producer' or 'consumer'

logger.info(f"Starting application in {APP_MODE} mode")
logger.info(f"SQS endpoint: {AWS_ENDPOINT_URL}")
logger.info(f"Queue name: {QUEUE_NAME}")

# Initialize SQS client
sqs = boto3.client('sqs',
    endpoint_url=AWS_ENDPOINT_URL,
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

def ensure_queue_exists():
    """Create queue if it doesn't exist and return its URL"""
    try:
        response = sqs.create_queue(QueueName=QUEUE_NAME)
        queue_url = response['QueueUrl']
        logger.info(f"Queue URL: {queue_url}")
        return queue_url
    except Exception as e:
        logger.error(f"Error creating queue: {e}")
        raise

queue_url = ensure_queue_exists()
consumer_thread = None

if APP_MODE == 'consumer':
    def consumer_thread_func():
        logger.info("Starting consumer thread...")
        while True:
            try:
                response = sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20
                )
                
                if 'Messages' in response:
                    for message in response['Messages']:
                        try:
                            message_body = json.loads(message['Body'])
                            logger.info(f"Received message: {message_body}")
                            
                            # Emit message to WebSocket clients with namespace
                            event_data = {
                                'value': message_body,
                                'message_id': message['MessageId'],
                                'receipt_handle': message['ReceiptHandle'],
                                'timestamp': time.time()
                            }
                            logger.info(f"Emitting message to clients: {event_data}")
                            socketio.emit('sqs_message', event_data, namespace='/', broadcast=True)
                            
                            # Delete the message
                            sqs.delete_message(
                                QueueUrl=queue_url,
                                ReceiptHandle=message['ReceiptHandle']
                            )
                            logger.info(f"Deleted message: {message['MessageId']}")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            
            except Exception as e:
                logger.error(f"Error in consumer thread: {e}")
                time.sleep(5)  # Wait before retrying

    consumer_thread = threading.Thread(target=consumer_thread_func)
    consumer_thread.daemon = True
    consumer_thread.start()
    logger.info("Consumer thread started")

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@app.route('/')
def index():
    logger.info(f"Serving index page in {APP_MODE} mode")
    return render_template('index.html', mode=APP_MODE)

@app.route('/produce', methods=['POST'])
def produce_message():
    if APP_MODE != 'producer':
        logger.error(f"Produce endpoint called but running in {APP_MODE} mode")
        return jsonify({'error': 'This instance is not configured as a producer'}), 400

    data = request.json
    message = data.get('message')
    
    if not message:
        logger.warning("Empty message received")
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        logger.info(f"Sending message: {message}")
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        result = {
            'success': True,
            'message': 'Message sent successfully',
            'metadata': {
                'message_id': response['MessageId'],
                'queue_url': queue_url
            }
        }
        logger.info(f"Message sent successfully: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def status():
    status_info = {
        'mode': APP_MODE,
        'sqs_endpoint': AWS_ENDPOINT_URL,
        'queue_name': QUEUE_NAME,
        'queue_url': queue_url,
        'status': 'running',
        'consumer_thread_running': consumer_thread is not None and consumer_thread.is_alive() if consumer_thread else False
    }
    logger.info(f"Status check: {status_info}")
    return jsonify(status_info) 