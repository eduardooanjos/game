class jogador:
    def __init__(self, nome, moedas, result):
        self.nome = nome
        self.moedas = moedas
        self.result = result
    
    def getsaldo(self):
        return self.moedas
    
    def getnome(self):
        return self.nome
    
    def getresult(self):
        return self.result

    def setresult(self, result):
        self.result = result
    
    def setmoedas(self, moedas):
        self.moedas = moedas