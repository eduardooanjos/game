import os
import socket
import time
from threading import RLock

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from jogador import Jogador
from rodada import Rodada


# Define os limites usados pelo fluxo principal das salas.
ROOM_TIMER_SECONDS = 30
DRAW_TIMER_SECONDS = 6
MIN_CAPACITY = 2
MAX_CAPACITY = 20
MIN_BET = 1
MAX_BET = 1000


# Centraliza jogadores, salas e transicoes do jogo.
class ServidorApostas:
    def __init__(self):
        # Guarda os jogadores cadastrados pelo nickname.
        self.jogadores = {}
        # Armazena as salas criadas pelo admin.
        self.salas = {}
        # Controla o identificador da proxima sala.
        self.proximo_id_sala = 1
        # Evita conflitos ao atualizar o estado em paralelo.
        self.lock = RLock()

    # Retorna um jogador existente ou cria um novo com saldo inicial.
    def obter_ou_criar_jogador(self, nickname):
        with self.lock:
            jogador = self.jogadores.get(nickname)
            criado = jogador is None
            if criado:
                jogador = Jogador(nickname)
                self.jogadores[nickname] = jogador
            return jogador, criado

    # Busca um jogador ja cadastrado.
    def obter_jogador(self, nickname):
        with self.lock:
            return self.jogadores.get(nickname)

    # Monta o ranking geral em ordem decrescente de saldo.
    def ranking(self):
        with self.lock:
            jogadores = sorted(
                self.jogadores.values(),
                key=lambda jogador: (-jogador.getsaldo(), jogador.getnome().lower()),
            )
            return [jogador.to_dict() for jogador in jogadores]

    # Cria uma nova sala com a configuracao basica.
    def criar_sala(self, nome, capacidade, aposta):
        with self.lock:
            sala = {
                "id": self.proximo_id_sala,
                "nome": nome,
                "capacidade": capacidade,
                "aposta": aposta,
                "ativa": True,
                "fase": "aguardando",
                "participantes": [],
                "ultimos_participantes": [],
                "ultima_rodada": None,
                "timer_inicio": None,
                "sortear_inicio": None,
            }
            self.salas[sala["id"]] = sala
            self.proximo_id_sala += 1
            return sala

    # Lista apenas as salas que continuam abertas.
    def listar_salas_ativas(self):
        with self.lock:
            return [sala for sala in self.salas.values() if sala["ativa"]]

    # Descobre em qual sala um jogador esta no momento.
    def localizar_sala_do_jogador(self, nickname):
        with self.lock:
            return self._localizar_sala_do_jogador(nickname)

    # Faz a busca interna pela sala atual do jogador.
    def _localizar_sala_do_jogador(self, nickname):
        for sala in self.salas.values():
            if nickname in sala["participantes"]:
                return sala
        return None

    # Calcula o tempo restante de um contador qualquer.
    def _tempo_restante(self, inicio, duracao):
        if inicio is None:
            return None
        return max(0, duracao - int(time.time() - inicio))

    # Calcula o tempo restante ate o sorteio da sala.
    def _tempo_restante_sala(self, sala):
        return self._tempo_restante(sala["timer_inicio"], ROOM_TIMER_SECONDS)

    # Calcula o tempo restante da animacao de sorteio.
    def _tempo_restante_sorteio(self, sala):
        return self._tempo_restante(sala["sortear_inicio"], DRAW_TIMER_SECONDS)

    # Reinicia a sala para a fase de espera.
    def _reiniciar_espera(self, sala):
        sala["fase"] = "aguardando"
        sala["sortear_inicio"] = None
        sala["timer_inicio"] = time.time() if sala["participantes"] else None

    # Valida e registra a entrada do jogador em uma sala.
    def entrar_na_sala(self, sala_id, nickname):
        with self.lock:
            sala = self.salas.get(sala_id)
            jogador, _ = self.obter_ou_criar_jogador(nickname)

            if sala is None or not sala["ativa"]:
                return False, "A sala escolhida nao esta mais disponivel."
            if sala["fase"] == "sorteando":
                return False, "O sorteio desta sala ja esta em andamento."

            sala_atual = self._localizar_sala_do_jogador(nickname)
            if sala_atual and sala_atual["id"] != sala_id:
                return False, f"Voce ja esta na sala {sala_atual['nome']}."
            if nickname in sala["participantes"]:
                return False, "Voce ja entrou nesta sala."
            if len(sala["participantes"]) >= sala["capacidade"]:
                return False, "A sala esta lotada."
            if jogador.getsaldo() < sala["aposta"]:
                return False, "Saldo insuficiente para cobrir a aposta desta sala."

            if sala["fase"] == "resultado":
                sala["ultima_rodada"] = None
                sala["ultimos_participantes"] = []
                sala["fase"] = "aguardando"

            sala["participantes"].append(nickname)
            if len(sala["participantes"]) == 1:
                sala["timer_inicio"] = time.time()

            return True, f"Entrada confirmada na sala {sala['nome']}."

    # Remove o jogador da sala respeitando as travas do sorteio.
    def sair_da_sala(self, nickname):
        with self.lock:
            sala = self._localizar_sala_do_jogador(nickname)
            if sala is None:
                return False, "Voce nao esta em nenhuma sala."
            if sala["fase"] == "sorteando":
                return False, "O sorteio ja esta em andamento. Aguarde o resultado."

            tempo_restante = self._tempo_restante_sala(sala)
            if tempo_restante is not None and tempo_restante < 10:
                return False, "Nao e permitido sair da sala nos 10 segundos finais antes do sorteio."

            sala["participantes"].remove(nickname)
            if not sala["participantes"]:
                sala["timer_inicio"] = None
                sala["fase"] = "aguardando"

            return True, f"Voce saiu da sala {sala['nome']}."

    # Atualiza todas as salas entre espera, sorteio e resultado.
    def sincronizar_temporizadores(self):
        with self.lock:
            for sala in self.salas.values():
                if not sala["ativa"]:
                    continue

                if sala["fase"] == "aguardando" and sala["timer_inicio"] is not None:
                    if self._tempo_restante_sala(sala) == 0:
                        if len(sala["participantes"]) >= 2:
                            sala["fase"] = "sorteando"
                            sala["sortear_inicio"] = time.time()
                            sala["ultimos_participantes"] = list(sala["participantes"])
                        else:
                            sala["timer_inicio"] = time.time()

                if sala["fase"] == "sorteando" and sala["sortear_inicio"] is not None:
                    if self._tempo_restante_sorteio(sala) == 0:
                        self._executar_rodada(sala)

    # Executa a rodada e salva o resultado final da sala.
    def _executar_rodada(self, sala):
        if len(sala["participantes"]) < 2:
            self._reiniciar_espera(sala)
            return False

        participantes = [
            self.jogadores[nickname]
            for nickname in sala["participantes"]
            if nickname in self.jogadores
        ]
        resultado = Rodada(participantes, sala["aposta"]).executar()

        for nickname in resultado["eliminados"]:
            self.jogadores.pop(nickname, None)

        sala["ultima_rodada"] = resultado
        sala["ultimos_participantes"] = list(sala["participantes"])
        sala["participantes"] = []
        sala["timer_inicio"] = None
        sala["sortear_inicio"] = None
        sala["fase"] = "resultado"
        return True

    # Encerra uma sala e limpa o estado temporario.
    def encerrar_sala(self, sala_id):
        with self.lock:
            sala = self.salas.get(sala_id)
            if sala is None or not sala["ativa"]:
                return False, "A sala informada nao esta ativa."

            sala["ativa"] = False
            sala["participantes"] = []
            sala["ultimos_participantes"] = []
            sala["timer_inicio"] = None
            sala["sortear_inicio"] = None
            return True, f"Sala {sala['nome']} encerrada."

    # Retorna os participantes atuais ou os ultimos da rodada.
    def _participantes_da_sala(self, sala, usar_ultimos=False):
        if usar_ultimos and sala["ultima_rodada"]:
            resultados = {
                item["nome"]: item["valor"]
                for item in sala["ultima_rodada"].get("resultados", [])
            }
            return [
                {
                    "nome": saldo["nome"],
                    "moedas": saldo["saldo"],
                    "resultado": resultados.get(saldo["nome"], 0),
                }
                for saldo in sala["ultima_rodada"].get("saldos", [])
            ]

        nomes = sala["ultimos_participantes"] if usar_ultimos else sala["participantes"]
        return [self.jogadores[nome].to_dict() for nome in nomes if nome in self.jogadores]

    # Monta um payload resumido com o estado da sala.
    def _serializar_sala(self, sala, usar_ultimos=False):
        tempo_restante = self._tempo_restante_sala(sala)
        return {
            "id": sala["id"],
            "nome": sala["nome"],
            "capacidade": sala["capacidade"],
            "aposta": sala["aposta"],
            "ativa": sala["ativa"],
            "fase": sala["fase"],
            "participantes": self._participantes_da_sala(sala, usar_ultimos=usar_ultimos),
            "ultima_rodada": sala["ultima_rodada"],
            "tempo_restante": tempo_restante,
            "tempo_sorteio": self._tempo_restante_sorteio(sala),
            "pode_sair": sala["fase"] != "sorteando" and (tempo_restante is None or tempo_restante >= 10),
        }

    # Prepara os dados exibidos no painel do admin.
    def estado_admin(self):
        with self.lock:
            salas = [
                self._serializar_sala(sala, usar_ultimos=sala["fase"] == "resultado")
                for sala in self.salas.values()
            ]
            return {"salas": sorted(salas, key=lambda sala: sala["id"]), "ranking": self.ranking()}

    # Prepara os dados exibidos no painel principal do jogador.
    def estado_jogador(self, nickname):
        with self.lock:
            jogador = self.jogadores.get(nickname)
            sala_atual = self._localizar_sala_do_jogador(nickname)
            return {
                "jogador": jogador,
                "sala_atual": None if sala_atual is None else self._serializar_sala(sala_atual),
                "salas_ativas": [self._serializar_sala(sala) for sala in self.listar_salas_ativas()],
                "ranking": self.ranking(),
            }

    # Retorna o estado completo de uma sala acessivel ao jogador.
    def estado_sala(self, sala_id, nickname):
        with self.lock:
            sala = self.salas.get(sala_id)
            if sala is None or not sala["ativa"]:
                return None

            autorizado = nickname in sala["participantes"] or nickname in sala["ultimos_participantes"]
            if not autorizado:
                return None

            payload = self._serializar_sala(sala, usar_ultimos=sala["fase"] == "resultado")
            payload["deadline_ms"] = (
                None if sala["timer_inicio"] is None else int((sala["timer_inicio"] + ROOM_TIMER_SECONDS) * 1000)
            )
            payload["sorteio_deadline_ms"] = (
                None
                if sala["sortear_inicio"] is None
                else int((sala["sortear_inicio"] + DRAW_TIMER_SECONDS) * 1000)
            )
            return {"jogador": self.jogadores.get(nickname), "sala": payload}


# Descobre o IP local para facilitar o acesso pela rede.
def descobrir_ip_local():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


# Retorna o nickname salvo na sessao atual.
def nickname_atual():
    return session.get("nickname", "").strip()


# Identifica se a sessao atual pertence ao admin.
def usuario_e_admin():
    return nickname_atual().lower() == "admin"


# Envia o usuario para a area correta conforme o perfil logado.
def redirecionar_para_area_correta():
    return redirect(url_for("painel_admin" if usuario_e_admin() else "painel_jogador"))


# Inicializa a aplicacao Flask e o servidor em memoria.
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "redes-local-secret")
servidor = ServidorApostas()
IP_LOCAL = descobrir_ip_local()


# Injeta dados globais usados pelos templates.
@app.context_processor
def inject_layout_context():
    nickname = nickname_atual()
    return {
        "ip_local": IP_LOCAL,
        "nickname_sessao": nickname,
        "jogador_logado": servidor.obter_jogador(nickname) if nickname else None,
        "usuario_admin": usuario_e_admin(),
    }


# Exibe o login ou redireciona quem ja estiver autenticado.
@app.get("/")
def index():
    servidor.sincronizar_temporizadores()
    if not nickname_atual():
        return render_template("login.html")
    return redirecionar_para_area_correta()


# Faz login do admin ou carrega um jogador comum.
@app.post("/login")
def login():
    nickname = request.form.get("nickname", "").strip()
    if not nickname:
        flash("Informe um nome para entrar no sistema.", "erro")
        return redirect(url_for("index"))

    session["nickname"] = nickname
    if nickname.lower() == "admin":
        flash("Acesso de administrador liberado.", "sucesso")
        return redirect(url_for("painel_admin"))

    jogador, criado = servidor.obter_ou_criar_jogador(nickname)
    mensagem = (
        f"Jogador {jogador.getnome()} cadastrado com {jogador.getsaldo()} moedas."
        if criado
        else f"Bem-vindo de volta, {jogador.getnome()}. Saldo carregado: {jogador.getsaldo()} moedas."
    )
    flash(mensagem, "sucesso")
    return redirect(url_for("painel_jogador"))


# Encerra a sessao aberta no navegador atual.
@app.post("/logout")
def logout():
    session.pop("nickname", None)
    flash("Sessao encerrada neste navegador.", "sucesso")
    return redirect(url_for("index"))


# Exibe o painel administrativo com salas e ranking.
@app.get("/admin")
def painel_admin():
    servidor.sincronizar_temporizadores()
    if not usuario_e_admin():
        flash("Apenas o admin pode acessar essa area.", "erro")
        return redirect(url_for("index"))
    return render_template("admin.html", estado=servidor.estado_admin())


# Cria uma nova sala a partir do formulario do admin.
@app.post("/admin/salas")
def criar_sala():
    if not usuario_e_admin():
        flash("Apenas o admin pode criar salas.", "erro")
        return redirect(url_for("index"))

    nome = request.form.get("nome", "").strip()
    if not nome:
        flash("Informe um nome para a sala.", "erro")
        return redirect(url_for("painel_admin"))

    try:
        capacidade = int(request.form.get("capacidade", "4").strip())
        aposta = int(request.form.get("aposta", "50").strip())
    except ValueError:
        flash("Capacidade e aposta devem ser numeros inteiros.", "erro")
        return redirect(url_for("painel_admin"))

    if not MIN_CAPACITY <= capacidade <= MAX_CAPACITY:
        flash(f"A capacidade deve ficar entre {MIN_CAPACITY} e {MAX_CAPACITY} jogadores.", "erro")
        return redirect(url_for("painel_admin"))
    if not MIN_BET <= aposta <= MAX_BET:
        flash(f"A aposta deve ficar entre {MIN_BET} e {MAX_BET} moedas.", "erro")
        return redirect(url_for("painel_admin"))

    sala = servidor.criar_sala(nome, capacidade, aposta)
    flash(
        f"Sala {sala['nome']} criada com capacidade para {capacidade} jogadores e aposta de {aposta} moedas.",
        "sucesso",
    )
    return redirect(url_for("painel_admin"))


# Permite ao admin encerrar uma sala ativa.
@app.post("/admin/salas/<int:sala_id>/encerrar")
def encerrar_sala(sala_id):
    if not usuario_e_admin():
        flash("Apenas o admin pode encerrar salas.", "erro")
        return redirect(url_for("index"))

    sucesso, mensagem = servidor.encerrar_sala(sala_id)
    flash(mensagem, "sucesso" if sucesso else "erro")
    return redirect(url_for("painel_admin"))


# Exibe a tela principal do jogador com salas e ranking.
@app.get("/jogador")
def painel_jogador():
    servidor.sincronizar_temporizadores()
    nickname = nickname_atual()
    if not nickname:
        flash("Informe seu nome para continuar.", "erro")
        return redirect(url_for("index"))
    if usuario_e_admin():
        return redirect(url_for("painel_admin"))
    return render_template("player.html", estado=servidor.estado_jogador(nickname))


# Processa a entrada do jogador em uma sala especifica.
@app.post("/salas/<int:sala_id>/entrar")
def entrar_sala(sala_id):
    nickname = nickname_atual()
    if not nickname or usuario_e_admin():
        flash("Somente jogadores podem entrar em salas.", "erro")
        return redirect(url_for("index"))

    sucesso, mensagem = servidor.entrar_na_sala(sala_id, nickname)
    flash(mensagem, "sucesso" if sucesso else "erro")
    return redirect(url_for("ver_sala", sala_id=sala_id) if sucesso else url_for("painel_jogador"))


# Processa a saida manual do jogador da sala atual.
@app.post("/salas/sair")
def sair_sala():
    nickname = nickname_atual()
    if not nickname or usuario_e_admin():
        flash("Somente jogadores podem sair de salas.", "erro")
        return redirect(url_for("index"))

    sucesso, mensagem = servidor.sair_da_sala(nickname)
    flash(mensagem, "sucesso" if sucesso else "erro")
    return redirect(url_for("painel_jogador"))


# Exibe a sala individual do jogador.
@app.get("/salas/<int:sala_id>")
def ver_sala(sala_id):
    servidor.sincronizar_temporizadores()
    nickname = nickname_atual()
    if not nickname or usuario_e_admin():
        flash("Somente jogadores podem acessar a sala.", "erro")
        return redirect(url_for("index"))

    estado = servidor.estado_sala(sala_id, nickname)
    if estado is None:
        flash("Essa sala nao esta disponivel para voce no momento.", "erro")
        return redirect(url_for("painel_jogador"))

    return render_template("room.html", estado=estado)


# Retorna o estado da sala em JSON para atualizar a interface.
@app.get("/api/salas/<int:sala_id>/estado")
def api_estado_sala(sala_id):
    servidor.sincronizar_temporizadores()
    nickname = nickname_atual()
    if not nickname or usuario_e_admin():
        return jsonify({"erro": "nao_autorizado"}), 403

    estado = servidor.estado_sala(sala_id, nickname)
    if estado is None:
        return jsonify({"erro": "sala_indisponivel"}), 404

    return jsonify(estado["sala"])


# Inicia o servidor Flask quando o arquivo for executado diretamente.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
