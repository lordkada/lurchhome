from abc import abstractmethod, ABC
from typing import Dict


class CallableTools(ABC):

    @abstractmethod
    async def call_tool(self, *, name= str, params= Dict) -> Dict[str, any]:
        ...