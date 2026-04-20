# Classe de cada um dos 10 jogadores
class jogador:
    def __init__(self, nome, moedas, result):
        self.nome = nome
        self.moedas = moedas
        self.result = result
    
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