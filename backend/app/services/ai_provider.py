# Services for AI provider abstraction

from abc import ABC, abstractmethod
from typing import Any, Dict


class AIProvider(ABC):
    """Abstract AI provider interface.

    Implementations must provide a ``generate`` method that returns a dict of
    generated values based on the supplied ``prompt`` and optional keyword args.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate a response from the AI model.

        Args:
            prompt: The prompt string sent to the model.
            **kwargs: Additional provider‑specific parameters.
        Returns:
            A dictionary containing the model's output. The concrete format is
            defined by the caller.
        """
        raise NotImplementedError
