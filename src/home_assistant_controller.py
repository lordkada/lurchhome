import asyncio, logging, os, json, re, httpx
from typing import Optional, Dict

"""Implementation of the MCP Protocol, version 2024-11-05
Read more: https://modelcontextprotocol.io/specification/2024-11-05
"""
MCP_PROTOCOL_VERSION = "2024-11-05"

def _create_jsonrpc_payload(method: str, params=None, id= None) -> str:
    payload = {
        "jsonrpc": "2.0",
        "method": method,
    }

    if params:
        payload["params"] = params

    if id:
        payload["id"] = id

    return json.dumps(payload)


def _is_valid_message_path(path):
    pattern = r'^/mcp_server/messages/[A-Z0-9]+$'
    return bool(re.match(pattern, path))


def _build_request_body(method: str, params=None, request_id=None):
    request_body = {
        'action': 'send_request',
        'method': method
    }

    if params:
        request_body['params'] = params

    if request_id:
        request_body['request_id'] = request_id

    return request_body


class HomeAssistantConnector:
    def __init__(self):
        self.base_url = os.getenv('HA_BASE_URL', "")
        self.api_token = os.getenv("HA_API_TOKEN", "")
        self.messages_url = None

        # Sync & inter-thread communication
        self._messages_url_ready = asyncio.Event()
        self._sse_initialized = asyncio.Event()
        self._pending_requests: Dict[int, asyncio.Event | Dict[str, any]] = {}
        self._current_request_id = 1
        self._client: Optional[httpx.AsyncClient] = None
        self._command_queue = asyncio.Queue()

    def __set_messages_url(self, messages_url: str):
        self.messages_url = messages_url
        self._messages_url_ready.set()

    def __get_post_headers(self):
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Accept': 'application/json'
        }

    async def __do_post_request(self, method: str, request_id= None, params=None):
        if not self.messages_url or not self._client:
            raise ValueError("HomeAssistantConnector not initialized!")

        payload = _create_jsonrpc_payload(method, params=params, id=request_id)
        url = f'{self.base_url}{self.messages_url}'

        logging.debug(f'__do_post_request: {url}')
        logging.debug(payload)

        response = await self._client.post(
            url,
            content=payload,
            headers=self.__get_post_headers()
        )

        if response.status_code != 200:
            raise httpx.HTTPError(f"HTTP {response.status_code}: {response.text}")

    async def __queue_request(self, method: str, params=None):
        await self._command_queue.put(_build_request_body(method, params=params))

    async def __queue_request_and_wait_response(self, method: str, params=None, timeout: float = 10) -> Dict[str, any] | None:
        ev = asyncio.Event()
        id = self._current_request_id
        self._current_request_id += 1
        self._pending_requests[id] = ev

        try:
            await self._command_queue.put(_build_request_body(method, params, id))

            try:
                await asyncio.wait_for(ev.wait(), timeout=timeout)
                return self._pending_requests[id]
            except asyncio.TimeoutError as e:
                logging.error(f"[RPC] Timeout waiting reply for the request_id {id})")
                raise e
            finally:
                self._pending_requests.pop(id, None)
        finally:
            if id in self._pending_requests:
                del self._pending_requests[id]
            logging.info(self._pending_requests)

    async def __command_processor(self):
        await self._messages_url_ready.wait()

        while True:
            try:
                command = await self._command_queue.get()
                if command['action'] == 'send_request':
                    await self.__do_post_request(
                        command['method'],
                        request_id= command.get('request_id'),
                        params= command.get('params')
                    )
                elif command['action'] == 'shutdown':
                    break

                self._command_queue.task_done()

            except Exception as e:
                logging.error(f"Errore nel command processor: {e}")
                await asyncio.sleep(1)

    async def __sse_listener(self):
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Accept': 'text/event-stream'
        }

        async with httpx.AsyncClient(timeout=None) as client:
            self._client = client

            async with client.stream('GET', f'{self.base_url}/mcp_server/sse', headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise httpx.HTTPError(f"HTTP {response.status_code}: {error_text.decode()}")

                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = line[6:].strip()

                        if not data:
                            continue

                        try:
                            event_data = json.loads(data)
                            logging.debug("SSE event:", event_data)

                            if 'id' in event_data and event_data['id'] in self._pending_requests:
                                request_id = event_data['id']
                                event = self._pending_requests[request_id]
                                self._pending_requests[request_id] = event_data['result']
                                event.set()

                        except json.JSONDecodeError:
                            if _is_valid_message_path(data):
                                self.__set_messages_url(data)
                            else:
                                logging.error(f"Not JSON data received: '{data}'")

                        except Exception as e:
                            logging.error(e)

    async def connect_and_run(self):
        sse_task = asyncio.create_task(self.__sse_listener(), name="sse_listener")
        cmd_task = asyncio.create_task(self.__command_processor(), name="command_processor")

        try:
            logging.info("Waiting the messages URL from the HA server")
            await self._messages_url_ready.wait()

            init_params = {
                "protocolVersion": f'{MCP_PROTOCOL_VERSION}',
                "capabilities": {},
                "clientInfo": {
                    "name": "LurchHome",
                    "version": "1.0.0"
                }
            }
            init_response = await self.__queue_request_and_wait_response("initialize", params=init_params)
            logging.info(init_response)
            if init_response:
                await self.__queue_request("notifications/initialized")
                self._sse_initialized.set()
                logging.info("SSE init complete!")

            await asyncio.gather(sse_task, cmd_task)

        finally:
            await self._command_queue.put({'action': 'shutdown'})
            sse_task.cancel()
            cmd_task.cancel()

            try:
                await asyncio.gather(sse_task, cmd_task, return_exceptions=True)
            except:
                pass

    async def get_tools(self) -> Dict[str, any]:
        await self._sse_initialized.wait()
        return await self.__queue_request_and_wait_response("tools/list")