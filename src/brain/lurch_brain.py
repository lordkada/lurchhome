import json
from typing import Dict, Any, List, Optional, AsyncIterator, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.utils import Output
from langchain_core.tools import Tool, StructuredTool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from jsonschema_pydantic import jsonschema_to_pydantic

from brain.lurch_prompt import SYSTEM_MSG

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_MSG),
    ("human", "{input}")
])


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

                print(f"ESEGUO {tool_name} con: {validated_params.model_dump()}")

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


    def talk_to_lurch(self, message:str="") -> AsyncIterator[Output]:
        if len(message) > 0:
           return self.chain.astream({"input": message}, stream_mode="values")

        return None