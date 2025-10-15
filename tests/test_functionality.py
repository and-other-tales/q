# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
# Test script to check if the PCB design agent provides its intended function
import asyncio
import tempfile
import os
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

# Import the agent components
from agent.state import State
from agent.graph import graph

async def test_pcb_design_workflow():
    """Test the complete PCB design workflow."""
    print("🧪 Testing PCB Design Agent Functionality...")
    
    # Create a test scenario
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup test configuration
        config = RunnableConfig(configurable={
            "output_dir": temp_dir,
            "model_name": "gpt2",  # Use simple model for testing
            "run_simulations": True,
            "simulation_detail_level": "basic"
        })
        
        # Create initial state with user requirements
        state = State()
        state.messages.append(HumanMessage(content="Design a simple LED blinker circuit with an Arduino microcontroller, LED, and current limiting resistor."))
        
        print(f"📝 Input Requirements: {state.user_requirements}")
        print(f"📁 Output Directory: {temp_dir}")
        
        try:
            # Run the workflow
            print("\n🔄 Executing PCB Design Workflow...")
            result = await graph.ainvoke(state, config=config)
            
            # Check if the workflow completed successfully
            print(f"\n✅ Workflow Status: {'COMPLETED' if result.get('design_complete') else 'INCOMPLETE'}")
            
            # Verify expected outputs
            if result.get('schematic_file'):
                print(f"📄 Schematic File: {result['schematic_file']}")
            
            if result.get('pcb_file'):
                print(f"🔧 PCB File: {result['pcb_file']}")
                
            if result.get('manufacturing_files'):
                print(f"🏭 Manufacturing Files: {len(result['manufacturing_files'])} files generated")
                for file in result['manufacturing_files']:
                    print(f"   - {os.path.basename(file)}")
                    
            if result.get('simulation_results'):
                print(f"🔬 Simulation Results: {result['simulation_results']}")
                
            # Check message flow
            print(f"\n💬 Message History ({len(result.get('messages', []))} messages):")
            for i, msg in enumerate(result.get('messages', [])[-5:], 1):  # Show last 5 messages
                print(f"   {i}. {type(msg).__name__}: {msg.content[:80]}...")
            
            return result.get('design_complete', False)
            
        except Exception as e:
            print(f"❌ Error during workflow execution: {e}")
            return False

if __name__ == "__main__":
    # Set up environment
    import sys
    sys.path.insert(0, "/home/coder/q/src")
    
    # Run the test
    success = asyncio.run(test_pcb_design_workflow())
    
    print(f"\n🎯 Overall Result: {'SUCCESS - Agent provides intended function' if success else 'FAILURE - Agent does not work as intended'}")