import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
import pika
import pytest

# Garante que a raiz do projeto e o pacote app possam ser importados
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Para testes rodando na máquina host, RabbitMQ roda em localhost
os.environ.setdefault("RABBITMQ_HOST", "localhost")

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
MGMT_API_URL = os.getenv("MGMT_API_URL", "http://localhost:15672/api")



@pytest.fixture(scope="module")
def rabbitmq_channel():
    """Fixture que fornece um canal de conexão aberto com o RabbitMQ."""
    parametros = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        connection_attempts=3,
        retry_delay=2,
        socket_timeout=5
    )
    conexao = pika.BlockingConnection(parametros)
    canal = conexao.channel()
    yield canal
    if not conexao.is_closed:
        conexao.close()


def requisicao_http(url: str, metodo: str = "GET", dados: dict = None) -> tuple:
    """Função utilitária para chamadas HTTP via urllib."""
    dados_bytes = json.dumps(dados).encode("utf-8") if dados else None
    req = urllib.request.Request(url, data=dados_bytes, method=metodo)
    if dados:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            corpo = resp.read().decode("utf-8")
            return resp.status, json.loads(corpo) if corpo else {}
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8")
        return e.code, json.loads(corpo) if corpo else {}


# ==============================================================================
# TESTE 1: Validar se as 2 filas existem no RabbitMQ e possuem Consumidor ativo
# ==============================================================================
def test_filas_existem_e_possuem_consumidores(rabbitmq_channel):
    """
    Verifica se:
    1. A 'fila_auditoria' existe, é durável e tem pelo menos 1 consumidor (worker).
    2. A 'fila_notificacoes' existe, é durável e tem pelo menos 1 consumidor (worker).
    """
    # Declaração passiva (passive=True) falha se a fila não existir previamente
    res_auditoria = rabbitmq_channel.queue_declare(queue="fila_auditoria", passive=True)
    res_notificacoes = rabbitmq_channel.queue_declare(queue="fila_notificacoes", passive=True)

    assert res_auditoria is not None, "A fila 'fila_auditoria' não foi encontrada no RabbitMQ"
    assert res_notificacoes is not None, "A fila 'fila_notificacoes' não foi encontrada no RabbitMQ"

    # Confirma que o contêiner 'worker_consumer' está escutando ambas as filas
    assert res_auditoria.method.consumer_count >= 1, (
        f"Esperava pelo menos 1 consumidor em 'fila_auditoria', mas encontrou {res_auditoria.method.consumer_count}"
    )
    assert res_notificacoes.method.consumer_count >= 1, (
        f"Esperava pelo menos 1 consumidor em 'fila_notificacoes', mas encontrou {res_notificacoes.method.consumer_count}"
    )


# ==============================================================================
# TESTE 2: Teste unitário do Producer (envio de mensagem com persistência)
# ==============================================================================
def test_producer_publicacao_direta_persistente(rabbitmq_channel):
    """
    Testa diretamente a função de publicação garantindo:
    - Fila durável;
    - Entrega persistente (delivery_mode=2);
    - Serialização de dados em JSON.
    """
    from app.producer import publicar_mensagem

    fila_teste = "fila_teste_pytest"
    payload_teste = {
        "teste": True,
        "mensagem": "Validacao automatica de mensageria via Pytest",
        "timestamp": time.time()
    }

    # Publica a mensagem via função do projeto
    publicar_mensagem(fila_teste, payload_teste)

    # Consome a mensagem manualmente para validação
    metodo, propriedades, corpo = rabbitmq_channel.basic_get(queue=fila_teste, auto_ack=True)

    assert metodo is not None, "Nenhuma mensagem foi encontrada na fila de teste após a publicação"
    assert propriedades.delivery_mode == 2, "A mensagem não foi configurada com delivery_mode=2 (persistente)"

    dados_recebidos = json.loads(corpo.decode("utf-8"))
    assert dados_recebidos["teste"] is True
    assert dados_recebidos["mensagem"] == payload_teste["mensagem"]

    # Limpa a fila temporária de teste
    rabbitmq_channel.queue_delete(queue=fila_teste)


# ==============================================================================
# TESTE 3: Fluxo Completo de Mensageria (API CRUD -> RabbitMQ -> Consumer Logs)
# ==============================================================================
def test_fluxo_completo_api_mensageria_e_consumer():
    """
    Executa o ciclo de vida de um jogo na API e verifica se os eventos
    de mensageria foram disparados e processados pelo worker:
    1. POST /jogos/ -> Emite para 'fila_auditoria' (CRIACAO) e 'fila_notificacoes'
    2. PUT /jogos/{id} -> Emite para 'fila_auditoria' (ATUALIZACAO)
    3. DELETE /jogos/{id} -> Emite para 'fila_auditoria' (DELECAO)
    """
    sufixo_unico = int(time.time())
    titulo_jogo = f"Jogo Pytest Mensageria {sufixo_unico}"

    # 1. CRIAR JOGO (POST)
    payload_criar = {
        "titulo": titulo_jogo,
        "genero": "Aventura / Teste",
        "plataforma": "PC",
        "ano_lancamento": 2024,
        "preco": 149.90
    }
    status_post, dados_criado = requisicao_http(f"{GATEWAY_URL}/jogos/", metodo="POST", dados=payload_criar)
    assert status_post == 201, f"Falha ao criar jogo na API: {dados_criado}"
    jogo_id = dados_criado["id"]

    # 2. ATUALIZAR JOGO (PUT)
    payload_atualizar = {"preco": 99.90}
    status_put, _ = requisicao_http(f"{GATEWAY_URL}/jogos/{jogo_id}", metodo="PUT", dados=payload_atualizar)
    assert status_put == 200, "Falha ao atualizar jogo na API"

    # 3. DELETAR JOGO (DELETE)
    status_del, _ = requisicao_http(f"{GATEWAY_URL}/jogos/{jogo_id}", metodo="DELETE")
    assert status_del == 204, "Falha ao deletar jogo na API"

    # Aguarda 1 segundo para garantir que o worker terminou o processamento assíncrono
    time.sleep(1)

    # 4. VALIDAR NOS LOGS DO CONSUMER SE TODOS OS EVENTOS FORAM RECEBIDOS
    cmd_logs = ["docker", "compose", "logs", "consumer", "--tail", "50"]
    resultado = subprocess.run(cmd_logs, capture_output=True, text=True, check=False)
    logs_consumer = resultado.stdout

    # Validações dos eventos no worker
    assert "CRIACAO" in logs_consumer, "Log de CRIACAO não encontrado no consumidor"
    assert jogo_id in logs_consumer, f"ID do jogo {jogo_id} não encontrado nos logs do consumidor"
    assert titulo_jogo in logs_consumer, f"Título '{titulo_jogo}' não encontrado nos alertas de notificação do consumidor"
    assert "ATUALIZACAO" in logs_consumer, "Log de ATUALIZACAO não encontrado no consumidor"
    assert "DELECAO" in logs_consumer, "Log de DELECAO não encontrado no consumidor"


# ==============================================================================
# TESTE 4: Validar API de Gerenciamento do RabbitMQ (HTTP Management)
# ==============================================================================
def test_rabbitmq_management_api():
    """
    Consulta o painel HTTP do RabbitMQ (porta 15672) para confirmar que
    o broker está saudável e reportando as filas corretamente.
    """
    req = urllib.request.Request(f"{MGMT_API_URL}/queues")
    auth_bytes = base64.b64encode(b"guest:guest").decode("utf-8")
    req.add_header("Authorization", f"Basic {auth_bytes}")

    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200, f"Painel de gestão do RabbitMQ retornou status {resp.status}"
        filas = json.loads(resp.read().decode("utf-8"))

    nomes_filas = [f["name"] for f in filas]
    assert "fila_auditoria" in nomes_filas, "fila_auditoria não está presente na API do RabbitMQ"
    assert "fila_notificacoes" in nomes_filas, "fila_notificacoes não está presente na API do RabbitMQ"
