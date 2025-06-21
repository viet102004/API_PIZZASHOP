from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
clients = []

@router.websocket("/ws/update")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Giữ kết nối mở
    except WebSocketDisconnect:
        clients.remove(websocket)

async def broadcast_update(entity_type: str):
    # Gửi tín hiệu cập nhật cho client
    for ws in clients:
        await ws.send_json({"action": "update", "entity": entity_type})
