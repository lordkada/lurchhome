import json
import logging
from pprint import pprint
from typing import Optional, AsyncIterator, Self, cast, Dict

from langchain_core.language_models import chat_models
from langchain_core.messages import messages_from_dict, BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langgraph.prebuilt import create_react_agent

from brain.lurch_prompt import LURCH_PROMPT
from integrations.ha.ha_mcp_connector import HAMCPConnector
from integrations.ha.ha_utils import build_tools, get_status


class Lurch:

    def __init__(self, model: chat_models, ha_mcp_connector: HAMCPConnector):
        if model is None:
            raise TypeError("model can't be None")
        self.model = model

        if ha_mcp_connector is None:
            raise TypeError("ha_mcp_connector can't be None")
        self.ha_mcp_connector = ha_mcp_connector

        self.chain = Optional[Runnable]

    async def startup(self) -> Self:
        tools = await build_tools(self.ha_mcp_connector)
        live_context = await self.ha_mcp_connector.call_tool(name='GetLiveContext', params={})
        status = (json.loads(live_context.get('content', {})[0].get('text')))['result']
        logging.info('Status %s', status)

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(LURCH_PROMPT),
            SystemMessage(status),
            ("human", "{input}")
        ])

        self.chain = prompt | create_react_agent(self.model, tools)
        return self

    async def talk_to_lurch(self, message:str="") -> AsyncIterator[BaseMessage]:
        async for step in self.chain.astream({"input": message}, stream_mode="values"):

            logging.debug("chain step: %s", step)

            msgs = step.get('agent', {}).get('messages') or []
            if not msgs:
                continue

            norm_msgs = msgs if isinstance(msgs[0], BaseMessage) else messages_from_dict(msgs)

            for m in norm_msgs:
                logging.debug("talk_to_lurch: message type %s", type(norm_msgs))
                yield m