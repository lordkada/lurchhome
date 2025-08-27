import json
import logging

from httpx_ws import aconnect_ws


async def ha_ws_subscribe(ws, event_types=None):
    next_id = 1
    async def send_and_wait(payload):
        nonlocal next_id
        payload["id"] = next_id
        await ws.send_text(json.dumps(payload))
        reply = json.loads(await ws.receive_text())
        ok = reply.get("success", True) if reply.get("type") == "result" else True
        next_id += 1
        return ok

    if event_types:
        for ev in event_types:
            res = await send_and_wait({"type": "subscribe_events", "event_type": ev})
            logging.debug("send_and_wait: subscribe_events result -> %s", res)

    else:
        res = await send_and_wait({"type": "subscribe_events"})
        logging.debug("send_and_wait: subscribe_events result -> %s", res)


class HAWSConnector:
    def __init__(self, *, ha_base_url: str, ha_api_token: str):
        self.base_url: str = ha_base_url
        self.api_token: str = ha_api_token

    async def listen_ws(self):
        async with aconnect_ws(f'{self.base_url}/api/websocket') as ws:
            first = json.loads(await ws.receive_text())
            if first.get("type") != "auth_required":
                raise RuntimeError(f"Unexpected first frame: {first}")

            await ws.send_text(json.dumps({"type": "auth", "access_token": self.api_token}))
            auth_reply = json.loads(await ws.receive_text())
            if auth_reply.get("type") != "auth_ok":
                raise RuntimeError(f"Auth failed: {auth_reply}")

            logging.info("Logged to the Home Assistant Websocket")

            await ha_ws_subscribe(ws, ["state_changed"])

            while True:
                data = await ws.receive_text()
                logging.debug("listen_ws: %s", data)