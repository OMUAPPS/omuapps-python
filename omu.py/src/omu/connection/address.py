class Address:
    def __init__(self, host: str, port: int, secure: bool = False) -> None:
        self.host = host
        self.port = port
        self.secure = secure

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"
