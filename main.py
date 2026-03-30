import random

from rodada import rodada
from jogador import jogador

def main():

    # Lista total de 10 jogadores, nomeados 'Jogador1' , "Jogador2", ... , até 'Jogador10'
    # Todos os jogadores iniciam-se com 100 moedas no saldo
    jogadores = [jogador("Jogador" + str(i), 100, 0) for i in range(1, 11)]

    # Ciclo de rodadas
    while True:

        continuar = input("\nNova rodada? (s/n) ")

        if continuar != "s":
            break

        # A cada nova rodada, um número de jogadores específico
        numjogadores = int(input("Quantos jogadores nesta rodada? "))

        # Entretanto, o número mínimo de jogadores de cada rodada é 2,
        if numjogadores < 2:
            print("Jogadores insuficientes!")
        
        # Porém, o máximo de jogadores é 10
        else if numjogadores > 10:
            print("Número máximo de jogadores excedido")
        
        # Caso as condições acima tenham sido satisfeitas, cria-se uma nova rodada,
        # com o número de jogadores especificado e a lista dos 10 jogadores
        else:
            mesa = rodada(numjogadores, jogadores)
            
            # E tem-se início uma rodada
            mesa.rodada()


if __name__ == "__main__":
    main()