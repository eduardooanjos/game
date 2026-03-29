import random

from rodada import rodada
from jogador import jogador

def main():

    jogadores = [jogador("Jogador" + str(i), 100, 0) for i in range(1, 11)]

    while True:

        continuar = input("\nNova rodada? (s/n) ")

        if continuar != "s":
            break

        numjogadores = int(input("Quantos jogadores nesta rodada? "))

        if numjogadores < 2:
            print("Jogadores insuficientes!")
        
        else:
            mesa = rodada(numjogadores, jogadores)
            mesa.rodada()


if __name__ == "__main__":
    main()