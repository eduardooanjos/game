import random

from rodada import rodada
from jogador import jogador

def main():

    while True:

        numjogadores = int(input("Quantos jogadores nesta rodada? "))

        if numjogadores < 2:
            print("Jogadores insuficientes")
        
        else:
            jogadores = [jogador(100) for i in range(0, numjogadores)]
            mesa = rodada(numjogadores, jogadores)
            mesa.rodada()

        continuar = input("Nova rodada? (s/n) ")

        if continuar != "s":
            break


if __name__ == "__main__":
    main()