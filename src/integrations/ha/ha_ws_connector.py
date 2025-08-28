import json
import logging
from json import JSONDecodeError
from typing import Optional

from httpx_ws import aconnect_ws

from persistence.storage_handler import StorageHandler

EVENT_TYPES = ['state_changed']


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
    def __init__(self, *, ha_base_url: str, ha_api_token: str, storage_handler: Optional[StorageHandler] = None):
        self.base_url: str = ha_base_url
        self.api_token: str = ha_api_token
        self.storage_handler: Optional[StorageHandler] = storage_handler

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
            await ha_ws_subscribe(ws, EVENT_TYPES)

            while True:
                try:
                    payload = json.loads(await ws.receive_text())
                    logging.debug("listen_ws: %s", payload)
                    event = payload.get('event', None)
                    if event:
                        data = event.get("data", {})
                        new_state = data.get('new_state', {})
                        ret_event = {
                            'entity_id': data.get("entity_id"),
                            'state': new_state.get('state'),
                            'attributes': json.dumps(new_state.get('attributes'), separators=(",", ":")),
                            'timestamp': event.get("time_fired") or event.get("time") or "",
                            'event_type': event.get("event_type") or ""
                        }
                        if self.storage_handler:
                            await self.storage_handler.store_ha_event(event=ret_event)

                except JSONDecodeError as e:
                    logging.error(f'listen_ws: json decode exception')
