import argparse
import asyncio
import contextlib
import logging
import os

from langchain_ollama import ChatOllama

from integrations.ha.ha_mcp_connector import HAMCPConnector
from brain.lurch_brain import Lurch


async def run():
    connector = HAMCPConnector(os.getenv('HA_BASE_URL'), os.getenv("HA_API_TOKEN"))
    connector_task = asyncio.create_task(connector.connect_and_run())  # long-running
    model = ChatOllama(model=os.getenv('LURCH_LLM_MODEL'), reasoning=True)
    lurch = await Lurch(model, connector).startup()

    while True:
        user_input = input("$ ")
        if user_input == 'bye':
            break

        if len(user_input) > 0:
            async for step in lurch.talk_to_lurch(message=user_input):
                print(f'> {step.text()}')

    connector_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await connector_task

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