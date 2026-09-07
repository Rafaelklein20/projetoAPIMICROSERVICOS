# API Microservicos - Catalogo de Jogos

Microsservico RESTful para gerenciamento de catalogo de jogos construido com **FastAPI**, **MongoDB**, **RabbitMQ** (Mensageria assíncrona com 2 filas) e **Nginx** (API Gateway com **Load Balancer** e **Rate Limiting**), orquestrado via **Docker Compose**.

```text
[ Cliente / Navegador ]
          │
          ▼ (Porta 80 / HTTP)
[ API Gateway (Nginx) ]
  ├─── (Load Balancer & Rate Limit) ───► [ Instancia 1 (api1:8000) ] ──┬──► [ MongoDB:27017 ]
  └─── (Load Balancer & Rate Limit) ───► [ Instancia 2 (api2:8000) ] ──┤
                                                                       └──► [ RabbitMQ:5672 ]
                                                                                   │
                                                                   ┌───────────────┴───────────────┐
                                                                   ▼                               ▼
                                                        [ Fila: fila_auditoria ]       [ Fila: fila_notificacoes ]
                                                                   └───────────────┬───────────────┘
                                                                                   ▼
                                                                       [ Consumer / Worker ]
```

---

## Estrutura de Pastas

```text
projetoAPIMICROSERVICOS/
├── app/                      # Codigo-fonte da aplicacao FastAPI
│   ├── routers/jogos.py      # Controller/Rotas do CRUD (/jogos)
│   ├── db.py                 # Conexao assincrona com o MongoDB
│   ├── models.py             # Operacoes de banco de dados
│   ├── schemas.py            # Validacoes e serializacao (Pydantic)
│   ├── errors.py             # Excecoes customizadas
│   ├── error_handlers.py     # Tratamento global de erros da API
│   ├── producer.py           # Produtor de mensagens assincronas (RabbitMQ)
│   ├── requirements.txt      # Dependencias Python da aplicacao
│   ├── dockerfile            # Imagem Docker da API
│   └── main.py               # Ponto de entrada da aplicacao
├── gateway/                  # API Gateway
│   ├── dockerfile            # Dockerfile do Nginx
│   └── nginx.conf            # Proxy reverso, Rate Limit e Load Balancer
├── mongodb/                  # Banco de dados
│   └── dockerfile            # Imagem do MongoDB 7.0
├── rabbitmq/                 # Mensageria
│   └── dockerfile            # Imagem do RabbitMQ com painel de gestao
├── consumer/                 # Servico Consumidor (Worker em background)
│   ├── dockerfile            # Dockerfile do worker
│   ├── requirements.txt      # Dependencias do consumidor (pika)
│   └── worker.py             # Processador de mensagens das 2 filas
├── tests/                    # Suite de testes automatizados
│   └── test_gateway.py       # Testes de Rate Limit e Load Balancer
├── docker-compose.yml        # Orquestrador multi-container com healthchecks
└── README.md                 # Documentacao do projeto
```

---

## Ambiente Python & Instalacao do Pytest

Para executar os testes automatizados ou rodar scripts fora do Docker:

### 1. Instalar suporte ao Python e venv (se necessario):

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
```

### 2. Criar e ativar o ambiente virtual (venv):

```bash
# Cria o ambiente virtual na pasta venv
python3 -m venv venv

# Ativa o ambiente virtual
source venv/bin/activate
```

> **Nota:** Para desativar o ambiente virtual quando terminar, basta digitar `deactivate`.

### 3. Instalar o Pytest:

Com a `venv` ativada, instale o framework de testes:

```bash
pip install pytest
```

---

## Como Executar o Projeto (Docker Compose)

O projeto sobe 6 conteineres (`mongodb`, `rabbitmq`, `api1`, `api2`, `consumer` e `gateway`) com **healthchecks** automaticos:

```bash
# Construir as imagens e iniciar todos os servicos em segundo plano
docker compose up --build -d

# Acompanhar logs em tempo real de todos os servicos
docker compose logs -f

# Acompanhar apenas o processamento das mensagens no Worker/Consumer
docker compose logs -f consumer

# Parar todos os servicos
docker compose down
```

### Enderecos dos Servicos:

- **API Gateway (Nginx):** `http://localhost` (Porta 80)
- **Documentacao Swagger UI:** `http://localhost/docs`
- **Painel de Gestao RabbitMQ:** `http://localhost:15672` (login: `guest`, senha: `guest`)
- **Porta AMQP RabbitMQ:** `localhost:5672`
- **MongoDB:** `localhost:27017`


---

## Rotas da API

| Metodo | Endpoint | Descricao | Status Sucesso |
|---|---|---|---|
| `GET` | `/` | Healthcheck da API | `200 OK` |
| `GET` | `/jogos` | Listar todos os jogos | `200 OK` |
| `POST` | `/jogos` | Cadastrar novo jogo | `201 Created` |
| `GET` | `/jogos/{id}` | Buscar jogo por ID | `200 OK` |
| `PUT` | `/jogos/{id}` | Atualizar dados de um jogo | `200 OK` |
| `DELETE` | `/jogos/{id}` | Remover um jogo do catalogo | `204 No Content` |

---

## Como Fazer os Testes

### 1. Teste Interativo pelo Navegador (Swagger / Docs)

Com os conteineres ligados, abra no navegador:  
**http://localhost/docs**

**Passo a passo para testar uma rota:**

1. Clique no endpoint desejado (exemplo: `POST /jogos/`).
2. Clique no botao **"Try it out"** no canto superior direito do bloco.
3. No campo do JSON de exemplo, insira os dados do jogo:

```json
{
  "titulo": "God of War Ragnarok",
  "genero": "Acao / Aventura",
  "plataforma": "PlayStation",
  "ano_lancamento": 2022,
  "preco": 299.90
}
```

4. Clique no botao azul **"Execute"**.
5. Role ate **"Responses"** e veja o codigo **`201`** com o ID gerado pelo MongoDB!

---

### 2. Testes via Terminal com cURL (Localhost)

Voce tambem pode testar diretamente pela porta 80 do Gateway via linha de comando:

**Verificar status da API:**

```bash
curl -i http://localhost/
```

**Criar um jogo:**

```bash
curl -i -X POST http://localhost/jogos/ \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Elden Ring",
    "genero": "RPG",
    "plataforma": "PC / Console",
    "ano_lancamento": 2022,
    "preco": 249.90
  }'
```

**Listar jogos cadastrados:**

```bash
curl -i http://localhost/jogos/
```

---

### 3. Testes Automatizados (Interativos)

Criamos testes no arquivo `tests/test_gateway.py` que **perguntam ao usuario quantas requisicoes deseja disparar** no terminal:

1. **Rate Limit:** Dispara a quantidade escolhida em rajada e verifica o bloqueio com **`429 Too Many Requests`**.
2. **Load Balancer:** Dispara requisicoes espacadas e exibe o relatorio de divisao de carga entre **`api1`** e **`api2`**.

**Como executar (qualquer uma das opcoes):**

```bash
# Opcao A: Via Pytest (com a flag -s para permitir digitacao no terminal)
pytest -v -s tests/test_gateway.py

# Opcao B: Direto via Python
python3 tests/test_gateway.py
```

> **Dica:** Se voce apenas pressionar **ENTER** no terminal, o teste usara automaticamente os valores padroes recomendados (30 no Rate Limit e 10 no Load Balancer).

**Exemplo de saida do teste:**

```text
tests/test_gateway.py::test_rate_limit_e_distribuicao 
==============================================================
RELATORIO: RATE LIMIT & LOAD BALANCER EM RAJADA
==============================================================
Total de requisicoes disparadas: 30

REQUISICOES ACEITAS (200 OK) POR CADA INSTANCIA:
   - Instancia 1 (172.18.0.3:8000): 5 requisicoes
   - Instancia 2 (172.18.0.4:8000): 6 requisicoes
   Subtotal aceitas: 11

REQUISICOES NEGADAS (429 Too Many Requests):
   - Bloqueadas pelo Gateway (Nginx): 19 requisicoes
==============================================================
PASSED

tests/test_gateway.py::test_load_balancer_balanceamento 
==============================================================
RELATORIO: DISTRIBUICAO DO LOAD BALANCER (SEM BLOQUEIOS)
==============================================================
Total de requisicoes enviadas: 10
Total aceitas: 10

Divisao de carga entre as instancias:
   - Instancia 1 (172.18.0.3:8000): 5 requisicoes (50%)
   - Instancia 2 (172.18.0.4:8000): 5 requisicoes (50%)
==============================================================
PASSED
```

---

### 4. Testes Automatizados de Mensageria (Pytest)

Criamos uma suite completa de testes em `tests/test_messaging.py` que valida a mensageria assíncrona:

1. **`test_filas_existem_e_possuem_consumidores`**: Valida a existência das filas `fila_auditoria` e `fila_notificacoes` e confirma que o contêiner `worker_consumer` está conectado escutando-as.
2. **`test_producer_publicacao_direta_persistente`**: Testa o envio de mensagens pelo `publicar_mensagem` comprovando a persistência (`delivery_mode=2`).
3. **`test_fluxo_completo_api_mensageria_e_consumer`**: Executa um ciclo completo de vida (POST -> PUT -> DELETE) via Gateway e valida se o Worker consumiu e logou cada evento correspondente.
4. **`test_rabbitmq_management_api`**: Consulta a API HTTP do painel do RabbitMQ (porta 15672) verificando a saúde do broker.

**Como executar:**

```bash
pytest -v tests/test_messaging.py
```

