from rodada import rodada
from jogador import jogador


# Controla o cadastro dos jogadores e a abertura das salas.
def main():
    # Guarda todos os jogadores cadastrados pelo nickname.
    jogadores = {}

    while True:
        # Permite abrir varias salas sem perder os cadastros.
        continuar = input("\nAbrir nova sala? (s/n) ").strip().lower()
        if continuar != "s":
            break

        # Lista dos jogadores que participarao da sala atual.
        participantes = []
        # Impede a entrada repetida do mesmo nickname na mesma sala.
        nicknames_na_sala = set()

        print("Sala aberta. Cada jogador deve informar seu nickname.")
        print("Digite vazio para fechar a entrada da sala.")

        while len(participantes) < 4:
            # Cada sala aceita no maximo quatro jogadores.
            nickname = input(f"Nickname do jogador {len(participantes) + 1}: ").strip()

            if nickname == "":
                break

            if nickname in nicknames_na_sala:
                print("Esse nickname ja entrou nesta sala.")
                continue

            if nickname not in jogadores:
                # Cria um novo cadastro com saldo inicial.
                jogadores[nickname] = jogador(nickname, 100, 0)
                print(f"Jogador {nickname} criado com 100 moedas.")
            else:
                # Reaproveita o jogador ja cadastrado em rodadas anteriores.
                print(
                    f"Jogador {nickname} encontrado com saldo de {jogadores[nickname].getsaldo()} moedas."
                )

            participantes.append(jogadores[nickname])
            nicknames_na_sala.add(nickname)

        # Nao inicia a rodada se houver menos de dois jogadores.
        if len(participantes) < 2:
            print("Jogadores insuficientes!")
            continue

        if len(participantes) == 4:
            print("Sala lotada.")

        # Executa a rodada e recebe a lista de eliminados.
        mesa = rodada(participantes)
        eliminados = mesa.rodada()

        for jogador_eliminado in eliminados:
            nickname = jogador_eliminado.getnome()
            if nickname in jogadores:
                # Remove do sistema quem perdeu todas as moedas.
                print(f"Jogador {nickname} perdeu, conta excluida!")
                del jogadores[nickname]

        # Exibe apenas os jogadores que continuam cadastrados.
        print("\nSaldo geral cadastrado:")
        for jogador_atual in jogadores.values():
            print(jogador_atual.getnome(), ": ", jogador_atual.getsaldo())


# Executa o programa quando este arquivo for iniciado diretamente.
if __name__ == "__main__":
    main()
