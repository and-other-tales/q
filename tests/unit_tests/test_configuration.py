from agent.configuration import Configuration


def test_configuration_empty() -> None:
    """Test that configuration can be created with empty input."""
    config = Configuration.from_runnable_config({})
    assert config.model_name == "othertales.ai/q-llama3.3-70B-pcb"
    assert config.output_dir == "output"
    assert config.use_kicad_api is False
    assert config.max_new_tokens == 512
    assert config.device == -1  # Default to CPU


def test_configuration_with_values() -> None:
    """Test that configuration respects provided values."""
    runnable_config = {
        "configurable": {
            "model_name": "gpt2-large",
            "output_dir": "test-output",
            "use_kicad_api": True,
            "default_board_width": 50.0,
            "device": 0,  # Use GPU
            "max_new_tokens": 256
        }
    }
    
    config = Configuration.from_runnable_config(runnable_config)
    assert config.model_name == "gpt2-large"
    assert config.output_dir == "test-output"
    assert config.use_kicad_api is True
    assert config.default_board_width == 50.0
    assert config.device == 0
    assert config.max_new_tokens == 256
    # Default values for fields not in the provided config
    assert config.default_board_height == 80.0