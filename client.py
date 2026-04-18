import sys

from Comunicador import Comunicador

if len(sys.argv) < 2:
    client_id = input("Informe o id (sera usado como login): ").strip()
    if not client_id:
        print("Uso: python client.py <id_cliente>")
        sys.exit(1)
else:
    client_id = sys.argv[1]

try:
    com = Comunicador(client_id)
except Exception as erro:
    print(f"Nao foi possivel conectar ao servidor: {erro}")
    sys.exit(1)

print(f"Conectado como {client_id}")
print("Comandos: list, join, saldo, exit")

try:
    while True:
        try:
            cmd = input("Comando: ").strip()
            if not cmd:
                continue
            if cmd.lower() in {"exit", "quit"}:
                print("Saindo do cliente.")
                break

            if cmd.lower() == "saldo":
                com.enviarMensagem("balance")
            else:
                com.enviarMensagem(cmd)

            response = com.receberMensagem()
            print("\n=== Resposta do servidor ===")
            print(response)
            print("===========================\n")
        except ConnectionError as erro:
            print(f"Conexao encerrada: {erro}")
            break
        except Exception as erro:
            print(f"Erro: {erro}")
            print("Tente novamente.")
except KeyboardInterrupt:
    print("\nSaindo do cliente.")
except EOFError:
    print("\nEntrada fechada. Saindo.")
finally:
    com.fechar()
