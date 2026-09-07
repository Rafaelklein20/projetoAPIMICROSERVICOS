import time
import os
import urllib.request
import urllib.error
from collections import defaultdict

BASE_URL = "http://localhost"

def pedir_quantidade(mensagem: str, padrao: int = 30) -> int:
    """
    Permite ao usuário digitar interativamente a quantidade de requisições.
    Se pressionar ENTER sem digitar nada, utiliza o valor padrão.
    Também aceita a variável de ambiente REQS (ex: REQS=50 pytest -s ...).
    """
    if "REQS" in os.environ and os.environ["REQS"].isdigit():
        return int(os.environ["REQS"])
        
    try:
        entrada = input(f"\n[?] {mensagem} [Pressione ENTER para padrao {padrao}]: ").strip()
        if entrada.isdigit() and int(entrada) > 0:
            return int(entrada)
    except (EOFError, KeyboardInterrupt):
        pass
    return padrao


def test_rate_limit_e_distribuicao():
    """
    Dispara requisições em rajada rápida para testar:
    1. Quantas requisições foram aceitas (200 OK) por cada instância da API.
    2. Quantas foram negadas (429 Too Many Requests) pelo Rate Limit no Gateway.
    """
    total_requisicoes = pedir_quantidade(
        "Quantas requisicoes deseja disparar no teste de Rate Limit?",
        padrao=30
    )

    aceitas_por_instancia = defaultdict(int)
    negadas_gateway = 0

    print(f"\nDisparando {total_requisicoes} requisicoes em rajada...")

    for _ in range(total_requisicoes):
        req = urllib.request.Request(f"{BASE_URL}/")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    instancia = resp.headers.get("X-Upstream-Addr", "Instancia desconhecida")
                    aceitas_por_instancia[instancia] += 1
        except urllib.error.HTTPError as e:
            if e.code == 429:
                negadas_gateway += 1

    total_aceitas = sum(aceitas_por_instancia.values())

    print("\n" + "=" * 62)
    print("RELATORIO: RATE LIMIT & LOAD BALANCER EM RAJADA")
    print("=" * 62)
    print(f"Total de requisicoes disparadas: {total_requisicoes}\n")
    
    print("REQUISICOES ACEITAS (200 OK) POR CADA INSTANCIA:")
    if aceitas_por_instancia:
        for idx, (instancia, qtd) in enumerate(sorted(aceitas_por_instancia.items()), start=1):
            print(f"   - Instancia {idx} ({instancia}): {qtd} requisicoes")
    else:
        print("   - Nenhuma requisicao aceita")
    print(f"   Subtotal aceitas: {total_aceitas}\n")

    print("REQUISICOES NEGADAS (429 Too Many Requests):")
    print(f"   - Bloqueadas pelo Gateway (Nginx): {negadas_gateway} requisicoes")
    print("=" * 62)

    assert total_aceitas > 0, "Nenhuma requisicao foi aceita"
    if total_requisicoes > 15:
        assert negadas_gateway > 0, "O Rate Limit nao bloqueou requisicoes (esperava 429 para quantidade alta)"


def test_load_balancer_balanceamento():
    """
    Dispara requisições espaçadas para validar a distribuição equilibrada
    do Load Balancer sem sofrer bloqueio do Rate Limit.
    """
    time.sleep(2)  # Aguarda o burst do rate limit resetar

    total_requisicoes = pedir_quantidade(
        "Quantas requisicoes deseja disparar no teste do Load Balancer?",
        padrao=10
    )

    print(f"\nEnviando {total_requisicoes} requisicoes espacadas para o Load Balancer...")

    aceitas_por_instancia = defaultdict(int)

    for _ in range(total_requisicoes):
        req = urllib.request.Request(f"{BASE_URL}/")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    instancia = resp.headers.get("X-Upstream-Addr", "Instancia desconhecida")
                    aceitas_por_instancia[instancia] += 1
        except urllib.error.HTTPError:
            pass
        time.sleep(0.3)

    total_aceitas = sum(aceitas_por_instancia.values())

    print("\n" + "=" * 62)
    print("RELATORIO: DISTRIBUICAO DO LOAD BALANCER (SEM BLOQUEIOS)")
    print("=" * 62)
    print(f"Total de requisicoes enviadas: {total_requisicoes}")
    print(f"Total aceitas: {total_aceitas}\n")
    print("Divisao de carga entre as instancias:")
    for idx, (instancia, qtd) in enumerate(sorted(aceitas_por_instancia.items()), start=1):
        porcentagem = (qtd / total_aceitas) * 100 if total_aceitas > 0 else 0
        print(f"   - Instancia {idx} ({instancia}): {qtd} requisicoes ({porcentagem:.0f}%)")
    print("=" * 62)

    if total_requisicoes >= 4:
        assert len(aceitas_por_instancia) >= 2, "O trafego nao foi balanceado entre as instancias"


if __name__ == "__main__":
    print("\n=== Executando testes interativos do Gateway ===")
    test_rate_limit_e_distribuicao()
    test_load_balancer_balanceamento()
    print("\nBateria de testes concluida com sucesso!")
