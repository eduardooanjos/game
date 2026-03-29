class jogador:
    def __init__(self, moedas):
        self.moedas = moedas
    
    def getsaldo(self):
        return self.moedas
    
    def ganhardinheiro(self, dinheiro):
        self.moedas = self.moedas + dinheiro
    
    def perderdinheiro(self, dinheiro):
        self.moedas = abs(self.moedas - dinheiro)
