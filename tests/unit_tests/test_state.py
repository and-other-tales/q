# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import pytest
from typing import List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from src.agent.state import State


def test_state_default_initialization() -> None:
    """Test that State initializes with correct default values."""
    state = State()
    
    assert state.user_requirements == ""
    assert state.components == []
    assert state.schematic_file == ""
    assert state.pcb_file == ""
    assert state.manufacturing_files == []
    assert state.simulation_results == {}
    assert state.messages == []
    assert state.current_agent == "user_interface"
    assert state.design_complete is False


def test_state_custom_initialization() -> None:
    """Test State initialization with custom values."""
    components = [{"name": "resistor", "value": "1k"}]
    manufacturing_files = ["file1.gbr", "file2.gbr"]
    simulation_results = {"drc": "pass", "signal_integrity": "good"}
    messages: List[BaseMessage] = [HumanMessage(content="Test message")]
    
    state = State(
        user_requirements="Design a simple circuit",
        components=components,
        schematic_file="test.sch",
        pcb_file="test.kicad_pcb",
        manufacturing_files=manufacturing_files,
        simulation_results=simulation_results,
        messages=messages,
        current_agent="component_research",
        design_complete=True
    )
    
    assert state.user_requirements == "Design a simple circuit"
    assert state.components == components
    assert state.schematic_file == "test.sch"
    assert state.pcb_file == "test.kicad_pcb"
    assert state.manufacturing_files == manufacturing_files
    assert state.simulation_results == simulation_results
    assert state.messages == messages
    assert state.current_agent == "component_research"
    assert state.design_complete is True


def test_state_mutable_defaults() -> None:
    """Test that mutable default values are properly isolated between instances."""
    state1 = State()
    state2 = State()
    
    # Modify lists in state1
    state1.components.append({"name": "capacitor"})
    state1.manufacturing_files.append("gerber.gbr")
    state1.simulation_results["test"] = "value"
    state1.messages.append(HumanMessage(content="Hello"))
    
    # state2 should remain unaffected
    assert state2.components == []
    assert state2.manufacturing_files == []
    assert state2.simulation_results == {}
    assert state2.messages == []


def test_state_components_manipulation() -> None:
    """Test manipulation of components list."""
    state = State()
    
    # Add components
    resistor = {"type": "resistor", "value": "10k", "package": "0805"}
    capacitor = {"type": "capacitor", "value": "100nF", "package": "0603"}
    
    state.components.append(resistor)
    state.components.append(capacitor)
    
    assert len(state.components) == 2
    assert state.components[0] == resistor
    assert state.components[1] == capacitor
    
    # Remove component
    state.components.remove(resistor)
    assert len(state.components) == 1
    assert state.components[0] == capacitor


def test_state_messages_types() -> None:
    """Test different types of messages in the messages list."""
    state = State()
    
    human_msg = HumanMessage(content="User input")
    ai_msg = AIMessage(content="AI response")
    system_msg = SystemMessage(content="System message")
    
    state.messages.extend([human_msg, ai_msg, system_msg])
    
    assert len(state.messages) == 3
    assert isinstance(state.messages[0], HumanMessage)
    assert isinstance(state.messages[1], AIMessage)
    assert isinstance(state.messages[2], SystemMessage)
    assert state.messages[0].content == "User input"
    assert state.messages[1].content == "AI response"
    assert state.messages[2].content == "System message"


def test_state_simulation_results_structure() -> None:
    """Test complex simulation results structure."""
    state = State()
    
    complex_results = {
        "design_rule_check": {
            "status": "PASS",
            "violations": [],
            "warnings": ["Minor clearance issue"]
        },
        "signal_integrity": {
            "max_crosstalk": -40.5,
            "units": "dB",
            "critical_nets": ["CLK", "DATA"]
        },
        "thermal_analysis": {
            "max_temperature": 65.2,
            "hotspots": [{"component": "U1", "temp": 65.2}]
        }
    }
    
    state.simulation_results = complex_results
    
    assert state.simulation_results["design_rule_check"]["status"] == "PASS"
    assert len(state.simulation_results["design_rule_check"]["warnings"]) == 1
    assert state.simulation_results["signal_integrity"]["max_crosstalk"] == -40.5
    assert state.simulation_results["thermal_analysis"]["max_temperature"] == 65.2


def test_state_manufacturing_files_paths() -> None:
    """Test manufacturing files with various path formats."""
    state = State()
    
    files = [
        "/absolute/path/design.gtl",
        "relative/path/design.gbl",
        "design.gto",
        "C:\\windows\\path\\design.drl",
        "/path/with spaces/design.csv"
    ]
    
    state.manufacturing_files = files
    
    assert len(state.manufacturing_files) == 5
    assert state.manufacturing_files[0] == "/absolute/path/design.gtl"
    assert state.manufacturing_files[4] == "/path/with spaces/design.csv"


def test_state_agent_transitions() -> None:
    """Test valid agent state transitions."""
    state = State()
    
    # Test agent progression
    agents = [
        "user_interface",
        "component_research", 
        "schematic_design",
        "pcb_layout",
        "simulation",
        "manufacturing_output"
    ]
    
    for agent in agents:
        state.current_agent = agent
        assert state.current_agent == agent


def test_state_requirements_edge_cases() -> None:
    """Test user requirements with edge cases."""
    state = State()
    
    # Empty string
    state.user_requirements = ""
    assert state.user_requirements == ""
    
    # Very long string
    long_requirements = "A" * 10000
    state.user_requirements = long_requirements
    assert len(state.user_requirements) == 10000
    
    # Special characters
    special_requirements = "Design with 5V ±10% tolerance, 100kΩ resistors, and µF capacitors"
    state.user_requirements = special_requirements
    assert state.user_requirements == special_requirements
    
    # Multiline requirements
    multiline_requirements = """Design a multi-layer PCB with:
    - STM32 microcontroller
    - USB interface
    - Power management
    """
    state.user_requirements = multiline_requirements
    assert "\n" in state.user_requirements


def test_state_file_paths_validation() -> None:
    """Test file path handling for various formats."""
    state = State()
    
    # Unix-style paths
    state.schematic_file = "/home/user/project/design.sch"
    state.pcb_file = "/home/user/project/design.kicad_pcb"
    
    assert state.schematic_file.endswith(".sch")
    assert state.pcb_file.endswith(".kicad_pcb")
    
    # Windows-style paths
    state.schematic_file = "C:\\Projects\\PCB\\design.sch"
    assert "\\" in state.schematic_file
    
    # Relative paths
    state.pcb_file = "output/design.kicad_pcb"
    assert not state.pcb_file.startswith("/")


def test_state_design_complete_flag() -> None:
    """Test design complete flag behavior."""
    state = State()
    
    # Initially False
    assert state.design_complete is False
    
    # Can be set to True
    state.design_complete = True
    assert state.design_complete is True
    
    # Can be toggled back
    state.design_complete = False
    assert state.design_complete is False


def test_state_component_data_structures() -> None:
    """Test various component data structures."""
    state = State()
    
    # Simple component
    simple_component = {"name": "R1", "value": "1k"}
    
    # Complex component with nested data
    complex_component = {
        "designator": "U1",
        "part_number": "STM32F4xx",
        "manufacturer": "STMicroelectronics",
        "specifications": {
            "voltage": {"min": 1.8, "max": 3.6},
            "current": {"typical": 100, "max": 150},
            "temperature": {"min": -40, "max": 85}
        },
        "pins": [
            {"number": 1, "name": "VDD", "type": "power"},
            {"number": 2, "name": "GND", "type": "ground"}
        ]
    }
    
    state.components = [simple_component, complex_component]
    
    assert len(state.components) == 2
    assert state.components[0]["name"] == "R1"
    assert state.components[1]["designator"] == "U1"
    assert state.components[1]["specifications"]["voltage"]["max"] == 3.6
    assert len(state.components[1]["pins"]) == 2