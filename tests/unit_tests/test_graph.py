# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import pytest
import asyncio
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from src.agent.configuration import Configuration
from src.agent.state import State


# Fixtures
@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = Mock()
    llm.bind.return_value = llm
    llm.ainvoke.return_value = "Mocked LLM response"
    return llm


@pytest.fixture
def mock_huggingface_pipeline():
    """Mock HuggingFacePipeline."""
    with patch('agent.graph.HuggingFacePipeline') as mock:
        mock_instance = Mock()
        mock.from_model_id.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_state():
    """Sample state for testing."""
    state = State()
    state.user_requirements = "Design a simple LED circuit"
    state.messages = [HumanMessage(content="I need a PCB for an LED circuit")]
    return state


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return RunnableConfig(configurable={
        "model_name": "test-model",
        "output_dir": "test_output",
        "max_new_tokens": 256
    })


class TestGetLLM:
    """Test cases for get_llm function."""
    
    @patch('agent.graph.HuggingFacePipeline.from_model_id')
    def test_get_llm_success(self, mock_from_model_id):
        """Test successful LLM initialization."""
        from src.agent.graph import get_llm
        
        mock_llm = Mock()
        mock_from_model_id.return_value = mock_llm
        
        config = Configuration(model_name="test-model")
        result = get_llm(config)
        
        assert result is mock_llm
        mock_from_model_id.assert_called_once_with(
            model_id="test-model",
            task="text-generation",
            device=-1,
            pipeline_kwargs={
                "max_new_tokens": 512,
                "temperature": 0.7,
                "do_sample": True,
                "top_k": 50,
                "top_p": 0.95,
                "repetition_penalty": 1.2,
                "pad_token_id": 50256,
                "eos_token_id": 50256,
                "return_full_text": False
            }
        )
    
    @patch('agent.graph.HuggingFacePipeline.from_model_id')
    def test_get_llm_fallback(self, mock_from_model_id):
        """Test LLM fallback when primary model fails."""
        from agent.graph import get_llm
        
        # First call fails, second succeeds
        mock_fallback_llm = Mock()
        mock_from_model_id.side_effect = [
            Exception("Model not found"),
            mock_fallback_llm
        ]
        
        config = Configuration(model_name="non-existent-model")
        result = get_llm(config)
        
        assert result is mock_fallback_llm
        assert mock_from_model_id.call_count == 2
        
        # Check fallback call
        fallback_call = mock_from_model_id.call_args_list[1]
        assert fallback_call[1]["model_id"] == "gpt2"
    
    @patch('agent.graph.HuggingFacePipeline.from_model_id')
    def test_get_llm_with_custom_config(self, mock_from_model_id):
        """Test LLM initialization with custom configuration."""
        from agent.graph import get_llm
        
        mock_llm = Mock()
        mock_from_model_id.return_value = mock_llm
        
        config = Configuration(
            model_name="custom-model",
            max_new_tokens=1024,
            temperature=0.8,
            device=0
        )
        result = get_llm(config)
        
        mock_from_model_id.assert_called_once_with(
            model_id="custom-model",
            task="text-generation",
            device=0,
            pipeline_kwargs={
                "max_new_tokens": 1024,
                "temperature": 0.8,
                "do_sample": True,
                "top_k": 50,
                "top_p": 0.95,
                "repetition_penalty": 1.2,
                "pad_token_id": 50256,
                "eos_token_id": 50256,
                "return_full_text": False
            }
        )


class TestUserInterfaceAgent:
    """Test cases for user_interface_agent function."""
    
    @pytest.mark.asyncio
    async def test_user_interface_agent_basic_functionality(self, sample_state, sample_config):
        """Test basic functionality of user interface agent."""
        from agent.graph import user_interface_agent
        
        # Mock the entire LangChain pipeline by patching the ainvoke call
        async def mock_ainvoke(*args, **kwargs):
            return "Mocked analysis result"
        
        with patch('agent.graph.get_llm') as mock_get_llm:
            # Create a mock chain that can be awaited
            mock_chain = Mock()
            mock_chain.ainvoke = mock_ainvoke
            
            # Create mock components
            mock_llm = Mock()
            mock_bound_llm = Mock()
            mock_bound_llm.__or__ = Mock(return_value=mock_chain)
            mock_llm.bind.return_value = mock_bound_llm
            mock_get_llm.return_value = mock_llm
            
            with patch('agent.graph.PromptTemplate') as mock_prompt_cls:
                mock_prompt = Mock()
                mock_prompt.__or__ = Mock(return_value=mock_bound_llm)
                mock_prompt_cls.from_template.return_value = mock_prompt
                
                with patch('agent.graph.StrOutputParser') as mock_parser_cls:
                    mock_parser = Mock()
                    mock_parser_cls.return_value = mock_parser
                    
                    result = await user_interface_agent(sample_state, sample_config)
                    
                    assert result["current_agent"] == "component_research"
                    assert sample_state.user_requirements == "I need a PCB for an LED circuit"
                    assert len(sample_state.messages) == 2  # Original + AI response


class TestComponentResearchAgent:
    """Test cases for component_research_agent function."""
    
    # Note: Complex LangChain pipeline mocking is tested in the simplified integration tests
    # This class is kept for potential future tests that don't require heavy mocking


class TestSchematicDesignAgent:
    """Test cases for schematic_design_agent function."""
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    async def test_schematic_design_agent(self, mock_makedirs, sample_state, sample_config):
        """Test schematic design agent."""
        from agent.graph import schematic_design_agent
        
        result = await schematic_design_agent(sample_state, sample_config)
        
        assert result["current_agent"] == "pcb_layout"
        assert sample_state.schematic_file.endswith("design.sch")
        assert "test_output" in sample_state.schematic_file
        mock_makedirs.assert_called_once_with("test_output", exist_ok=True)
        assert len(sample_state.messages) == 2


class TestPCBLayoutAgent:
    """Test cases for pcb_layout_agent function."""
    
    @pytest.mark.asyncio
    async def test_pcb_layout_agent(self, sample_state, sample_config):
        """Test PCB layout agent."""
        from agent.graph import pcb_layout_agent
        
        result = await pcb_layout_agent(sample_state, sample_config)
        
        assert result["current_agent"] == "simulation"
        assert sample_state.pcb_file.endswith("design.kicad_pcb")
        assert "test_output" in sample_state.pcb_file
        assert len(sample_state.messages) == 2


class TestSimulationAgent:
    """Test cases for simulation_agent function."""
    
    @pytest.mark.asyncio
    async def test_simulation_agent_enabled(self, sample_state, sample_config):
        """Test simulation agent with simulations enabled."""
        from agent.graph import simulation_agent
        
        result = await simulation_agent(sample_state, sample_config)
        
        assert result["current_agent"] == "manufacturing_output"
        assert "design_rule_check" in sample_state.simulation_results
        assert sample_state.simulation_results["design_rule_check"] == "PASS"
        assert len(sample_state.messages) == 2
    
    @pytest.mark.asyncio
    async def test_simulation_agent_disabled(self, sample_state):
        """Test simulation agent with simulations disabled."""
        from agent.graph import simulation_agent
        
        config = RunnableConfig(configurable={"run_simulations": False})
        result = await simulation_agent(sample_state, config)
        
        assert result["current_agent"] == "manufacturing_output"
        assert sample_state.simulation_results == {}  # Should remain empty
        assert len(sample_state.messages) == 2


class TestManufacturingOutputAgent:
    """Test cases for manufacturing_output_agent function."""
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    async def test_manufacturing_output_agent(self, mock_makedirs, sample_state, sample_config):
        """Test manufacturing output agent."""
        from agent.graph import manufacturing_output_agent
        from langgraph.graph import END
        
        result = await manufacturing_output_agent(sample_state, sample_config)
        
        assert result["current_agent"] == END  # Should be the END constant
        assert sample_state.design_complete is True
        assert len(sample_state.manufacturing_files) == 7  # All expected output files
        
        # Check file types
        file_extensions = [os.path.splitext(f)[1] for f in sample_state.manufacturing_files]
        expected_extensions = [".gtl", ".gbl", ".gto", ".gbo", ".gm1", ".drl", ".csv"]
        assert all(ext in file_extensions for ext in expected_extensions)
        
        mock_makedirs.assert_called_once_with("test_output", exist_ok=True)
        assert len(sample_state.messages) == 2


class TestRouter:
    """Test cases for router function."""
    
    def test_router(self):
        """Test router function."""
        from agent.graph import router
        
        state = State()
        state.current_agent = "test_agent"
        
        result = router(state)
        assert result == "test_agent"
    
    def test_router_different_agents(self):
        """Test router with different agent states."""
        from agent.graph import router
        
        agents = ["user_interface", "component_research", "schematic_design", 
                 "pcb_layout", "simulation", "manufacturing_output"]
        
        for agent in agents:
            state = State()
            state.current_agent = agent
            result = router(state)
            assert result == agent


class TestGraphConstruction:
    """Test cases for graph construction and structure."""
    
    def test_graph_exists(self):
        """Test that the graph is properly constructed."""
        from agent.graph import graph
        
        assert graph is not None
        assert hasattr(graph, 'name')
        assert graph.name == "Othertales Q PCB Design"
    
    def test_workflow_construction(self):
        """Test that the workflow is properly constructed."""
        # This test verifies that the graph is properly constructed
        # The graph is already created when the module is imported
        from agent.graph import workflow, graph
        
        assert workflow is not None
        assert graph is not None
        
        # Test that the graph has the expected name
        assert graph.name == "Othertales Q PCB Design"


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    @patch('agent.graph.get_llm')
    async def test_llm_error_handling(self, mock_get_llm, sample_state, sample_config):
        """Test error handling when LLM fails."""
        from agent.graph import user_interface_agent
        
        # Mock LLM to raise an exception
        mock_get_llm.side_effect = Exception("LLM initialization failed")
        
        with pytest.raises(Exception):
            await user_interface_agent(sample_state, sample_config)
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    async def test_file_creation_error_handling(self, mock_makedirs, sample_state, sample_config):
        """Test error handling when file operations fail."""
        from agent.graph import schematic_design_agent
        
        # Mock makedirs to raise an exception
        mock_makedirs.side_effect = OSError("Permission denied")
        
        with pytest.raises(OSError):
            await schematic_design_agent(sample_state, sample_config)