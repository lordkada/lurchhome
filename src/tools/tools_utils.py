import json
import logging
from pprint import pformat
from typing import Dict, Any, List

from jsonschema_pydantic import jsonschema_to_pydantic
from langchain_core.tools import StructuredTool, BaseTool

from tools.lurch_callable_tools import CallableTools
from tools.lurch_with_tools import WithTools


def _create_langchain_tool(*, tool_data: Dict[str, Any], callable_tool: CallableTools) -> BaseTool:
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
                        f"{tool_name} received unexpected positional args: {args}"
                    )

            validated_params = input_model(**kwargs).model_dump(exclude_none=True, exclude_unset=True)

            logging.info(f'Calling tool: %s', tool_name)
            logging.debug(f'Params %s', pformat(validated_params))

            result = await callable_tool.call_tool(
                name=tool_name,
                params=validated_params
            )

            logging.debug(f'Result: %s', pformat(result))

            return json.dumps(result)

        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    return StructuredTool.from_function(
        name=tool_name,
        description=tool_description,
        args_schema=input_model,
        coroutine=tool_function,
    )


async def build_tools(*, with_tools: WithTools, callable_tools: CallableTools) -> List[BaseTool]:
    tools = await with_tools.get_tools()
    return [_create_langchain_tool(tool_data=tool, callable_tool=callable_tools) for tool in tools]
