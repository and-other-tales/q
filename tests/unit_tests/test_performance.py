# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import pytest
import time
import asyncio
from unittest.mock import patch, Mock
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from agent.state import State
from agent.configuration import Configuration


class TestPerformanceAndStress:
    """Performance and stress tests for the PCB design agent."""
    
    def test_large_user_requirements(self):
        """Test handling of very large user requirements."""
        state = State()
        
        # Create a very large requirements string (10KB)
        large_req = "Design a complex multi-board PCB system for industrial automation: " + "A" * 10000  # Large content
        
        state.user_requirements = large_req
        
        # Should handle large input without issues
        assert len(state.user_requirements) > 10000
        assert state.user_requirements.startswith("Design a complex")
    
    def test_many_components(self):
        """Test handling of a large number of components."""
        state = State()
        
        # Add 1000 components
        for i in range(1000):
            component = {
                "designator": f"U{i}",
                "part_number": f"IC-{i:04d}",
                "type": "integrated_circuit",
                "package": "QFP-64",
                "specifications": {
                    "voltage": 3.3,
                    "current": 0.1,
                    "frequency": 100e6
                }
            }
            state.components.append(component)
        
        assert len(state.components) == 1000
        assert state.components[0]["designator"] == "U0"
        assert state.components[999]["designator"] == "U999"
    
    def test_large_message_history(self):
        """Test handling of large message history."""
        state = State()
        
        # Add 500 messages (alternating human and AI)
        for i in range(250):
            state.messages.append(HumanMessage(content=f"User message {i}"))
            state.messages.append(AIMessage(content=f"AI response {i}"))
        
        assert len(state.messages) == 500
        assert isinstance(state.messages[0], HumanMessage)
        assert isinstance(state.messages[1], AIMessage)
        assert isinstance(state.messages[-1], AIMessage)
    
    def test_complex_simulation_results(self):
        """Test handling of complex simulation data structures."""
        state = State()
        
        # Create complex nested simulation results
        complex_sim = {
            "design_rule_check": {
                "violations": [
                    {
                        "type": "clearance",
                        "severity": "error",
                        "location": {"x": 12.5, "y": 8.3},
                        "description": "Trace too close to via",
                        "rule": "min_clearance_0.1mm"
                    }
                ] * 100,  # 100 violations
                "warnings": [
                    {
                        "type": "silkscreen",
                        "severity": "warning", 
                        "location": {"x": 15.2, "y": 10.1},
                        "description": "Text overlaps component"
                    }
                ] * 50   # 50 warnings
            },
            "signal_integrity": {
                "nets": {f"NET_{i}": {
                    "impedance": 50.0 + i * 0.1,
                    "length": 10.0 + i * 0.5,
                    "crosstalk": -40.0 - i * 0.2
                } for i in range(200)}  # 200 nets
            },
            "thermal_analysis": {
                "components": {f"U{i}": {
                    "temperature": 45.0 + i * 0.3,
                    "power": 0.5 + i * 0.01,
                    "thermal_resistance": 20.0 + i * 0.1
                } for i in range(100)}  # 100 components
            }
        }
        
        state.simulation_results = complex_sim
        
        assert len(state.simulation_results["design_rule_check"]["violations"]) == 100
        assert len(state.simulation_results["signal_integrity"]["nets"]) == 200
        assert len(state.simulation_results["thermal_analysis"]["components"]) == 100
    
    def test_many_manufacturing_files(self):
        """Test handling of large numbers of manufacturing files."""
        state = State()
        
        # Simulate a complex multi-board design with many files
        file_types = ["gtl", "gbl", "gto", "gbo", "gts", "gbs", "gm1", "gm2", "gm3", "drl"]
        
        # 10 boards, each with all file types
        for board in range(10):
            for file_type in file_types:
                filename = f"board_{board:02d}.{file_type}"
                state.manufacturing_files.append(filename)
        
        # Add BOM and assembly files
        for board in range(10):
            state.manufacturing_files.append(f"board_{board:02d}_bom.csv")
            state.manufacturing_files.append(f"board_{board:02d}_assembly.pdf")
        
        assert len(state.manufacturing_files) == 120  # 10 boards * 12 files each
    
    def test_configuration_with_extreme_values(self):
        """Test configuration with extreme but valid values."""
        config = Configuration(
            max_new_tokens=4096,  # Very large
            temperature=0.0,      # Minimum
            top_k=1,              # Minimum  
            top_p=1.0,            # Maximum
            repetition_penalty=2.0,  # High value
            default_board_width=1000.0,   # Very large board
            default_board_height=1000.0
        )
        
        assert config.max_new_tokens == 4096
        assert config.temperature == 0.0
        assert config.top_k == 1
        assert config.top_p == 1.0
        assert config.repetition_penalty == 2.0
        assert config.default_board_width == 1000.0
        assert config.default_board_height == 1000.0
    
    def test_memory_efficiency_large_state(self):
        """Test memory efficiency with large state objects."""
        import sys
        
        # Create a large state
        state = State()
        
        # Add substantial data
        for i in range(100):
            state.components.append({
                "id": i,
                "data": "x" * 1000  # 1KB per component
            })
        
        for i in range(50):
            state.messages.append(HumanMessage(content="x" * 2000))  # 2KB per message
            state.messages.append(AIMessage(content="x" * 2000))
        
        # The state should exist and be usable
        assert len(state.components) == 100
        assert len(state.messages) == 100
        
        # Basic memory check - state should be reasonable size
        # This is a rough check, actual size may vary
        state_size = sys.getsizeof(state)
        assert state_size < 10 * 1024 * 1024  # Less than 10MB
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_operations(self):
        """Test concurrent operations on different agents."""
        from agent.graph import schematic_design_agent, pcb_layout_agent
        
        # Create multiple states
        states = [State() for _ in range(5)]
        configs = [RunnableConfig(configurable={"output_dir": f"output_{i}"}) for i in range(5)]
        
        # Add messages to each state
        for i, state in enumerate(states):
            state.messages.append(HumanMessage(content=f"Design PCB {i}"))
        
        # Run agents concurrently
        with patch('os.makedirs'):
            tasks = []
            for state, config in zip(states, configs):
                task = schematic_design_agent(state, config)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 5
        for result in results:
            assert result["current_agent"] == "pcb_layout"
    
    def test_string_processing_performance(self):
        """Test performance of string processing with large inputs."""
        import time
        
        # Large user requirements
        large_text = "Design a PCB with " + "microcontroller and sensor " * 1000
        
        state = State()
        
        start_time = time.time()
        state.user_requirements = large_text
        end_time = time.time()
        
        # Should be very fast (under 1 second)
        processing_time = end_time - start_time
        assert processing_time < 1.0
        
        # Verify the data is correct
        assert len(state.user_requirements) > 20000
        assert "microcontroller" in state.user_requirements
    
    def test_state_serialization_size(self):
        """Test that state objects don't grow unreasonably large."""
        import pickle
        
        state = State()
        
        # Add typical data
        state.user_requirements = "Design a 4-layer PCB for IoT device"
        state.components = [
            {"type": "mcu", "part": "ESP32"},
            {"type": "sensor", "part": "BME280"},
            {"type": "resistor", "part": "0805"}
        ]
        state.messages = [
            HumanMessage(content="Design request"),
            AIMessage(content="Analysis complete")
        ]
        state.simulation_results = {
            "drc": "PASS",
            "signal_integrity": "GOOD"
        }
        state.manufacturing_files = [
            "design.gtl", "design.gbl", "design.drl"
        ]
        
        # Test JSON serialization as a proxy for data size efficiency
        import json
        from dataclasses import asdict
        
        # Convert to dict for JSON serialization (excluding messages which have complex objects)
        state_dict = {
            "user_requirements": state.user_requirements,
            "components": state.components,
            "simulation_results": state.simulation_results,
            "manufacturing_files": state.manufacturing_files,
            "current_agent": state.current_agent,
            "design_complete": state.design_complete
        }
        serialized = json.dumps(state_dict)
        
        # Should be reasonable size (under 10KB for typical data)
        assert len(serialized) < 10 * 1024
        
        # Should be deserializable  
        deserialized_dict = json.loads(serialized)
        assert deserialized_dict["user_requirements"] == state.user_requirements
        assert len(deserialized_dict["components"]) == len(state.components)
    
    def test_nested_data_structure_depth(self):
        """Test handling of deeply nested data structures."""
        state = State()
        
        # Create deeply nested structure
        nested_data = {"level_0": {}}
        current_level = nested_data["level_0"]
        
        # Create 20 levels of nesting
        for i in range(1, 20):
            current_level[f"level_{i}"] = {}
            current_level = current_level[f"level_{i}"]
        
        current_level["data"] = "deep_value"
        
        state.simulation_results = nested_data
        
        # Should handle deep nesting
        assert state.simulation_results["level_0"]["level_1"]["level_2"] is not None
        
        # Should be able to access the deep value
        deep_value = state.simulation_results
        for i in range(20):
            deep_value = deep_value[f"level_{i}"]
        assert deep_value["data"] == "deep_value"