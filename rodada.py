import random
import select
import socket
import time

from jogador import Jogador
from rede import enviar_mensagem, receber_mensagem


class Rodada:
    def __init__(
        self,
        host="127.0.0.1",
        porta=5000,
        saldo_inicial=100,
        custo_sala=20,
        premio_vitoria=20,
        intervalo_rodada=15,
        max_jogadores=10,
    ):
        # Define os limites e valores da sala.
        self.host = host
        self.porta = porta
        self.saldo_inicial = saldo_inicial
        self.custo_sala = custo_sala
        self.premio_vitoria = premio_vitoria
        self.intervalo_rodada = intervalo_rodada
        self.max_jogadores = max_jogadores

        # Guarda tudo que pertence ao servidor.
        self.contas = {}
        self.clientes = {}
        self.nicknames_conectados = set()
        self.proximo_id = 1
        self.numero_rodada = 1

    def normalizar(self, nickname):
        return nickname.strip().casefold()

    def obter_jogador(self, nickname):
        # Cria ou recupera a conta do jogador.
        nome = nickname.strip()
        chave = self.normalizar(nome)
        conta = self.contas.get(chave)

        if conta is None:
            self.contas[chave] = {"nome": nome, "saldo": self.saldo_inicial}
            return Jogador(nome, self.saldo_inicial), True

        return Jogador(conta["nome"], conta["saldo"]), False

    def salvar_jogador(self, jogador):
        # Mantem o saldo atualizado no servidor.
        chave = self.normalizar(jogador.getnome())
        self.contas[chave] = {
            "nome": jogador.getnome(),
            "saldo": max(0, jogador.getsaldo()),
        }

    def enviar(self, id_cliente, tipo, *campos):
        # Envia mensagem para o cliente.
        try:
            enviar_mensagem(self.clientes[id_cliente]["conexao"], tipo, *campos)
            return True
        except OSError:
            self.remover_cliente(id_cliente)
            return False

    def remover_cliente(self, id_cliente):
        # Tira o jogador da sala.
        cliente = self.clientes.pop(id_cliente, None)
        if cliente is None:
            return

        jogador = cliente["jogador"]
        self.nicknames_conectados.discard(self.normalizar(jogador.getnome()))

        try:
            cliente["conexao"].close()
        except OSError:
            pass

        print(f"{jogador.getnome()} saiu da sala.")

    def recusar(self, conexao, motivo):
        enviar_mensagem(conexao, "X", motivo)
        conexao.close()

    def aceitar_cliente(self, servidor):
        # Recebe um pedido de entrada.
        try:
            conexao, _ = servidor.accept()
        except TimeoutError:
            return

        try:
            campos = receber_mensagem(conexao)
        except (ConnectionError, OSError):
            conexao.close()
            return

        if len(campos) < 2 or campos[0] != "E":
            self.recusar(conexao, "Mensagem invalida")
            return

        nickname = campos[1].strip()
        chave = self.normalizar(nickname)

        if not chave:
            self.recusar(conexao, "Nickname invalido")
            return

        if chave in self.nicknames_conectados:
            self.recusar(conexao, "Esse nickname ja esta conectado")
            return

        if len(self.clientes) >= self.max_jogadores:
            self.recusar(conexao, "Sala cheia")
            return

        jogador, conta_nova = self.obter_jogador(nickname)
        if jogador.getsaldo() < self.custo_sala:
            self.recusar(conexao, "Voce nao tem moedas suficientes para entrar na sala")
            return

        id_cliente = self.proximo_id
        self.proximo_id += 1
        self.clientes[id_cliente] = {"conexao": conexao, "jogador": jogador}
        self.nicknames_conectados.add(chave)

        enviar_mensagem(conexao, "A", id_cliente, jogador.getsaldo())
        status = "Conta criada para" if conta_nova else "Conta recuperada para"
        print(f"{status} {jogador.getnome()} com {jogador.getsaldo()} moedas.")
        print(f"{jogador.getnome()} entrou na sala.")

    def ler_clientes(self):
        # Escuta pedidos de saida.
        if not self.clientes:
            return

        conexoes = [cliente["conexao"] for cliente in self.clientes.values()]
        prontas, _, _ = select.select(conexoes, [], [], 0)
        ids_por_conexao = {
            cliente["conexao"]: id_cliente
            for id_cliente, cliente in self.clientes.items()
        }

        for conexao in prontas:
            id_cliente = ids_por_conexao.get(conexao)
            if id_cliente is None:
                continue

            try:
                campos = receber_mensagem(conexao)
            except (ConnectionError, OSError):
                self.remover_cliente(id_cliente)
                continue

            if campos[0] == "S":
                self.enviar(id_cliente, "X", "Voce saiu da sala")
            else:
                self.enviar(id_cliente, "X", "Mensagem invalida")

            self.remover_cliente(id_cliente)

    def participantes(self):
        # Filtra quem consegue pagar a rodada.
        return [
            id_cliente
            for id_cliente, cliente in self.clientes.items()
            if cliente["jogador"].getsaldo() >= self.custo_sala
        ]

    def avisar_todos(self, mensagem):
        for id_cliente in list(self.clientes):
            self.enviar(id_cliente, "I", mensagem)

    def run(self):
        # Controla a sala aberta.
        print("\nServidor iniciado.")
        print(f"Sorteio a cada {self.intervalo_rodada} segundos.")
        print("O sorteio acontece com 2 ou mais jogadores aptos.")
        print("Abra os clientes em outros terminais.")
        print("Pressione Ctrl+C para encerrar o servidor.\n")

        proxima_rodada = time.monotonic() + self.intervalo_rodada

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
            servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            servidor.bind((self.host, self.porta))
            servidor.listen(self.max_jogadores)
            servidor.settimeout(1)

            try:
                while True:
                    self.aceitar_cliente(servidor)
                    self.ler_clientes()

                    if time.monotonic() >= proxima_rodada:
                        self.sortear()
                        proxima_rodada = time.monotonic() + self.intervalo_rodada
            except KeyboardInterrupt:
                print("\nServidor encerrado.")

        for id_cliente in list(self.clientes):
            self.remover_cliente(id_cliente)

    def sortear(self):
        # Controla as rodadas.
        participantes = self.participantes()

        if len(participantes) < 2:
            print("Rodada cancelada: aguardando 2 ou mais jogadores aptos.")
            self.avisar_todos("Aguardando 2 ou mais jogadores aptos")
            return

        print(f"\nRodada {self.numero_rodada}")
        resultados = {
            id_cliente: random.randint(1, 10)
            for id_cliente in participantes
        }

        for id_cliente, numero in resultados.items():
            self.enviar(id_cliente, "N", self.numero_rodada, numero)

        maior = max(resultados.values())
        vencedores = [
            self.clientes[id_cliente]["jogador"].getnome()
            for id_cliente, numero in resultados.items()
            if numero == maior
        ]

        print("maior valor:", maior)
        print("Vencedor(es):", ", ".join(vencedores))

        for id_cliente, numero in resultados.items():
            jogador = self.clientes[id_cliente]["jogador"]
            jogador.setmoedas(max(0, jogador.getsaldo() - self.custo_sala))
            resultado = "FIM"

            if numero == maior:
                resultado = "GANHOU"
                jogador.setmoedas(
                    jogador.getsaldo() + self.custo_sala + self.premio_vitoria
                )

            self.salvar_jogador(jogador)
            self.enviar(
                id_cliente,
                "R",
                self.numero_rodada,
                resultado,
                jogador.getsaldo(),
                maior,
                ", ".join(vencedores),
            )

        print("\nDinheiro atual:")
        for cliente in self.clientes.values():
            jogador = cliente["jogador"]
            print(jogador.getnome(), ":", jogador.getsaldo())

        self.numero_rodada += 1
