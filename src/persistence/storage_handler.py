import asyncio

import redis.asyncio as aioredis

INPUT_TOKEN_KEY = 'i_tok'
OUTPUT_TOKEN_KEY = 'o_tok'

class StorageHandler:

    def __init__(self, *, host='localhost', port=6379):
        self.redis = aioredis.Redis(
            host=host,
            port=port,
            db=0
        )

    async def update_llm_tokens(self, *, input_tokens: int, output_tokens: int) -> tuple[int, int]:
        async with self.redis.pipeline(transaction=True) as pipe:
            await asyncio.gather(pipe.incrby(INPUT_TOKEN_KEY, input_tokens),pipe.incrby(OUTPUT_TOKEN_KEY, output_tokens))
            new_input, new_output = await pipe.execute()
        return int(new_input), int(new_output)