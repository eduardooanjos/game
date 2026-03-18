
import random

MOEDAS_INICIAIS = 100


def rodada(jogadores):

    participantes = []

    for nome in jogadores:
        if jogadores[nome] >= 20:
            entrar = input(f"{nome} quer entrar na sala? (s/n) ")
            if entrar == "s":
                jogadores[nome] -= 20
                participantes.append(nome)

    if len(participantes) < 2:
        print("Jogadores insuficientes")
        return

    resultados = {}
    pote = 20 * len(participantes)

    for nome in participantes:
        n = random.randint(1, 10)
        resultados[nome] = n
        print(nome, "tirou", n)

    maior = max(resultados.values())

    vencedores = []
    for nome in resultados:
        if resultados[nome] == maior:
            vencedores.append(nome)

    premio = pote // len(vencedores)

    for v in vencedores:
        jogadores[v] += premio

    print("Vencedores:", vencedores)
    print("Premio:", premio)

    for nome in jogadores:
        print(nome, jogadores[nome])


def main():

    n = int(input("Quantos jogadores? "))

    jogadores = {}

    for i in range(n):
        jogadores[f"Jogador{i+1}"] = MOEDAS_INICIAIS

    while True:

        rodada(jogadores)

        continuar = input("Nova rodada? (s/n) ")

        if continuar != "s":
            break


if __name__ == "__main__":
    main()