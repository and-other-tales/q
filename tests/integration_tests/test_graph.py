import pytest
from langsmith import unit
from langchain_core.messages import HumanMessage

from agent import graph
from agent.state import State


@pytest.mark.asyncio
@unit
async def test_agent_initialization() -> None:
    """Test that the agent can be initialized."""
    state = State()
    result = await graph.ainvoke(state)
    assert result is not None


@pytest.mark.asyncio
@unit
async def test_agent_with_user_message() -> None:
    """Test that the agent processes a user message."""
    state = State()
    state.messages.append(HumanMessage(content="I need a PCB for an Arduino temperature monitor."))
    result = await graph.ainvoke(state)
    assert result is not None
    assert result.design_complete is True
    assert result.schematic_file != ""
    assert result.pcb_file != ""
    assert len(result.manufacturing_files) > 0
    assert len(result.messages) > 1