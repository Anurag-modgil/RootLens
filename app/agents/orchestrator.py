import logging
import asyncio
from typing import Dict, List, Any
from app.agents.base_agent import BaseAgent
from app.services.websocket import manager as ws_manager

logger = logging.getLogger("rootlens.orchestrator")

class AgentOrchestrator:
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.event_history: List[Dict[str, Any]] = []

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.name] = agent
        logger.info(f"Registered Agent: {agent.name}")

    def dispatch_event(self, event_type: str, data: Dict[str, Any]):
        """
        Main event loop to propagate events between cooperative agents.
        """
        logger.info(f"Orchestrator: Dispatching event '{event_type}' with data: {data}")
        self.event_history.append({"event_type": event_type, "data": data})

        # Broadcast event via WebSocket to update UI in real-time
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                loop.create_task(ws_manager.broadcast({"event_type": event_type, "data": data}))
            else:
                loop.run_until_complete(ws_manager.broadcast({"event_type": event_type, "data": data}))
        except Exception as ws_err:
            logger.warning(f"Failed to broadcast websocket event: {str(ws_err)}")

        # Propagate to all registered agents
        for agent_name, agent in self.agents.items():
            try:
                agent.handle_event(event_type, data, self)
            except Exception as e:
                logger.error(f"Error handling event '{event_type}' inside agent '{agent_name}': {str(e)}")

orchestrator = AgentOrchestrator()

