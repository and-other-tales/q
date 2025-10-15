# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
KiCad Library Parser and Internal Component Database Builder.
Fetches KiCad footprints and symbols to build a comprehensive component database.
"""

import os
import json
import tempfile
import shutil
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import asyncio
import aiohttp
from urllib.parse import urljoin

from .component_db import Component


@dataclass
class KiCadFootprint:
    """Represents a KiCad footprint."""
    name: str
    library: str
    description: str
    keywords: List[str]
    pads: List[Dict[str, Any]]
    dimensions: Dict[str, float]
    package_type: str
    pin_count: int
    
    
@dataclass
class KiCadSymbol:
    """Represents a KiCad symbol."""
    name: str
    library: str
    description: str
    keywords: List[str]
    pins: List[Dict[str, Any]]
    properties: Dict[str, str]
    unit_count: int


class KiCadLibraryFetcher:
    """Fetches and processes KiCad libraries from GitLab."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.mkdtemp(prefix="kicad_libs_"))
        self.footprints_dir = self.temp_dir / "kicad-footprints"
        self.symbols_dir = self.temp_dir / "kicad-symbols"
        
        # KiCad GitLab repository URLs
        self.footprints_repo = "https://gitlab.com/kicad/libraries/kicad-footprints.git"
        self.symbols_repo = "https://gitlab.com/kicad/libraries/kicad-symbols.git"
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    async def fetch_libraries(self, shallow: bool = True) -> bool:
        """Fetch KiCad footprint and symbol libraries."""
        try:
            # Create temp directory
            self.temp_dir.mkdir(exist_ok=True)
            
            # Clone footprints repository
            self.logger.info("Fetching KiCad footprints repository...")
            footprint_success = await self._clone_repository(
                self.footprints_repo, 
                self.footprints_dir,
                shallow=shallow
            )
            
            if not footprint_success:
                self.logger.error("Failed to fetch footprints repository")
                return False
                
            # Clone symbols repository  
            self.logger.info("Fetching KiCad symbols repository...")
            symbol_success = await self._clone_repository(
                self.symbols_repo,
                self.symbols_dir, 
                shallow=shallow
            )
            
            if not symbol_success:
                self.logger.error("Failed to fetch symbols repository")
                return False
                
            self.logger.info("Successfully fetched KiCad libraries")
            return True
            
        except Exception as e:
            self.logger.error(f"Error fetching libraries: {e}")
            return False
    
    async def _clone_repository(self, repo_url: str, target_dir: Path, shallow: bool = True) -> bool:
        """Clone a git repository."""
        try:
            cmd = ["git", "clone"]
            if shallow:
                cmd.extend(["--depth", "1"])
            cmd.extend([repo_url, str(target_dir)])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.logger.info(f"Successfully cloned {repo_url}")
                return True
            else:
                self.logger.error(f"Git clone failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cloning repository {repo_url}: {e}")
            return False
    
    def parse_footprints(self) -> List[KiCadFootprint]:
        """Parse all KiCad footprints."""
        footprints = []
        
        if not self.footprints_dir.exists():
            self.logger.error("Footprints directory not found")
            return footprints
            
        # Find all .kicad_mod files
        mod_files = list(self.footprints_dir.rglob("*.kicad_mod"))
        self.logger.info(f"Found {len(mod_files)} footprint files")
        
        for mod_file in mod_files:
            try:
                footprint = self._parse_footprint_file(mod_file)
                if footprint:
                    footprints.append(footprint)
            except Exception as e:
                self.logger.warning(f"Error parsing {mod_file}: {e}")
                continue
                
        self.logger.info(f"Successfully parsed {len(footprints)} footprints")
        return footprints
    
    def _parse_footprint_file(self, mod_file: Path) -> Optional[KiCadFootprint]:
        """Parse a single KiCad footprint file."""
        try:
            with open(mod_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract footprint name
            name_match = re.search(r'\(footprint\s+"([^"]+)"', content)
            if not name_match:
                return None
            name = name_match.group(1)
            
            # Extract library (from directory structure)
            library = mod_file.parent.name
            
            # Extract description
            desc_match = re.search(r'\(descr\s+"([^"]*)"', content)
            description = desc_match.group(1) if desc_match else ""
            
            # Extract keywords/tags
            tags_match = re.search(r'\(tags\s+"([^"]*)"', content)
            keywords = tags_match.group(1).split() if tags_match else []
            
            # Parse pads
            pads = self._parse_pads(content)
            
            # Calculate dimensions
            dimensions = self._calculate_footprint_dimensions(content)
            
            # Determine package type
            package_type = self._determine_package_type(name, keywords, library)
            
            return KiCadFootprint(
                name=name,
                library=library,
                description=description,
                keywords=keywords,
                pads=pads,
                dimensions=dimensions,
                package_type=package_type,
                pin_count=len(pads)
            )
            
        except Exception as e:
            self.logger.warning(f"Error parsing footprint {mod_file}: {e}")
            return None
    
    def _parse_pads(self, content: str) -> List[Dict[str, Any]]:
        """Parse pad information from footprint content."""
        pads = []
        
        # Find all pad definitions
        pad_matches = re.finditer(r'\(pad\s+"([^"]*)"([^)]+)\)', content, re.DOTALL)
        
        for match in pad_matches:
            pad_number = match.group(1)
            pad_content = match.group(2)
            
            # Extract pad type
            pad_type_match = re.search(r'\s+(thru_hole|smd|np_thru_hole|connect)', pad_content)
            pad_type = pad_type_match.group(1) if pad_type_match else "unknown"
            
            # Extract pad shape
            shape_match = re.search(r'\s+(circle|oval|rect|roundrect|trapezoid|custom)', pad_content)
            shape = shape_match.group(1) if shape_match else "unknown"
            
            # Extract position
            at_match = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)', pad_content)
            position = [float(at_match.group(1)), float(at_match.group(2))] if at_match else [0, 0]
            
            # Extract size
            size_match = re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)', pad_content)
            size = [float(size_match.group(1)), float(size_match.group(2))] if size_match else [0, 0]
            
            pads.append({
                'number': pad_number,
                'type': pad_type,
                'shape': shape,
                'position': position,
                'size': size
            })
            
        return pads
    
    def _calculate_footprint_dimensions(self, content: str) -> Dict[str, float]:
        """Calculate overall footprint dimensions."""
        dimensions = {'length': 0.0, 'width': 0.0, 'height': 0.0}
        
        # Extract bounding box information
        # This is a simplified calculation - real implementation would be more complex
        
        # Look for courtyard or fabrication layer boundaries
        fp_lines = re.findall(r'\(fp_line\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)', content)
        
        if fp_lines:
            x_coords = []
            y_coords = []
            
            for line in fp_lines:
                x_coords.extend([float(line[0]), float(line[2])])
                y_coords.extend([float(line[1]), float(line[3])])
            
            if x_coords and y_coords:
                dimensions['length'] = max(x_coords) - min(x_coords)
                dimensions['width'] = max(y_coords) - min(y_coords)
        
        return dimensions
    
    def _determine_package_type(self, name: str, keywords: List[str], library: str) -> str:
        """Determine package type from name and keywords."""
        name_lower = name.lower()
        keywords_str = ' '.join(keywords).lower()
        library_lower = library.lower()
        
        # Common package types
        if any(term in name_lower for term in ['soic', 'so-']):
            return 'SOIC'
        elif any(term in name_lower for term in ['qfp', 'lqfp', 'tqfp']):
            return 'QFP'
        elif any(term in name_lower for term in ['bga', 'fbga', 'pbga']):
            return 'BGA'
        elif any(term in name_lower for term in ['dip', 'pdip']):
            return 'DIP'
        elif any(term in name_lower for term in ['sot', 'sot-23', 'sot-89']):
            return 'SOT'
        elif any(term in name_lower for term in ['qfn', 'dfn']):
            return 'QFN'
        elif any(term in name_lower for term in ['0805', '0603', '1206', '1210']):
            return 'SMD_Resistor_Capacitor'
        elif 'connector' in library_lower:
            return 'Connector'
        elif 'crystal' in library_lower:
            return 'Crystal'
        else:
            return 'Unknown'
    
    def parse_symbols(self) -> List[KiCadSymbol]:
        """Parse all KiCad symbols."""
        symbols = []
        
        if not self.symbols_dir.exists():
            self.logger.error("Symbols directory not found")
            return symbols
            
        # Find all .kicad_sym files
        sym_files = list(self.symbols_dir.rglob("*.kicad_sym"))
        self.logger.info(f"Found {len(sym_files)} symbol files")
        
        for sym_file in sym_files:
            try:
                file_symbols = self._parse_symbol_file(sym_file)
                symbols.extend(file_symbols)
            except Exception as e:
                self.logger.warning(f"Error parsing {sym_file}: {e}")
                continue
                
        self.logger.info(f"Successfully parsed {len(symbols)} symbols")
        return symbols
    
    def _parse_symbol_file(self, sym_file: Path) -> List[KiCadSymbol]:
        """Parse a single KiCad symbol file."""
        symbols = []
        
        try:
            with open(sym_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all symbol definitions in the file
            symbol_matches = re.finditer(r'\(symbol\s+"([^"]+)"[^{]*{([^}]+)}', content, re.DOTALL)
            
            for match in symbol_matches:
                symbol_name = match.group(1)
                symbol_content = match.group(2)
                
                # Extract library (from file name)
                library = sym_file.stem
                
                # Extract properties
                properties = self._parse_symbol_properties(symbol_content)
                
                # Extract description
                description = properties.get('ki_description', '')
                
                # Extract keywords
                keywords = properties.get('ki_keywords', '').split()
                
                # Parse pins
                pins = self._parse_symbol_pins(symbol_content)
                
                # Count units
                unit_count = self._count_symbol_units(symbol_content)
                
                symbol = KiCadSymbol(
                    name=symbol_name,
                    library=library,
                    description=description,
                    keywords=keywords,
                    pins=pins,
                    properties=properties,
                    unit_count=unit_count
                )
                
                symbols.append(symbol)
                
        except Exception as e:
            self.logger.warning(f"Error parsing symbol file {sym_file}: {e}")
            
        return symbols
    
    def _parse_symbol_properties(self, content: str) -> Dict[str, str]:
        """Parse symbol properties."""
        properties = {}
        
        prop_matches = re.finditer(r'\(property\s+"([^"]+)"\s+"([^"]*)"', content)
        for match in prop_matches:
            prop_name = match.group(1)
            prop_value = match.group(2)
            properties[prop_name] = prop_value
            
        return properties
    
    def _parse_symbol_pins(self, content: str) -> List[Dict[str, Any]]:
        """Parse symbol pin information."""
        pins = []
        
        pin_matches = re.finditer(r'\(pin\s+(\w+)\s+(\w+)\s+\(at\s+([-\d.]+)\s+([-\d.]+)[^)]*\)\s+\(length\s+([-\d.]+)\)[^)]*\(name\s+"([^"]*)"[^)]*\)\s+\(number\s+"([^"]*)"', content)
        
        for match in pin_matches:
            electrical_type = match.group(1)
            graphic_style = match.group(2)
            x_pos = float(match.group(3))
            y_pos = float(match.group(4))
            length = float(match.group(5))
            pin_name = match.group(6)
            pin_number = match.group(7)
            
            pins.append({
                'number': pin_number,
                'name': pin_name,
                'electrical_type': electrical_type,
                'graphic_style': graphic_style,
                'position': [x_pos, y_pos],
                'length': length
            })
            
        return pins
    
    def _count_symbol_units(self, content: str) -> int:
        """Count the number of units in a symbol."""
        unit_matches = re.findall(r'\(symbol\s+"[^"]*_\d+_\d+"', content)
        return max(1, len(unit_matches))
    
    def cleanup(self):
        """Clean up temporary directories."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.logger.info("Cleaned up temporary directories")
        except Exception as e:
            self.logger.warning(f"Error cleaning up: {e}")


class InternalComponentDatabaseBuilder:
    """Builds internal component database from KiCad libraries."""
    
    def __init__(self, output_file: str = "internal_component_db.json"):
        self.output_file = Path(output_file)
        self.logger = logging.getLogger(__name__)
        
    async def build_database(self, include_footprints: bool = True, include_symbols: bool = True) -> Dict[str, Any]:
        """Build the complete internal component database."""
        
        self.logger.info("Starting internal component database build...")
        
        # Initialize fetcher
        fetcher = KiCadLibraryFetcher()
        
        try:
            # Fetch libraries
            if not await fetcher.fetch_libraries():
                self.logger.error("Failed to fetch KiCad libraries")
                return {}
            
            database = {
                'metadata': {
                    'version': '1.0',
                    'created_date': None,
                    'kicad_version': 'latest',
                    'component_count': 0,
                    'footprint_count': 0,
                    'symbol_count': 0
                },
                'components': [],
                'footprints': [],
                'symbols': [],
                'mappings': {
                    'component_to_footprint': {},
                    'component_to_symbol': {},
                    'manufacturer_aliases': {}
                }
            }
            
            # Parse footprints
            footprints = []
            if include_footprints:
                self.logger.info("Parsing KiCad footprints...")
                footprints = fetcher.parse_footprints()
                database['footprints'] = [asdict(fp) for fp in footprints]
                database['metadata']['footprint_count'] = len(footprints)
            
            # Parse symbols
            symbols = []
            if include_symbols:
                self.logger.info("Parsing KiCad symbols...")
                symbols = fetcher.parse_symbols()
                database['symbols'] = [asdict(sym) for sym in symbols]
                database['metadata']['symbol_count'] = len(symbols)
            
            # Generate components from symbols and footprints
            self.logger.info("Generating component database...")
            components = self._generate_components_from_kicad_data(symbols, footprints)
            database['components'] = [asdict(comp) for comp in components]
            database['metadata']['component_count'] = len(components)
            
            # Build mappings
            database['mappings'] = self._build_component_mappings(components, symbols, footprints)
            
            # Set creation date
            from datetime import datetime
            database['metadata']['created_date'] = datetime.now().isoformat()
            
            # Save to file
            self.logger.info(f"Saving database to {self.output_file}...")
            with open(self.output_file, 'w') as f:
                json.dump(database, f, indent=2)
            
            self.logger.info(f"Internal component database created successfully!")
            self.logger.info(f"  Components: {len(components)}")
            self.logger.info(f"  Footprints: {len(footprints)}")
            self.logger.info(f"  Symbols: {len(symbols)}")
            
            return database
            
        finally:
            # Clean up temporary files
            fetcher.cleanup()
    
    def _generate_components_from_kicad_data(self, symbols: List[KiCadSymbol], footprints: List[KiCadFootprint]) -> List[Component]:
        """Generate component database from KiCad symbols and footprints."""
        components = []
        
        # Create components from symbols
        for symbol in symbols:
            # Extract manufacturer if available
            manufacturer = self._extract_manufacturer_from_symbol(symbol)
            
            # Generate part number if not available
            part_number = symbol.properties.get('MPN', symbol.name)
            
            # Determine category
            category = self._determine_component_category(symbol)
            
            # Find matching footprint
            footprint_name = self._find_matching_footprint(symbol, footprints)
            
            # Create component
            component = Component(
                name=symbol.name,
                category=category,
                manufacturer=manufacturer,
                part_number=part_number,
                description=symbol.description,
                package=self._extract_package_from_symbol(symbol),
                voltage_rating=self._extract_voltage_rating(symbol),
                current_rating=self._extract_current_rating(symbol),
                footprint=footprint_name,
                datasheet_url=symbol.properties.get('ki_datasheet', ''),
                availability="Internal_Database"
            )
            
            components.append(component)
        
        # Add components for footprints without symbols (e.g., mechanical parts)
        for footprint in footprints:
            if not self._has_matching_symbol(footprint, symbols):
                component = self._create_component_from_footprint(footprint)
                if component:
                    components.append(component)
        
        return components
    
    def _extract_manufacturer_from_symbol(self, symbol: KiCadSymbol) -> str:
        """Extract manufacturer from symbol properties."""
        # Check various property fields
        manufacturer = symbol.properties.get('Manufacturer', '')
        if not manufacturer:
            manufacturer = symbol.properties.get('Mfg', '')
        if not manufacturer:
            manufacturer = symbol.properties.get('Mfr', '')
        if not manufacturer:
            # Try to extract from part number or name
            manufacturer = self._guess_manufacturer_from_name(symbol.name)
        
        return manufacturer or "Unknown"
    
    def _guess_manufacturer_from_name(self, name: str) -> str:
        """Guess manufacturer from component name."""
        name_lower = name.lower()
        
        # Common manufacturer prefixes/patterns
        manufacturer_patterns = {
            'stm32': 'STMicroelectronics',
            'at90': 'Microchip',
            'atmega': 'Microchip',
            'pic': 'Microchip',
            'lm': 'Texas Instruments',
            'tl': 'Texas Instruments',
            'ne': 'Texas Instruments',
            'max': 'Maxim Integrated',
            'ad': 'Analog Devices',
            'lt': 'Linear Technology',
            'mcp': 'Microchip',
            'esp': 'Espressif',
            'nrf': 'Nordic Semiconductor',
            'cy': 'Cypress',
            'ftdi': 'FTDI',
            'cp21': 'Silicon Labs'
        }
        
        for pattern, manufacturer in manufacturer_patterns.items():
            if pattern in name_lower:
                return manufacturer
        
        return "Unknown"
    
    def _determine_component_category(self, symbol: KiCadSymbol) -> str:
        """Determine component category from symbol information."""
        name_lower = symbol.name.lower()
        desc_lower = symbol.description.lower()
        keywords = ' '.join(symbol.keywords).lower()
        library_lower = symbol.library.lower()
        
        # Category determination logic
        if any(term in name_lower for term in ['mcu', 'microcontroller', 'atmega', 'stm32', 'pic']):
            return 'Microcontroller'
        elif any(term in library_lower for term in ['resistor', 'r_']):
            return 'Resistor'
        elif any(term in library_lower for term in ['capacitor', 'c_']):
            return 'Capacitor'
        elif any(term in library_lower for term in ['inductor', 'l_']):
            return 'Inductor'
        elif any(term in library_lower for term in ['diode', 'd_']):
            return 'Diode'
        elif any(term in name_lower for term in ['transistor', 'mosfet', 'bjt']):
            return 'Transistor'
        elif any(term in library_lower for term in ['led']):
            return 'LED'
        elif any(term in library_lower for term in ['connector']):
            return 'Connector'
        elif any(term in library_lower for term in ['crystal', 'oscillator']):
            return 'Crystal/Oscillator'
        elif any(term in name_lower for term in ['regulator', 'ldo', 'buck', 'boost']):
            return 'Power Management'
        elif any(term in name_lower for term in ['opamp', 'amplifier']):
            return 'Amplifier'
        elif any(term in name_lower for term in ['sensor']):
            return 'Sensor'
        elif any(term in name_lower for term in ['memory', 'eeprom', 'flash']):
            return 'Memory'
        else:
            return 'Unknown'
    
    def _extract_package_from_symbol(self, symbol: KiCadSymbol) -> str:
        """Extract package information from symbol."""
        package = symbol.properties.get('Package', '')
        if not package:
            package = symbol.properties.get('Footprint', '')
        if not package:
            # Try to extract from footprint reference
            footprint_ref = symbol.properties.get('ki_fp_filters', '')
            if footprint_ref:
                # Extract package type from footprint filter
                package = footprint_ref.split()[0] if footprint_ref.split() else ''
        
        return package or "Unknown"
    
    def _extract_voltage_rating(self, symbol: KiCadSymbol) -> Optional[str]:
        """Extract voltage rating from symbol properties."""
        voltage = symbol.properties.get('Voltage', '')
        if not voltage:
            voltage = symbol.properties.get('VDD', '')
        if not voltage:
            voltage = symbol.properties.get('Supply_Voltage', '')
        
        return voltage if voltage else None
    
    def _extract_current_rating(self, symbol: KiCadSymbol) -> Optional[str]:
        """Extract current rating from symbol properties."""
        current = symbol.properties.get('Current', '')
        if not current:
            current = symbol.properties.get('Max_Current', '')
        if not current:
            current = symbol.properties.get('IDD', '')
        
        return current if current else None
    
    def _find_matching_footprint(self, symbol: KiCadSymbol, footprints: List[KiCadFootprint]) -> Optional[str]:
        """Find matching footprint for a symbol."""
        # Look for footprint reference in symbol properties
        footprint_filters = symbol.properties.get('ki_fp_filters', '').split()
        
        for filter_pattern in footprint_filters:
            # Simple pattern matching - could be more sophisticated
            for footprint in footprints:
                if re.match(filter_pattern.replace('*', '.*'), footprint.name):
                    return f"{footprint.library}:{footprint.name}"
        
        # Fallback: try to match by pin count and package type
        symbol_pin_count = len(symbol.pins)
        for footprint in footprints:
            if footprint.pin_count == symbol_pin_count:
                return f"{footprint.library}:{footprint.name}"
        
        return None
    
    def _has_matching_symbol(self, footprint: KiCadFootprint, symbols: List[KiCadSymbol]) -> bool:
        """Check if footprint has a matching symbol."""
        for symbol in symbols:
            if len(symbol.pins) == footprint.pin_count:
                return True
        return False
    
    def _create_component_from_footprint(self, footprint: KiCadFootprint) -> Optional[Component]:
        """Create component from footprint (for mechanical parts, etc.)."""
        if footprint.package_type == 'Connector':
            return Component(
                name=footprint.name,
                category='Connector',
                manufacturer='Generic',
                part_number=footprint.name,
                description=footprint.description,
                package=footprint.package_type,
                footprint=f"{footprint.library}:{footprint.name}",
                availability="Internal_Database"
            )
        
        return None
    
    def _build_component_mappings(self, components: List[Component], symbols: List[KiCadSymbol], footprints: List[KiCadFootprint]) -> Dict[str, Any]:
        """Build mapping tables for components, symbols, and footprints."""
        mappings = {
            'component_to_footprint': {},
            'component_to_symbol': {},
            'manufacturer_aliases': {},
            'category_to_symbols': {},
            'package_to_footprints': {}
        }
        
        # Build component mappings
        for component in components:
            comp_key = f"{component.manufacturer}:{component.part_number}"
            
            if component.footprint:
                mappings['component_to_footprint'][comp_key] = component.footprint
        
        # Build category mappings
        for symbol in symbols:
            category = self._determine_component_category(symbol)
            if category not in mappings['category_to_symbols']:
                mappings['category_to_symbols'][category] = []
            mappings['category_to_symbols'][category].append(f"{symbol.library}:{symbol.name}")
        
        # Build package mappings
        for footprint in footprints:
            package = footprint.package_type
            if package not in mappings['package_to_footprints']:
                mappings['package_to_footprints'][package] = []
            mappings['package_to_footprints'][package].append(f"{footprint.library}:{footprint.name}")
        
        # Build manufacturer aliases
        manufacturer_aliases = {
            'TI': 'Texas Instruments',
            'ST': 'STMicroelectronics',
            'ADI': 'Analog Devices',
            'MCHP': 'Microchip',
            'NXP': 'NXP Semiconductors',
            'FTDI': 'FTDI',
            'Cypress': 'Infineon Technologies'
        }
        mappings['manufacturer_aliases'] = manufacturer_aliases
        
        return mappings


# Integration with existing component database
class EnhancedComponentDatabaseWithKiCad:
    """Enhanced component database that includes KiCad internal database."""
    
    def __init__(self, internal_db_file: str = "internal_component_db.json"):
        self.internal_db_file = Path(internal_db_file)
        self.internal_data = None
        self.logger = logging.getLogger(__name__)
        
    async def ensure_internal_database(self) -> bool:
        """Ensure internal database exists, build if necessary."""
        if not self.internal_db_file.exists():
            self.logger.info("Internal component database not found, building from KiCad libraries...")
            builder = InternalComponentDatabaseBuilder(str(self.internal_db_file))
            await builder.build_database()
        
        return self.internal_db_file.exists()
    
    def load_internal_database(self) -> Dict[str, Any]:
        """Load internal component database."""
        if self.internal_data is None:
            if self.internal_db_file.exists():
                with open(self.internal_db_file, 'r') as f:
                    self.internal_data = json.load(f)
            else:
                self.internal_data = {'components': [], 'footprints': [], 'symbols': []}
        
        return self.internal_data
    
    def search_internal_components(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[Component]:
        """Search internal component database."""
        data = self.load_internal_database()
        components = []
        
        query_lower = query.lower()
        
        for comp_data in data.get('components', []):
            # Convert dict back to Component object
            component = Component(**comp_data)
            
            # Simple search logic
            matches = (
                query_lower in component.name.lower() or
                query_lower in component.description.lower() or
                query_lower in component.manufacturer.lower() or
                query_lower in component.part_number.lower()
            )
            
            if category:
                matches = matches and component.category.lower() == category.lower()
            
            if matches:
                components.append(component)
                
            if len(components) >= limit:
                break
        
        return components
    
    def get_component_footprint(self, component: Component) -> Optional[Dict[str, Any]]:
        """Get footprint information for a component."""
        data = self.load_internal_database()
        mappings = data.get('mappings', {})
        
        comp_key = f"{component.manufacturer}:{component.part_number}"
        footprint_ref = mappings.get('component_to_footprint', {}).get(comp_key)
        
        if footprint_ref:
            # Find footprint details
            for fp_data in data.get('footprints', []):
                fp_name = f"{fp_data['library']}:{fp_data['name']}"
                if fp_name == footprint_ref:
                    return fp_data
        
        return None
    
    def get_component_symbol(self, component: Component) -> Optional[Dict[str, Any]]:
        """Get symbol information for a component."""
        data = self.load_internal_database()
        
        # Search for matching symbol by name/part number
        for sym_data in data.get('symbols', []):
            if (sym_data['name'].lower() == component.name.lower() or 
                sym_data['name'].lower() == component.part_number.lower()):
                return sym_data
        
        return None


# Update the global component database to include KiCad data
async def initialize_internal_component_database():
    """Initialize the internal component database from KiCad libraries."""
    enhanced_db = EnhancedComponentDatabaseWithKiCad()
    await enhanced_db.ensure_internal_database()
    return enhanced_db