
from unittest.mock import Mock

from backend.app.agents.policy_analyst_agent import PolicyAnalystAgent


def make_agent():
    agent = PolicyAnalystAgent.__new__(PolicyAnalystAgent)
    agent._name = "PolicyAnalystAgent"
    agent._retriever = Mock()
    agent._answer_generator = Mock()
    return agent


def test_llm_failure_is_propagated():
    agent = make_agent()
    agent._retriever.search.return_value = [
        Mock(page_content="Sample procurement policy", metadata={"source": "policy.txt"})
    ]
    agent._answer_generator.generate_answer.return_value = {
        "status": "error",
        "answer": "The language model service was unavailable.",
        "sources": {},
        "error_type": "RuntimeError",
    }

    result = agent.run({"query": "What is the late delivery penalty?"})

    assert result["status"] == "error"
    assert result["agent"] == "PolicyAnalystAgent"
    assert "RuntimeError" in result["error"]
    assert result["sources"] == {}


def test_no_retrieved_documents_returns_consistent_sources_key():
    agent = make_agent()
    agent._retriever.search.return_value = []

    result = agent.run({"query": "What is the late delivery penalty?"})

    assert result["status"] == "success"
    assert result["sources"] == {}
    assert "source" not in result


def test_invalid_query_is_rejected():
    agent = make_agent()

    result = agent.run({"query": "  "})

    assert result["status"] == "error"
    assert "query" in result["error"].lower()
    agent._retriever.search.assert_not_called()
