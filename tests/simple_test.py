# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
# Simple test script for the improved PCB design agent
import asyncio
import tempfile
import os
import sys
sys.path.insert(0, "/home/coder/q/src")

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from agent.state import State
from agent.graph import graph

async def test_improved_functionality():
    """Test the improved PCB design functionality."""
    print("🧪 Testing Improved PCB Design Agent...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = RunnableConfig(configurable={
            "output_dir": temp_dir,
            "model_name": "gpt2",
            "run_simulations": True,
            "component_db_path": "component_db.json"
        })
        
        state = State()
        state.messages.append(HumanMessage(content="Design a simple Arduino LED blinker circuit with current limiting resistor."))
        
        print(f"📝 Requirements: {state.messages[0].content}")
        print(f"📁 Output Directory: {temp_dir}")
        
        try:
            result = await graph.ainvoke(state, config=config)
            
            print(f"\n✅ Workflow Status: {'COMPLETED' if result.get('design_complete') else 'INCOMPLETE'}")
            
            # Check each stage
            print(f"\n📊 Results Summary:")
            print(f"   User Requirements: '{result.get('user_requirements', 'NOT SET')[:50]}...'")
            print(f"   Components Selected: {len(result.get('components', []))} components")
            print(f"   Schematic File: {result.get('schematic_file', 'NOT CREATED')}")
            print(f"   PCB File: {result.get('pcb_file', 'NOT CREATED')}")
            print(f"   Simulation Results: {len(result.get('simulation_results', {}))} checks")
            print(f"   Manufacturing Files: {len(result.get('manufacturing_files', []))} files")
            
            # Check if files actually exist
            print(f"\n📁 File Verification:")
            if result.get('schematic_file'):
                exists = os.path.exists(result['schematic_file'])
                print(f"   Schematic exists: {'✅' if exists else '❌'}")
                
            if result.get('pcb_file'):
                exists = os.path.exists(result['pcb_file'])
                print(f"   PCB exists: {'✅' if exists else '❌'}")
                
            # Check manufacturing files
            mf_exist_count = 0
            for mf in result.get('manufacturing_files', []):
                if os.path.exists(mf):
                    mf_exist_count += 1
            
            total_mf = len(result.get('manufacturing_files', []))
            print(f"   Manufacturing files: {mf_exist_count}/{total_mf} exist")
            
            # Component details
            if result.get('components'):
                print(f"\n🔧 Component Details:")
                for i, comp in enumerate(result['components'][:3], 1):  # Show first 3
                    name = comp.get('name', 'Unknown')
                    category = comp.get('category', 'Unknown')
                    part_number = comp.get('part_number', 'Unknown')
                    print(f"   {i}. {name} ({category}) - {part_number}")
            
            # Simulation results
            if result.get('simulation_results'):
                print(f"\n🔬 Simulation Results:")
                sim_results = result['simulation_results']
                for key, value in sim_results.items():
                    print(f"   {key}: {value}")
            
            # Overall assessment
            success_criteria = [
                result.get('design_complete', False),
                len(result.get('components', [])) > 0,
                result.get('schematic_file') and os.path.exists(result['schematic_file']),
                result.get('pcb_file') and os.path.exists(result['pcb_file']),
                len(result.get('manufacturing_files', [])) > 0,
                mf_exist_count > 0
            ]
            
            success_count = sum(success_criteria)
            total_criteria = len(success_criteria)
            success_rate = (success_count / total_criteria) * 100
            
            print(f"\n🎯 Success Rate: {success_rate:.1f}% ({success_count}/{total_criteria} criteria met)")
            
            return success_rate >= 80
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = asyncio.run(test_improved_functionality())
    
    print(f"\n🎯 Final Result: {'SUCCESS - Improved agent provides full functionality' if success else 'PARTIAL - Still has gaps'}")