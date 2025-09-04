import json
import logging
from typing import Optional, AsyncIterator, Self

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langgraph.prebuilt import create_react_agent

from lurchhome.brain.lurch_prompt import LURCH_PROMPT
from lurchhome.integrations.ha.ha_mcp_connector import HAMCPConnector
from lurchhome.integrations.ha.ha_ws_connector import HAWSConnector
from lurchhome.persistence.storage_handler import StorageHandler
from lurchhome.tools.tools_utils import build_tools


class Lurch:

    def __init__(self,
                 *,
                 llm_model: BaseChatModel,
                 ha_mcp_connector: Optional[HAMCPConnector] = None,
                 storage_handler: Optional[StorageHandler] = None,
                 ha_ws_connector: Optional[HAWSConnector] = None):

        if llm_model is None:
            raise TypeError("model can't be None")

        self.llm_model = llm_model
        self.ha_mcp_connector = ha_mcp_connector
        self.storage_handler = storage_handler
        self.chain = Optional[Runnable]
        self.ha_ws_connector = ha_ws_connector

    async def startup(self) -> Self:
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(LURCH_PROMPT),
            SystemMessage("{home_status}"),
            ("human", "{input}")
        ])

        tools = []
        if self.ha_ws_connector:
            tools = await build_tools(with_and_callable_tools=self.ha_mcp_connector)

        self.chain = prompt | create_react_agent(self.llm_model, tools)
        return self

    async def __save_analytics(self, m: AIMessage):
        if self.storage_handler and hasattr(m, 'response_metadata'):
            response_metadata = m.response_metadata
            try:
                input_tokens, output_tokens = 0, 0
                if 'prompt_eval_count' in response_metadata and 'eval_count' in response_metadata:
                    input_tokens = response_metadata.get('prompt_eval_count')
                    output_tokens = response_metadata.get('eval_count')
                elif 'token_usage' in response_metadata:
                    token_usage = response_metadata.get('token_usage')
                    input_tokens = token_usage.get('prompt_tokens')
                    output_tokens = token_usage.get('completion_tokens')

                if input_tokens + output_tokens > 0:
                    total_input_tokens, total_output_tokens = await self.storage_handler.update_llm_tokens(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens)
                    logging.info('Current step LLM usage stats: %i->%i. Total LLM stats: %i->%i',
                                 input_tokens, output_tokens,
                                 total_input_tokens, total_output_tokens)
            except KeyError:
                pass

    async def talk_to_lurch(self, message: str = "") -> AsyncIterator[BaseMessage]:
        evaluate_payload = {"input": message}

        if self.ha_mcp_connector:
            live_context = await self.ha_mcp_connector.call_tool(name='GetLiveContext', params={})
            status = (json.loads(live_context.get('content', {})[0].get('text')))['result']
            logging.debug('Status %s', status)
            evaluate_payload["home_status"] = status

        async for step in self.chain.astream(input=evaluate_payload, stream_mode="values"):
            logging.debug("chain step: %s", step)
            if getattr(step, 'get', None):
                msgs = step.get('agent', {}).get('messages') or []
            else:
                msgs = [step]

            for m in msgs:
                await self.__save_analytics(m)
                yield m
