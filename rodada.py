import random


# Controla uma rodada com os participantes da sala atual.
class Rodada:
    def __init__(self, participantes, aposta):
        # Lista de jogadores que vao disputar a rodada.
        self.participantes = participantes
        # Valor apostado por cada perdedor na rodada.
        self.aposta = aposta

    def executar(self):
        # A rodada so acontece com pelo menos dois jogadores.
        if len(self.participantes) < 2:
            return {
                "erro": "Jogadores insuficientes para realizar a rodada.",
                "resultados": [],
                "vencedores": [],
                "eliminados": [],
                "premio_total": 0,
                "premio_por_vencedor": 0,
                "aposta": self.aposta,
            }

        # Guarda quem ficou sem moedas ao fim da rodada.
        eliminados = []
        # Armazena os valores sorteados de cada participante.
        resultados = []

        for participante in self.participantes:
            # Sorteia um valor para cada participante.
            participante.setresult(random.randint(1, 10))
            resultados.append(
                {
                    "nome": participante.getnome(),
                    "valor": participante.getresult(),
                }
            )

        # Descobre o maior valor para definir os vencedores.
        maior = max(p.getresult() for p in self.participantes)
        vencedores = [
            participante
            for participante in self.participantes
            if participante.getresult() == maior
        ]
        perdedores = [
            participante
            for participante in self.participantes
            if participante.getresult() != maior
        ]

        # Soma o valor perdido por cada derrotado para formar o premio total.
        premio_total = 0
        for participante in perdedores:
            perda = min(participante.getsaldo(), self.aposta)
            participante.setmoedas(participante.getsaldo() - perda)
            premio_total += perda
            if participante.getsaldo() == 0:
                eliminados.append(participante)

        # Divide o premio entre os vencedores e distribui eventual sobra.
        premio_por_vencedor = premio_total // len(vencedores) if vencedores else 0
        sobra = premio_total % len(vencedores) if vencedores else 0

        for indice, participante in enumerate(vencedores):
            bonus = premio_por_vencedor + (1 if indice < sobra else 0)
            participante.setmoedas(participante.getsaldo() + bonus)

        # Guarda o saldo final de todos os participantes apos a rodada.
        saldos = [
            {
                "nome": participante.getnome(),
                "saldo": participante.getsaldo(),
            }
            for participante in self.participantes
        ]

        return {
            "erro": None,
            "maior": maior,
            "resultados": resultados,
            "vencedores": [participante.getnome() for participante in vencedores],
            "eliminados": [participante.getnome() for participante in eliminados],
            "saldos": saldos,
            "premio_total": premio_total,
            "premio_por_vencedor": premio_por_vencedor,
            "aposta": self.aposta,
        }


# Mantem compatibilidade com o nome antigo da classe.
class rodada(Rodada):
    def rodada(self):
        dados = self.executar()
        return [
            participante
            for participante in self.participantes
            if participante.getnome() in dados["eliminados"]
        ]
