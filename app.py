import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import os
import logging
import time
from dotenv import load_dotenv
from sqs_producer import create_producer, send_message
from sqs_consumer import create_consumer, process_message

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
    manage_session=False
)

# Application mode
APP_MODE = os.getenv('APP_MODE', 'producer')  # 'producer' or 'consumer'
logger.info(f"Starting application in {APP_MODE} mode")

if APP_MODE == 'consumer':
    # Initialize SQS consumer
    sqs, queue_url = create_consumer()
    
    def consumer_thread_func():
        """Thread function to receive messages from SQS and emit to WebSocket clients"""
        logger.info("Starting consumer thread...")
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
                        try:
                            message_body = json.loads(message['Body'])
                            logger.info(f"Received message: {message_body}")
                            
                            event_data = {
                                'value': message_body,
                                'message_id': message['MessageId'],
                                'receipt_handle': message['ReceiptHandle'],
                                'timestamp': time.time()
                            }
                            
                            # Emit message to WebSocket clients
                            logger.info(f"Emitting message to clients: {event_data}")
                            socketio.emit('sqs_message', event_data, namespace='/')
                            
                            # Delete message after sending
                            sqs.delete_message(
                                QueueUrl=queue_url,
                                ReceiptHandle=message['ReceiptHandle']
                            )
                            logger.info(f"Deleted message: {message['MessageId']}")
                            
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            
            except Exception as e:
                logger.error(f"Error in consumer thread: {e}")
                eventlet.sleep(5)

    # Start consumer thread
    consumer_thread = eventlet.spawn(consumer_thread_func)
    logger.info("Consumer thread started")

else:
    # Initialize SQS producer
    sqs, queue_url = create_producer()

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
        message_id = send_message(sqs, queue_url, message)
        if message_id:
            result = {
                'success': True,
                'message': 'Message sent successfully',
                'metadata': {
                    'message_id': message_id,
                    'queue_url': queue_url
                }
            }
            logger.info(f"Message sent successfully: {result}")
            return jsonify(result)
        else:
            return jsonify({'error': 'Failed to send message'}), 500
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def status():
    status_info = {
        'mode': APP_MODE,
        'queue_url': queue_url,
        'status': 'running'
    }
    logger.info(f"Status check: {status_info}")
    return jsonify(status_info)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 