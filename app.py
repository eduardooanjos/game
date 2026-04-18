import os
import time
from threading import RLock

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from Comunicador import Comunicador
from jogador import Jogador
from rodada import Rodada

ROOM_TIMER_SECONDS, DRAW_TIMER_SECONDS = 30, 6
MIN_CAPACITY, MAX_CAPACITY, MIN_BET, MAX_BET = 2, 20, 1, 1000


# Encapsula o canal de mensagens usado pelo flash da interface.
class Mensageiro:
    def __init__(self, canal):
        self.a, self.b = Comunicador(canal), Comunicador(canal)

    def enviar(self, mensagem):
        self.a.enviarMensagem(mensagem)
        return self.b.receberMensagem()

# Centraliza jogadores, salas e transicoes da partida.
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

    # Valida a entrada e inicia o timer quando a sala recebe o primeiro jogador.
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

    # Impede saida durante o sorteio e nos segundos finais antes dele.
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

    # Executa o sorteio da rodada e remove jogadores zerados.
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

    # Move a sala entre espera, sorteio e resultado de acordo com os timers.
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

    # Reaproveita os dados da ultima rodada quando a sala ja exibiu o resultado.
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

    # Entrega ao admin a visao completa das salas e do ranking.
    def estado_admin(self):
        with self.lock:
            salas = [self.dados_sala(s, s["fase"] == "resultado") for s in self.salas.values()]
            return {"salas": sorted(salas, key=lambda s: s["id"]), "ranking": self.ranking()}

    # Entrega ao jogador as salas abertas, a sala atual e o ranking.
    def estado_jogador(self, nickname):
        with self.lock:
            atual = self.sala_do_jogador(nickname)
            ativas = [self.dados_sala(s) for s in self.salas.values() if s["ativa"]]
            return {"jogador": self.jogadores.get(nickname), "sala_atual": None if not atual else self.dados_sala(atual), "salas_ativas": ativas, "ranking": self.ranking()}

    # So permite abrir a sala para quem participa dela ou acabou de jogar nela.
    def estado_sala(self, sala_id, nickname):
        with self.lock:
            sala = self.salas.get(sala_id)
            if not sala or not sala["ativa"] or nickname not in sala["participantes"] + sala["ultimos"]:
                return None
            return {"jogador": self.jogadores.get(nickname), "sala": self.dados_sala(sala, sala["fase"] == "resultado")}


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "redes-local-secret")
servidor, mensageiro = ServidorApostas(), Mensageiro("sala-apostas-interface")


# Retorna o nickname salvo na sessao atual.
def nick():
    return session.get("nickname", "").strip()


# Identifica se a sessao atual pertence ao admin.
def admin():
    return nick().lower() == "admin"


# Encaminha mensagens para a interface sem acoplar as rotas ao comunicador.
def msg(texto, categoria):
    flash(mensageiro.enviar(texto), categoria)


# Redireciona cada perfil para sua pagina principal.
def destino():
    return redirect(url_for("painel_admin" if admin() else "painel_jogador"))


# Aproveita o host da requisicao para exibir o endereco de acesso.
def endereco():
    return request.host.split(":")[0].strip() or "127.0.0.1"











#================
#=====Rotas======
#================


@app.context_processor
def contexto():
    nome = nick()
    return {"ip_local": endereco(), "nickname_sessao": nome, "jogador_logado": servidor.jogador(nome) if nome else None, "usuario_admin": admin()}


@app.get("/")
def index():
    servidor.sincronizar()
    return render_template("login.html") if not nick() else destino()


@app.post("/login")
def login():
    nome = request.form.get("nickname", "").strip()
    if not nome:
        msg("Informe um nome para entrar no sistema.", "erro")
        return redirect(url_for("index"))
    session["nickname"] = nome
    if nome.lower() == "admin":
        msg("Acesso de administrador liberado.", "sucesso")
        return redirect(url_for("painel_admin"))
    criado = servidor.jogador(nome) is None
    jogador = servidor.jogador(nome, True)
    texto = f"Jogador {jogador.getnome()} cadastrado com {jogador.getsaldo()} moedas." if criado else f"Bem-vindo de volta, {jogador.getnome()}. Saldo carregado: {jogador.getsaldo()} moedas."
    msg(texto, "sucesso")
    return redirect(url_for("painel_jogador"))


@app.post("/logout")
def logout():
    session.pop("nickname", None)
    msg("Sessao encerrada neste navegador.", "sucesso")
    return redirect(url_for("index"))


@app.get("/admin")
def painel_admin():
    servidor.sincronizar()
    if not admin():
        msg("Apenas o admin pode acessar essa area.", "erro")
        return redirect(url_for("index"))
    return render_template("admin.html", estado=servidor.estado_admin())


@app.post("/admin/salas")
def criar_sala():
    if not admin():
        msg("Apenas o admin pode criar salas.", "erro")
        return redirect(url_for("index"))
    nome = request.form.get("nome", "").strip()
    if not nome:
        msg("Informe um nome para a sala.", "erro")
        return redirect(url_for("painel_admin"))
    try:
        capacidade, aposta = int(request.form.get("capacidade", 4)), int(request.form.get("aposta", 50))
    except ValueError:
        msg("Capacidade e aposta devem ser numeros inteiros.", "erro")
        return redirect(url_for("painel_admin"))
    if not MIN_CAPACITY <= capacidade <= MAX_CAPACITY:
        msg(f"A capacidade deve ficar entre {MIN_CAPACITY} e {MAX_CAPACITY} jogadores.", "erro")
        return redirect(url_for("painel_admin"))
    if not MIN_BET <= aposta <= MAX_BET:
        msg(f"A aposta deve ficar entre {MIN_BET} e {MAX_BET} moedas.", "erro")
        return redirect(url_for("painel_admin"))
    sala = servidor.criar_sala(nome, capacidade, aposta)
    msg(f"Sala {sala['nome']} criada com capacidade para {capacidade} jogadores e aposta de {aposta} moedas.", "sucesso")
    return redirect(url_for("painel_admin"))


@app.post("/admin/salas/<int:sala_id>/encerrar")
def encerrar_sala(sala_id):
    if not admin():
        msg("Apenas o admin pode encerrar salas.", "erro")
        return redirect(url_for("index"))
    ok, texto = servidor.encerrar(sala_id)
    msg(texto, "sucesso" if ok else "erro")
    return redirect(url_for("painel_admin"))


@app.get("/jogador")
def painel_jogador():
    servidor.sincronizar()
    if not nick():
        msg("Informe seu nome para continuar.", "erro")
        return redirect(url_for("index"))
    if admin():
        return redirect(url_for("painel_admin"))
    return render_template("player.html", estado=servidor.estado_jogador(nick()))


@app.post("/salas/<int:sala_id>/entrar")
def entrar_sala(sala_id):
    if not nick() or admin():
        msg("Somente jogadores podem entrar em salas.", "erro")
        return redirect(url_for("index"))
    ok, texto = servidor.entrar(sala_id, nick())
    msg(texto, "sucesso" if ok else "erro")
    return redirect(url_for("ver_sala", sala_id=sala_id) if ok else url_for("painel_jogador"))


@app.post("/salas/sair")
def sair_sala():
    if not nick() or admin():
        msg("Somente jogadores podem sair de salas.", "erro")
        return redirect(url_for("index"))
    ok, texto = servidor.sair(nick())
    msg(texto, "sucesso" if ok else "erro")
    return redirect(url_for("painel_jogador"))


@app.get("/salas/<int:sala_id>")
def ver_sala(sala_id):
    servidor.sincronizar()
    if not nick() or admin():
        msg("Somente jogadores podem acessar a sala.", "erro")
        return redirect(url_for("index"))
    estado = servidor.estado_sala(sala_id, nick())
    if not estado:
        msg("Essa sala nao esta disponivel para voce no momento.", "erro")
        return redirect(url_for("painel_jogador"))
    return render_template("room.html", estado=estado)


@app.get("/api/salas/<int:sala_id>/estado")
def api_estado_sala(sala_id):
    servidor.sincronizar()
    if not nick() or admin():
        return jsonify({"erro": "nao_autorizado"}), 403
    estado = servidor.estado_sala(sala_id, nick())
    return (jsonify({"erro": "sala_indisponivel"}), 404) if not estado else jsonify(estado["sala"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
