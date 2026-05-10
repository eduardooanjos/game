from rodada import Rodada


# Ajustes principais da sala.
SALDO_INICIAL = 100
CUSTO_SALA = 20
HOST = "127.0.0.1"
PORTA = 5000
INTERVALO_RODADA = 15
MAX_JOGADORES = 10


def main():
    # O servidor fica aberto esperando clientes externos.
    Rodada(
        host=HOST,
        porta=PORTA,
        saldo_inicial=SALDO_INICIAL,
        custo_sala=CUSTO_SALA,
        premio_vitoria=CUSTO_SALA,
        intervalo_rodada=INTERVALO_RODADA,
        max_jogadores=MAX_JOGADORES,
    ).run()


if __name__ == "__main__":
    main()
