import sys
from Comunicador import Comunicador

if len(sys.argv) < 2:
    print("Usage: python client.py <client_id>")
    sys.exit(1)

client_id = sys.argv[1]
com = Comunicador(client_id)

print(f"Connected as {client_id}")
print("Commands: login <nick>, list, create <name> <cap> <bet>, join <id>, leave, status, close <id>")

while True:
    try:
        cmd = input("Command: ").strip()
        if not cmd:
            continue
        com.enviarMensagem(cmd)
        response = com.receberMensagem()
        print("Response:", response)
    except KeyboardInterrupt:
        print("Exiting")
        break
    except Exception as e:
        print(f"Error: {e}")