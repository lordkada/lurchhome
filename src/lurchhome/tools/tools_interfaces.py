from abc import abstractmethod, ABC
from typing import Dict, List, Any


class CallableTools(ABC):

    @abstractmethod
    async def call_tool(self, *, name=str, params=Dict) -> Dict[str, any]:
        ...


class WithTools(ABC):

    @abstractmethod
    async def get_tools(self) -> List[Dict[str, Any]]:
        ...
