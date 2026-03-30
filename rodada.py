import random


# Controla uma rodada com os participantes da sala atual.
class rodada:
    def __init__(self, participantes):
        # Lista de jogadores que vao disputar a rodada.
        self.participantes = participantes

    def rodada(self):
        # A rodada so acontece com pelo menos dois jogadores.
        if len(self.participantes) < 2:
            print("Jogadores insuficientes!")
            return []

        # Guarda quem ficou sem moedas ao fim da rodada.
        eliminados = []
        #teste
        print("\nResultados: ")
        for participante in self.participantes:
            # Sorteia um valor para cada participante.
            participante.setresult(random.randint(1, 10))
            print(participante.getnome(), " tirou: ", participante.getresult())

        # Descobre o maior valor para definir os vencedores.
        maior = max(p.getresult() for p in self.participantes)
        print("\nmaior valor: ", maior)

        print("\nVencedor(es): ")
        for participante in self.participantes:
            if participante.getresult() == maior:
                # Quem empata no maior valor tambem vence.
                print(participante.getnome())
                participante.setmoedas(participante.getsaldo() + 100)
            else:
                # Perdedor perde 50 moedas, sem permitir saldo negativo.
                participante.setmoedas(max(0, participante.getsaldo() - 50))
                if participante.getsaldo() == 0:
                    eliminados.append(participante)

        print("\nSaldo atual dos participantes:")
        for participante in self.participantes:
            print(participante.getnome(), ": ", participante.getsaldo())

        # Retorna os jogadores que devem ser removidos do cadastro.
        return eliminados
