import threading

class Singleton(type):
    def __init__(cls, name, bases, dic):
        super(Singleton, cls).__init__(name, bases, dic)
        cls.instance = {}

    def __call__(cls, *args, **kw):
        id = args[1]
        if id in cls.instance:
            return cls.instance[id]

        instance = super(Singleton, cls).__call__(*args, **kw)
        cls.instance[id] = instance
        return instance

class Buffer(metaclass=Singleton):
    def __init__(self, obj, id):
        self.id = id
        self.__obj1 = obj
        self.__buffer12 = []
        self.__buffer21 = []
        self.__condition = threading.Condition()

    def inserirMensagem(self, remetente, mensagem: str):
        with self.__condition:
            if remetente == self.__obj1:
                self.__buffer12.append(mensagem)
            else:
                self.__buffer21.append(mensagem)
            self.__condition.notify_all()

    def removerMensagem(self, destinatario) -> str:
        with self.__condition:
            if destinatario == self.__obj1:
                while len(self.__buffer21) == 0:
                    self.__condition.wait()
                return self.__buffer21.pop(0)
            else:
                while len(self.__buffer12) == 0:
                    self.__condition.wait()
                return self.__buffer12.pop(0)
