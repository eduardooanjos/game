import threading
from Comunicador import Comunicador

# Cada jogador roda em uma thread separada
class Cliente(threading.Thread):
    def __init__(self, id, nome, comunicador=None):
        super().__init__()
        self.id = id
        self.nome = nome
        self.com = comunicador if comunicador is not None else Comunicador(id)

    def run(self):
        print(f"{self.nome} entrou na sala")

        # Envia mensagem para servidor
        self.com.enviarMensagem("ENTRAR")

        # Recebe número sorteado
        numero = self.com.receberMensagem()
        print(f"{self.nome} tirou: {numero}")

        # Confirma recebimento
        self.com.enviarMensagem("OK")

        # Recebe resultado final
        resultado = self.com.receberMensagem()
        if resultado == "GANHOU":
            print(f"{self.nome}: {resultado}")
