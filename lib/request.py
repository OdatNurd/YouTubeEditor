###----------------------------------------------------------------------------


class Request(dict):
    """
    Simple wrapper for a request object. This is essentially a hashable
    dictionary object that doesn't throw exceptions when you attempt to access
    a key that doesn't exist, and which inherently knows what it's name is
    and for what reason it was created.

    handler is a special field the caller can use to track how the result
    should be handled; any other arguments are regular dict type values.
    """
    def __init__(self, name, handler=None, reason=None, **kwargs):
        super().__init__(self, **kwargs)
        self.name = name
        self.reason = reason or name
        self.handler = handler or '_' + name

    def __key(self):
        return tuple((k,self[k]) for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __getitem__(self, key):
        return self.get(key, None)

    def __set_name(self, value):
        self["_name"] = value

    def __get_name(self):
        return self.get("_name", None)

    def __get_reason(self):
        return self.reason

    def __set_handler(self, value):
        self["_handler"] = value

    def __get_handler(self):
        return self.get("_handler", None)

    name = property(__get_name, __set_name)
    handler = property(__get_handler, __set_handler)


###----------------------------------------------------------------------------
