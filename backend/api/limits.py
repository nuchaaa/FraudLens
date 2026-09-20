from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BusinessRequestLimits:
    """Bound actual streamed bytes before JSON parsing, including chunked requests."""

    def __init__(self, app: ASGIApp, max_bytes: int = 16_384) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/v1/"):
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_bytes:
                await JSONResponse(
                    {"detail": f"request body exceeds {self.max_bytes} bytes"},
                    status_code=413,
                    headers={"Cache-Control": "no-store"},
                )(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        async def private_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message["headers"] if k.lower() != b"cache-control"]
                message["headers"] = [*headers, (b"cache-control", b"no-store")]
            await send(message)

        await self.app(scope, bounded_receive, private_send)
