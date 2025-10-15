# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from agent.configuration import Configuration
from agent.state import State


# Simple unit tests for graph.py functions that avoid complex LangChain mocking
class TestGraphSimplified:
    """Simplified test cases for graph.py functions."""
    
    @pytest.fixture
    def sample_state(self):
        """Sample state for testing."""
        state = State()
        state.user_requirements = "Design a simple LED circuit"
        state.messages = [HumanMessage(content="I need a PCB for an LED circuit")]
        return state
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return RunnableConfig(configurable={
            "model_name": "test-model",
            "output_dir": "test_output",
            "max_new_tokens": 256
        })
    
    def test_router_function(self):
        """Test the router function."""
        from agent.graph import router
        
        state = State()
        state.current_agent = "test_agent"
        
        result = router(state)
        assert result == "test_agent"
        
        # Test with different agents
        agents = ["user_interface", "component_research", "schematic_design", 
                 "pcb_layout", "simulation", "manufacturing_output"]
        
        for agent in agents:
            state.current_agent = agent
            result = router(state)
            assert result == agent
    
    @patch('agent.graph.HuggingFacePipeline.from_model_id')
    def test_get_llm_success(self, mock_from_model_id):
        """Test successful LLM initialization."""
        from agent.graph import get_llm
        
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
                "repetition_penalty": 1.2
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
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    async def test_schematic_design_agent(self, mock_makedirs, sample_state, sample_config):
        """Test schematic design agent file creation."""
        from agent.graph import schematic_design_agent
        
        result = await schematic_design_agent(sample_state, sample_config)
        
        assert result["current_agent"] == "pcb_layout"
        assert sample_state.schematic_file.endswith("design.sch")
        assert "test_output" in sample_state.schematic_file
        mock_makedirs.assert_called_once_with("test_output", exist_ok=True)
        
        # Check that a message was added
        assert len(sample_state.messages) == 2
        assert isinstance(sample_state.messages[-1], AIMessage)
    
    @pytest.mark.asyncio
    async def test_pcb_layout_agent(self, sample_state, sample_config):
        """Test PCB layout agent file creation."""
        from agent.graph import pcb_layout_agent
        
        result = await pcb_layout_agent(sample_state, sample_config)
        
        assert result["current_agent"] == "simulation"
        assert sample_state.pcb_file.endswith("design.kicad_pcb")
        assert "test_output" in sample_state.pcb_file
        
        # Check that a message was added
        assert len(sample_state.messages) == 2
        assert isinstance(sample_state.messages[-1], AIMessage)
    
    @pytest.mark.asyncio
    async def test_simulation_agent_enabled(self, sample_state, sample_config):
        """Test simulation agent with simulations enabled."""
        from agent.graph import simulation_agent
        
        result = await simulation_agent(sample_state, sample_config)
        
        assert result["current_agent"] == "manufacturing_output"
        assert "design_rule_check" in sample_state.simulation_results
        assert sample_state.simulation_results["design_rule_check"] == "PASS"
        
        # Check that a message was added
        assert len(sample_state.messages) == 2
        assert isinstance(sample_state.messages[-1], AIMessage)
    
    @pytest.mark.asyncio
    async def test_simulation_agent_disabled(self, sample_state):
        """Test simulation agent with simulations disabled."""
        from agent.graph import simulation_agent
        
        config = RunnableConfig(configurable={"run_simulations": False})
        result = await simulation_agent(sample_state, config)
        
        assert result["current_agent"] == "manufacturing_output"
        assert sample_state.simulation_results == {}  # Should remain empty
        
        # Check that a message was added
        assert len(sample_state.messages) == 2
        assert isinstance(sample_state.messages[-1], AIMessage)
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    async def test_manufacturing_output_agent(self, mock_makedirs, sample_state, sample_config):
        """Test manufacturing output agent."""
        from agent.graph import manufacturing_output_agent
        from langgraph.graph import END
        
        result = await manufacturing_output_agent(sample_state, sample_config)
        
        assert result["current_agent"] == END
        assert sample_state.design_complete is True
        assert len(sample_state.manufacturing_files) == 7  # All expected output files
        
        # Check file types
        file_extensions = [os.path.splitext(f)[1] for f in sample_state.manufacturing_files]
        expected_extensions = [".gtl", ".gbl", ".gto", ".gbo", ".gm1", ".drl", ".csv"]
        assert all(ext in file_extensions for ext in expected_extensions)
        
        mock_makedirs.assert_called_once_with("test_output", exist_ok=True)
        
        # Check that a message was added and design is complete
        assert len(sample_state.messages) == 2
        assert isinstance(sample_state.messages[-1], AIMessage)
    
    def test_graph_exists(self):
        """Test that the graph is properly constructed and accessible."""
        from agent.graph import graph, workflow
        
        assert graph is not None
        assert workflow is not None
        assert hasattr(graph, 'name')
        assert graph.name == "Othertales Q PCB Design"
    
    @pytest.mark.asyncio
    async def test_error_handling_file_operations(self, sample_state, sample_config):
        """Test error handling in file operations."""
        from agent.graph import schematic_design_agent
        
        with patch('os.makedirs', side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                await schematic_design_agent(sample_state, sample_config)
    
    def test_configuration_from_runnable_config(self, sample_config):
        """Test configuration extraction from RunnableConfig."""
        from agent.graph import user_interface_agent
        
        # This tests that Configuration.from_runnable_config works in the context
        config = Configuration.from_runnable_config(sample_config)
        assert config.model_name == "test-model"
        assert config.output_dir == "test_output"
        assert config.max_new_tokens == 256
    
    def test_state_message_processing(self, sample_state):
        """Test that state properly processes messages."""
        # Test with HumanMessage
        assert len(sample_state.messages) == 1
        assert isinstance(sample_state.messages[0], HumanMessage)
        assert sample_state.messages[0].content == "I need a PCB for an LED circuit"
        
        # Add an AI message
        sample_state.messages.append(AIMessage(content="Processing request"))
        assert len(sample_state.messages) == 2
        assert isinstance(sample_state.messages[-1], AIMessage)
    
    def test_component_data_structure(self, sample_state):
        """Test component data structure handling."""
        # Initially empty
        assert sample_state.components == []
        
        # Add component data
        component_data = {
            "text": "Component analysis: LED (5mm, red), Resistor (220Ω), Battery (9V)"
        }
        sample_state.components.append(component_data)
        
        assert len(sample_state.components) == 1
        assert "LED" in sample_state.components[0]["text"]
        assert "Resistor" in sample_state.components[0]["text"]
    
    def test_simulation_results_structure(self, sample_state):
        """Test simulation results data structure."""
        # Initially empty
        assert sample_state.simulation_results == {}
        
        # Add simulation data
        sample_state.simulation_results = {
            "design_rule_check": "PASS",
            "signal_integrity": "GOOD",
            "thermal_analysis": "ACCEPTABLE"
        }
        
        assert sample_state.simulation_results["design_rule_check"] == "PASS"
        assert sample_state.simulation_results["signal_integrity"] == "GOOD"
        assert sample_state.simulation_results["thermal_analysis"] == "ACCEPTABLE"
    
    def test_manufacturing_files_list(self, sample_state):
        """Test manufacturing files list handling."""
        # Initially empty
        assert sample_state.manufacturing_files == []
        
        # Add files
        files = [
            "design.gtl", "design.gbl", "design.gto", 
            "design.gbo", "design.gm1", "design.drl", "design.csv"
        ]
        sample_state.manufacturing_files = files
        
        assert len(sample_state.manufacturing_files) == 7
        assert all(f.startswith("design.") for f in sample_state.manufacturing_files)