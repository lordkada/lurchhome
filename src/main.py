import argparse
import asyncio
import contextlib
import logging
import os

from langchain.chat_models.base import init_chat_model
from langchain_core.messages import AIMessage

from brain.lurch_brain import Lurch
from integrations.ha.ha_mcp_connector import HAMCPConnector
from integrations.ha.ha_ws_connector import HAWSConnector
from persistence.storage_handler import StorageHandler


async def run():
    ha_base_url = os.getenv('HA_BASE_URL')
    ha_api_token = os.getenv("HA_API_TOKEN")

    '''
        SET_ENVIRONMENT_API_KEY allows the user to specify a variable whose value will be injected into
        the Operating System environment, eg:

        SET_ENVIRONMENT_API_KEY=OPENAI_API_KEY
        OPENAI_API_KEY=<your API token>
    '''
    if os.getenv("SET_ENVIRONMENT_API_KEY") and os.getenv(os.getenv("SET_ENVIRONMENT_API_KEY")):
        os.environ[os.getenv("SET_ENVIRONMENT_API_KEY")] = os.getenv(os.getenv("SET_ENVIRONMENT_API_KEY"))

    storage_handler = StorageHandler()
    ha_mcp_connector = HAMCPConnector(ha_base_url=ha_base_url, ha_api_token=ha_api_token)
    ha_ws_connector = HAWSConnector(ha_base_url=ha_base_url, ha_api_token=ha_api_token, storage_handler=storage_handler)

    async with asyncio.TaskGroup() as tg:
        t_mcp = tg.create_task(ha_mcp_connector.connect_and_run())
        t_ws = tg.create_task(ha_ws_connector.listen_ws())

        model = init_chat_model(model=os.getenv('LURCH_LLM_MODEL'), model_provider=os.getenv('LURCH_LLM_PROVIDER'))

        lurch = await (Lurch(llm_model=model,
                             ha_mcp_connector=ha_mcp_connector,
                             storage_handler=storage_handler,
                             ha_ws_connector=ha_ws_connector)
                       .startup())

        try:
            while True:
                user_input = await asyncio.to_thread(input, "$ ")
                if user_input.strip().lower() == 'bye':
                    with contextlib.suppress(Exception):
                        if hasattr(ha_mcp_connector, "aclose"):
                            await ha_mcp_connector.aclose()
                        if hasattr(ha_ws_connector, "aclose"):
                            await ha_ws_connector.aclose()

                    t_mcp.cancel()
                    t_ws.cancel()
                    break

                if len(user_input) > 0:
                    async for step in lurch.talk_to_lurch(message=user_input):
                        if isinstance(step, AIMessage):
                            if hasattr(step, 'content') and step.content:
                                print(f'> {step.text()}')
                            else:
                                print(f'| working')
        finally:
            t_mcp.cancel()
            t_ws.cancel()


if __name__ == "__main__":
    print(r"""
      L   U   U RRRR   CCCC  H  H  H  H  OOO   M   M  EEEE
      L   U   U R   R C      H  H  H  H O   O  MM MM  E   
      L   U   U RRRR  C      HHHH  HHHH O   O  M M M  EEE 
      L   U   U R R   C      H  H  H  H O   O  M   M  E   
      LLL  UUU  R  R   CCCC  H  H  H  H  OOO   M   M  EEEE

    +------------------------------------------------------------------+
    | Project : LurchHome                                              |
    | License : Apache 2.0                                             |
    | Repo    : https://github.com/lordkada/lurchhome                  |
    +------------------------------------------------------------------+
    | Smart Butler for Home Assistant • AI orchestration & automations |
    +------------------------------------------------------------------+
    """)

    parser = argparse.ArgumentParser(description="Set the logging level via command line")
    parser.add_argument('--log', default='WARNING',
                        help='Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    args = parser.parse_args()
    logging.basicConfig(level=args.log.upper(), format='%(levelname)s: %(message)s')

    asyncio.run(run())
