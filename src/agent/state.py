# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""Define the state structures for the PCB design agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


@dataclass
class State:
    """Defines the state for the PCB design agent.
    
    This class holds the state information for the PCB design workflow,
    including user requirements, components, files, and messages history.
    """
    
    # User inputs and requirements
    user_requirements: str = ""
    
    # Component selection data
    components: List[Dict[str, Any]] = field(default_factory=list)
    
    # File paths for generated assets
    schematic_file: str = ""
    pcb_file: str = ""
    manufacturing_files: List[str] = field(default_factory=list)
    
    # Simulation and analysis results
    simulation_results: Dict[str, Any] = field(default_factory=dict)
    
    # Message history
    messages: List[BaseMessage] = field(default_factory=list)
    
    # Workflow state tracking
    current_agent: str = "user_interface"
    design_complete: bool = False