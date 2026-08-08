from typing import Dict, Any, Optional

class BaseAgent:
    """
    Base Agent Interface for Part 2 AI Research & Intent Routing Agents.
    """
    def __init__(self, name: str):
        self.name = name

    async def execute(self, user_id: int, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement execute()")
