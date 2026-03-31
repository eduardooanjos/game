import os
import socket
import time
from threading import RLock

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from jogador import Jogador
from rodada import Rodada


# Centraliza o estado do jogo e controla salas, jogadores e temporizadores.
class ServidorApostas:
    def __init__(self):
        self.jogadores = {}
        self.salas = {}
        self.proximo_id_sala = 1
        self.lock = RLock()

    # Retorna um jogador existente ou cria um novo com saldo inicial.
    def obter_ou_criar_jogador(self, nickname):
        with self.lock:
            jogador = self.jogadores.get(nickname)
            criado = False

            if jogador is None:
                jogador = Jogador(nickname)
                self.jogadores[nickname] = jogador
                criado = True

            return jogador, criado

    # Busca um jogador ja cadastrado pelo nickname.
    def obter_jogador(self, nickname):
        with self.lock:
            return self.jogadores.get(nickname)

    # Descobre em qual sala um jogador esta no momento.
    def localizar_sala_do_jogador(self, nickname):
        with self.lock:
            for sala in self.salas.values():
                if nickname in sala["participantes"]:
                    return sala
            return None

    # Cria uma nova sala com configuracoes iniciaiS.
    def criar_sala(self, nome, capacidade, aposta):
        with self.lock:
            sala_id = self.proximo_id_sala
            self.salas[sala_id] = {
                "id": sala_id,
                "nome": nome,
                "capacidade": capacidade,
                "aposta": aposta,
                "participantes": [],
                "ultimos_participantes": [],
                "ultima_rodada": None,
                "ativa": True,
                "timer_inicio": None,
                "timer_duracao": 30,
                "sortear_inicio": None,
                "sortear_duracao": 6,
                "fase": "aguardando",
            }
            self.proximo_id_sala += 1
            return self.salas[sala_id]

    # Lista somente as salas que ainda estao abertas.
    def listar_salas_ativas(self):
        with self.lock:
            return [sala for sala in self.salas.values() if sala["ativa"]]

    # Valida a entrada do jogador e inicia o contador ao entrar o primeiro participante.
    def entrar_na_sala(self, sala_id, nickname):
        with self.lock:
            sala = self.salas.get(sala_id)
            jogador, _ = self.obter_ou_criar_jogador(nickname)

            if sala is None or not sala["ativa"]:
                return False, "A sala escolhida nao esta mais disponivel.", None

            if sala["fase"] == "sorteando":
                return False, "O sorteio desta sala ja esta em andamento.", jogador

            sala_atual = self.localizar_sala_do_jogador(nickname)
            if sala_atual and sala_atual["id"] != sala_id:
                return False, f"Voce ja esta na sala {sala_atual['nome']}.", jogador

            if nickname in sala["participantes"]:
                return False, "Voce ja entrou nesta sala.", jogador

            if len(sala["participantes"]) >= sala["capacidade"]:
                return False, "A sala esta lotada.", jogador

            if jogador.getsaldo() < sala["aposta"]:
                return False, "Saldo insuficiente para cobrir a aposta desta sala.", jogador

            # Limpa o resultado anterior quando uma nova rodada vai comecar na mesma sala.
            if sala["fase"] == "resultado":
                sala["ultima_rodada"] = None
                sala["ultimos_participantes"] = []
                sala["fase"] = "aguardando"

            sala["participantes"].append(nickname)
            session["ultima_sala_id"] = sala_id

            if len(sala["participantes"]) == 1:
                sala["timer_inicio"] = time.time()

            return True, f"Entrada confirmada na sala {sala['nome']}.", jogador

    # Remove o jogador da sala, respeitando as regras de bloqueio proximas ao sorteio.
    def sair_da_sala(self, nickname):
        with self.lock:
            sala = self.localizar_sala_do_jogador(nickname)
            if sala is None:
                return False, "Voce nao esta em nenhuma sala."

            tempo_restante = self._tempo_restante_sala(sala)
            if sala["fase"] == "sorteando":
                return False, "O sorteio ja esta em andamento. Aguarde o resultado."

            if tempo_restante is not None and tempo_restante < 10:
                return False, "Nao e permitido sair da sala nos 10 segundos finais antes do sorteio."

            sala["participantes"].remove(nickname)
            if not sala["participantes"]:
                sala["timer_inicio"] = None
                sala["fase"] = "aguardando"
            return True, f"Voce saiu da sala {sala['nome']}."

    # Calcula o tempo restante do contador principal da sala.
    def _tempo_restante_sala(self, sala):
        if sala["timer_inicio"] is None:
            return None

        restante = sala["timer_duracao"] - int(time.time() - sala["timer_inicio"])
        return max(0, restante)

    # Calcula quanto tempo falta para concluir a fase visual do sorteio.
    def _tempo_restante_sorteio(self, sala):
        if sala["sortear_inicio"] is None:
            return None

        restante = sala["sortear_duracao"] - int(time.time() - sala["sortear_inicio"])
        return max(0, restante)

    # Avanca as salas entre espera, sorteio e resultado de acordo com os temporizadores.
    def sincronizar_temporizadores(self):
        with self.lock:
            iniciar_sorteio_ids = []
            finalizar_sorteio_ids = []

            for sala in self.salas.values():
                if not sala["ativa"]:
                    continue

                if sala["fase"] == "aguardando" and sala["timer_inicio"] is not None:
                    if self._tempo_restante_sala(sala) == 0:
                        if len(sala["participantes"]) >= 2:
                            iniciar_sorteio_ids.append(sala["id"])
                        else:
                            sala["timer_inicio"] = time.time()

                if sala["fase"] == "sorteando" and sala["sortear_inicio"] is not None:
                    if self._tempo_restante_sorteio(sala) == 0:
                        finalizar_sorteio_ids.append(sala["id"])

        for sala_id in iniciar_sorteio_ids:
            self.iniciar_sorteio(sala_id)

        for sala_id in finalizar_sorteio_ids:
            self.executar_rodada(sala_id)

    # Troca a sala para a fase de sorteio visual.
    def iniciar_sorteio(self, sala_id):
        with self.lock:
            sala = self.salas.get(sala_id)
            if sala is None or not sala["ativa"]:
                return False

            if len(sala["participantes"]) < 2:
                sala["timer_inicio"] = time.time()
                return False

            sala["fase"] = "sorteando"
            sala["sortear_inicio"] = time.time()
            sala["ultimos_participantes"] = list(sala["participantes"])
            return True

    # Executa a rodada de fato e guarda o resultado para exibicao posterior.
    def executar_rodada(self, sala_id):
        with self.lock:
            sala = self.salas.get(sala_id)
            if sala is None or not sala["ativa"]:
                return False, "A sala informada nao esta ativa."

            if len(sala["participantes"]) < 2:
                sala["fase"] = "aguardando"
                sala["sortear_inicio"] = None
                sala["timer_inicio"] = time.time() if sala["participantes"] else None
                return False, "Sao necessarios pelo menos 2 jogadores na sala."

            participantes = [
                self.jogadores[nickname]
                for nickname in sala["participantes"]
                if nickname in self.jogadores
            ]
            resultado = Rodada(participantes, sala["aposta"]).executar()

            # Remove do cadastro quem ficou sem saldo.
            for nickname in resultado["eliminados"]:
                self.jogadores.pop(nickname, None)

            sala["ultima_rodada"] = resultado
            sala["ultimos_participantes"] = list(sala["participantes"])
            sala["timer_inicio"] = None
            sala["sortear_inicio"] = None
            sala["fase"] = "resultado"
            sala["participantes"] = []
            return True, f"Sorteio realizado com sucesso na sala {sala['nome']}."

    # Fecha a sala e limpa qualquer estado temporario.
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

    # Monta o ranking geral em ordem decrescente de saldo.
    def ranking(self):
        with self.lock:
            jogadores = sorted(
                self.jogadores.values(),
                key=lambda jogador: (-jogador.getsaldo(), jogador.getnome().lower()),
            )
            return [jogador.to_dict() for jogador in jogadores]

    # Retorna os participantes atuais ou os ultimos da rodada ja concluida.
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
        return [
            self.jogadores[nome].to_dict()
            for nome in nomes
            if nome in self.jogadores
        ]

    # Monta um payload padrao com o estado resumido de uma sala.
    def _payload_sala(self, sala, usar_ultimos=False):
        tempo_restante = self._tempo_restante_sala(sala)
        return {
            "id": sala["id"],
            "nome": sala["nome"],
            "capacidade": sala["capacidade"],
            "aposta": sala["aposta"],
            "participantes": self._participantes_da_sala(sala, usar_ultimos=usar_ultimos),
            "ultima_rodada": sala["ultima_rodada"],
            "tempo_restante": tempo_restante,
            "tempo_sorteio": self._tempo_restante_sorteio(sala),
            "fase": sala["fase"],
            "pode_sair": sala["fase"] != "sorteando" and (tempo_restante is None or tempo_restante >= 10),
        }

    # Prepara os dados usados pelo painel do admin.
    def estado_admin(self):
        with self.lock:
            salas = []
            for sala in self.salas.values():
                salas.append(
                    {
                        "id": sala["id"],
                        "nome": sala["nome"],
                        "capacidade": sala["capacidade"],
                        "aposta": sala["aposta"],
                        "ativa": sala["ativa"],
                        "participantes": self._participantes_da_sala(
                            sala, usar_ultimos=sala["fase"] == "resultado"
                        ),
                        "ultima_rodada": sala["ultima_rodada"],
                        "tempo_restante": self._tempo_restante_sala(sala),
                        "tempo_sorteio": self._tempo_restante_sorteio(sala),
                        "fase": sala["fase"],
                    }
                )

            return {
                "salas": sorted(salas, key=lambda sala: sala["id"]),
                "ranking": self.ranking(),
            }

    # Prepara os dados usados pela tela principal do jogador.
    def estado_jogador(self, nickname):
        with self.lock:
            jogador = self.jogadores.get(nickname)
            sala_atual = self.localizar_sala_do_jogador(nickname)
            salas_ativas = []

            for sala in self.listar_salas_ativas():
                salas_ativas.append(self._payload_sala(sala))

            return {
                "jogador": jogador,
                "sala_atual": None if sala_atual is None else self._payload_sala(sala_atual),
                "salas_ativas": salas_ativas,
                "ranking": self.ranking(),
            }

    # Retorna o estado completo da sala aberta pelo jogador.
    def estado_sala(self, sala_id, nickname):
        with self.lock:
            sala = self.salas.get(sala_id)
            if sala is None or not sala["ativa"]:
                return None

            autorizado = nickname in sala["participantes"] or nickname in sala["ultimos_participantes"]
            if not autorizado:
                return None

            jogador = self.jogadores.get(nickname)
            usar_ultimos = sala["fase"] == "resultado"
            payload = self._payload_sala(sala, usar_ultimos=usar_ultimos)
            payload["deadline_ms"] = (
                None
                if sala["timer_inicio"] is None
                else int((sala["timer_inicio"] + sala["timer_duracao"]) * 1000)
            )
            payload["sorteio_deadline_ms"] = (
                None
                if sala["sortear_inicio"] is None
                else int((sala["sortear_inicio"] + sala["sortear_duracao"]) * 1000)
            )

            return {
                "jogador": jogador,
                "sala": payload,
            }


# Descobre o IP local para facilitar o acesso de outros dispositivos da rede.
def descobrir_ip_local():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


# Identifica se a sessao atual pertence ao usuario administrador.
def usuario_e_admin():
    return session.get("nickname", "").strip().lower() == "admin"


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "redes-local-secret")
servidor = ServidorApostas()


# Injeta dados globais usados em varias paginas do sistema.
@app.context_processor
def inject_layout_context():
    nickname = session.get("nickname")
    jogador = servidor.obter_jogador(nickname) if nickname else None

    return {
        "ip_local": descobrir_ip_local(),
        "nickname_sessao": nickname,
        "jogador_logado": jogador,
        "usuario_admin": usuario_e_admin(),
    }


# Direciona o usuario para a tela correta conforme a sessao atual.
@app.get("/")
def index():
    servidor.sincronizar_temporizadores()
    nickname = session.get("nickname")
    if not nickname:
        return render_template("login.html")

    if usuario_e_admin():
        return redirect(url_for("painel_admin"))

    return redirect(url_for("painel_jogador"))


# Faz login do admin ou carrega/cria um jogador comum.
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

    if criado:
        flash(
            f"Jogador {jogador.getnome()} cadastrado com {jogador.getsaldo()} moedas.",
            "sucesso",
        )
    else:
        flash(
            f"Bem-vindo de volta, {jogador.getnome()}. Saldo carregado: {jogador.getsaldo()} moedas.",
            "sucesso",
        )

    return redirect(url_for("painel_jogador"))


# Encerra a sessao do navegador atual.
@app.post("/logout")
def logout():
    session.pop("nickname", None)
    session.pop("ultima_sala_id", None)
    flash("Sessao encerrada neste navegador.", "sucesso")
    return redirect(url_for("index"))


# Exibe o painel administrativo com ranking e estado das salas.
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
    capacidade_bruta = request.form.get("capacidade", "4").strip()
    aposta_bruta = request.form.get("aposta", "50").strip()

    if not nome:
        flash("Informe um nome para a sala.", "erro")
        return redirect(url_for("painel_admin"))

    try:
        capacidade = int(capacidade_bruta)
    except ValueError:
        flash("A capacidade deve ser um numero inteiro.", "erro")
        return redirect(url_for("painel_admin"))

    try:
        aposta = int(aposta_bruta)
    except ValueError:
        flash("A aposta deve ser um numero inteiro.", "erro")
        return redirect(url_for("painel_admin"))

    if capacidade < 2 or capacidade > 20:
        flash("A capacidade deve ficar entre 2 e 20 jogadores.", "erro")
        return redirect(url_for("painel_admin"))

    if aposta < 1 or aposta > 1000:
        flash("A aposta deve ficar entre 1 e 1000 moedas.", "erro")
        return redirect(url_for("painel_admin"))

    sala = servidor.criar_sala(nome, capacidade, aposta)
    flash(
        f"Sala {sala['nome']} criada com capacidade para {capacidade} jogadores e aposta de {aposta} moedas.",
        "sucesso",
    )
    return redirect(url_for("painel_admin"))


# Mantida para compatibilidade, embora o sorteio manual nao esteja mais exposto na interface.
@app.post("/admin/salas/<int:sala_id>/sortear")
def sortear(sala_id):
    if not usuario_e_admin():
        flash("Apenas o admin pode executar sorteios.", "erro")
        return redirect(url_for("index"))

    sucesso, mensagem = servidor.executar_rodada(sala_id)
    flash(mensagem, "sucesso" if sucesso else "erro")
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
    nickname = session.get("nickname")
    if not nickname:
        flash("Informe seu nome para continuar.", "erro")
        return redirect(url_for("index"))

    if usuario_e_admin():
        return redirect(url_for("painel_admin"))

    return render_template("player.html", estado=servidor.estado_jogador(nickname))


# Processa a entrada do jogador em uma sala especifica.
@app.post("/salas/<int:sala_id>/entrar")
def entrar_sala(sala_id):
    nickname = session.get("nickname")
    if not nickname or usuario_e_admin():
        flash("Somente jogadores podem entrar em salas.", "erro")
        return redirect(url_for("index"))

    sucesso, mensagem, _ = servidor.entrar_na_sala(sala_id, nickname)
    flash(mensagem, "sucesso" if sucesso else "erro")
    if sucesso:
        return redirect(url_for("ver_sala", sala_id=sala_id))
    return redirect(url_for("painel_jogador"))


# Processa a saida manual do jogador da sala atual.
@app.post("/salas/sair")
def sair_sala():
    nickname = session.get("nickname")
    if not nickname or usuario_e_admin():
        flash("Somente jogadores podem sair de salas.", "erro")
        return redirect(url_for("index"))

    sucesso, mensagem = servidor.sair_da_sala(nickname)
    flash(mensagem, "sucesso" if sucesso else "erro")
    return redirect(url_for("painel_jogador"))


# Exibe a sala individual do jogador, com timer e slot machine da rodada.
@app.get("/salas/<int:sala_id>")
def ver_sala(sala_id):
    servidor.sincronizar_temporizadores()
    nickname = session.get("nickname")
    if not nickname or usuario_e_admin():
        flash("Somente jogadores podem acessar a sala.", "erro")
        return redirect(url_for("index"))

    estado = servidor.estado_sala(sala_id, nickname)
    if estado is None:
        flash("Essa sala nao esta disponivel para voce no momento.", "erro")
        return redirect(url_for("painel_jogador"))

    return render_template("room.html", estado=estado)


# Endpoint usado pelo frontend para atualizar a sala sem recarregar a pagina inteira.
@app.get("/api/salas/<int:sala_id>/estado")
def api_estado_sala(sala_id):
    servidor.sincronizar_temporizadores()
    nickname = session.get("nickname")
    if not nickname or usuario_e_admin():
        return jsonify({"erro": "nao_autorizado"}), 403

    estado = servidor.estado_sala(sala_id, nickname)
    if estado is None:
        return jsonify({"erro": "sala_indisponivel"}), 404

    return jsonify(estado["sala"])


# Inicia o servidor Flask quando o arquivo e executado diretamente.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
