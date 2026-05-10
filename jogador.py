from dataclasses import dataclass


@dataclass
class Jogador:
    # Dados que o servidor acompanha para cada jogador.
    nome: str
    moedas: int
    resultado: int = 0

    def getsaldo(self):
        return self.moedas

    def getnome(self):
        return self.nome

    def getresult(self):
        return self.resultado

    def setresult(self, resultado):
        self.resultado = resultado

    def setmoedas(self, moedas):
        self.moedas = moedas
