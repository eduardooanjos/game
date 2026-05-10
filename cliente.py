import msvcrt
import select
import socket
import time

from rede import enviar_mensagem, receber_mensagem


# Servidor local.
HOST = "127.0.0.1"
PORTA = 5000


class Cliente:
    def __init__(self, nome, host=HOST, porta=PORTA):
        self.nome = nome
        self.host = host
        self.porta = porta
        self.conexao = None

    def conectar(self):
        # Permite abrir o cliente antes ou depois do servidor.
        while True:
            try:
                self.conexao = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conexao.connect((self.host, self.porta))
                return
            except ConnectionRefusedError:
                print("Servidor indisponivel. Tentando novamente...")
                time.sleep(1)

    def run(self):
        # Depois de entrar, o cliente fica preso ao servidor ate sair ou cair.
        self.conectar()

        try:
            enviar_mensagem(self.conexao, "E", self.nome)
            self.receber_confirmacao_entrada()
            self.escutar_servidor()
        finally:
            self.conexao.close()

    def receber_confirmacao_entrada(self):
        # A entrada pode ser aceita ou recusada pelo servidor.
        campos = receber_mensagem(self.conexao)

        if campos[0] == "X":
            print(campos[1])
            raise SystemExit

        if campos[0] != "A":
            raise ValueError("Mensagem de tipo inesperado")

        print(f"{self.nome} entrou na sala")
        print(f"ID: {campos[1]}")
        print(f"Saldo inicial: {campos[2]}")
        print("Aguardando sorteios...")
        print("Pressione s para sair da sala.")

    def usuario_pediu_saida(self):
        # Leitura de tecla sem bloquear as mensagens que chegam pela rede.
        if not msvcrt.kbhit():
            return False

        tecla = msvcrt.getwch().lower()
        return tecla == "s"

    def escutar_servidor(self):
        # Mantem o terminal vivo entre uma rodada e outra.
        while True:
            if self.usuario_pediu_saida():
                enviar_mensagem(self.conexao, "S")
                print("Pedido de saida enviado ao servidor.")

            try:
                pronto, _, _ = select.select([self.conexao], [], [], 0.2)
            except ConnectionError:
                print("Conexao com o servidor encerrada.")
                return

            if not pronto:
                continue

            try:
                campos = receber_mensagem(self.conexao)
            except ConnectionError:
                print("Conexao com o servidor encerrada.")
                return

            tipo = campos[0]

            if tipo == "I":
                print(campos[1])
            elif tipo == "N":
                print(f"\nRodada {campos[1]}")
                print(f"{self.nome} tirou: {campos[2]}")
            elif tipo == "R":
                self.mostrar_resultado(campos)
            elif tipo == "X":
                print(campos[1])
                return
            else:
                raise ValueError("Mensagem de tipo inesperado")

    def mostrar_resultado(self, campos):
        # Resumo final da rodada enviado pelo servidor.
        rodada = campos[1]
        resultado = campos[2]
        saldo = campos[3]
        maior = campos[4]
        vencedores = campos[5]

        print(f"Resultado da rodada {rodada}: {resultado}")
        print(f"Maior numero: {maior}")
        print(f"Vencedor(es): {vencedores}")
        print(f"Seu saldo atual: {saldo}")
        print("Aguardando proximo sorteio...")


def main():
    nome = input("Nickname: ").strip()
    if not nome:
        print("Digite um nickname valido.")
        return

    # O protocolo usa # como separador interno.
    if "#" in nome:
        print("O nickname nao pode conter #.")
        return

    Cliente(nome).run()


if __name__ == "__main__":
    main()
