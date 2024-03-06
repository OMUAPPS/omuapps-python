from .chatprovider import client

__all__ = ["client"]


async def main():
    await client.start()
