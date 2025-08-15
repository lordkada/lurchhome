import argparse
import asyncio
import logging

from home_assistant_controller import HomeAssistantConnector

async def run():
    connector = HomeAssistantConnector()
    await connector.connect_and_run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set the logging level via command line")
    parser.add_argument('--log', default='WARNING',
                        help='Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    args = parser.parse_args()
    logging.basicConfig(level=args.log.upper(), format='%(levelname)s: %(message)s')

    asyncio.run(run())