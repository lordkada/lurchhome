from abc import abstractmethod, ABC
from typing import Dict, Any, List


class WithTools(ABC):

    @abstractmethod
    async def get_tools(self) -> List[Dict[str, Any]]:
        ...
