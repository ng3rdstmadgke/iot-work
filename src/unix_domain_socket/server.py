import os
import socket

# https://qiita.com/t_katsumura/items/a83431671a41d9b6358f
class BlockingServerBase:
    def __init__(self, timeout:int=60, buffer:int=1024):
        self.__socket = None
        self.__timeout = timeout
        self.__buffer = buffer
        self.close()

    def __del__(self):
        self.close()

    def close(self) -> None:
        try:
            self.__socket.shutdown(socket.SHUT_RDWR)
            self.__socket.close()
        except:
            pass

    def accept(self, address, family:int, typ:int, proto:int) -> None:
        self.__socket = socket.socket(family, typ, proto)
        self.__socket.settimeout(self.__timeout)
        self.__socket.bind(address)
        self.__socket.listen(1)
        print("Server started :", address)
        conn, _ = self.__socket.accept()

        while True:
            try:
                message_recv = conn.recv(self.__buffer).decode('utf-8')
                message_resp = self.respond(message_recv)
                conn.send(message_resp.encode('utf-8'))
            except ConnectionResetError:
                break
            except BrokenPipeError:
                break
        self.close()

    def respond(self, message:str) -> str:
        return ""

class UnixServer(BlockingServerBase):
    def __init__(self, path:str="server.sock"):
        self.server = path
        self.delete()
        super().__init__(timeout=60, buffer=1024)
        super().accept(self.server, socket.AF_UNIX, socket.SOCK_STREAM, 0)

    def __del__(self):
        self.delete()

    def delete(self):
        if os.path.exists(self.server):
            os.remove(self.server)

    def respond(self, message:str) -> str:
        print("received -> ", message)
        return "Server accepted !!"

if __name__=="__main__":
    UnixServer()