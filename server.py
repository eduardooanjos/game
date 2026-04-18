import threading
import time
from threading import RLock

from Comunicador import ServidorComunicador
from jogador import Jogador
from rodada import Rodada

HOST = "127.0.0.1"
PORT = 6000
DRAW_TIMER_SECONDS = 2
MIN_CAPACITY, MAX_CAPACITY, MIN_BET, MAX_BET = 2, 20, 1, 1000


class ServidorApostas:
    def __init__(self):
        self.jogadores = {}
        self.salas = {}
        self.proximo_id = 1
        self.lock = RLock()
        self.clientes_conectados = set()
        self.criar_sala("Principal", 20, 10)

    def jogador(self, nickname, criar=False):
        with self.lock:
            if criar and nickname not in self.jogadores:
                self.jogadores[nickname] = Jogador(nickname)
            return self.jogadores.get(nickname)

    def registrar_conexao(self, nickname):
        with self.lock:
            if nickname in self.clientes_conectados:
                return False
            self.clientes_conectados.add(nickname)
            return True

    def desconectar(self, nickname):
        with self.lock:
            self.clientes_conectados.discard(nickname)
            sala = self.sala_do_jogador(nickname)
            if sala and nickname in sala["participantes"] and sala["fase"] != "sorteando":
                sala["participantes"].remove(nickname)
                if not sala["participantes"]:
                    sala["fase"] = "aguardando"
                    sala["timer"] = None

    def ranking(self):
        with self.lock:
            itens = sorted(self.jogadores.values(), key=lambda j: (-j.getsaldo(), j.getnome().lower()))
            return [j.to_dict() for j in itens]

    def sala_do_jogador(self, nickname):
        return next((s for s in self.salas.values() if nickname in s["participantes"]), None)

    def tempo(self, inicio, duracao):
        return None if inicio is None else max(0, duracao - int(time.time() - inicio))

    def criar_sala(self, nome, capacidade, aposta):
        with self.lock:
            sala = {
                "id": self.proximo_id,
                "nome": nome,
                "capacidade": capacidade,
                "aposta": aposta,
                "ativa": True,
                "fase": "aguardando",
                "participantes": [],
                "ultimos": [],
                "rodada": None,
                "timer": None,
                "sorteio": None,
            }
            self.salas[self.proximo_id] = sala
            self.proximo_id += 1
            return sala

    def listar_salas(self, detalhado=False):
        with self.lock:
            salas = []
            for sala in sorted(self.salas.values(), key=lambda item: item["id"]):
                if not sala["ativa"]:
                    continue
                resumo = f"{sala['id']}: {sala['nome']} ({len(sala['participantes'])}/{sala['capacidade']}) aposta {sala['aposta']}"
                if detalhado:
                    resumo += f" fase {sala['fase']}"
                salas.append(resumo)
            return salas

    def entrar(self, sala_id, nickname):
        with self.lock:
            sala = self.salas.get(sala_id)
            jogador = self.jogador(nickname, True)
            atual = self.sala_do_jogador(nickname)
            if not sala or not sala["ativa"]:
                return False, "A sala escolhida nao esta disponivel."
            if sala["fase"] == "sorteando":
                return False, "O sorteio desta sala ja esta em andamento."
            if atual and atual["id"] != sala_id:
                return False, f"Voce ja esta na sala {atual['nome']}."
            if nickname in sala["participantes"]:
                return False, "Voce ja entrou nesta sala."
            if len(sala["participantes"]) >= sala["capacidade"]:
                return False, "A sala esta lotada."
            if jogador.getsaldo() < sala["aposta"]:
                return False, "Saldo insuficiente para cobrir a aposta desta sala."
            if sala["fase"] == "resultado":
                sala["fase"] = "aguardando"
                sala["rodada"] = None
                sala["ultimos"] = []
            sala["participantes"].append(nickname)
            sala["timer"] = sala["timer"] or time.time()
            return True, f"Entrada confirmada na sala {sala['nome']}."

    def sair(self, nickname):
        with self.lock:
            sala = self.sala_do_jogador(nickname)
            if not sala:
                return False, "Voce nao esta em nenhuma sala."
            if sala["fase"] == "sorteando":
                return False, "O sorteio ja esta em andamento. Aguarde o resultado."
            sala["participantes"].remove(nickname)
            if not sala["participantes"]:
                sala["fase"] = "aguardando"
                sala["timer"] = None
            return True, f"Voce saiu da sala {sala['nome']}."

    def executar_rodada(self, sala):
        if len(sala["participantes"]) < 2:
            sala["fase"] = "aguardando"
            sala["sorteio"] = None
            sala["timer"] = time.time() if sala["participantes"] else None
            return

        participantes = [self.jogadores[nome] for nome in sala["participantes"] if nome in self.jogadores]
        resultado = Rodada(participantes, sala["aposta"]).executar()
        for eliminado in resultado["eliminados"]:
            self.jogadores.pop(eliminado, None)
            self.clientes_conectados.discard(eliminado)
        sala["rodada"] = resultado
        sala["ultimos"] = list(sala["participantes"])
        sala["participantes"] = []
        sala["timer"] = None
        sala["sorteio"] = None
        sala["fase"] = "resultado"

        vencedor = resultado["resultados"][0]
        print(
            f"Resultado da sala {sala['nome']}: vencedor {vencedor['nome']} "
            f"com valor {vencedor['valor']}"
        )

    def sincronizar(self):
        with self.lock:
            for sala in self.salas.values():
                if not sala["ativa"]:
                    continue
                if sala["fase"] == "sorteando" and sala["sorteio"] and self.tempo(sala["sorteio"], DRAW_TIMER_SECONDS) == 0:
                    self.executar_rodada(sala)

    def iniciar_sorteio(self, sala_id=1):
        with self.lock:
            sala = self.salas.get(sala_id)
            if not sala or not sala["ativa"]:
                return False, "Sala nao encontrada ou inativa."
            if sala["fase"] != "aguardando":
                return False, "Sorteio ja iniciado ou em andamento."
            if len(sala["participantes"]) < 2:
                return False, "Precisa de pelo menos 2 participantes."
            sala["fase"] = "sorteando"
            sala["sorteio"] = time.time()
            sala["ultimos"] = list(sala["participantes"])
            return True, f"Sorteio iniciado na sala {sala['nome']}."

    def participantes(self, sala, ultimos=False):
        if ultimos and sala["rodada"]:
            resultados = {item["nome"]: item["valor"] for item in sala["rodada"].get("resultados", [])}
            return [
                {"nome": saldo["nome"], "saldo": saldo["saldo"], "resultado": resultados.get(saldo["nome"], 0)}
                for saldo in sala["rodada"].get("saldos", [])
            ]
        nomes = sala["ultimos"] if ultimos else sala["participantes"]
        return [self.jogadores[nome].to_dict() for nome in nomes if nome in self.jogadores]

    def dados_sala(self, sala, ultimos=False):
        return {
            "id": sala["id"],
            "nome": sala["nome"],
            "capacidade": sala["capacidade"],
            "aposta": sala["aposta"],
            "ativa": sala["ativa"],
            "fase": sala["fase"],
            "participantes": self.participantes(sala, ultimos),
            "ultima_rodada": sala["rodada"],
            "pode_sair": sala["fase"] != "sorteando",
        }

    def estado_admin(self):
        with self.lock:
            salas = [self.dados_sala(sala, sala["fase"] == "resultado") for sala in self.salas.values()]
            return {"salas": sorted(salas, key=lambda sala: sala["id"]), "ranking": self.ranking()}


def handle_client(client_id, servidor, com):
    nick = client_id
    servidor.jogador(nick, True)
    try:
        while True:
            msg = com.receberMensagem()
            parts = msg.split()
            if not parts:
                continue
            cmd = parts[0].lower()
            if cmd == "login":
                response = f"O id '{nick}' ja e o login da conexao."
            elif cmd == "list":
                salas = servidor.listar_salas(detalhado=True)
                response = "\n".join(salas) if salas else "Nenhuma sala ativa."
            elif cmd == "join":
                if len(parts) != 1:
                    response = "Uso: join"
                else:
                    _, response = servidor.entrar(1, nick)
            elif cmd == "balance":
                jogador = servidor.jogador(nick, criar=False)
                response = (
                    f"Jogador: {jogador.getnome()}\nSaldo: {jogador.getsaldo()}"
                    if jogador
                    else "Jogador nao encontrado."
                )
            else:
                response = "Comando desconhecido. Disponiveis: list, join, balance"
            com.enviarMensagem(response)
    except ConnectionError:
        pass
    except Exception as erro:
        try:
            com.enviarMensagem(f"Erro: {erro}")
        except Exception:
            pass
    finally:
        servidor.desconectar(nick)
        com.fechar()


def print_server_help():
    print("Comandos do servidor:")
    print("  list")
    print("  start")
    print("  status")
    print("  exit")


def accept_loop(servidor):
    listener = ServidorComunicador(HOST, PORT)
    print(f"Servidor ouvindo em {HOST}:{PORT}")
    try:
        while True:
            com, _addr = listener.aceitar()
            try:
                client_id = com.receberMensagem().strip()
                if not client_id:
                    com.enviarMensagem("ID invalido. Fechando.")
                    com.fechar()
                    continue
                if not servidor.registrar_conexao(client_id):
                    com.enviarMensagem(f"O id '{client_id}' ja esta conectado.")
                    com.fechar()
                    continue
                threading.Thread(target=handle_client, args=(client_id, servidor, com), daemon=True).start()
            except Exception as erro:
                try:
                    com.enviarMensagem(f"Erro: {erro}")
                except Exception:
                    pass
                com.fechar()
    finally:
        listener.fechar()


if __name__ == "__main__":
    servidor = ServidorApostas()

    def sync_loop():
        while True:
            servidor.sincronizar()
            time.sleep(1)

    threading.Thread(target=sync_loop, daemon=True).start()
    threading.Thread(target=accept_loop, args=(servidor,), daemon=True).start()

    print(f"Servidor iniciado em {HOST}:{PORT}.")
    print("A camada de rede fica centralizada em Comunicador.py.")
    print_server_help()

    while True:
        try:
            cmd = input("Comando do servidor: ").strip()
            if not cmd:
                continue
            parts = cmd.split()
            action = parts[0].lower()
            if action == "list":
                salas = servidor.listar_salas(detalhado=True)
                print("Salas ativas:" if salas else "Nenhuma sala ativa")
                if salas:
                    print("\n".join(salas))
            elif action == "start":
                if len(parts) > 1:
                    print("Uso: start")
                    continue
                _, texto = servidor.iniciar_sorteio(1)
                print(texto)
            elif action == "status":
                estado = servidor.estado_admin()
                print("Salas:")
                for sala in estado["salas"]:
                    print(
                        f"{sala['id']}: {sala['nome']} - fase {sala['fase']} - "
                        f"participantes {len(sala['participantes'])}/{sala['capacidade']}"
                    )
                print("Ranking:")
                for posicao, ranking in enumerate(estado["ranking"][:10], 1):
                    print(f"{posicao}. {ranking['nome']} - {ranking['saldo']}")
            elif action == "exit":
                print("Servidor finalizando.")
                break
            else:
                print("Comando desconhecido.")
                print_server_help()
        except KeyboardInterrupt:
            print("\nServidor finalizando.")
            break
        except EOFError:
            print("\nServidor finalizando.")
            break
