"""WebSocket streaming endpoint — scaffold for future telephony integration."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


@router.websocket("/conversations/{session_id}/stream")
async def stream_conversation(websocket: WebSocket, session_id: str):
    """Bidirectional audio streaming. Not yet implemented for MVP.

    Future: telephony adapter pipes audio chunks here.
    Server sends back audio response frames.
    """
    await websocket.accept()
    try:
        await websocket.send_json({
            "type": "error",
            "message": "WebSocket streaming not yet implemented. Use REST /turn endpoint for MVP.",
        })
        await websocket.close()
    except WebSocketDisconnect:
        pass
