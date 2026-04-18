from Buffer import Buffer

# O comunicador serve para enviar e receber mensagens
# entre duas entidades que utilizam o mesmo id
# Caso você tenha um jogo em que os dois clientes se
# comunicam diretamente, basta criar um comunicador em
# cada um, utilizando o mesmo id. Caso você use uma 
# arquitetura em que os clientes se comunicam com uma
# entidade centralizadora, crie um comunicador entre
# cada cliente e essa entidade (ou seja, na entidade)
# existirão N comunicadores, um para cada jogador. Nesse
# segundo caso, cada cliente terá um id diferente, e a
# entidade centralizadora terá um comunicador de cada id
# utilizado.

class Comunicador:

    def __init__(self, id):
        self.buffer = Buffer(self,id)

    # Envia a mensagem para o outro lado da comunicação
    def enviarMensagem(self, mensagem:str):
        self.buffer.inserirMensagem(self, mensagem)

    # Recebe uma mensagem enviada pelo outro lado da comunicação
    def receberMensagem(self) -> str:
        return self.buffer.removerMensagem(self)