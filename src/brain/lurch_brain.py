import json
import logging
from typing import Optional, AsyncIterator, Self

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import messages_from_dict, BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langgraph.prebuilt import create_react_agent

from brain.lurch_prompt import LURCH_PROMPT
from integrations.ha.ha_mcp_connector import HAMCPConnector
from integrations.ha.ha_utils import build_tools
from integrations.ha.ha_ws_connector import HAWSConnector
from persistence.storage_handler import StorageHandler


class Lurch:

    def __init__(self,
                 *,
                 llm_model: BaseChatModel,
                 ha_mcp_connector: HAMCPConnector,
                 storage_handler: StorageHandler,
                 ha_ws_connector: Optional[HAWSConnector]):

        if llm_model is None:
            raise TypeError("model can't be None")

        if ha_mcp_connector is None:
            raise TypeError("ha_mcp_connector can't be None")

        self.llm_model = llm_model
        self.ha_mcp_connector = ha_mcp_connector
        self.storage_handler = storage_handler
        self.chain = Optional[Runnable]
        self.ha_ws_connector = ha_ws_connector

    async def startup(self) -> Self:
        tools = await build_tools(self.ha_mcp_connector)

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(LURCH_PROMPT),
            SystemMessage("{home_status}"),
            ("human", "{input}")
        ])

        self.chain = prompt | create_react_agent(self.llm_model, tools)

        return self

    async def talk_to_lurch(self, message: str = "") -> AsyncIterator[BaseMessage]:
        live_context = await self.ha_mcp_connector.call_tool(name='GetLiveContext', params={})
        status = (json.loads(live_context.get('content', {})[0].get('text')))['result']
        logging.debug('Status %s', status)

        async for step in self.chain.astream({"input": message, "home_status": status}, stream_mode="values"):
            logging.debug("chain step: %s", step)

            msgs = step.get('agent', {}).get('messages') or []
            if not msgs:
                continue

            norm_msgs = msgs if isinstance(msgs[0], BaseMessage) else messages_from_dict(msgs)

            for m in norm_msgs:
                if hasattr(m, 'content') and m.content:
                    logging.debug(f"Content: {m.content[:100]}...")
                if hasattr(m, 'tool_calls') and m.tool_calls:
                    logging.debug(f"Tool call: {m.tool_calls[:100]}...")
                if hasattr(m, 'additional_kwargs') and m.additional_kwargs:
                    logging.debug(f"Reasoning: {m.additional_kwargs}...")

                logging.debug("talk_to_lurch: message type %s", type(m))

                if self.storage_handler:
                    try:
                        input_tokens, output_tokens = (m.response_metadata.get('prompt_eval_count'),
                                                       m.response_metadata.get('eval_count'))
                        total_input_tokens, total_output_tokens = await self.storage_handler.update_llm_tokens(
                            input_tokens=input_tokens,
                            output_tokens=output_tokens)
                        logging.info('Current step LLM usage stats: %i->%i. Total LLM stats: %i->%i',
                                     input_tokens, output_tokens,
                                     total_input_tokens, total_output_tokens)
                    except KeyError:
                        pass
                yield m
