import time
import threading
from threading import RLock

from Comunicador import Comunicador
from jogador import Jogador
from rodada import Rodada

ROOM_TIMER_SECONDS, DRAW_TIMER_SECONDS = 30, 6
MIN_CAPACITY, MAX_CAPACITY, MIN_BET, MAX_BET = 2, 20, 1, 1000

class ServidorApostas:
    def __init__(self):
        self.jogadores, self.salas, self.proximo_id, self.lock = {}, {}, 1, RLock()

    def jogador(self, nickname, criar=False):
        with self.lock:
            if criar and nickname not in self.jogadores:
                self.jogadores[nickname] = Jogador(nickname)
            return self.jogadores.get(nickname)

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

    def entrar(self, sala_id, nickname):
        with self.lock:
            sala, jogador = self.salas.get(sala_id), self.jogador(nickname, True)
            atual = self.sala_do_jogador(nickname)
            if not sala or not sala["ativa"]:
                return False, "A sala escolhida nao esta mais disponivel."
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
                sala["fase"], sala["rodada"], sala["ultimos"] = "aguardando", None, []
            sala["participantes"].append(nickname)
            sala["timer"] = sala["timer"] or time.time()
            return True, f"Entrada confirmada na sala {sala['nome']}."

    def sair(self, nickname):
        with self.lock:
            sala = self.sala_do_jogador(nickname)
            restante = None if not sala else self.tempo(sala["timer"], ROOM_TIMER_SECONDS)
            if not sala:
                return False, "Voce nao esta em nenhuma sala."
            if sala["fase"] == "sorteando":
                return False, "O sorteio ja esta em andamento. Aguarde o resultado."
            if restante is not None and restante < 10:
                return False, "Nao e permitido sair da sala nos 10 segundos finais antes do sorteio."
            sala["participantes"].remove(nickname)
            if not sala["participantes"]:
                sala["fase"], sala["timer"] = "aguardando", None
            return True, f"Voce saiu da sala {sala['nome']}."

    def executar_rodada(self, sala):
        if len(sala["participantes"]) < 2:
            sala["fase"], sala["sorteio"], sala["timer"] = "aguardando", None, time.time() if sala["participantes"] else None
            return
        participantes = [self.jogadores[n] for n in sala["participantes"] if n in self.jogadores]
        resultado = Rodada(participantes, sala["aposta"]).executar()
        for eliminado in resultado["eliminados"]:
            self.jogadores.pop(eliminado, None)
        sala["rodada"], sala["ultimos"] = resultado, list(sala["participantes"])
        sala["participantes"], sala["timer"], sala["sorteio"], sala["fase"] = [], None, None, "resultado"

    def sincronizar(self):
        with self.lock:
            for sala in self.salas.values():
                if not sala["ativa"]:
                    continue
                if sala["fase"] == "aguardando" and sala["timer"] and self.tempo(sala["timer"], ROOM_TIMER_SECONDS) == 0:
                    if len(sala["participantes"]) >= 2:
                        sala["fase"], sala["sorteio"], sala["ultimos"] = "sorteando", time.time(), list(sala["participantes"])
                    else:
                        sala["timer"] = time.time()
                if sala["fase"] == "sorteando" and sala["sorteio"] and self.tempo(sala["sorteio"], DRAW_TIMER_SECONDS) == 0:
                    self.executar_rodada(sala)

    def encerrar(self, sala_id):
        with self.lock:
            sala = self.salas.get(sala_id)
            if not sala or not sala["ativa"]:
                return False, "A sala informada nao esta ativa."
            sala["ativa"], sala["participantes"], sala["ultimos"], sala["timer"], sala["sorteio"] = False, [], [], None, None
            return True, f"Sala {sala['nome']} encerrada."

    def participantes(self, sala, ultimos=False):
        if ultimos and sala["rodada"]:
            resultados = {i["nome"]: i["valor"] for i in sala["rodada"].get("resultados", [])}
            return [{"nome": s["nome"], "moedas": s["saldo"], "resultado": resultados.get(s["nome"], 0)} for s in sala["rodada"].get("saldos", [])]
        nomes = sala["ultimos"] if ultimos else sala["participantes"]
        return [self.jogadores[n].to_dict() for n in nomes if n in self.jogadores]

    def dados_sala(self, sala, ultimos=False):
        restante = self.tempo(sala["timer"], ROOM_TIMER_SECONDS)
        return {
            "id": sala["id"],
            "nome": sala["nome"],
            "capacidade": sala["capacidade"],
            "aposta": sala["aposta"],
            "ativa": sala["ativa"],
            "fase": sala["fase"],
            "participantes": self.participantes(sala, ultimos),
            "ultima_rodada": sala["rodada"],
            "tempo_restante": restante,
            "tempo_sorteio": self.tempo(sala["sorteio"], DRAW_TIMER_SECONDS),
            "pode_sair": sala["fase"] != "sorteando" and (restante is None or restante >= 10),
        }

    def estado_admin(self):
        with self.lock:
            salas = [self.dados_sala(s, s["fase"] == "resultado") for s in self.salas.values()]
            return {"salas": sorted(salas, key=lambda s: s["id"]), "ranking": self.ranking()}

    def estado_jogador(self, nickname):
        with self.lock:
            atual = self.sala_do_jogador(nickname)
            ativas = [self.dados_sala(s) for s in self.salas.values() if s["ativa"]]
            return {"jogador": self.jogadores.get(nickname), "sala_atual": None if not atual else self.dados_sala(atual), "salas_ativas": ativas, "ranking": self.ranking()}

    def estado_sala(self, sala_id, nickname):
        with self.lock:
            sala = self.salas.get(sala_id)
            if not sala or not sala["ativa"] or nickname not in sala["participantes"] + sala["ultimos"]:
                return None
            return {"jogador": self.jogadores.get(nickname), "sala": self.dados_sala(sala, sala["fase"] == "resultado")}

def handle_client(id, servidor):
    com = Comunicador(id)
    nick = None
    while True:
        try:
            msg = com.receberMensagem()
            parts = msg.split()
            if not parts:
                continue
            cmd = parts[0].lower()
            if cmd == "login":
                if len(parts) < 2:
                    response = "Usage: login <nickname>"
                else:
                    nick = parts[1]
                    jogador = servidor.jogador(nick, True)
                    response = f"Logged in as {nick}, saldo {jogador.getsaldo()}"
            elif cmd == "list":
                salas = [f"{s['id']}: {s['nome']} ({len(s['participantes'])}/{s['capacidade']}) aposta {s['aposta']}" for s in servidor.salas.values() if s["ativa"]]
                response = "\n".join(salas) if salas else "No active rooms"
            elif cmd == "create":
                if nick != "admin":
                    response = "Only admin can create rooms"
                elif len(parts) < 4:
                    response = "Usage: create <name> <capacity> <bet>"
                else:
                    try:
                        name, cap, bet = parts[1], int(parts[2]), int(parts[3])
                        if not (MIN_CAPACITY <= cap <= MAX_CAPACITY):
                            response = f"Capacity must be between {MIN_CAPACITY} and {MAX_CAPACITY}"
                        elif not (MIN_BET <= bet <= MAX_BET):
                            response = f"Bet must be between {MIN_BET} and {MAX_BET}"
                        else:
                            sala = servidor.criar_sala(name, cap, bet)
                            response = f"Room {sala['nome']} created with id {sala['id']}"
                    except ValueError:
                        response = "Capacity and bet must be numbers"
            elif cmd == "join":
                if not nick:
                    response = "Login first"
                elif len(parts) < 2:
                    response = "Usage: join <room_id>"
                else:
                    try:
                        room_id = int(parts[1])
                        ok, texto = servidor.entrar(room_id, nick)
                        response = texto
                    except ValueError:
                        response = "Room id must be a number"
            elif cmd == "leave":
                if not nick:
                    response = "Login first"
                else:
                    ok, texto = servidor.sair(nick)
                    response = texto
            elif cmd == "status":
                if not nick:
                    response = "Login first"
                else:
                    estado = servidor.estado_jogador(nick)
                    response = f"Player: {estado['jogador']}\nCurrent room: {estado['sala_atual']}\nActive rooms: {len(estado['salas_ativas'])}\nRanking: {estado['ranking'][:5]}"  # simple
            elif cmd == "close":
                if nick != "admin":
                    response = "Only admin can close rooms"
                elif len(parts) < 2:
                    response = "Usage: close <room_id>"
                else:
                    try:
                        room_id = int(parts[1])
                        ok, texto = servidor.encerrar(room_id)
                        response = texto
                    except ValueError:
                        response = "Room id must be a number"
            else:
                response = "Unknown command. Available: login, list, create, join, leave, status, close"
            com.enviarMensagem(response)
        except Exception as e:
            com.enviarMensagem(f"Error: {str(e)}")

if __name__ == "__main__":
    servidor = ServidorApostas()
    # Create some initial rooms for demo
    servidor.criar_sala("Sala1", 4, 10)
    servidor.criar_sala("Sala2", 3, 20)
    # Start sync thread
    def sync_loop():
        while True:
            servidor.sincronizar()
            time.sleep(1)
    threading.Thread(target=sync_loop, daemon=True).start()
    # Start client handlers
    for i in range(1, 5):  # up to 4 clients
        threading.Thread(target=handle_client, args=(f"client{i}", servidor), daemon=True).start()
    print("Server started. Clients can connect with ids client1 to client4")
    # Keep main thread alive
    while True:
        time.sleep(1)