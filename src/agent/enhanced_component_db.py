# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
Enhanced component database with real-time component sourcing and datasheet analysis.
Integrates with major component distributors and manufacturer APIs.
"""

import requests
import json
import asyncio
import aiohttp
import hashlib
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from urllib.parse import urljoin, urlparse
import re
import tempfile
import pypdf
import io

from .component_db import Component
from .kicad_library_parser import EnhancedComponentDatabaseWithKiCad, initialize_internal_component_database


@dataclass
class DatasheetAnalysis:
    """Results from datasheet analysis."""
    component_id: str
    pin_configuration: Dict[str, Any]
    electrical_characteristics: Dict[str, Any]
    package_dimensions: Dict[str, Any]
    recommended_layout: Dict[str, Any]
    power_requirements: Dict[str, Any]
    signal_integrity_notes: List[str]
    thermal_considerations: Dict[str, Any]
    
    
class ComponentSourcer:
    """Enhanced component sourcing with real-time distributor APIs and KiCad internal database."""
    
    def __init__(self):
        # Initialize distributors - these would be implemented as actual API classes
        self.distributors = {}  # Will be populated when actual APIs are implemented
        self.kicad_db = None
        self.datasheet_analyzer = DatasheetAnalyzer()
        
    async def initialize_kicad_database(self):
        """Initialize KiCad internal component database."""
        try:
            self.kicad_db = await initialize_internal_component_database()
            logging.info("KiCad internal database initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize KiCad database: {e}")
            self.kicad_db = None
        
    async def search_components(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[Component]:
        """Search components across all sources including KiCad internal database."""
        all_components = []
        
        # Initialize KiCad database if not already done
        if self.kicad_db is None:
            await self.initialize_kicad_database()
        
        # Search KiCad internal database first
        if self.kicad_db:
            try:
                internal_components = self.kicad_db.search_internal_components(query, category or "", limit // 2)
                all_components.extend(internal_components)
                logging.info(f"Found {len(internal_components)} components in KiCad internal database")
            except Exception as e:
                logging.error(f"Error searching KiCad database: {e}")
        
        # Search external distributors
        search_tasks = []
        for name, distributor in self.distributors.items():
            task = self._search_single_distributor(name, distributor, query, category, limit // len(self.distributors))
            search_tasks.append(task)
        
        distributor_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        for result in distributor_results:
            if isinstance(result, list):
                all_components.extend(result)
            elif isinstance(result, Exception):
                logging.warning(f"Distributor search failed: {result}")
        
        # Remove duplicates and rank results
        unique_components = self._deduplicate_components(all_components)
        ranked_components = self._rank_search_results(unique_components, query)
        
        return ranked_components[:limit]
    
    async def _search_single_api(self, api, query: str, category: str, limit: int) -> List[Component]:
        """Search a single API for components."""
        try:
            return await api.search(query, category, limit)
        except Exception as e:
            logging.error(f"Error searching {api.__class__.__name__}: {e}")
            return []
            
    async def get_detailed_component_info(self, component: Component) -> Component:
        """Get detailed information for a specific component."""
        # Try to get detailed info from the component's preferred distributor
        for distributor in self.distributors.values():
            if hasattr(distributor, 'is_available') and distributor.is_available():
                try:
                    detailed = await distributor.get_component_details(component.part_number)
                    if detailed:
                        return detailed
                except Exception as e:
                    logging.error(f"Error getting details from {distributor.__class__.__name__}: {e}")
                    continue
                    
        return component

    async def get_component_details(self, component: Component) -> Dict[str, Any]:
        """Get comprehensive component information including KiCad footprint and symbol data."""
        details = {
            'basic_info': component,
            'availability': {},
            'pricing': {},
            'datasheet_analysis': {},
            'kicad_data': {}
        }
        
        # Get KiCad footprint and symbol information
        if self.kicad_db:
            try:
                footprint_data = self.kicad_db.get_component_footprint(component)
                symbol_data = self.kicad_db.get_component_symbol(component)
                
                details['kicad_data'] = {
                    'footprint': footprint_data,
                    'symbol': symbol_data,
                    'pcb_layout_recommendations': self._generate_pcb_layout_recommendations(footprint_data or {}, component)
                }
            except Exception as e:
                logging.error(f"Error retrieving KiCad data: {e}")
        
        # Get availability from distributors
        availability_tasks = []
        for name, distributor in self.distributors.items():
            task = self._get_component_availability(name, distributor, component)
            availability_tasks.append(task)
        
        availability_results = await asyncio.gather(*availability_tasks, return_exceptions=True)
        
        for i, result in enumerate(availability_results):
            distributor_name = list(self.distributors.keys())[i]
            if isinstance(result, dict):
                details['availability'][distributor_name] = result
            elif isinstance(result, Exception):
                logging.warning(f"Availability check failed for {distributor_name}: {result}")
        
        # Analyze datasheet if available
        if component.datasheet_url:
            try:
                details['datasheet_analysis'] = await self.datasheet_analyzer.analyze_component_datasheet(component)
            except Exception as e:
                logging.error(f"Datasheet analysis failed: {e}")
                details['datasheet_analysis'] = {}
        
        return details
    
    def _generate_pcb_layout_recommendations(self, footprint_data: Dict[str, Any], component: Component) -> Dict[str, Any]:
        """Generate PCB layout recommendations based on KiCad footprint data."""
        if not footprint_data:
            return {}
            
        recommendations = {
            'placement_notes': [],
            'routing_guidelines': [],
            'thermal_considerations': [],
            'signal_integrity': []
        }
        
        # Analyze footprint for specific recommendations
        package_type = footprint_data.get('package_type', '').upper()
        pin_count = footprint_data.get('pin_count', 0)
        dimensions = footprint_data.get('dimensions', {})
        
        # Package-specific recommendations
        if 'BGA' in package_type:
            recommendations['placement_notes'].extend([
                'Requires precise placement and alignment',
                'Consider using via-in-pad for high pin count BGAs',
                'Ensure proper solder mask registration'
            ])
            recommendations['routing_guidelines'].extend([
                'Use microvias for escape routing',
                'Maintain consistent via sizes',
                'Consider blind/buried vias for complex routing'
            ])
        elif 'QFP' in package_type:
            recommendations['placement_notes'].extend([
                'Ensure adequate clearance for package body',
                'Consider lead coplanarity requirements'
            ])
            recommendations['routing_guidelines'].extend([
                'Route traces at 45-degree angles from pins',
                'Maintain minimum trace width based on current requirements'
            ])
        elif 'SOIC' in package_type or 'SO-' in package_type:
            recommendations['placement_notes'].extend([
                'Standard SMD placement guidelines apply',
                'Ensure proper solder paste stencil design'
            ])
        
        # Pin count based recommendations
        if pin_count > 100:
            recommendations['signal_integrity'].extend([
                'Consider power/ground plane placement',
                'Implement proper decoupling capacitor placement',
                'Route critical signals on inner layers'
            ])
        
        # Size-based thermal recommendations
        length = dimensions.get('length', 0)
        width = dimensions.get('width', 0)
        
        if length > 10 or width > 10:  # Large components (>10mm)
            recommendations['thermal_considerations'].extend([
                'Consider thermal vias under component',
                'Evaluate copper pour requirements',
                'Check component thermal derating'
            ])
        
        return recommendations
        
    async def _search_single_distributor(self, name: str, distributor, query: str, category: Optional[str], limit: int) -> List[Component]:
        """Search a single distributor for components."""
        try:
            if hasattr(distributor, 'search'):
                return await distributor.search(query, category, limit)
            else:
                return []
        except Exception as e:
            logging.error(f"Error searching {name}: {e}")
            return []
    
    async def _get_component_availability(self, name: str, distributor, component: Component) -> Dict[str, Any]:
        """Get component availability from a distributor."""
        try:
            if hasattr(distributor, 'get_availability'):
                return await distributor.get_availability(component.part_number)
            elif hasattr(distributor, 'get_component_details'):
                details = await distributor.get_component_details(component.part_number)
                if details:
                    return {
                        'available': True,
                        'stock_quantity': getattr(details, 'stock_quantity', 'Unknown'),
                        'price': getattr(details, 'price', 'Contact for pricing'),
                        'lead_time': getattr(details, 'lead_time', 'Unknown')
                    }
            return {'available': False, 'reason': 'Not found'}
        except Exception as e:
            logging.error(f"Error checking availability at {name}: {e}")
            return {'available': False, 'reason': str(e)}
    
    def _deduplicate_components(self, components: List[Component]) -> List[Component]:
        """Remove duplicate components based on part number and manufacturer."""
        seen = set()
        unique = []
        
        for component in components:
            key = f"{component.manufacturer}:{component.part_number}".lower()
            if key not in seen:
                seen.add(key)
                unique.append(component)
        
        return unique
    
    def _rank_search_results(self, components: List[Component], query: str) -> List[Component]:
        """Rank search results by relevance to query."""
        query_lower = query.lower()
        
        def relevance_score(component: Component) -> int:
            score = 0
            
            # Exact matches get highest score
            if query_lower == component.part_number.lower():
                score += 1000
            elif query_lower in component.part_number.lower():
                score += 500
            
            if query_lower in component.name.lower():
                score += 300
            
            if query_lower in component.description.lower():
                score += 100
            
            if query_lower in component.manufacturer.lower():
                score += 50
            
            # Prefer components with availability info
            if component.availability == "In Stock":
                score += 25
            elif component.availability and "stock" in component.availability.lower():
                score += 10
            
            return score
        
        return sorted(components, key=relevance_score, reverse=True)


class DatasheetAnalyzer:
    """Analyzes component datasheets to extract PCB layout information."""
    
    def __init__(self):
        self.cache_dir = Path("datasheet_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
    async def analyze_component_datasheet(self, component: Component) -> DatasheetAnalysis:
        """Download and analyze component datasheet."""
        if not component.datasheet_url:
            return self._create_minimal_analysis(component)
            
        # Download datasheet if not cached
        datasheet_path = await self._download_datasheet(component)
        if not datasheet_path:
            return self._create_minimal_analysis(component)
            
        # Extract information from PDF
        analysis = await self._extract_datasheet_info(datasheet_path, component)
        return analysis
    
    async def _download_datasheet(self, component: Component) -> Optional[Path]:
        """Download datasheet PDF and cache it."""
        if not component.datasheet_url:
            return None
            
        cache_filename = f"{component.manufacturer}_{component.part_number}.pdf"
        cache_path = self.cache_dir / cache_filename
        
        # Return cached version if exists
        if cache_path.exists():
            return cache_path
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(component.datasheet_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(cache_path, 'wb') as f:
                            f.write(content)
                        return cache_path
        except Exception as e:
            logging.error(f"Error downloading datasheet for {component.part_number}: {e}")
            
        return None
    
    async def _extract_datasheet_info(self, datasheet_path: Path, component: Component) -> DatasheetAnalysis:
        """Extract key information from datasheet PDF."""
        try:
            with open(datasheet_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                full_text = ""
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    full_text += page.extract_text() + "\n"
                
                # Parse the extracted text for key information
                analysis = self._parse_datasheet_text(full_text, component)
                return analysis
                
        except Exception as e:
            logging.error(f"Error parsing datasheet {datasheet_path}: {e}")
            return self._create_minimal_analysis(component)
    
    def _parse_datasheet_text(self, text: str, component: Component) -> DatasheetAnalysis:
        """Parse datasheet text to extract PCB layout information."""
        
        # Pin configuration extraction
        pin_config = self._extract_pin_configuration(text)
        
        # Electrical characteristics
        electrical = self._extract_electrical_characteristics(text)
        
        # Package information
        package_dims = self._extract_package_dimensions(text)
        
        # Layout recommendations
        layout_rec = self._extract_layout_recommendations(text)
        
        # Power requirements
        power_req = self._extract_power_requirements(text)
        
        # Signal integrity notes
        signal_notes = self._extract_signal_integrity_notes(text)
        
        # Thermal considerations
        thermal = self._extract_thermal_considerations(text)
        
        return DatasheetAnalysis(
            component_id=f"{component.manufacturer}_{component.part_number}",
            pin_configuration=pin_config,
            electrical_characteristics=electrical,
            package_dimensions=package_dims,
            recommended_layout=layout_rec,
            power_requirements=power_req,
            signal_integrity_notes=signal_notes,
            thermal_considerations=thermal
        )
    
    def _extract_pin_configuration(self, text: str) -> Dict[str, Any]:
        """Extract pin configuration from datasheet text."""
        pin_config = {}
        
        # Look for pin description tables
        pin_patterns = [
            r'Pin\s+(\d+)[\s:]+([A-Za-z0-9_/]+)[\s:]+(.+?)(?=Pin\s+\d+|$)',
            r'(\d+)\s+([A-Za-z0-9_/]+)\s+([IO]+)\s+(.+?)(?=\n\d+|$)',
        ]
        
        for pattern in pin_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 3:
                    pin_num = match.group(1)
                    pin_name = match.group(2)
                    pin_desc = match.group(3) if len(match.groups()) > 2 else ""
                    
                    pin_config[pin_num] = {
                        'name': pin_name,
                        'description': pin_desc.strip(),
                        'type': self._determine_pin_type(pin_name, pin_desc)
                    }
        
        return pin_config
    
    def _extract_electrical_characteristics(self, text: str) -> Dict[str, Any]:
        """Extract electrical characteristics."""
        electrical = {}
        
        # Common electrical parameters
        patterns = {
            'supply_voltage': r'Supply Voltage[\s:]+([0-9.]+)\s*[Vv]?\s*to\s*([0-9.]+)\s*[Vv]',
            'operating_current': r'Operating Current[\s:]+([0-9.]+)\s*([mMuUnN]?[Aa])',
            'max_frequency': r'Maximum Frequency[\s:]+([0-9.]+)\s*([MmKkGg]?[Hh]z)',
            'input_voltage_high': r'VIH[\s:]+([0-9.]+)\s*[Vv]',
            'input_voltage_low': r'VIL[\s:]+([0-9.]+)\s*[Vv]',
            'output_voltage_high': r'VOH[\s:]+([0-9.]+)\s*[Vv]',
            'output_voltage_low': r'VOL[\s:]+([0-9.]+)\s*[Vv]'
        }
        
        for param, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                electrical[param] = match.group(1)
                if len(match.groups()) > 1:
                    electrical[f"{param}_unit"] = match.group(2)
        
        return electrical
    
    def _extract_package_dimensions(self, text: str) -> Dict[str, Any]:
        """Extract package dimensions and footprint info."""
        package = {}
        
        # Look for package dimension tables
        dimension_patterns = [
            r'Package Dimensions[\s\S]*?(?=\n\n|\f)',
            r'Mechanical Data[\s\S]*?(?=\n\n|\f)',
        ]
        
        for pattern in dimension_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dim_text = match.group(0)
                
                # Extract specific dimensions
                length_match = re.search(r'Length[\s:]+([0-9.]+)\s*mm', dim_text, re.IGNORECASE)
                width_match = re.search(r'Width[\s:]+([0-9.]+)\s*mm', dim_text, re.IGNORECASE)
                height_match = re.search(r'Height[\s:]+([0-9.]+)\s*mm', dim_text, re.IGNORECASE)
                pitch_match = re.search(r'Pitch[\s:]+([0-9.]+)\s*mm', dim_text, re.IGNORECASE)
                
                if length_match:
                    package['length_mm'] = float(length_match.group(1))
                if width_match:
                    package['width_mm'] = float(width_match.group(1))
                if height_match:
                    package['height_mm'] = float(height_match.group(1))
                if pitch_match:
                    package['pitch_mm'] = float(pitch_match.group(1))
        
        return package
    
    def _extract_layout_recommendations(self, text: str) -> Dict[str, Any]:
        """Extract PCB layout recommendations."""
        layout = {}
        
        # Look for layout guidance sections
        layout_sections = [
            r'PCB Layout[\s\S]*?(?=\n\n|\f)',
            r'Layout Considerations[\s\S]*?(?=\n\n|\f)',
            r'Application Information[\s\S]*?(?=\n\n|\f)'
        ]
        
        for pattern in layout_sections:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                layout_text = match.group(0)
                
                # Extract specific recommendations
                if 'ground plane' in layout_text.lower():
                    layout['requires_ground_plane'] = True
                if 'power plane' in layout_text.lower():
                    layout['requires_power_plane'] = True
                if 'differential' in layout_text.lower():
                    layout['has_differential_pairs'] = True
                
                # Extract trace impedance requirements
                impedance_match = re.search(r'([0-9]+)\s*[Ωohm].*?impedance', layout_text, re.IGNORECASE)
                if impedance_match:
                    layout['required_impedance'] = int(impedance_match.group(1))
        
        return layout
    
    def _extract_power_requirements(self, text: str) -> Dict[str, Any]:
        """Extract power supply requirements."""
        power = {}
        
        # Power-related patterns
        patterns = {
            'vdd_voltage': r'VDD[\s:]+([0-9.]+)\s*[Vv]',
            'vss_voltage': r'VSS[\s:]+([0-9.]+)\s*[Vv]',
            'supply_current': r'Supply Current[\s:]+([0-9.]+)\s*([mMuU]?[Aa])',
            'power_dissipation': r'Power Dissipation[\s:]+([0-9.]+)\s*([mMuU]?[Ww])'
        }
        
        for param, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                power[param] = match.group(1)
                if len(match.groups()) > 1:
                    power[f"{param}_unit"] = match.group(2)
        
        return power
    
    def _extract_signal_integrity_notes(self, text: str) -> List[str]:
        """Extract signal integrity recommendations."""
        notes = []
        
        # Look for signal integrity related text
        si_keywords = [
            'signal integrity', 'crosstalk', 'noise', 'EMI', 'EMC',
            'high speed', 'differential', 'impedance matching'
        ]
        
        for keyword in si_keywords:
            pattern = rf'([^.\n]*{keyword}[^.\n]*\.)'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                notes.append(match.group(1).strip())
        
        return list(set(notes))  # Remove duplicates
    
    def _extract_thermal_considerations(self, text: str) -> Dict[str, Any]:
        """Extract thermal management information."""
        thermal = {}
        
        # Thermal patterns
        patterns = {
            'junction_temp_max': r'Junction Temperature[\s:]+([0-9-]+)\s*°?C',
            'storage_temp_min': r'Storage Temperature[\s:]+([0-9-]+)\s*°?C',
            'storage_temp_max': r'Storage Temperature[\s:]+-?[0-9]+\s*to\s*([0-9]+)\s*°?C',
            'thermal_resistance': r'Thermal Resistance[\s:]+([0-9.]+)\s*°?C/W'
        }
        
        for param, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                thermal[param] = match.group(1)
        
        return thermal
    
    def _determine_pin_type(self, pin_name: str, pin_desc: str) -> str:
        """Determine pin type from name and description."""
        name_lower = pin_name.lower()
        desc_lower = pin_desc.lower()
        
        if any(term in name_lower for term in ['vdd', 'vcc', 'vbat', 'power']):
            return 'power'
        elif any(term in name_lower for term in ['vss', 'gnd', 'ground']):
            return 'ground'
        elif any(term in name_lower for term in ['clk', 'clock', 'osc']):
            return 'clock'
        elif any(term in desc_lower for term in ['input', 'in']):
            return 'input'
        elif any(term in desc_lower for term in ['output', 'out']):
            return 'output'
        elif any(term in desc_lower for term in ['bidirectional', 'i/o']):
            return 'bidirectional'
        else:
            return 'unknown'
    
    def _create_minimal_analysis(self, component: Component) -> DatasheetAnalysis:
        """Create minimal analysis when datasheet is not available."""
        return DatasheetAnalysis(
            component_id=f"{component.manufacturer}_{component.part_number}",
            pin_configuration={},
            electrical_characteristics={},
            package_dimensions={},
            recommended_layout={},
            power_requirements={},
            signal_integrity_notes=[],
            thermal_considerations={}
        )


# API Implementations for major distributors
class DigiKeyAPI:
    """Digi-Key API integration."""
    
    def __init__(self):
        self.base_url = "https://api.digikey.com"
        self.api_key = os.getenv('DIGIKEY_API_KEY')
        
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def search(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[Component]:
        # Implementation would use Digi-Key's actual API
        # For now, return empty list if no API key
        return []
    
    async def get_component_details(self, part_number: str) -> Optional[Component]:
        # Implementation would fetch detailed component info
        return None


class MouserAPI:
    """Mouser Electronics API integration."""
    
    def __init__(self):
        self.base_url = "https://api.mouser.com"
        self.api_key = os.getenv('MOUSER_API_KEY')
        
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def search(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[Component]:
        return []
    
    async def get_component_details(self, part_number: str) -> Optional[Component]:
        return None


class LCSCComponentAPI:
    """LCSC (JLCPCB) Component API integration."""
    
    def __init__(self):
        self.base_url = "https://jlcpcb.com/componentSearch"
        
    def is_available(self) -> bool:
        return True  # Public API
    
    async def search(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[Component]:
        # Implementation for LCSC search
        return []
    
    async def get_component_details(self, part_number: str) -> Optional[Component]:
        return None


class OctopartAPI:
    """Octopart API integration."""
    
    def __init__(self):
        self.base_url = "https://octopart.com/api"
        self.api_key = os.getenv('OCTOPART_API_KEY')
        
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def search(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[Component]:
        return []
    
    async def get_component_details(self, part_number: str) -> Optional[Component]:
        return None


class ArrowAPI:
    """Arrow Electronics API integration."""
    
    def __init__(self):
        self.base_url = "https://api.arrow.com"
        self.api_key = os.getenv('ARROW_API_KEY')
        
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def search(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[Component]:
        return []
    
    async def get_component_details(self, part_number: str) -> Optional[Component]:
        return None


# Global initialization function for the enhanced component sourcing system
async def initialize_enhanced_component_system():
    """Initialize the enhanced component system with KiCad integration."""
    sourcer = ComponentSourcer()
    await sourcer.initialize_kicad_database()
    return sourcer