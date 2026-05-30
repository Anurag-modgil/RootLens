from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def handle_event(self, event_type: str, data: Dict[str, Any], orchestrator: Any) -> Any:
        pass
