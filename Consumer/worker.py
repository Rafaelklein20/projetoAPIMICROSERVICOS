# consumer/worker.py
import os
import time
import json
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

def processar_auditoria(ch, method, properties, body):
    evento = json.loads(body)
    print(f" [AUDITORIA] Registrando evento: {evento['acao']} para o jogo {evento.get('jogo_id')}")
    
    ch.basic_ack(delivery_tag=method.delivery_tag)

def processar_notificacao(ch, method, properties, body):
    notif = json.loads(body)
    print(f" [NOTIFICAÇÃO] Disparando e-mails para '{notif['tipo']}': O jogo '{notif['titulo']}' está disponível por R$ {notif['preco']}!")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def iniciar_consumer():
    
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            break
        except pika.exceptions.AMQPConnectionError:
            print("Aguardando RabbitMQ...")
            time.sleep(3)

    channel = connection.channel()

    
    channel.queue_declare(queue="fila_auditoria", durable=True)
    channel.basic_consume(queue="fila_auditoria", on_message_callback=processar_auditoria)


    channel.queue_declare(queue="fila_notificacoes", durable=True)
    channel.basic_consume(queue="fila_notificacoes", on_message_callback=processar_notificacao)

    print(" [*] Worker aguardando mensagens em 'fila_auditoria' e 'fila_notificacoes'.")
    channel.start_consuming()

if __name__ == "__main__":
    iniciar_consumer()