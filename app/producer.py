
import json
import os
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

def publicar_mensagem(nome_fila: str, mensagem: dict):
    """Conecta ao RabbitMQ, garante a existência da fila e envia a mensagem."""
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
             
        channel.queue_declare(queue=nome_fila, durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key=nome_fila,
            body=json.dumps(mensagem),
            properties=pika.BasicProperties(
                delivery_mode=2  # Torna a mensagem persistente
            )
        )
        connection.close()
    except Exception as e:
        print(f"[ERRO PRODUCER] Falha ao enviar para {nome_fila}: {e}")