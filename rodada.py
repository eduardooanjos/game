from jogador import jogador

import random

# Classe principal do jogo, (Cada objeto criado é uma rodada nova, com atributos novos)
class rodada:

    def __init__(self, numjogadores, jogadores):
        
        self.numjogadores = numjogadores    # atributo da quantidade de jogadores da rodada atual
        self.jogadores = jogadores          # lista de jogadores total (que vão ou não entrar na rodada)

    # Função principal que controla o funcionamento de uma rodada
    def rodada(self):

        participantes = []      # lista de participantes que irão jogar a rodada atual

        n = self.numjogadores

        # Primeiramente pergunta a cada um dos 10 jogadores se ele vai querer jogar a rodada atual
        for nome in range(0, 10):
            entrar = input(self.jogadores[nome].getnome() + " quer entrar na sala? (s/n) ")
            if entrar == "s":
                # Se a resposta do jogador for positiva, ele é incluído na lista de participantes da rodada atual,
                # com o seu nome, seu saldo atual e o atributo 'result' sendo zerado apenas para indicar uma nova randomização
                participantes.append(jogador(self.jogadores[nome].getnome(), self.jogadores[nome].getsaldo(), 0))
                n -= 1
            if n == 0:
                # Se a lista de participantes encher o número de jogadores da rodada, não precisa perguntar para os próximos
                break

        # Mas, se após perguntar para os 10 possíveis jogadores, não houver jogadores interessados o suficiente,
        # quebra e termina a rodada atual, e tenta numa próxima
        if n != 0:
            print("Jogadores insuficientes!")
            return

        # Anúncio dos resultados
        print("\nResultados: ")
        for res in range(0, self.numjogadores):
            # Cada participante tira um número aleatório de 1 a 10. Esse é o seu 'resultado'
            participantes[res].setresult(random.randint(1, 10))
            print(participantes[res].getnome(), " tirou: ", participantes[res].getresult())

        # O maior valor entre os 'resultados' dos participantes é o que determinará os vencedores
        maior = max(p.getresult() for p in participantes)
        print("\nmaior valor: ", maior)

        # Anúncio dos vencedores
        print("\nVencedor(es): ")
        for nome in range(0, self.numjogadores):
            # Se o participante houver tirado o maior número, ele ganha 100 moedas
            # (Observação: Se mais de um participante houver tirado o maior número, ambos são vencedores e ambos ganham 100 moedas)
            if participantes[nome].getresult() == maior:
                print(participantes[nome].getnome())
                participantes[nome].setmoedas(participantes[nome].getsaldo()+100)
            # Caso o participante tenha perdido, é descontado 50 moedas de sua conta (mas ninguém fica com saldo negativo)
            else:
                participantes[nome].setmoedas(max(0,participantes[nome].getsaldo()-50))
                
        # Premiação dos jogadores, alterando os saldos (apenas de quem participou da rodada)
        mapa_participantes = {obj.nome: obj.moedas for obj in participantes}
        for obj in self.jogadores:
            if obj.nome in mapa_participantes:
                obj.moedas = mapa_participantes[obj.nome]
                
        # Por fim, mostra o saldo atual de todos os 10 jogadores, que entraram na rodada ou não
        print("\nDinheiro atual:")
        for i in range(0, 10):
            print("Jogador", i+1, ": ",self.jogadores[i].getsaldo())
            

