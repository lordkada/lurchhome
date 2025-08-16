import argparse
import asyncio
import contextlib
import logging
import os

from home_assistant_controller import HomeAssistantConnector

async def run():
    ha_base_url: str = os.getenv('HA_BASE_URL', "")
    ha_api_token: str = os.getenv("HA_API_TOKEN", "")

    connector = HomeAssistantConnector(ha_base_url, ha_api_token)
    connector_task = asyncio.create_task(connector.connect_and_run())  # long-running

    tools = await connector.get_tools()
    print(tools)

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