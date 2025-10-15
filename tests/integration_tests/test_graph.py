# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent import graph
from agent.state import State
from agent.configuration import Configuration


class TestIntegrationGraph:
    """Integration tests for the graph workflow."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture 
    def mock_llm_pipeline(self):
        """Mock the HuggingFace pipeline to avoid loading actual models."""
        with patch('agent.graph.HuggingFacePipeline.from_model_id') as mock:
            mock_llm = Mock()
            mock.return_value = mock_llm
            yield mock_llm
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self) -> None:
        """Test that the agent can be initialized."""
        state = State()
        result = await graph.ainvoke(state)
        assert result is not None
    
    @pytest.mark.asyncio 
    async def test_agent_with_user_message(self, mock_llm_pipeline) -> None:
        """Test that the agent processes a user message."""
        # Mock the LangChain pipeline to avoid actual LLM calls
        async def mock_ainvoke(*args, **kwargs):
            return "Mocked analysis result"
        
        # Create a mock chain that can be awaited
        mock_chain = Mock()
        mock_chain.ainvoke = mock_ainvoke
        
        with patch('agent.graph.PromptTemplate') as mock_prompt_cls, \
             patch('agent.graph.StrOutputParser') as mock_parser_cls:
            
            # Setup pipeline mocking
            mock_prompt = Mock()
            mock_prompt.__or__ = Mock(return_value=mock_chain)
            mock_prompt_cls.from_template.return_value = mock_prompt
            
            mock_parser = Mock()
            mock_parser_cls.return_value = mock_parser
            
            mock_bound_llm = Mock()
            mock_bound_llm.__or__ = Mock(return_value=mock_chain)
            mock_llm_pipeline.bind.return_value = mock_bound_llm
            
            state = State()
            state.messages.append(HumanMessage(content="I need a PCB for an Arduino temperature monitor."))
            
            result = await graph.ainvoke(state)
            
            assert result is not None
            # Result should be the final state which was passed through the workflow
            # LangGraph returns state as dict, so access as dict keys
            assert 'design_complete' in result
            assert result['design_complete'] is True
            assert result['schematic_file'] != ""
            assert result['pcb_file'] != ""
            assert len(result['manufacturing_files']) > 0
            assert len(result['messages']) > 1
    
    @pytest.mark.asyncio
    async def test_configuration_handling(self, temp_output_dir, mock_llm_pipeline):
        """Test that configuration is properly handled throughout the workflow."""
        async def mock_ainvoke(*args, **kwargs):
            return "Mocked analysis result"
        
        mock_chain = Mock()
        mock_chain.ainvoke = mock_ainvoke
        
        with patch('agent.graph.PromptTemplate') as mock_prompt_cls, \
             patch('agent.graph.StrOutputParser') as mock_parser_cls:
            
            mock_prompt = Mock()
            mock_prompt.__or__ = Mock(return_value=mock_chain)
            mock_prompt_cls.from_template.return_value = mock_prompt
            
            mock_parser = Mock()
            mock_parser_cls.return_value = mock_parser
            
            mock_bound_llm = Mock()
            mock_bound_llm.__or__ = Mock(return_value=mock_chain)
            mock_llm_pipeline.bind.return_value = mock_bound_llm
            
            config = RunnableConfig(configurable={
                "output_dir": temp_output_dir,
                "model_name": "test-model",
                "run_simulations": True,
                "simulation_detail_level": "detailed"
            })
            
            state = State()
            state.messages.append(HumanMessage(content="Design a microcontroller PCB."))
            
            result = await graph.ainvoke(state, config=config)
            
            assert result['design_complete'] is True
            assert temp_output_dir in result['schematic_file']
            assert temp_output_dir in result['pcb_file']
            # Check simulation was run
            assert len(result['simulation_results']) > 0
    
    @pytest.mark.asyncio
    async def test_disabled_simulations(self, temp_output_dir, mock_llm_pipeline):
        """Test workflow with simulations disabled."""
        async def mock_ainvoke(*args, **kwargs):
            return "Mocked analysis result"
        
        mock_chain = Mock()
        mock_chain.ainvoke = mock_ainvoke
        
        with patch('agent.graph.PromptTemplate') as mock_prompt_cls, \
             patch('agent.graph.StrOutputParser') as mock_parser_cls:
            
            mock_prompt = Mock()
            mock_prompt.__or__ = Mock(return_value=mock_chain)
            mock_prompt_cls.from_template.return_value = mock_prompt
            
            mock_parser = Mock()
            mock_parser_cls.return_value = mock_parser
            
            mock_bound_llm = Mock()
            mock_bound_llm.__or__ = Mock(return_value=mock_chain)
            mock_llm_pipeline.bind.return_value = mock_bound_llm
            
            config = RunnableConfig(configurable={
                "output_dir": temp_output_dir,
                "run_simulations": False
            })
            
            state = State()
            state.messages.append(HumanMessage(content="Design a simple LED circuit."))
            
            result = await graph.ainvoke(state, config=config)
            
            assert result['design_complete'] is True
            # Simulations should be skipped but design should still complete
            assert result['simulation_results'] == {}
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, mock_llm_pipeline):
        """Test that the workflow can handle errors gracefully."""
        async def mock_ainvoke(*args, **kwargs):
            return "Mocked analysis result"
        
        mock_chain = Mock()
        mock_chain.ainvoke = mock_ainvoke
        
        with patch('agent.graph.PromptTemplate') as mock_prompt_cls, \
             patch('agent.graph.StrOutputParser') as mock_parser_cls, \
             patch('os.makedirs', side_effect=OSError("Disk full")) as mock_makedirs:
            
            mock_prompt = Mock()
            mock_prompt.__or__ = Mock(return_value=mock_chain)
            mock_prompt_cls.from_template.return_value = mock_prompt
            
            mock_parser = Mock()
            mock_parser_cls.return_value = mock_parser
            
            mock_bound_llm = Mock()
            mock_bound_llm.__or__ = Mock(return_value=mock_chain)
            mock_llm_pipeline.bind.return_value = mock_bound_llm
            
            state = State()
            state.messages.append(HumanMessage(content="Design a PCB."))
            
            # The workflow should fail at the schematic design stage
            with pytest.raises(OSError):
                await graph.ainvoke(state)
    
    @pytest.mark.asyncio 
    async def test_state_transitions(self, mock_llm_pipeline):
        """Test that state transitions work correctly through the workflow."""
        async def mock_ainvoke(*args, **kwargs):
            return "Mocked analysis result"
        
        mock_chain = Mock()
        mock_chain.ainvoke = mock_ainvoke
        
        with patch('agent.graph.PromptTemplate') as mock_prompt_cls, \
             patch('agent.graph.StrOutputParser') as mock_parser_cls:
            
            mock_prompt = Mock()
            mock_prompt.__or__ = Mock(return_value=mock_chain)
            mock_prompt_cls.from_template.return_value = mock_prompt
            
            mock_parser = Mock()
            mock_parser_cls.return_value = mock_parser
            
            mock_bound_llm = Mock()
            mock_bound_llm.__or__ = Mock(return_value=mock_chain)
            mock_llm_pipeline.bind.return_value = mock_bound_llm
            
            state = State()
            state.messages.append(HumanMessage(content="Design a sensor interface PCB."))
            
            # Track the initial state
            initial_agent = state.current_agent
            assert initial_agent == "user_interface"
            
            result = await graph.ainvoke(state)
            
            # Verify the workflow completed
            assert result['design_complete'] is True
            assert result['current_agent'] != initial_agent
    
    @pytest.mark.asyncio
    async def test_complex_requirements(self, temp_output_dir, mock_llm_pipeline):
        """Test with complex PCB requirements."""
        async def mock_ainvoke(*args, **kwargs):
            return "Complex PCB analysis with multiple components"
        
        mock_chain = Mock()
        mock_chain.ainvoke = mock_ainvoke
        
        with patch('agent.graph.PromptTemplate') as mock_prompt_cls, \
             patch('agent.graph.StrOutputParser') as mock_parser_cls:
            
            mock_prompt = Mock()
            mock_prompt.__or__ = Mock(return_value=mock_chain)
            mock_prompt_cls.from_template.return_value = mock_prompt
            
            mock_parser = Mock()
            mock_parser_cls.return_value = mock_parser
            
            mock_bound_llm = Mock()
            mock_bound_llm.__or__ = Mock(return_value=mock_chain)
            mock_llm_pipeline.bind.return_value = mock_bound_llm
            
            complex_requirements = """
            Design a 4-layer PCB for a data acquisition system with:
            - STM32F4 microcontroller
            - 16-bit ADC with differential inputs
            - USB 2.0 interface
            - microSD card slot
            - Multiple voltage rails (3.3V, 1.8V, VREF)
            - EMI/EMC compliance required
            - Operating temperature: -40°C to +85°C
            """
            
            config = RunnableConfig(configurable={
                "output_dir": temp_output_dir,
                "simulation_detail_level": "detailed"
            })
            
            state = State()
            state.messages.append(HumanMessage(content=complex_requirements))
            
            result = await graph.ainvoke(state, config=config)
            
            assert result['design_complete'] is True
            assert len(result['messages']) > 1
            assert len(result['components']) > 0
            assert len(result['manufacturing_files']) == 7  # All expected files
            assert result['simulation_results']  # Should have simulation data
    
    @pytest.mark.asyncio
    async def test_manufacturing_file_generation(self, temp_output_dir, mock_llm_pipeline):
        """Test that all manufacturing files are generated correctly."""
        async def mock_ainvoke(*args, **kwargs):
            return "Manufacturing analysis complete"
        
        mock_chain = Mock()
        mock_chain.ainvoke = mock_ainvoke
        
        with patch('agent.graph.PromptTemplate') as mock_prompt_cls, \
             patch('agent.graph.StrOutputParser') as mock_parser_cls:
            
            mock_prompt = Mock()
            mock_prompt.__or__ = Mock(return_value=mock_chain)
            mock_prompt_cls.from_template.return_value = mock_prompt
            
            mock_parser = Mock()
            mock_parser_cls.return_value = mock_parser
            
            mock_bound_llm = Mock()
            mock_bound_llm.__or__ = Mock(return_value=mock_chain)
            mock_llm_pipeline.bind.return_value = mock_bound_llm
            
            config = RunnableConfig(configurable={"output_dir": temp_output_dir})
            
            state = State()
            state.messages.append(HumanMessage(content="Design a simple PCB."))
            
            result = await graph.ainvoke(state, config=config)
            
            # Verify all expected manufacturing files
            expected_extensions = [".gtl", ".gbl", ".gto", ".gbo", ".gm1", ".drl", ".csv"]
            actual_extensions = [os.path.splitext(f)[1] for f in result['manufacturing_files']]
            
            for ext in expected_extensions:
                assert ext in actual_extensions, f"Missing manufacturing file with extension {ext}"
            
            # Verify files are in the correct output directory
            for file_path in result['manufacturing_files']:
                assert temp_output_dir in file_path
    
    def test_graph_metadata(self):
        """Test graph metadata and configuration."""
        assert hasattr(graph, 'name')
        assert graph.name == "Othertales Q PCB Design"
        
        # Test that the graph is compiled and ready
        assert graph is not None
        
        # Test that we can get basic information about the graph
        # Note: LangGraph's internal structure may vary, so we test what we can
        assert callable(graph.ainvoke)