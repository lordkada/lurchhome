import asyncio
import logging
from typing import Dict

import redis.asyncio as aioredis
from redis import RedisError

INPUT_TOKEN_KEY = 'i_tok'
OUTPUT_TOKEN_KEY = 'o_tok'
EVENTS_STREAM_KEY = 'lurch:ha:events'
EVENTS_MAXLEN = 10


class StorageHandler:

    def __init__(self, *, host='localhost', port=6379):
        self.redis = aioredis.Redis(
            host=host,
            port=port,
            db=0
        )

    async def update_llm_tokens(self, *, input_tokens: int, output_tokens: int) -> tuple[int, int]:
        async with self.redis.pipeline(transaction=True) as pipe:
            await asyncio.gather(pipe.incrby(INPUT_TOKEN_KEY, input_tokens),
                                 pipe.incrby(OUTPUT_TOKEN_KEY, output_tokens))
            new_input, new_output = await pipe.execute()
        return int(new_input), int(new_output)

    async def store_ha_event(self, *, event: Dict):
        try:
            await self.redis.xadd(EVENTS_STREAM_KEY, event, maxlen=EVENTS_MAXLEN)
        except RedisError as e:
            logging.error(e)
        logging.debug("StorageHandler.store_ha_event")
