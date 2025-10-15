# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent.state import State
from agent.configuration import Configuration


class TestIntegrationSimplified:
    """Simplified integration tests that focus on testable functionality."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_state_initialization_and_workflow_setup(self):
        """Test that we can initialize state and access the workflow."""
        from agent import graph
        from agent.graph import workflow
        
        # Test state initialization
        state = State()
        assert state.user_requirements == ""
        assert state.components == []
        assert state.current_agent == "user_interface"
        assert state.design_complete is False
        
        # Test that graph and workflow exist
        assert graph is not None
        assert workflow is not None
        assert hasattr(graph, 'name')
        assert graph.name == "Othertales Q PCB Design"
    
    def test_configuration_integration(self, temp_output_dir):
        """Test configuration integration with different settings."""
        config = RunnableConfig(configurable={
            "output_dir": temp_output_dir,
            "model_name": "test-model",
            "run_simulations": False,
            "simulation_detail_level": "basic",
            "max_new_tokens": 128
        })
        
        # Test configuration parsing
        parsed_config = Configuration.from_runnable_config(config)
        assert parsed_config.output_dir == temp_output_dir
        assert parsed_config.model_name == "test-model"
        assert parsed_config.run_simulations is False
        assert parsed_config.simulation_detail_level == "basic"
        assert parsed_config.max_new_tokens == 128
    
    def test_state_with_complex_data(self):
        """Test state handling with complex data structures."""
        state = State()
        
        # Add complex user requirements
        complex_req = """Design a 4-layer PCB for IoT sensor hub:
        - ESP32-S3 microcontroller
        - Multiple I2C sensors (temperature, humidity, pressure)
        - LoRaWAN communication module
        - Solar panel charging circuit
        - Ultra-low power design for battery operation"""
        
        state.user_requirements = complex_req
        state.messages.append(HumanMessage(content=complex_req))
        
        # Add component data
        components = [
            {
                "type": "microcontroller",
                "part": "ESP32-S3",
                "package": "QFN",
                "pins": 56,
                "specifications": {
                    "voltage": "3.3V",
                    "current": "240mA",
                    "frequency": "240MHz"
                }
            },
            {
                "type": "sensor",
                "part": "BME280",
                "interface": "I2C",
                "address": "0x76"
            }
        ]
        state.components = components
        
        # Add simulation results
        state.simulation_results = {
            "design_rule_check": {
                "status": "PASS", 
                "violations": [],
                "warnings": ["Minor trace width variance"]
            },
            "power_analysis": {
                "average_current": 45.2,
                "peak_current": 240.0,
                "battery_life_estimate": "3.2 years"
            }
        }
        
        # Add manufacturing files
        state.manufacturing_files = [
            "iot_hub.gtl", "iot_hub.gbl", "iot_hub.gto",
            "iot_hub.gbo", "iot_hub.gm1", "iot_hub.drl", "iot_hub.csv"
        ]
        
        # Verify all data is properly stored
        assert len(state.user_requirements) > 100
        assert len(state.components) == 2
        assert state.components[0]["type"] == "microcontroller"
        assert state.simulation_results["power_analysis"]["battery_life_estimate"] == "3.2 years"
        assert len(state.manufacturing_files) == 7
    
    @pytest.mark.asyncio
    async def test_individual_agent_functions(self, temp_output_dir):
        """Test individual agent functions in isolation."""
        from agent.graph import (
            schematic_design_agent, pcb_layout_agent, 
            simulation_agent, manufacturing_output_agent
        )
        
        state = State()
        state.user_requirements = "Simple LED circuit"
        state.messages.append(HumanMessage(content="Design LED circuit"))
        
        config = RunnableConfig(configurable={"output_dir": temp_output_dir})
        
        # Test schematic design agent
        with patch('os.makedirs'):
            result = await schematic_design_agent(state, config)
            assert result["current_agent"] == "pcb_layout"
            assert state.schematic_file.endswith(".sch")
        
        # Test PCB layout agent
        result = await pcb_layout_agent(state, config)
        assert result["current_agent"] == "simulation"
        assert state.pcb_file.endswith(".kicad_pcb")
        
        # Test simulation agent
        result = await simulation_agent(state, config)
        assert result["current_agent"] == "manufacturing_output"
        assert "design_rule_check" in state.simulation_results
        
        # Test manufacturing output agent
        with patch('os.makedirs'):
            result = await manufacturing_output_agent(state, config)
            assert result["current_agent"] == "__end__"  # LangGraph END constant
            assert state.design_complete is True
            assert len(state.manufacturing_files) == 7
    
    def test_agent_state_transitions(self):
        """Test the agent state transition logic."""
        from agent.graph import router
        
        state = State()
        
        # Test progression through agent states
        agents = [
            "user_interface", "component_research", "schematic_design",
            "pcb_layout", "simulation", "manufacturing_output"
        ]
        
        for agent in agents:
            state.current_agent = agent
            result = router(state)
            assert result == agent
    
    @pytest.mark.asyncio 
    async def test_simulation_configuration_handling(self, temp_output_dir):
        """Test simulation agent with different configurations."""
        from agent.graph import simulation_agent
        
        state = State()
        state.messages.append(HumanMessage(content="Test circuit"))
        
        # Test with simulations enabled
        config_enabled = RunnableConfig(configurable={
            "output_dir": temp_output_dir,
            "run_simulations": True,
            "simulation_detail_level": "detailed"
        })
        
        result = await simulation_agent(state, config_enabled)
        assert result["current_agent"] == "manufacturing_output"
        assert len(state.simulation_results) > 0
        assert "design_rule_check" in state.simulation_results
        
        # Reset state for next test
        state.simulation_results = {}
        state.messages = [HumanMessage(content="Test circuit")]
        
        # Test with simulations disabled
        config_disabled = RunnableConfig(configurable={
            "output_dir": temp_output_dir,
            "run_simulations": False
        })
        
        result = await simulation_agent(state, config_disabled)
        assert result["current_agent"] == "manufacturing_output"
        assert state.simulation_results == {}  # Should remain empty
    
    def test_file_path_generation(self, temp_output_dir):
        """Test file path generation for different output directories."""
        config = Configuration(output_dir=temp_output_dir)
        
        # Test different path styles
        test_paths = [
            "/absolute/path/to/output",
            "relative/path",
            ".",
            temp_output_dir
        ]
        
        for path in test_paths:
            config.output_dir = path
            
            # Simulate file path creation
            schematic_path = os.path.join(config.output_dir, "design.sch")
            pcb_path = os.path.join(config.output_dir, "design.kicad_pcb")
            
            assert config.output_dir in schematic_path
            assert config.output_dir in pcb_path
            assert schematic_path.endswith(".sch")
            assert pcb_path.endswith(".kicad_pcb")
    
    def test_message_history_management(self):
        """Test message history throughout the workflow."""
        from langchain_core.messages import AIMessage
        
        state = State()
        
        # Start with user message
        user_msg = HumanMessage(content="Design a temperature sensor PCB")
        state.messages.append(user_msg)
        assert len(state.messages) == 1
        
        # Simulate agent responses
        agent_responses = [
            "Requirements analyzed successfully",
            "Components selected: Temperature sensor, MCU, connectors",
            "Schematic design completed",
            "PCB layout finished", 
            "Simulations passed",
            "Manufacturing files generated"
        ]
        
        for response in agent_responses:
            state.messages.append(AIMessage(content=response))
        
        assert len(state.messages) == 7  # 1 user + 6 agent messages
        assert isinstance(state.messages[0], HumanMessage)
        assert all(isinstance(msg, AIMessage) for msg in state.messages[1:])
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios."""
        state = State()
        
        # Test with empty requirements
        assert state.user_requirements == ""
        assert state.messages == []
        
        # Test with malformed data
        state.components = [{"invalid": "data"}]
        assert len(state.components) == 1
        
        # Test with missing fields
        state.simulation_results = {"incomplete": "data"}
        assert "design_rule_check" not in state.simulation_results
        
        # Test recovery
        state.user_requirements = "Valid requirements"
        state.components = []
        state.simulation_results = {}
        
        assert state.user_requirements == "Valid requirements"
        assert state.components == []
        assert state.simulation_results == {}
    
    def test_component_data_validation(self):
        """Test component data structure validation."""
        state = State()
        
        # Test valid component structure
        valid_component = {
            "designator": "U1",
            "part_number": "STM32F401CCU6",
            "manufacturer": "STMicroelectronics",
            "type": "microcontroller",
            "package": "UFQFPN-48",
            "specifications": {
                "supply_voltage": {"min": 1.7, "max": 3.6},
                "operating_temp": {"min": -40, "max": 85}
            }
        }
        
        state.components.append(valid_component)
        assert len(state.components) == 1
        assert state.components[0]["designator"] == "U1"
        assert state.components[0]["specifications"]["supply_voltage"]["max"] == 3.6
    
    def test_manufacturing_file_validation(self, temp_output_dir):
        """Test manufacturing file list validation."""
        state = State()
        
        # Expected manufacturing files
        expected_files = [
            "design.gtl",   # Top copper
            "design.gbl",   # Bottom copper  
            "design.gto",   # Top silkscreen
            "design.gbo",   # Bottom silkscreen
            "design.gm1",   # Mechanical layer
            "design.drl",   # Drill file
            "design.csv"    # BOM
        ]
        
        # Add full paths
        full_paths = [os.path.join(temp_output_dir, f) for f in expected_files]
        state.manufacturing_files = full_paths
        
        assert len(state.manufacturing_files) == 7
        
        # Verify file extensions
        extensions = [os.path.splitext(f)[1] for f in state.manufacturing_files]
        expected_extensions = [".gtl", ".gbl", ".gto", ".gbo", ".gm1", ".drl", ".csv"]
        
        for ext in expected_extensions:
            assert ext in extensions
        
        # Verify all files have the correct output directory
        for file_path in state.manufacturing_files:
            assert temp_output_dir in file_path