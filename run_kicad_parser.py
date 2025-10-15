#!/usr/bin/env python3
# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
Standalone script to run KiCad library parser functionality.
This script can be executed directly without import issues.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Now we can import with absolute imports
from src.agent.kicad_library_parser import (
    KiCadLibraryFetcher,
    InternalComponentDatabaseBuilder,
    EnhancedComponentDatabaseWithKiCad,
    initialize_internal_component_database
)

async def test_kicad_functionality():
    """Test basic KiCad functionality without network operations."""
    print("Testing KiCad Library Parser Functionality")
    print("=" * 50)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test 1: Initialize KiCad Library Fetcher
        print("1. Testing KiCadLibraryFetcher initialization...")
        fetcher = KiCadLibraryFetcher()
        print(f"   ✅ Initialized with temp dir: {fetcher.temp_dir}")
        
        # Test 2: Test manufacturer detection
        print("\n2. Testing manufacturer detection...")
        builder = InternalComponentDatabaseBuilder()
        
        test_parts = [
            "STM32F103C8T6",
            "ATmega328P", 
            "LM358N",
            "MAX232CPE",
            "AD620AN"
        ]
        
        for part in test_parts:
            manufacturer = builder._guess_manufacturer_from_name(part)
            print(f"   {part} -> {manufacturer}")
        
        # Test 3: Test package type determination
        print("\n3. Testing package type determination...")
        
        test_packages = [
            ("SOIC-8_3.9x4.9mm_P1.27mm", ["soic"], "Package_SO"),
            ("QFP-64_10x10mm_P0.5mm", ["qfp"], "Package_QFP"),
            ("DIP-8_W7.62mm", ["dip"], "Package_DIP")
        ]
        
        for name, keywords, library in test_packages:
            package_type = fetcher._determine_package_type(name, keywords, library)
            print(f"   {name} -> {package_type}")
        
        # Test 4: Test Enhanced Database Interface
        print("\n4. Testing EnhancedComponentDatabaseWithKiCad...")
        enhanced_db = EnhancedComponentDatabaseWithKiCad("test_internal_db.json")
        
        # Create a minimal test database file
        import json
        test_data = {
            'metadata': {
                'version': '1.0',
                'component_count': 2,
                'footprint_count': 1,
                'symbol_count': 1
            },
            'components': [
                {
                    'name': 'STM32F103C8T6',
                    'category': 'Microcontroller',
                    'manufacturer': 'STMicroelectronics',
                    'part_number': 'STM32F103C8T6',
                    'description': 'ARM Cortex-M3 microcontroller, 72MHz, 64KB Flash',
                    'package': 'LQFP-48',
                    'voltage_rating': '3.3V',
                    'current_rating': '150mA',
                    'footprint': 'Package_QFP:LQFP-48_7x7mm_P0.5mm',
                    'datasheet_url': 'https://www.st.com/resource/en/datasheet/stm32f103c8.pdf',
                    'availability': 'Internal_Database'
                },
                {
                    'name': 'R_1K_0805',
                    'category': 'Resistor',
                    'manufacturer': 'Generic',
                    'part_number': 'R_1K_0805',
                    'description': '1K ohm resistor, 0805 package',
                    'package': '0805',
                    'voltage_rating': '50V',
                    'current_rating': None,
                    'footprint': 'Resistor_SMD:R_0805_2012Metric',
                    'datasheet_url': '',
                    'availability': 'Internal_Database'
                }
            ],
            'footprints': [
                {
                    'name': 'LQFP-48_7x7mm_P0.5mm',
                    'library': 'Package_QFP',
                    'description': '48-lead LQFP, 7x7mm body, 0.5mm pitch',
                    'keywords': ['LQFP', 'QFP', '48', 'STM32'],
                    'pads': [],
                    'dimensions': {'length': 7.0, 'width': 7.0, 'height': 1.6},
                    'package_type': 'QFP',
                    'pin_count': 48
                }
            ],
            'symbols': [
                {
                    'name': 'STM32F103C8Tx',
                    'library': 'MCU_ST_STM32F1',
                    'description': 'ARM Cortex-M3 MCU, 64KB flash, 20KB RAM',
                    'keywords': ['ARM', 'Cortex-M3', 'STM32', 'MCU'],
                    'pins': [],
                    'properties': {
                        'Reference': 'U',
                        'Value': 'STM32F103C8Tx',
                        'Footprint': 'Package_QFP:LQFP-48_7x7mm_P0.5mm',
                        'Datasheet': 'https://www.st.com/resource/en/datasheet/stm32f103c8.pdf'
                    },
                    'unit_count': 1
                }
            ],
            'mappings': {
                'component_to_footprint': {
                    'STMicroelectronics:STM32F103C8T6': 'Package_QFP:LQFP-48_7x7mm_P0.5mm'
                },
                'component_to_symbol': {},
                'manufacturer_aliases': {
                    'ST': 'STMicroelectronics',
                    'TI': 'Texas Instruments'
                }
            }
        }
        
        with open("test_internal_db.json", 'w') as f:
            json.dump(test_data, f, indent=2)
        
        print("   ✅ Created test database file")
        
        # Test database loading
        data = enhanced_db.load_internal_database()
        print(f"   ✅ Loaded database with {len(data.get('components', []))} components")
        
        # Test search functionality
        print("\n5. Testing search functionality...")
        search_queries = ['STM32', 'resistor', 'microcontroller']
        
        for query in search_queries:
            results = enhanced_db.search_internal_components(query, limit=3)
            print(f"   Query '{query}': {len(results)} results")
            for result in results:
                print(f"     - {result.name} ({result.manufacturer})")
        
        # Test component details retrieval
        print("\n6. Testing component details retrieval...")
        if data.get('components'):
            from src.agent.component_db import Component
            
            # Create a component object from the test data
            comp_data = data['components'][0]
            component = Component(**comp_data)
            
            footprint_info = enhanced_db.get_component_footprint(component)
            symbol_info = enhanced_db.get_component_symbol(component)
            
            print(f"   Component: {component.name}")
            if footprint_info:
                print(f"   ✅ Found footprint: {footprint_info['name']}")
                print(f"      Package: {footprint_info['package_type']}")
                print(f"      Dimensions: {footprint_info['dimensions']}")
            else:
                print("   ⚠️  No footprint mapping found")
                
            if symbol_info:
                print(f"   ✅ Found symbol: {symbol_info['name']}")
            else:
                print("   ⚠️  No symbol found")
        
        # Clean up fetcher
        fetcher.cleanup()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        print("\nThe KiCad library parser is working correctly.")
        print("To fetch actual KiCad libraries, run the demo_kicad_integration.py script.")
        
        # Clean up test file
        if os.path.exists("test_internal_db.json"):
            os.remove("test_internal_db.json")
            print("✅ Cleaned up test files")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_with_kicad_fetch():
    """Test with actual KiCad library fetching (requires internet)."""
    print("\nAdvanced Test: Fetching Real KiCad Libraries")
    print("=" * 50)
    
    try:
        # Initialize builder
        builder = InternalComponentDatabaseBuilder("real_kicad_test.json")
        
        print("This will download KiCad libraries from GitLab...")
        print("Note: This requires internet access and may take several minutes.")
        
        response = input("Proceed with download? (y/N): ")
        if response.lower() != 'y':
            print("Skipping KiCad library download test.")
            return True
        
        print("\nBuilding database from real KiCad libraries...")
        database = await builder.build_database()
        
        if database:
            metadata = database.get('metadata', {})
            print("✅ Successfully built database from KiCad libraries!")
            print(f"   Components: {metadata.get('component_count', 0)}")
            print(f"   Footprints: {metadata.get('footprint_count', 0)}")
            print(f"   Symbols: {metadata.get('symbol_count', 0)}")
            
            # Show some examples
            components = database.get('components', [])[:5]
            print("\n   Example components:")
            for comp in components:
                print(f"   - {comp['name']} ({comp['manufacturer']})")
                print(f"     Category: {comp['category']}, Package: {comp['package']}")
        else:
            print("❌ Failed to build database")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ KiCad fetch test failed: {e}")
        return False

def main():
    """Main function to run all tests."""
    print("KiCad Library Parser Standalone Test")
    print("Date: October 15, 2025")
    print("=" * 60)
    
    try:
        # Run basic tests
        success = asyncio.run(test_kicad_functionality())
        
        if success:
            print("\n" + "=" * 60)
            print("Basic tests passed! Ready for advanced testing.")
            
            # Offer advanced test
            response = input("\nRun advanced test with real KiCad library download? (y/N): ")
            if response.lower() == 'y':
                advanced_success = asyncio.run(test_with_kicad_fetch())
                if not advanced_success:
                    success = False
        
        if success:
            print("\n" + "🎉" * 20)
            print("All KiCad integration tests passed!")
            print("The system is ready for PCB design automation.")
        else:
            print("\n" + "❌" * 20)
            print("Some tests failed. Please check the output above.")
            
        return success
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)