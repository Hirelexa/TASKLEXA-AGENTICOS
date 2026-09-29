from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Protocol


class WebSocketConnection(Protocol):
    def __aiter__(self) -> AsyncIterator[str]: ...

    async def send(self, message: str) -> None: ...

    async def close(self) -> None: ...


WebSocketConnector = Callable[[str], Awaitable[WebSocketConnection]]


async def default_connector(url: str) -> WebSocketConnection:
    import websockets

    return await websockets.connect(url)
