from jogador import jogador
from rodada import rodada
from cliente import Cliente
from Comunicador import Comunicador
import time


SALDO_INICIAL = 100
CUSTO_SALA = 20


def normalizar_nickname(nickname):
    return nickname.strip().casefold()


def buscar_ou_criar_jogador(nickname, contas):
    nome_limpo = nickname.strip()
    chave = normalizar_nickname(nome_limpo)
    conta = contas.get(chave)

    if conta is None:
        contas[chave] = {"nome": nome_limpo, "saldo": SALDO_INICIAL}
        return jogador(nome_limpo, SALDO_INICIAL, 0), True

    return jogador(conta["nome"], conta["saldo"], 0), False


def atualizar_contas(jogadores, contas):
    for jogador_atual in jogadores:
        chave = normalizar_nickname(jogador_atual.getnome())
        contas[chave] = {
            "nome": jogador_atual.getnome(),
            "saldo": max(0, jogador_atual.getsaldo()),
        }


def main():
    contas = {}
    proximo_id = 1

    while True:
        continuar = input("\nNova rodada? (s/n) ").strip().lower()
        if continuar != "s":
            break

        try:
            numjogadores = int(input("Quantos jogadores nesta rodada? "))
        except ValueError:
            print("Digite um numero valido.")
            continue

        if numjogadores < 2:
            print("Jogadores insuficientes!")
            continue

        if numjogadores > 10:
            print("Numero maximo excedido")
            continue

        jogadores = []
        nicknames_rodada = set()

        for indice in range(1, numjogadores + 1):
            while True:
                nickname = input(f"Nickname do jogador {indice}: ").strip()
                chave = normalizar_nickname(nickname)

                if not chave:
                    print("Digite um nickname valido.")
                    continue

                if chave in nicknames_rodada:
                    print("Esse nickname ja esta nesta rodada.")
                    continue

                jogador_atual, conta_nova = buscar_ou_criar_jogador(
                    nickname,
                    contas,
                )

                if jogador_atual.getsaldo() < CUSTO_SALA:
                    print(
                        f"{jogador_atual.getnome()} nao tem moedas suficientes "
                        f"para entrar na sala."
                    )
                    continue

                jogadores.append(jogador_atual)
                nicknames_rodada.add(chave)

                if conta_nova:
                    print(
                        f"Conta criada para {jogador_atual.getnome()} com "
                        f"{jogador_atual.getsaldo()} moedas."
                    )
                else:
                    print(
                        f"{jogador_atual.getnome()} voltou com "
                        f"{jogador_atual.getsaldo()} moedas."
                    )
                break

        ids = list(range(proximo_id, proximo_id + numjogadores))
        proximo_id += numjogadores
        comunicadores_servidor = {}
        clientes = []

        # Cria cada par cliente/servidor em sequencia para manter
        # o canal correto com a implementacao atual do buffer.
        for id_jogador, jogador_atual in zip(ids, jogadores):
            comunicador_cliente = Comunicador(id_jogador)
            comunicadores_servidor[id_jogador] = Comunicador(id_jogador)
            clientes.append(
                Cliente(
                    id_jogador,
                    jogador_atual.getnome(),
                    comunicador=comunicador_cliente,
                )
            )

        servidor = rodada(
            jogadores,
            ids,
            comunicadores_servidor,
            custo_sala=CUSTO_SALA,
            premio_vitoria=CUSTO_SALA,
        )

        servidor.start()
        time.sleep(0.5)

        for cliente in clientes:
            cliente.start()

        for cliente in clientes:
            cliente.join()

        servidor.join()
        atualizar_contas(jogadores, contas)


if __name__ == "__main__":
    main()
