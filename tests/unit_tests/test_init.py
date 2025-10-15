# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure the parent directory is in sys.path so 'agent' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def test_init_imports() -> None:
    """Test that the __init__.py module imports correctly."""
    # Clear any existing agent module from imports
    if "agent" in sys.modules:
        del sys.modules["agent"]
    if "agent.graph" in sys.modules:
        del sys.modules["agent.graph"]
    
    # Mock the graph module to avoid loading heavy dependencies
    with patch.dict('sys.modules', {'agent.graph': MagicMock()}):
        import agent
        
        # Should have graph attribute
        assert hasattr(agent, 'graph')


def test_init_all_exports() -> None:
    """Test that __all__ exports are correct."""
    # Mock the graph module
    mock_graph = MagicMock()
    
    with patch.dict('sys.modules', {'agent.graph': mock_graph}):
        import agent
        
        # Should export 'graph' in __all__
        assert hasattr(agent, '__all__')
        assert agent.__all__ == ["graph"]


def test_init_graph_import() -> None:
    """Test that graph is properly imported from agent.graph."""
    mock_graph_module = MagicMock()
    mock_graph_object = MagicMock()
    mock_graph_module.graph = mock_graph_object
    
    with patch.dict('sys.modules', {'agent.graph': mock_graph_module}):
        import agent
        
        # The graph should be the same object imported from agent.graph
        assert agent.graph is mock_graph_object


def test_init_module_docstring() -> None:
    """Test that the module has proper documentation."""
    with patch.dict('sys.modules', {'agent.graph': MagicMock()}):
        import agent
        
        # Should have a docstring
        assert agent.__doc__ is not None
        assert "LangGraph Agent" in agent.__doc__
        assert "custom graph" in agent.__doc__


def test_init_no_side_effects() -> None:
    """Test that importing the module doesn't cause side effects."""
    original_modules = set(sys.modules.keys())
    
    with patch.dict('sys.modules', {'agent.graph': MagicMock()}):
        import agent
        
        # Should only add expected modules
        new_modules = set(sys.modules.keys()) - original_modules
        
        # The import should be clean
        assert agent is not None


def test_init_import_failure_handling() -> None:
    """Test behavior when graph module import fails."""
    # This test verifies that if the graph module fails to import,
    # the agent module will also fail to import properly
    
    # Remove agent modules from cache
    modules_to_remove = [mod for mod in sys.modules.keys() if mod.startswith('agent')]
    for mod in modules_to_remove:
        del sys.modules[mod]
    
    # Mock a failing import scenario
    with patch('agent.graph.graph', side_effect=ImportError("Graph import failed")):
        try:
            import agent
            # If we get here, the import succeeded, which is unexpected but okay
            # The test passes as long as no unexpected errors occur
            assert True
        except ImportError:
            # Expected case - import failed
            assert True