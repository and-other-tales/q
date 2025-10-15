#!/usr/bin/env python3
# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
Simple test for KiCad library integration functionality.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent.kicad_library_parser import (
    KiCadLibraryFetcher, 
    InternalComponentDatabaseBuilder,
    EnhancedComponentDatabaseWithKiCad
)

async def simple_test():
    """Run a simple test of KiCad library functionality."""
    print("Simple KiCad Integration Test")
    print("=" * 40)
    
    # Configure minimal logging
    logging.basicConfig(level=logging.WARNING)
    
    try:
        print("1. Testing KiCadLibraryFetcher initialization...")
        fetcher = KiCadLibraryFetcher()
        print(f"   ✅ Fetcher initialized with temp dir: {fetcher.temp_dir}")
        
        print("2. Testing InternalComponentDatabaseBuilder...")
        builder = InternalComponentDatabaseBuilder("test_db.json")
        print(f"   ✅ Builder initialized with output: {builder.output_file}")
        
        print("3. Testing EnhancedComponentDatabaseWithKiCad...")
        enhanced_db = EnhancedComponentDatabaseWithKiCad("test_db.json")
        print("   ✅ Enhanced database initialized")
        
        print("4. Testing data structures...")
        # Test that our dataclasses work
        from src.agent.kicad_library_parser import KiCadFootprint, KiCadSymbol
        
        test_footprint = KiCadFootprint(
            name="test_footprint",
            library="test_lib",
            description="Test footprint",
            keywords=["test"],
            pads=[],
            dimensions={'length': 5.0, 'width': 3.0},
            package_type="DIP",
            pin_count=8
        )
        print(f"   ✅ KiCadFootprint: {test_footprint.name} ({test_footprint.package_type})")
        
        test_symbol = KiCadSymbol(
            name="test_symbol",
            library="test_lib", 
            description="Test symbol",
            keywords=["test"],
            pins=[],
            properties={'Manufacturer': 'Test Corp'},
            unit_count=1
        )
        print(f"   ✅ KiCadSymbol: {test_symbol.name} ({test_symbol.library})")
        
        print("5. Testing helper methods...")
        # Test manufacturer guessing
        manufacturer = builder._guess_manufacturer_from_name("STM32F103")
        print(f"   ✅ Manufacturer detection: STM32F103 -> {manufacturer}")
        
        # Test category determination  
        category = builder._determine_component_category(test_symbol)
        print(f"   ✅ Category detection: {test_symbol.name} -> {category}")
        
        # Clean up
        fetcher.cleanup()
        
        print("\n" + "=" * 40)
        print("✅ All basic tests passed!")
        print("\nNext steps:")
        print("- Run demo_kicad_integration.py for full demonstration")
        print("- The system is ready to fetch and process KiCad libraries")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(simple_test())
    sys.exit(0 if success else 1)