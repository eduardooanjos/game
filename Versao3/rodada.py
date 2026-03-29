from jogador import jogador

import random

class rodada:

    def __init__(self, numjogadores, jogadores):
        
        self.numjogadores = numjogadores
        self.jogadores = jogadores

    def rodada(self):

        participantes = []

        n = self.numjogadores

        for nome in range(0, 10):
            entrar = input(self.jogadores[nome].getnome() + " quer entrar na sala? (s/n) ")
            if entrar == "s":
                participantes.append(jogador(self.jogadores[nome].getnome(), self.jogadores[nome].getsaldo(), 0))
                n -= 1
            if n == 0:
                break

        if n != 0:
            print("Jogadores insuficientes!")
            return

        # Anúncio dos resultados
        print("\nResultados: ")
        for res in range(0, self.numjogadores):
            participantes[res].setresult(random.randint(1, 10))
            print(participantes[res].getnome(), " tirou: ", participantes[res].getresult())

        maior = max(p.getresult() for p in participantes)
        print("\nmaior valor: ", maior)

        # Anúncio dos vencedores
        print("\nVencedor(es): ")
        for nome in range(0, self.numjogadores):
            if participantes[nome].getresult() == maior:
                print(participantes[nome].getnome())
                participantes[nome].setmoedas(participantes[nome].getsaldo()+100)
            else:
                participantes[nome].setmoedas(max(0,participantes[nome].getsaldo()-50))
                
        # Premiação
        mapa_participantes = {obj.nome: obj.moedas for obj in participantes}

        for obj in self.jogadores:
            if obj.nome in mapa_participantes:
                obj.moedas = mapa_participantes[obj.nome]
                
        # Dinheiro de todos os 10 jogadores, que entraram na rodada ou não
        print("\nDinheiro atual:")
        for i in range(0, 10):
            print("Jogador", i+1, ": ",self.jogadores[i].getsaldo())
            

