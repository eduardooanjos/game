import socket
import struct

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6000
ENCODING = "utf-8"


class Comunicador:
    def __init__(self, id, host=DEFAULT_HOST, port=DEFAULT_PORT, conn=None, server_side=False):
        self.id = id
        self.conn = conn
        if conn is None:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((host, port))
            self.enviarMensagem(id)

    def enviarMensagem(self, mensagem: str):
        payload = mensagem.encode(ENCODING)
        header = struct.pack("!I", len(payload))
        self.conn.sendall(header + payload)

    def receberMensagem(self) -> str:
        header = self._receber_exato(4)
        tamanho = struct.unpack("!I", header)[0]
        payload = self._receber_exato(tamanho)
        return payload.decode(ENCODING)

    def _receber_exato(self, tamanho: int) -> bytes:
        dados = bytearray()
        while len(dados) < tamanho:
            bloco = self.conn.recv(tamanho - len(dados))
            if not bloco:
                raise ConnectionError("Conexao fechada")
            dados.extend(bloco)
        return bytes(dados)

    def fechar(self):
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass


class ServidorComunicador:
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, backlog=5):
        self.host = host
        self.port = port
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((host, port))
        self.server_sock.listen(backlog)

    def aceitar(self):
        conn, addr = self.server_sock.accept()
        return Comunicador(None, conn=conn, server_side=True), addr

    def fechar(self):
        try:
            self.server_sock.close()
        except Exception:
            pass
