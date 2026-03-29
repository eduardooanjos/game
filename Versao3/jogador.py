# Classe de cada um dos 10 jogadores
class jogador:
    def __init__(self, nome, moedas, result):
        self.nome = nome        # atributo nome (ex.: Jogador1, Jogador2, ...)
        self.moedas = moedas    # atributo da quantidade de moedas atual, a ser alterado ao decorrer das rodadas
        self.result = result    # atributo do resultado de uma rodada, somente sendo alterado se jogador participar da rodada atual
    
    # Getters:

    def getsaldo(self):
        return self.moedas
    
    def getnome(self):
        return self.nome
    
    def getresult(self):
        return self.result

    # Setters:

    def setresult(self, result):
        self.result = result
    
    def setmoedas(self, moedas):
        self.moedas = moedas