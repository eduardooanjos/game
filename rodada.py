from Comunicador import Comunicador
import threading
import random


class rodada(threading.Thread):

    def __init__(
        self,
        jogadores,
        ids,
        comunicadores=None,
        custo_sala=20,
        premio_vitoria=20,
    ):
        super().__init__()
        self.jogadores = jogadores
        self.ids = ids
        self.custo_sala = custo_sala
        self.premio_vitoria = premio_vitoria
        self.jogadores_por_id = {
            id_jogador: jogador_atual
            for id_jogador, jogador_atual in zip(ids, jogadores)
        }

        # Um comunicador para cada jogador
        self.comunicadores = (
            comunicadores
            if comunicadores is not None
            else {id: Comunicador(id) for id in ids}
        )

    # Função principal da rodada 
    def run(self):

        participantes = []

        print("\nServidor aguardando jogadores...")

        # Espera jogadores entrarem
        for id, com in self.comunicadores.items():
            msg = com.receberMensagem()
            if msg == "ENTRAR":
                participantes.append(id)

        # Se não tiver jogadores suficientes
        if len(participantes) < len(self.ids):
            print("Jogadores insuficientes!")
            return

        print("\nResultados:")

        resultados = {}

        # Sorteio e envio para jogadores
        for id in participantes:
            numero = random.randint(1, 10)
            resultados[id] = numero
            self.comunicadores[id].enviarMensagem(str(numero))

        # Recebe confirmação dos jogadores
        for id in participantes:
            _ = self.comunicadores[id].receberMensagem()

        # Determina maior valor
        maior = max(resultados.values())
        print("\nmaior valor:", maior)

        for id in participantes:
            jogador_obj = self.jogadores_por_id[id]
            jogador_obj.setmoedas(
                max(0, jogador_obj.getsaldo() - self.custo_sala)
            )

        print("\nVencedor(es):")

        # Atualiza saldo
        for id in participantes:
            jogador_obj = self.jogadores_por_id[id]

            if resultados[id] == maior:
                print(jogador_obj.getnome())
                jogador_obj.setmoedas(
                    jogador_obj.getsaldo()
                    + self.custo_sala
                    + self.premio_vitoria
                )
                self.comunicadores[id].enviarMensagem("GANHOU")
            else:
                self.comunicadores[id].enviarMensagem("FIM")

        # Mostra saldo final
        print("\nDinheiro atual:")
        for jogador_obj in self.jogadores:
            print(jogador_obj.getnome(), ":", jogador_obj.getsaldo())
