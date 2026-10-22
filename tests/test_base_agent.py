from typing import Any
from backend.app.agents.base_agent import BaseAgent

class DummyAgent(BaseAgent):
    def run(self, context):
        return{
            "agent": self.name,
            "status": "success",
            "recieved": context
        }    
    def test_agent_name():
        agent = DummyAgent("TestAgent")
        assert agent.name == "TestAgent"

    def test_agent_run():
        agent = DummyAgent("TestAgent")
        result = agent.run({"product_id": 101})

        assert result["status"] == "success"
        assert result["recieved"]["product_id"] == 101

    def test_empty_agent_name_is_rejected():
        try:
            DummyAgent(" ")
        except ValueError:
            pass
        else:
            raise AssertionError("expected value error for an empty name")