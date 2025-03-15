from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from config import logger
from models import Order

app = FastAPI()

# Хранилище активных WebSocket-соединений
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# WebSocket endpoint для подписки
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Ожидание любых сообщений от клиента (необязательно)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)



# orders storage
order_book = {
    "ask": {5: 300, 10: 100},
    "bid": {}
}

last_price = 0


async def process_order(order: Order):
    logger.info("process order...")
    await manager.broadcast("Hello, WebSocket World!")
    # if order.price:
    #     if not order.price in order_book[order.type]:
    #         order_book[order.type][order.price] = 0
    #     order_book[order.type][order.price] += order.volume
    #
    #     logger.info(order_book)
    # else:
    #     pass

    lookup_type = "ask"
    if order.type == "ask":
        lookup_type = "bid"

    logger.info(lookup_type)

    cleanup = []
    needet_volume = order.volume
    if lookup_type == "bid":
        for ok,ov in order_book[lookup_type].items():
            if order.price <= ok:
                if needet_volume < ov:
                    order_book[lookup_type][ok] -= needet_volume
                    last_price = ok
                    return "done"
                if needet_volume >= ov:
                    logger.info("eat order level")
                    needet_volume -= ov
                    cleanup.append(ok)
                    last_price = ok
    if lookup_type == "ask":
        for ok,ov in order_book[lookup_type].items():
            if order.price >= ok:
                if needet_volume < ov:
                    order_book[lookup_type][ok] -= needet_volume
                    last_price = ok
                    return "done"
                if needet_volume >= ov:
                    logger.info("eat order level")
                    needet_volume -= ov
                    cleanup.append(ok)
                    last_price = ok

    for i in cleanup:
        del order_book[lookup_type][i]

    if needet_volume > 0:
        if not order.price in order_book[order.type]:
            order_book[order.type][order.price] = 0
        order_book[order.type][order.price] += needet_volume

    return "part done"


# HTML-страница для тестирования
@app.get("/")
async def get():
    return HTMLResponse("""
        <html>
            <head>
                <title>WebSocket Demo</title>
            </head>
            <body>
                <h1>FastAPI WebSocket Demo</h1>
                <button onclick="connectWebSocket()">Connect</button>
                <button onclick="callHello()">Call Hello World</button>
                <div id="messages"></div>
                <script>
                    let ws;

                    function connectWebSocket() {
                        ws = new WebSocket("ws://localhost:8000/ws");

                        ws.onmessage = function(event) {
                            const messages = document.getElementById('messages');
                            messages.innerHTML += `<p>${event.data}</p>`;
                        };
                    }

                    function callHello() {
                        fetch('/hello-world');
                    }
                </script>
            </body>
        </html>
    """)


@app.get("/order_book")
async def read_book():
    return order_book


@app.post("/order")
async def create_order(order: Order):
    await process_order(order)
    return order_book