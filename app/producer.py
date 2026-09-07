
import json
import os
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

def publicar_mensagem(nome_fila: str, mensagem: dict):
    """Conecta ao RabbitMQ, garante a existência da fila e envia a mensagem de forma persistente."""
    connection = None
    try:
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            connection_attempts=2,
            retry_delay=1,
            socket_timeout=3
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
             
        channel.queue_declare(queue=nome_fila, durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key=nome_fila,
            body=json.dumps(mensagem, default=str),
            properties=pika.BasicProperties(
                delivery_mode=2  # Torna a mensagem persistente em disco
            )
        )
    except Exception as e:
        print(f"[ERRO PRODUCER] Falha ao enviar mensagem para '{nome_fila}': {e}")
    finally:
        if connection and not connection.is_closed:
            try:
                connection.close()
            except Exception:
                pass