# Representa um jogador cadastrado no sistema.
class jogador:
    def __init__(self, nome, moedas, result):
        # Nickname usado para identificar o jogador.
        self.nome = nome
        # Saldo acumulado ao longo das rodadas.
        self.moedas = moedas
        # Ultimo valor sorteado para o jogador.
        self.result = result

    # Retorna o saldo atual do jogador.
    def getsaldo(self):
        return self.moedas

    # Retorna o nickname do jogador.
    def getnome(self):
        return self.nome

    # Retorna o resultado da rodada mais recente.
    def getresult(self):
        return self.result

    # Atualiza o valor obtido na rodada.
    def setresult(self, result):
        self.result = result

    # Atualiza a quantidade de moedas do jogador.
    def setmoedas(self, moedas):
        self.moedas = moedas
