from jogador import jogador

import random

class rodada:

    def __init__(self, numjogadores, jogadores):
        
        self.numjogadores = numjogadores
        self.jogadores = jogadores

    def rodada(self):

        resultados = [None] * self.numjogadores

        for nome in range(0, self.numjogadores):
            resultados[nome] = random.randint(1, 10)

        maior = max(resultados)

        print("Vencedor(es): ")
        for nome in range(0, self.numjogadores):
            if resultados[nome] == maior:
                self.jogadores[nome].ganhardinheiro(100)
                print("Jogador", nome+1)
            else:
                self.jogadores[nome].perderdinheiro(100)
        
        print("Dinheiro atual:")
        for i in range(0, self.numjogadores):
            print("Jogador",i+1,": ",self.jogadores[i].getsaldo())
            

