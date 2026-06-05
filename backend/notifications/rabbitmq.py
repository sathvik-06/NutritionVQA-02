import pika
import logging
import json
from config.settings import settings

logger = logging.getLogger("notifications")

class RabbitMQService:
    def __init__(self):
        self.params = None
        if settings.RABBITMQ_URL:
            try:
                self.params = pika.URLParameters(settings.RABBITMQ_URL)
                # Increase timeouts to prevent handshake errors on slow connections
                self.params.connection_attempts = 1
                self.params.retry_delay = 1
                self.params.socket_timeout = 1
                self.params.heartbeat = 60
                logger.info("RabbitMQ parameters initialized with increased timeouts.")
            except Exception as e:
                logger.error(f"Failed to initialize RabbitMQ parameters: {e}")

    def send_notification(self, user_id: str, message: str, notification_type: str = "info"):
        if not self.params:
            logger.warning("RabbitMQ URL not configured. Cannot send notification.")
            return False
            
        try:
            connection = pika.BlockingConnection(self.params)
            channel = connection.channel()
            
            queue_name = f"notifications_{user_id}"
            channel.queue_declare(queue=queue_name, durable=True)
            
            payload = {
                "user_id": user_id,
                "message": message,
                "type": notification_type
            }
            
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                ))
            
            connection.close()
            logger.info(f"Notification sent to queue {queue_name}.")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification via RabbitMQ: {e}")
            return False

rabbitmq_service = RabbitMQService()
