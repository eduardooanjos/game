class Singleton(type):
    
    def __init__(cls,name,bases,dic):
        super(Singleton,cls).__init__(name,bases,dic)
        cls.instance={}
        cls.ids = []
    
    def __call__(cls,*args,**kw):
        id = args[1]
        if id in cls.ids:
            return cls.instance[str('id')]
        else:
            cls.ids.append(id)
            cls.instance[str('id')]=super(Singleton,cls).__call__(*args,**kw)
            return cls.instance[str('id')]

class Buffer(metaclass=Singleton):

    def __init__(self, obj, id):
        if not hasattr(self, 'obj1'):
            self.id = id
            self.__obj1 = obj
            self.__buffer12 = []
            self.__buffer21 = []


    def inserirMensagem(self, remetente, mensagem:str):
        if remetente == self.__obj1:
            self.__buffer12.append(mensagem)
        else:
            self.__buffer21.append(mensagem)

    def removerMensagem(self, destinatario) -> str:
        if destinatario == self.__obj1:
            if len(self.__buffer21) > 0:
                return self.__buffer21.pop(0)
            else:
                while len(self.__buffer21) == 0:
                    pass
                return self.__buffer21.pop(0)
        else:
            if len(self.__buffer12) > 0:
                return self.__buffer12.pop(0)
            else:
                while len(self.__buffer12) == 0:
                    pass
                return self.__buffer12.pop(0)