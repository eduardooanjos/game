class Jogador:
    def __init__(self, nome, saldo_inicial=100):
        self.nome = nome
        self.saldo = saldo_inicial

    def getnome(self):
        return self.nome

    def getsaldo(self):
        return self.saldo

    def adicionar_saldo(self, valor):
        self.saldo += valor

    def subtrair_saldo(self, valor):
        self.saldo -= valor

    def to_dict(self):
        return {"nome": self.nome, "saldo": self.saldo}