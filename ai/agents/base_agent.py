from abc import ABC, abstractmethod
from typing import Any

class BaseAgent(ABC):
    """Abstract base class for SupplyWise AI agents."""

    def __init__(self, name):
        if not name.strip():
            raise ValueError("Agent name cannot be empty")

        self._name = name

    @property
    def name(self):
        return self._name

    @abstractmethod
    def run(self, context):
         raise NotImplementedError