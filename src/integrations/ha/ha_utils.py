import json

from typing import Dict, Any, List
from langchain_core.tools import Tool, StructuredTool
from jsonschema_pydantic import jsonschema_to_pydantic

from integrations.ha.ha_mcp_connector import HAMCPConnector


def _create_langchain_tool(tool_data: Dict[str, Any]) -> StructuredTool:
    tool_name = tool_data['name']
    tool_description = tool_data['description']
    input_schema = tool_data.get('inputSchema', {})

    input_model = jsonschema_to_pydantic(input_schema)

    async def tool_function(*args, **kwargs) -> str:
        try:
            if args:
                if len(args) == 1 and isinstance(args[0], dict):
                    kwargs = {**args[0], **kwargs}
                else:
                    raise TypeError(
                        f"{tool_name} ha ricevuto argomenti posizionali inattesi: {args}"
                    )

            validated_params = input_model(**kwargs)

            # Chiamata MCP (ripristina la tua riga reale)
            # result = await self.mcp_client.call_tool(
            #     name=tool_name,
            #     arguments=validated_params.dict()
            # )
            result = {}  # <— placeholder

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
        langchain_tool = _create_langchain_tool(tool_data)
        langchain_tools.append(langchain_tool)

    return langchain_tools
