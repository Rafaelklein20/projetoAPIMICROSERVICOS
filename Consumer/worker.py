import json
import os
import sys
import time
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")


def processar_auditoria(ch, method, properties, body):
    """Callback para a fila de Auditoria (registro e compliance de eventos no catálogo)."""
    try:
        mensagem = json.loads(body.decode("utf-8"))
        evento = mensagem.get("evento", "DESCONHECIDO")
        jogo_id = mensagem.get("jogo_id", "N/A")
        detalhes = mensagem.get("dados") or mensagem.get("alteracoes") or {}
        
        print("\n" + "=" * 60, flush=True)
        print(f"[AUDITORIA] Evento Recebido: {evento}", flush=True)
        print(f" - Jogo ID: {jogo_id}", flush=True)
        print(f" - Detalhes: {json.dumps(detalhes, ensure_ascii=False)}", flush=True)
        print("=" * 60 + "\n", flush=True)

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[ERRO AUDITORIA] Falha ao processar mensagem: {e}", flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def processar_notificacao(ch, method, properties, body):
    """Callback para a fila de Notificações (alertas de marketing, novos jogos e promoções)."""
    try:
        mensagem = json.loads(body.decode("utf-8"))
        tipo = mensagem.get("tipo", "GERAL")
        titulo = mensagem.get("titulo", "Jogo sem título")
        preco = mensagem.get("preco", 0.0)

        print("\n" + "*" * 60, flush=True)
        print(f"[NOTIFICACAO] Disparando alerta aos usuários!", flush=True)
        print(f" - Tipo: {tipo}", flush=True)
        print(f" - Titulo: '{titulo}'", flush=True)
        print(f" - Preco: R$ {preco:.2f}", flush=True)
        print(" -> [SIMULACAO] Notificacao enviada com sucesso para a base de clientes.", flush=True)
        print("*" * 60 + "\n", flush=True)

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[ERRO NOTIFICACAO] Falha ao processar mensagem: {e}", flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def conectar_com_retry(max_tentativas=15, intervalo_segundos=3):
    """Tenta conectar ao RabbitMQ com retry para aguardar o serviço inicializar."""
    parametros = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        heartbeat=60,
        blocked_connection_timeout=300
    )
    for tentativa in range(1, max_tentativas + 1):
        try:
            print(f"[*] Tentativa {tentativa}/{max_tentativas}: Conectando ao RabbitMQ em '{RABBITMQ_HOST}'...", flush=True)
            conexao = pika.BlockingConnection(parametros)
            print("[SUCESSO] Conexao com RabbitMQ estabelecida com sucesso!", flush=True)
            return conexao
        except pika.exceptions.AMQPConnectionError as err:
            print(f"[!] RabbitMQ ainda indisponivel ({err}). Aguardando {intervalo_segundos}s...", flush=True)
            time.sleep(intervalo_segundos)
    raise RuntimeError(f"Nao foi possivel conectar ao RabbitMQ apos {max_tentativas} tentativas.")


def main():
    conexao = conectar_com_retry()
    canal = conexao.channel()

    # Garante que as duas filas existem e sao duraveis
    canal.queue_declare(queue="fila_auditoria", durable=True)
    canal.queue_declare(queue="fila_notificacoes", durable=True)

    # Distribui uma mensagem por vez para o worker
    canal.basic_qos(prefetch_count=1)

    # Registra os consumidores para cada fila
    canal.basic_consume(queue="fila_auditoria", on_message_callback=processar_auditoria)
    canal.basic_consume(queue="fila_notificacoes", on_message_callback=processar_notificacao)

    print("\n[SUCESSO] Worker iniciado e aguardando mensagens em 'fila_auditoria' e 'fila_notificacoes'...\n", flush=True)
    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        print("\n[!] Encerrando worker...", flush=True)
        canal.stop_consuming()
        conexao.close()
        sys.exit(0)


if __name__ == "__main__":
    main()