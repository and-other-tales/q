#!/usr/bin/env python3
# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
Comprehensive tests for agent.configuration module
Tests every function to ensure 100% coverage.
"""

import pytest
import unittest
from unittest.mock import Mock, patch
import tempfile
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent.configuration import Configuration
from langchain_core.runnables import RunnableConfig

class TestConfiguration:
    """Comprehensive tests for Configuration class."""
    
    def test_configuration_init_defaults(self):
        """Test Configuration initialization with default values."""
        config = Configuration()
        
        # Test all default values
        assert config.model_name == "openai/gpt-oss-120b"
        assert config.chat_format == "harmony"
        assert config.max_new_tokens == 512
        assert config.temperature == 0.7
        assert config.do_sample == True
        assert config.top_k == 50
        assert config.top_p == 0.95
        assert config.repetition_penalty == 1.2
        assert config.device == -1
        assert config.output_dir == "output"
        assert config.use_kicad_api == False
        assert config.component_db_path == "component_db"
        assert config.default_board_width == 100.0
        assert config.default_board_height == 80.0
        assert config.run_simulations == True
        assert config.simulation_detail_level == "standard"
    
    def test_configuration_init_custom_values(self):
        """Test Configuration initialization with custom values."""
        config = Configuration(
            model_name="custom-model",
            temperature=0.5,
            max_new_tokens=1024,
            output_dir="custom_output",
            run_simulations=False
        )
        
        assert config.model_name == "custom-model"
        assert config.temperature == 0.5
        assert config.max_new_tokens == 1024
        assert config.output_dir == "custom_output"
        assert config.run_simulations == False
        
        # Check that other defaults are preserved
        assert config.chat_format == "harmony"
        assert config.default_board_width == 100.0
    
    def test_from_runnable_config_with_valid_config(self):
        """Test from_runnable_config with valid RunnableConfig."""
        runnable_config = RunnableConfig(
            configurable={
                "model_name": "test-model",
                "temperature": 0.8,
                "output_dir": "test_output",
                "run_simulations": False,
                "max_new_tokens": 2048
            }
        )
        
        config = Configuration.from_runnable_config(runnable_config)
        
        assert config.model_name == "test-model"
        assert config.temperature == 0.8
        assert config.output_dir == "test_output"
        assert config.run_simulations == False
        assert config.max_new_tokens == 2048
        
        # Check defaults for non-specified values
        assert config.chat_format == "harmony"
        assert config.default_board_width == 100.0
    
    def test_from_runnable_config_with_none(self):
        """Test from_runnable_config with None config."""
        config = Configuration.from_runnable_config(None)
        
        # Should return default configuration
        assert config.model_name == "openai/gpt-oss-120b"
        assert config.temperature == 0.7
        assert config.chat_format == "harmony"
    
    def test_from_runnable_config_with_empty_configurable(self):
        """Test from_runnable_config with empty configurable dict."""
        runnable_config = RunnableConfig(configurable={})
        
        config = Configuration.from_runnable_config(runnable_config)
        
        # Should return default configuration
        assert config.model_name == "openai/gpt-oss-120b"
        assert config.temperature == 0.7
        assert config.chat_format == "harmony"
    
    def test_from_runnable_config_with_partial_config(self):
        """Test from_runnable_config with partial configuration."""
        runnable_config = RunnableConfig(
            configurable={
                "model_name": "partial-model",
                "temperature": 0.3
                # Missing other values
            }
        )
        
        config = Configuration.from_runnable_config(runnable_config)
        
        # Should use provided values
        assert config.model_name == "partial-model"
        assert config.temperature == 0.3
        
        # Should use defaults for missing values
        assert config.max_new_tokens == 512
        assert config.output_dir == "output"
        assert config.chat_format == "harmony"
    
    def test_configuration_field_types(self):
        """Test that all configuration fields have correct types."""
        config = Configuration()
        
        assert isinstance(config.model_name, str)
        assert isinstance(config.chat_format, str)
        assert isinstance(config.max_new_tokens, int)
        assert isinstance(config.temperature, float)
        assert isinstance(config.do_sample, bool)
        assert isinstance(config.top_k, int)
        assert isinstance(config.top_p, float)
        assert isinstance(config.repetition_penalty, float)
        assert isinstance(config.device, int)
        assert isinstance(config.output_dir, str)
        assert isinstance(config.use_kicad_api, bool)
        assert isinstance(config.component_db_path, str)
        assert isinstance(config.default_board_width, float)
        assert isinstance(config.default_board_height, float)
        assert isinstance(config.run_simulations, bool)
        assert isinstance(config.simulation_detail_level, str)
    
    def test_configuration_serialization(self):
        """Test configuration can be serialized and deserialized."""
        config = Configuration(
            model_name="test-model",
            temperature=0.5,
            output_dir="test_dir"
        )
        
        # Test that configuration can be converted to dict
        # (This tests the dataclass functionality)
        from dataclasses import asdict
        config_dict = asdict(config)
        
        assert config_dict["model_name"] == "test-model"
        assert config_dict["temperature"] == 0.5
        assert config_dict["output_dir"] == "test_dir"
    
    def test_configuration_equality(self):
        """Test configuration equality comparison."""
        config1 = Configuration(model_name="test", temperature=0.5)
        config2 = Configuration(model_name="test", temperature=0.5)
        config3 = Configuration(model_name="different", temperature=0.5)
        
        assert config1 == config2
        assert config1 != config3
    
    def test_configuration_repr(self):
        """Test configuration string representation."""
        config = Configuration(model_name="test-model")
        repr_str = repr(config)
        
        assert "Configuration" in repr_str
        assert "test-model" in repr_str
    
    def test_simulation_detail_levels(self):
        """Test valid simulation detail levels."""
        valid_levels = ["basic", "standard", "detailed"]
        
        for level in valid_levels:
            config = Configuration(simulation_detail_level=level)
            assert config.simulation_detail_level == level
    
    def test_chat_format_configuration(self):
        """Test chat format configuration."""
        # Test default
        config1 = Configuration()
        assert config1.chat_format == "harmony"
        
        # Test custom
        config2 = Configuration(chat_format="custom")
        assert config2.chat_format == "custom"
    
    def test_board_dimensions_positive(self):
        """Test that board dimensions are positive."""
        config = Configuration(
            default_board_width=150.0,
            default_board_height=120.0
        )
        
        assert config.default_board_width > 0
        assert config.default_board_height > 0
    
    def test_temperature_range(self):
        """Test temperature value range."""
        # Test valid range
        config = Configuration(temperature=0.5)
        assert 0.0 <= config.temperature <= 1.0
        
        # Test edge cases
        config_min = Configuration(temperature=0.0)
        assert config_min.temperature == 0.0
        
        config_max = Configuration(temperature=1.0)
        assert config_max.temperature == 1.0
    
    def test_max_new_tokens_positive(self):
        """Test that max_new_tokens is positive."""
        config = Configuration(max_new_tokens=2048)
        assert config.max_new_tokens > 0
    
    def test_device_configuration(self):
        """Test device configuration options."""
        # CPU (-1)
        config_cpu = Configuration(device=-1)
        assert config_cpu.device == -1
        
        # GPU (0+)
        config_gpu = Configuration(device=0)
        assert config_gpu.device == 0
    
    def test_kicad_api_configuration(self):
        """Test KiCad API configuration."""
        # Disabled by default
        config1 = Configuration()
        assert config1.use_kicad_api == False
        
        # Can be enabled
        config2 = Configuration(use_kicad_api=True)
        assert config2.use_kicad_api == True
    
    def test_output_dir_creation(self):
        """Test output directory handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_output = os.path.join(temp_dir, "test_output")
            config = Configuration(output_dir=custom_output)
            
            assert config.output_dir == custom_output
    
    def test_configuration_mutability(self):
        """Test that configuration can be modified after creation."""
        config = Configuration()
        original_model = config.model_name
        
        # Configuration is a dataclass, so it should be mutable
        config.model_name = "modified-model"
        assert config.model_name == "modified-model"
        assert config.model_name != original_model
    
    def test_from_runnable_config_edge_cases(self):
        """Test edge cases for from_runnable_config."""
        # Test with configurable key missing
        runnable_config_no_configurable = RunnableConfig()
        config = Configuration.from_runnable_config(runnable_config_no_configurable)
        assert config.model_name == "openai/gpt-oss-120b"  # Default
        
        # Test with unknown fields in configurable (should be ignored)
        runnable_config_unknown = RunnableConfig(
            configurable={
                "model_name": "test-model",
                "unknown_field": "should_be_ignored"
            }
        )
        config = Configuration.from_runnable_config(runnable_config_unknown)
        assert config.model_name == "test-model"
        # Unknown field should not cause errors
    
    def test_all_configuration_fields_covered(self):
        """Test that we're testing all configuration fields."""
        from dataclasses import fields
        
        config_fields = {field.name for field in fields(Configuration)}
        
        # These are the fields we expect based on the Configuration class
        expected_fields = {
            'model_name', 'chat_format', 'max_new_tokens', 'temperature', 
            'do_sample', 'top_k', 'top_p', 'repetition_penalty', 'device',
            'output_dir', 'use_kicad_api', 'component_db_path', 
            'default_board_width', 'default_board_height', 'run_simulations', 
            'simulation_detail_level'
        }
        
        # Verify all expected fields exist
        assert config_fields == expected_fields, f"Field mismatch. Expected: {expected_fields}, Found: {config_fields}"
    
    def test_repetition_penalty_range(self):
        """Test repetition penalty configuration."""
        config = Configuration(repetition_penalty=1.5)
        assert config.repetition_penalty == 1.5
        assert config.repetition_penalty > 1.0  # Should be > 1.0 for penalty
    
    def test_top_p_range(self):
        """Test top_p value range."""
        config = Configuration(top_p=0.9)
        assert 0.0 < config.top_p <= 1.0
    
    def test_component_db_path_format(self):
        """Test component database path configuration."""
        config = Configuration(component_db_path="custom_db_path")
        assert config.component_db_path == "custom_db_path"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])