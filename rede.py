# Protocolo compartilhado pelo cliente, servidor e monitor de rede.

import socket

TAMANHO_CABECALHO = 2
SEPARADOR = "#"
ENCODING = "UTF-8"
HOST_LOG = "127.0.0.1"
PORTA_LOG = 5001


def endereco(socket_conexao):
    # Ajuda o monitor a identificar de onde a mensagem veio.
    try:
        return f"{socket_conexao.getpeername()[0]}:{socket_conexao.getpeername()[1]}"
    except OSError:
        return "desconectado"


def log_rede(acao, socket_conexao, mensagem):
    # Logs seguem para o monitor em rede.py, sem poluir cliente e servidor.
    texto = f"[REDE] {acao} {endereco(socket_conexao)} -> {mensagem}"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as logger:
            logger.sendto(texto.encode(ENCODING), (HOST_LOG, PORTA_LOG))
    except OSError:
        pass


def enviar_mensagem(socket_conexao, tipo, *campos):
    # Mensagem do jogo: TIPO#campo1#campo2...
    partes = [tipo, *[str(campo) for campo in campos]]

    # O separador pertence ao protocolo.
    if any(SEPARADOR in parte for parte in partes):
        raise ValueError("Campos da mensagem nao podem conter #")

    mensagem = SEPARADOR.join(partes)
    dados = mensagem.encode(ENCODING)

    socket_conexao.sendall(len(dados).to_bytes(TAMANHO_CABECALHO, "big") + dados)
    log_rede("ENVIADO para", socket_conexao, mensagem)


def receber_tudo(socket_conexao, tamanho):
    # Garante que o pacote chegue inteiro antes de continuar.
    dados = b""

    while len(dados) < tamanho:
        parte = socket_conexao.recv(tamanho - len(dados))
        if not parte:
            raise ConnectionError("Conexao encerrada")
        dados += parte

    return dados


def receber_mensagem(socket_conexao):
    # O cabecalho informa quantos bytes formam a mensagem.
    tamanho_bytes = receber_tudo(socket_conexao, TAMANHO_CABECALHO)
    tamanho = int.from_bytes(tamanho_bytes, "big")

    dados = receber_tudo(socket_conexao, tamanho)
    mensagem = dados.decode(ENCODING)
    log_rede("RECEBIDO de", socket_conexao, mensagem)

    return mensagem.split(SEPARADOR)


def main():
    # Terminal dedicado para acompanhar a conversa de rede.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as monitor:
        monitor.bind((HOST_LOG, PORTA_LOG))
        print(f"Monitor de rede ouvindo em {HOST_LOG}:{PORTA_LOG}")
        print("Execute main.py e cliente.py em outros terminais.\n")

        while True:
            dados, _ = monitor.recvfrom(4096)
            print(dados.decode(ENCODING))


if __name__ == "__main__":
    main()
