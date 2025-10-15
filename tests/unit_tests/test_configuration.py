# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import pytest
from langchain_core.runnables import RunnableConfig
from src.agent.configuration import Configuration


def test_configuration_empty() -> None:
    """Test that configuration can be created with empty input."""
    config = Configuration.from_runnable_config({})
    assert config.model_name == "openai/gpt-oss-120b"
    assert config.output_dir == "output"
    assert config.use_kicad_api is False
    assert config.max_new_tokens == 512
    assert config.device == -1  # Default to CPU


def test_configuration_with_values() -> None:
    """Test that configuration respects provided values."""
    runnable_config = RunnableConfig(configurable={
        "model_name": "gpt2-large",
        "output_dir": "test-outpgit ut",
        "use_kicad_api": True,
        "default_board_width": 50.0,
        "device": 0,  # Use GPU
        "max_new_tokens": 256
    })
    
    config = Configuration.from_runnable_config(runnable_config)
    assert config.model_name == "gpt2-large"
    assert config.output_dir == "test-output"
    assert config.use_kicad_api is True
    assert config.default_board_width == 50.0
    assert config.device == 0
    assert config.max_new_tokens == 256
    # Default values for fields not in the provided config
    assert config.default_board_height == 80.0


def test_configuration_none_input() -> None:
    """Test that configuration works with invalid config types."""
    config = Configuration.from_runnable_config(RunnableConfig(configurable={"other_key": "other_value"}))


def test_configuration_missing_configurable_key() -> None:
    """Test configuration with runnable_config but no 'configurable' key."""
    config = Configuration.from_runnable_config({})
    assert config.model_name == "openai/gpt-oss-120b"
    assert config.output_dir == "output"
    assert config.use_kicad_api is False


def test_configuration_partial_values() -> None:
    """Test that configuration works with partial configuration values."""
    runnable_config = RunnableConfig(configurable={
        "temperature": 0.9,
        "top_k": 25,
        "component_db_path": "custom_components"
    })
    
    config = Configuration.from_runnable_config(runnable_config)
    # Changed values
    assert config.temperature == 0.9
    assert config.top_k == 25
    assert config.component_db_path == "custom_components"
    # Default values for unchanged fields
    assert config.model_name == "openai/gpt-oss-120b"
    assert config.max_new_tokens == 512
    assert config.use_kicad_api is False


def test_configuration_all_values() -> None:
    """Test that configuration works with all configurable values."""
    runnable_config = RunnableConfig(configurable={
        "model_name": "custom-model",
        "max_new_tokens": 1024,
        "temperature": 0.8,
        "do_sample": False,
        "top_k": 30,
        "top_p": 0.9,
        "repetition_penalty": 1.1,
        "device": 1,
        "output_dir": "custom-output",
        "use_kicad_api": True,
        "component_db_path": "components",
        "default_board_width": 120.0,
        "default_board_height": 100.0,
        "run_simulations": False,
        "simulation_detail_level": "detailed"
    })
    
    config = Configuration.from_runnable_config(runnable_config)
    
    config = Configuration.from_runnable_config(runnable_config)
    assert config.model_name == "custom-model"
    assert config.max_new_tokens == 1024
    assert config.temperature == 0.8
    assert config.do_sample is False
    assert config.top_k == 30
    assert config.top_p == 0.9
    assert config.repetition_penalty == 1.1
    assert config.device == 1
    assert config.output_dir == "custom-output"
    assert config.use_kicad_api is True
    assert config.component_db_path == "components"
    assert config.default_board_width == 120.0
    assert config.default_board_height == 100.0
    assert config.run_simulations is False
    assert config.simulation_detail_level == "detailed"


def test_configuration_default_values() -> None:
    """Test all default values are as expected."""
    config = Configuration()
    assert config.model_name == "openai/gpt-oss-120b"
    assert config.max_new_tokens == 512
    assert config.temperature == 0.7
    assert config.do_sample is True
    assert config.top_k == 50
    assert config.top_p == 0.95
    assert config.repetition_penalty == 1.2
    assert config.device == -1
    assert config.output_dir == "output"
    assert config.use_kicad_api is False
    assert config.component_db_path == "component_db"
    assert config.default_board_width == 100.0
    assert config.default_board_height == 80.0
    assert config.run_simulations is True
    assert config.simulation_detail_level == "standard"


def test_configuration_invalid_fields_ignored() -> None:
    """Test that invalid/unknown fields are ignored."""
    runnable_config = RunnableConfig(configurable={
        "model_name": "valid-model",
        "invalid_field": "should_be_ignored",
        "another_invalid": 123,
        "max_new_tokens": 256
    })
    
    config = Configuration.from_runnable_config(runnable_config)
    assert config.model_name == "valid-model"
    assert config.max_new_tokens == 256
    # Should not have invalid fields
    assert not hasattr(config, "invalid_field")
    assert not hasattr(config, "another_invalid")


def test_configuration_edge_values() -> None:
    """Test that configuration works with edge case values."""
    runnable_config = RunnableConfig(configurable={
        "max_new_tokens": 1,
        "temperature": 0.0,
        "top_k": 1,
        "top_p": 0.01,
        "repetition_penalty": 1.0,
        "device": -1,
        "default_board_width": 0.1,
        "default_board_height": 0.1
    })
    
    config = Configuration.from_runnable_config(runnable_config)
    assert config.max_new_tokens == 1
    assert config.temperature == 0.0
    assert config.top_k == 1
    assert config.top_p == 0.01
    assert config.repetition_penalty == 1.0
    assert config.device == -1
    assert config.default_board_width == 0.1
    assert config.default_board_height == 0.1


def test_configuration_string_types() -> None:
    """Test configuration with various string types."""
    runnable_config = RunnableConfig(configurable={
        "simulation_detail_level": "basic",
        "output_dir": "",
        "component_db_path": "/absolute/path/to/components"
    })
    
    config = Configuration.from_runnable_config(runnable_config)
    assert config.simulation_detail_level == "basic"
    assert config.output_dir == ""
    assert config.component_db_path == "/absolute/path/to/components"