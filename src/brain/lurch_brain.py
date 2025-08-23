import json
from typing import Dict, Any, List, Optional, AsyncIterator, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.utils import Output
from langchain_core.tools import Tool, StructuredTool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from brain.lurch_prompt import SYSTEM_MSG

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_MSG),
    ("human", "{input}")
])


def _json_schema_to_type(prop_schema: Dict[str, Any], is_required: bool) -> tuple:

    prop_type = prop_schema.get('type', 'string')
    default_value = prop_schema.get('default')
    enum_values = prop_schema.get('enum')

    if prop_type == 'string':
        if enum_values:
            python_type = str
        else:
            python_type = str
    elif prop_type == 'integer':
        python_type = int
    elif prop_type == 'number':
        python_type = float
    elif prop_type == 'boolean':
        python_type = bool
    elif prop_type == 'array':
        python_type = List[str]
    else:
        python_type = Any

    if not is_required:
        if default_value is not None:
            return Optional[python_type], default_value
        else:
            return Optional[python_type], None
    else:
        return python_type, ...


class Lurch:
    def __init__(self, tools: dict):
        model = ChatOllama(model="qwen3:30b", reasoning=True)
        converted_tools = self.convert_tools(tools)
        self.chain = prompt | create_react_agent(model, converted_tools)

    def convert_tools(self, mcp_tools_response: Dict[str, Any]) -> List[Tool]:
        langchain_tools = []
        for tool_data in mcp_tools_response.get('tools', []):
            langchain_tool = self._create_langchain_tool(tool_data)
            langchain_tools.append(langchain_tool)

        return langchain_tools

    def _create_langchain_tool(self, tool_data: Dict[str, Any]) -> StructuredTool:
        tool_name = tool_data['name']
        tool_description = tool_data['description']
        input_schema = tool_data.get('inputSchema', {})

        input_model = self._create_pydantic_model(tool_name, input_schema)

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

                print(f"ESEGUO {tool_name} con: {validated_params.dict()}")

                # Chiamata MCP (ripristina la tua riga reale)
                # result = await self.mcp_client.call_tool(
                #     name=tool_name,
                #     arguments=validated_params.dict()
                # )
                result = {}  # <— placeholder

                if isinstance(result, (dict, list)):
                    return json.dumps(result, indent=2, ensure_ascii=False)
                return str(result)

            except Exception as e:
                return f"Error executing {tool_name}: {str(e)}"

        return StructuredTool.from_function(
            name=tool_name,
            description=tool_description,
            args_schema=input_model,
            coroutine=tool_function,
        )


    def _create_pydantic_model(self, tool_name: str, json_schema: Dict[str, Any]) -> type[BaseModel]:

        if not json_schema or json_schema.get('type') != 'object':
            return BaseModel

        properties = json_schema.get('properties', {})
        required = json_schema.get('required', [])

        annotations = {}
        defaults = {}

        for prop_name, prop_schema in properties.items():
            prop_type, default_value = _json_schema_to_type(prop_schema, prop_name in required)
            annotations[prop_name] = prop_type
            if default_value is not ...:
                defaults[prop_name] = default_value

        model_name = f"{tool_name}Input"

        def __init__(self, **kwargs):
            for key, value in defaults.items():
                if key not in kwargs:
                    kwargs[key] = value
            BaseModel.__init__(self, **kwargs)

        model_class = type(model_name, (BaseModel,), {
            '__annotations__': annotations,
            '__init__': __init__
        })

        return cast(type[BaseModel], model_class)

    def talk_to_lurch(self, message:str="") -> AsyncIterator[Output]:
        if len(message) > 0:
           return self.chain.astream({"input": message}, stream_mode="values")

        return None