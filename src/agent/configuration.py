# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""Define the configurable parameters for the PCB design agent."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Optional, Dict, Any

from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:
    """The configuration for the PCB design agent."""

    # LLM model configuration
    model_name: str = "openai/gpt-oss-120b"  # Harmony chat format compatible model
    chat_format: str = "harmony"  # Chat format for the model
    
    # HuggingFace Pipeline settings
    max_new_tokens: int = 512
    temperature: float = 0.7
    do_sample: bool = True
    top_k: int = 50
    top_p: float = 0.95
    repetition_penalty: float = 1.2
    
    # Device configuration (-1 for CPU, 0+ for specific GPU)
    device: int = -1
    
    # Output directory for generated files
    output_dir: str = "output"
    
    # KiCad configuration
    use_kicad_api: bool = False
    
    # Component database configuration
    component_db_path: str = "component_db"
    
    # Default board dimensions (in mm)
    default_board_width: float = 100.0
    default_board_height: float = 80.0
    
    # Simulation parameters
    run_simulations: bool = True
    simulation_detail_level: str = "standard"  # "basic", "standard", or "detailed"

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        configurable = (config.get("configurable") or {}) if config else {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})