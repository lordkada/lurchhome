import pytest
import asyncio
import json
import httpx
from unittest.mock import AsyncMock, Mock, patch
import os

import integrations.ha.ha_mcp_connector as ha_mcp_connector
from integrations.ha.ha_mcp_connector import HAMCPConnector

class TestUtilityFunctions:
    """Test per le funzioni utility."""

    def test_create_jsonrpc_payload_minimal(self):
        result = ha_mcp_connector._create_jsonrpc_payload("test_method")
        expected = {
            "jsonrpc": "2.0",
            "method": "test_method"
        }
        assert json.loads(result) == expected

    def test_create_jsonrpc_payload_with_params(self):
        params = {"key": "value", "number": 42}
        result = ha_mcp_connector._create_jsonrpc_payload("test_method", params=params)
        expected = {
            "jsonrpc": "2.0",
            "method": "test_method",
            "params": params
        }
        assert json.loads(result) == expected

    def test_create_jsonrpc_payload_with_id(self):
        result = ha_mcp_connector._create_jsonrpc_payload("test_method", rpc_id=123)
        expected = {
            "jsonrpc": "2.0",
            "method": "test_method",
            "id": 123
        }
        assert json.loads(result) == expected

    def test_create_jsonrpc_payload_complete(self):
        params = {"test": True}
        result = ha_mcp_connector._create_jsonrpc_payload("test_method", params=params, rpc_id="abc123")
        expected = {
            "jsonrpc": "2.0",
            "method": "test_method",
            "params": params,
            "id": "abc123"
        }
        assert json.loads(result) == expected

    def test_is_valid_message_path_valid(self):
        valid_paths = [
            "/mcp_server/messages/ABC123",
            "/mcp_server/messages/XYZ789",
            "/mcp_server/messages/A1B2C3"
        ]
        for path in valid_paths:
            assert ha_mcp_connector._is_valid_message_path(path), f"Path {path} should be valid"

    def test_is_valid_message_path_invalid(self):
        invalid_paths = [
            "/mcp_server/messages/",
            "/mcp_server/messages/abc123",  # lowercase
            "/wrong/path/ABC123",
            "/mcp_server/messages/ABC-123",  # hyphen not allowed
            "mcp_server/messages/ABC123",  # missing leading slash
            "/mcp_server/messages/ABC123/extra"
        ]
        for path in invalid_paths:
            assert not ha_mcp_connector._is_valid_message_path(path), f"Path {path} shouldn't be valid"

    def test_build_request_body_minimal(self):
        result = ha_mcp_connector._build_request_body("test_method")
        expected = {
            'action': 'send_request',
            'method': 'test_method'
        }
        assert result == expected

    def test_build_request_body_with_params(self):
        params = {"key": "value"}
        result = ha_mcp_connector._build_request_body("test_method", params=params)
        expected = {
            'action': 'send_request',
            'method': 'test_method',
            'params': params
        }
        assert result == expected

    def test_build_request_body_with_request_id(self):
        result = ha_mcp_connector._build_request_body("test_method", request_id=42)
        expected = {
            'action': 'send_request',
            'method': 'test_method',
            'request_id': 42
        }
        assert result == expected

    def test_build_request_body_complete(self):
        """Test costruzione body request completo."""
        params = {"test": True}
        result = ha_mcp_connector._build_request_body("test_method", params=params, request_id="test_id")
        expected = {
            'action': 'send_request',
            'method': 'test_method',
            'params': params,
            'request_id': "test_id"
        }
        assert result == expected

class TestHomeAssistantConnector:
    @pytest.fixture
    def connector(self):
        return HAMCPConnector('http://test.local', 'test_token')

    def test_init_default_values(self):
        with patch.dict(os.environ, {}, clear=True):
            connector = HAMCPConnector('http://test.local', 'test_token')
            assert connector.base_url == "http://test.local"
            assert connector.api_token == "test_token"
            assert connector.messages_url is None


    def test_init_with_env_vars(self, connector):
        assert connector.base_url == 'http://test.local'
        assert connector.api_token == 'test_token'
        assert connector.messages_url is None
        assert connector._current_request_id == 1
        assert isinstance(connector._pending_requests, dict)
        assert len(connector._pending_requests) == 0


    def test_set_messages_url(self, connector: HAMCPConnector):
        test_url = "/mcp_server/messages/TEST123"
        connector._HAMCPConnector__set_messages_url(test_url)
        assert connector.messages_url == test_url
        assert connector._messages_url_ready.is_set()


    @pytest.mark.asyncio
    async def test_do_post_request_not_initialized(self, connector):
        with pytest.raises(ValueError, match="HomeAssistantConnector not initialized!"):
            await connector._HAMCPConnector__do_post_request("test_method")

    @pytest.mark.asyncio
    async def test_do_post_request_success(self, connector):
        connector.messages_url = "/mcp_server/messages/TEST123"

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        connector._client = mock_client

        await connector._HAMCPConnector__do_post_request("test_method", request_id=1, params={"test": True})

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args.args[0] == 'http://test.local/mcp_server/messages/TEST123'
        assert 'Authorization' in call_args[1]['headers']

    @pytest.mark.asyncio
    async def test_do_post_request_http_error(self, connector):
        connector.messages_url = "/mcp_server/messages/TEST123"

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_client.post.return_value = mock_response
        connector._client = mock_client

        with pytest.raises(httpx.HTTPError, match="HTTP 404"):
            await connector._HAMCPConnector__do_post_request("test_method")

    @pytest.mark.asyncio
    async def test_queue_request(self, connector):
        await connector._HAMCPConnector__queue_request("test_method", params={"test": True})

        assert connector._command_queue.qsize() == 1

        command = await connector._command_queue.get()
        expected = {
            'action': 'send_request',
            'method': 'test_method',
            'params': {'test': True}
        }
        assert command == expected

    @pytest.mark.asyncio
    async def test_queue_request_and_wait_response_timeout(self, connector):
        with pytest.raises(asyncio.TimeoutError):
            await connector._HAMCPConnector__queue_request_and_wait_response(
                "test_method", timeout=0.1
            )

    @pytest.mark.asyncio
    async def test_queue_request_and_wait_response_success(self, connector):

        async def mock_response():
            await asyncio.sleep(0.05)
            request_id = 1
            if request_id in connector._pending_requests:
                event = connector._pending_requests[request_id]
                connector._pending_requests[request_id] = {"result": "success"}
                event.set()

        response_task = asyncio.create_task(mock_response())

        try:
            result = await connector._HAMCPConnector__queue_request_and_wait_response(
                "test_method", timeout=1.0
            )
            assert result == {"result": "success"}
        finally:
            response_task.cancel()
            try:
                await response_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_command_processor_send_request(self, connector):
        connector.messages_url = "/mcp_server/messages/TEST123"
        connector._messages_url_ready.set()

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        connector._client = mock_client

        command = {
            'action': 'send_request',
            'method': 'test_method',
            'params': {'test': True},
            'request_id': 1
        }
        await connector._command_queue.put(command)

        await connector._HAMCPConnector__command_processor(forever=False)

        mock_client.post.assert_called_once()


    @pytest.mark.asyncio
    async def test_get_tools_not_initialized(self, connector):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(connector.get_tools(), timeout=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])