from dataclasses import dataclass


# Representa um jogador com nome, saldo atual e ultimo valor sorteado.
@dataclass
class Jogador:
    nome: str
    moedas: int = 100
    result: int = 0

    # Mantem os nomes de metodos antigos para facilitar o reaproveitamento.
    def getsaldo(self):
        return self.moedas

    # Retorna o nickname do jogador.
    def getnome(self):
        return self.nome

    # Retorna o ultimo valor sorteado na rodada.
    def getresult(self):
        return self.result

    # Atualiza o valor sorteado do jogador.
    def setresult(self, result):
        self.result = result

    # Atualiza o saldo atual de moedas.
    def setmoedas(self, moedas):
        self.moedas = moedas

    # Converte o jogador para dicionario para facilitar o uso em JSON e templates.
    def to_dict(self):
        return {
            "nome": self.nome,
            "moedas": self.moedas,
            "resultado": self.result,
        }


# Alias para manter compatibilidade com o codigo anterior.
jogador = Jogador
