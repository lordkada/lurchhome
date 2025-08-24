import json
import logging

from typing import Dict, Any, List
from langchain_core.tools import Tool, StructuredTool
from jsonschema_pydantic import jsonschema_to_pydantic

from integrations.ha.ha_mcp_connector import HAMCPConnector


def _create_langchain_tool(ha_mcp_connector: HAMCPConnector, tool_data: Dict[str, Any]) -> StructuredTool:
    tool_name = tool_data['name']
    tool_description = tool_data['description']
    input_schema = tool_data.get('inputSchema', {})

    input_model = jsonschema_to_pydantic(input_schema)

    async def tool_function(*args, **kwargs) -> str:

        logging.debug(f'Calling tool: %s', tool_name)

        try:
            if args:
                if len(args) == 1 and isinstance(args[0], dict):
                    kwargs = {**args[0], **kwargs}
                else:
                    raise TypeError(
                        f"{tool_name} received unexpected positional args: {args}"
                    )

            validated_params = input_model(**kwargs)

            result = await ha_mcp_connector.call_tool(
                name=tool_name,
                params=validated_params.model_dump(exclude_none=True, exclude_unset=True)
            )

            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    return StructuredTool.from_function(
        name=tool_name,
        description=tool_description,
        args_schema=input_model,
        coroutine=tool_function,
    )

async def build_tools(ha_mcp_connector: HAMCPConnector) -> List[Tool]:
    langchain_tools = []
    for tool_data in ((await ha_mcp_connector.get_tools()).get('tools', [])):
        langchain_tool = _create_langchain_tool(ha_mcp_connector, tool_data)
        langchain_tools.append(langchain_tool)

    return langchain_tools
