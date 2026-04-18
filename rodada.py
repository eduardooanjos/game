import random

class Rodada:
    def __init__(self, participantes, aposta):
        self.participantes = participantes
        self.aposta = aposta

    def executar(self):
        if len(self.participantes) < 2:
            return {"resultados": [], "saldos": [p.to_dict() for p in self.participantes], "eliminados": []}

        resultados = []
        for p in self.participantes:
            valor = random.randint(1, 100)  # simple random
            resultados.append({"nome": p.getnome(), "valor": valor})

        # Sort by valor descending
        resultados.sort(key=lambda x: x["valor"], reverse=True)
        vencedor = resultados[0]["nome"]

        pot = len(self.participantes) * self.aposta

        eliminados = []
        saldos = []
        for p in self.participantes:
            if p.getnome() == vencedor:
                p.adicionar_saldo(pot - self.aposta)  # win the pot minus own bet
            else:
                p.subtrair_saldo(self.aposta)
            if p.getsaldo() <= 0:
                eliminados.append(p.getnome())
            saldos.append(p.to_dict())

        return {"resultados": resultados, "saldos": saldos, "eliminados": eliminados}