import argparse
import asyncio
import contextlib
import logging

from home_assistant_controller import HomeAssistantConnector

async def run():
    connector = HomeAssistantConnector()
    connector_task = asyncio.create_task(connector.connect_and_run())  # long-running
    tools = await connector.get_tools()

    print(tools)

    connector_task.cancel()

    with contextlib.suppress(asyncio.CancelledError):
        await connector_task

if __name__ == "__main__":
    print("Welcome to the LurchHome project")

    parser = argparse.ArgumentParser(description="Set the logging level via command line")
    parser.add_argument('--log', default='WARNING',
                        help='Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    args = parser.parse_args()
    logging.basicConfig(level=args.log.upper(), format='%(levelname)s: %(message)s')

    asyncio.run(run())