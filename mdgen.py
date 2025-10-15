# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import os
import re
import ast
import sys
import time
import json
import shlex
import compileall
import requests
import importlib.metadata
import importlib.util
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from utils.version import get_version_string

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Loading .env manually...")
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Constants
EULA_TEMPLATE_URL = "https://www.apple.com/legal/sla/docs/macOSSequoia.pdf"
MIT_LICENSE_URL = "https://raw.githubusercontent.com/github/choosealicense.com/gh-pages/_licenses/mit.txt"
GITHUB_API_BASE = "https://api.github.com/repos"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Common license file names to check
LICENSE_FILE_NAMES = [
    'LICENSE', 'LICENSE.txt', 'LICENSE.md', 'LICENSE.rst',
    'LICENCE', 'LICENCE.txt', 'LICENCE.md', 'LICENCE.rst',
    'COPYING', 'COPYING.txt', 'COPYING.md',
    'COPYRIGHT', 'COPYRIGHT.txt', 'COPYRIGHT.md',
    'license', 'licence', 'copying', 'copyright'
]

# Cache for license lookups to avoid repeated API calls
license_cache = {}

# Paths
BUILD_INFO_PATH = Path("build_info.json")

# Comprehensive license verification mappings for GitHub-supported licenses
GITHUB_SUPPORTED_LICENSES = {
    "AFL-3.0", "Apache-2.0", "Artistic-2.0", "BSL-1.0", "BSD-2-Clause", 
    "BSD-3-Clause", "BSD-3-Clause-Clear", "BSD-4-Clause", "0BSD", "CC0-1.0", 
    "CC-BY-4.0", "CC-BY-SA-4.0", "WTFPL", "ECL-2.0", "EPL-1.0", "EPL-2.0", 
    "EUPL-1.1", "AGPL-3.0", "GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", 
    "ISC", "LPPL-1.3c", "MS-PL", "MIT", "MPL-2.0", "OSL-3.0", "PostgreSQL", 
    "OFL-1.1", "NCSA", "Unlicense", "Zlib"
}

LICENSE_MAPPINGS = {
    'Apache Software License': 'Apache-2.0',
    'Apache License': 'Apache-2.0',
    'Apache License 2.0': 'Apache-2.0',
    'Apache-2.0': 'Apache-2.0',
    'MIT License': 'MIT',
    'MIT': 'MIT',
    'BSD License': 'BSD-3-Clause',
    'BSD-3-Clause': 'BSD-3-Clause',
    'BSD-2-Clause': 'BSD-2-Clause',
    'GNU General Public License (GPL)': 'GPL-3.0',
    'GNU General Public License v3': 'GPL-3.0',
    'GNU General Public License v3 (GPLv3)': 'GPL-3.0',
    'GNU General Public License v3 or later (GPLv3+)': 'GPL-3.0',
    'GNU General Public License v2': 'GPL-2.0',
    'GNU General Public License v2 (GPLv2)': 'GPL-2.0',
    'GNU General Public License v2 or later (GPLv2+)': 'GPL-2.0',
    'GNU Lesser General Public License v3': 'LGPL-3.0',
    'GNU Lesser General Public License v3 (LGPLv3)': 'LGPL-3.0',
    'GNU Lesser General Public License v3 or later (LGPLv3+)': 'LGPL-3.0',
    'GNU Lesser General Public License v2.1': 'LGPL-2.1',
    'GNU Lesser General Public License v2.1 (LGPLv2.1)': 'LGPL-2.1',
    'GNU Lesser General Public License v2.1 or later (LGPLv2.1+)': 'LGPL-2.1',
    'GNU Affero General Public License v3': 'AGPL-3.0',
    'GNU Affero General Public License v3 (AGPLv3)': 'AGPL-3.0',
    'Python Software Foundation License': 'PSF-2.0',
    'Mozilla Public License 2.0 (MPL 2.0)': 'MPL-2.0',
    'Mozilla Public License 2.0': 'MPL-2.0',
    'Mozilla Public License Version 2.0': 'MPL-2.0',
    'ISC License (ISCL)': 'ISC',
    'ISC License': 'ISC',
    'Zope Public License': 'ZPL-2.1',
    'Artistic License 2.0': 'Artistic-2.0',
    'Eclipse Public License 1.0': 'EPL-1.0',
    'Eclipse Public License 2.0': 'EPL-2.0',
    'European Union Public License 1.1': 'EUPL-1.1',
    'Academic Free License v3.0': 'AFL-3.0',
    'Boost Software License 1.0': 'BSL-1.0',
    'Creative Commons Zero v1.0 Universal': 'CC0-1.0',
    'Creative Commons Attribution 4.0': 'CC-BY-4.0',
    'Creative Commons Attribution Share Alike 4.0': 'CC-BY-SA-4.0',
    'Do What The F*ck You Want To Public License': 'WTFPL',
    'Educational Community License v2.0': 'ECL-2.0',
    'LaTeX Project Public License v1.3c': 'LPPL-1.3c',
    'Microsoft Public License': 'MS-PL',
    'Open Software License 3.0': 'OSL-3.0',
    'PostgreSQL License': 'PostgreSQL',
    'SIL Open Font License 1.1': 'OFL-1.1',
    'University of Illinois/NCSA Open Source License': 'NCSA',
    'The Unlicense': 'Unlicense',
    'zlib License': 'Zlib',
    'zlib/libpng License': 'Zlib'
}

# License requirements for proper attribution and compliance
LICENSE_REQUIREMENTS = {
    'Apache-2.0': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': True,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': False,
        'patent_grant': True
    },
    'MIT': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': False,
        'patent_grant': False
    },
    'GPL-3.0': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': True,
        'patent_grant': True,
        'copyleft': True
    },
    'GPL-2.0': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': True,
        'patent_grant': False,
        'copyleft': True
    },
    'LGPL-3.0': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': True,
        'patent_grant': True,
        'copyleft': 'library_only'
    },
    'LGPL-2.1': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': True,
        'patent_grant': False,
        'copyleft': 'library_only'
    },
    'BSD-3-Clause': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': False,
        'patent_grant': False
    },
    'BSD-2-Clause': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': False,
        'patent_grant': False
    },
    'ISC': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': False,
        'patent_grant': False
    },
    'MPL-2.0': {
        'requires_copyright_notice': True,
        'requires_license_text': True,
        'requires_notice_file': True,
        'requires_attribution': True,
        'allows_modification': True,
        'requires_source_disclosure': True,
        'patent_grant': True,
        'copyleft': 'file_level'
    },
    'CC0-1.0': {
        'requires_copyright_notice': False,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': False,
        'allows_modification': True,
        'requires_source_disclosure': False,
        'patent_grant': False,
        'public_domain': True
    },
    'Unlicense': {
        'requires_copyright_notice': False,
        'requires_license_text': True,
        'requires_notice_file': False,
        'requires_attribution': False,
        'allows_modification': True,
        'requires_source_disclosure': False,
        'patent_grant': False,
        'public_domain': True
    }
}

def make_request_with_retry(url, headers=None, timeout=5):
    """Make HTTP request with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 429:  # Rate limited
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                print(f"    Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}")
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise e
            wait_time = RETRY_DELAY * (2 ** attempt)
            print(f"    Request failed, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait_time)
    return None

def normalize_license_name(license_name):
    """Normalize license names for consistency."""
    if not license_name or license_name.lower() in ['unknown', 'none', '']:
        return None
    
    # Check for exact mapping
    if license_name in LICENSE_MAPPINGS:
        return LICENSE_MAPPINGS[license_name]
    
    # Fuzzy matching for common variations
    license_lower = license_name.lower()
    
    if 'apache' in license_lower:
        if '2.0' in license_lower or 'apache-2.0' in license_lower:
            return 'Apache-2.0'
        return 'Apache-2.0'  # Default to 2.0
    
    if 'mit' in license_lower:
        return 'MIT'
    
    if 'bsd' in license_lower:
        if '2-clause' in license_lower:
            return 'BSD-2-Clause'
        elif '3-clause' in license_lower:
            return 'BSD-3-Clause'
        return 'BSD-3-Clause'  # Default to 3-clause
    
    if 'gpl' in license_lower:
        if 'lgpl' in license_lower or 'lesser' in license_lower:
            if 'v2.1' in license_lower or '2.1' in license_lower:
                return 'LGPL-2.1'
            return 'LGPL-3.0'
        if 'agpl' in license_lower or 'affero' in license_lower:
            return 'AGPL-3.0'
        if 'v3' in license_lower or '3.0' in license_lower:
            return 'GPL-3.0'
        if 'v2' in license_lower or '2.0' in license_lower:
            return 'GPL-2.0'
        return 'GPL-3.0'  # Default to v3
    
    if 'mozilla' in license_lower or 'mpl' in license_lower:
        return 'MPL-2.0'
    
    if 'isc' in license_lower:
        return 'ISC'
    
    if 'artistic' in license_lower:
        return 'Artistic-2.0'
    
    if 'eclipse' in license_lower or 'epl' in license_lower:
        if '2.0' in license_lower:
            return 'EPL-2.0'
        return 'EPL-1.0'
    
    if 'creative commons' in license_lower or 'cc-' in license_lower:
        if 'cc0' in license_lower or 'zero' in license_lower:
            return 'CC0-1.0'
        elif 'by-sa' in license_lower:
            return 'CC-BY-SA-4.0'
        elif 'by' in license_lower:
            return 'CC-BY-4.0'
    
    if 'unlicense' in license_lower:
        return 'Unlicense'
    
    if 'zlib' in license_lower:
        return 'Zlib'
    
    if 'boost' in license_lower:
        return 'BSL-1.0'
    
    # Check if it's already a SPDX identifier
    if license_name in GITHUB_SUPPORTED_LICENSES:
        return license_name
    
    return license_name  # Return original if no mapping found

def extract_copyright_info(text):
    """Extract copyright information from license text or source files."""
    if not text:
        return []
    
    copyright_patterns = [
        r'Copyright\s*©?\s*(\d{4}(?:-\d{4})?)\s+(.+?)(?:\n|$)',
        r'©\s*(\d{4}(?:-\d{4})?)\s+(.+?)(?:\n|$)',
        r'\(c\)\s*(\d{4}(?:-\d{4})?)\s+(.+?)(?:\n|$)',
        r'Copyright\s+\(c\)\s*(\d{4}(?:-\d{4})?)\s+(.+?)(?:\n|$)',
        r'Copyright\s+(\d{4}(?:-\d{4})?)\s+by\s+(.+?)(?:\n|$)',
    ]
    
    copyrights = []
    for pattern in copyright_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            year = match.group(1)
            holder = match.group(2).strip().rstrip('.,;')
            if holder and len(holder) > 3:  # Filter out noise
                copyrights.append(f"Copyright © {year} {holder}")
    
    return list(set(copyrights))  # Remove duplicates

def validate_license_compliance(license_name, license_text, copyright_notices):
    """Validate that we have all required information for license compliance."""
    if not license_name or license_name not in LICENSE_REQUIREMENTS:
        return False, ["Unknown or unsupported license type"]
    
    requirements = LICENSE_REQUIREMENTS[license_name]
    issues = []
    
    # Check if copyright notice is required but missing
    if requirements.get('requires_copyright_notice', False) and not copyright_notices:
        issues.append(f"License {license_name} requires copyright notice but none found")
    
    # Check if license text is required but missing
    if requirements.get('requires_license_text', False) and not license_text:
        issues.append(f"License {license_name} requires full license text but none found")
    
    # Check for copyleft licenses that require source disclosure
    if requirements.get('requires_source_disclosure', False):
        issues.append(f"License {license_name} requires source code disclosure - ensure compliance")
    
    return len(issues) == 0, issues

def get_enhanced_package_info(package_name):
    """Get comprehensive package information including copyright and attribution."""
    package_info = {
        'name': package_name,
        'version': 'Unknown',
        'license_name': None,
        'license_text': None,
        'copyright_notices': [],
        'authors': [],
        'homepage': None,
        'source_url': None,
        'compliance_status': 'unknown'
    }
    
    # Try to get local package metadata
    try:
        dist = importlib.metadata.distribution(package_name)
        package_info['version'] = dist.version
        
        # Get authors
        author = dist.metadata.get('Author')
        author_email = dist.metadata.get('Author-email')
        maintainer = dist.metadata.get('Maintainer')
        maintainer_email = dist.metadata.get('Maintainer-email')
        
        if author:
            package_info['authors'].append(author)
        if maintainer and maintainer != author:
            package_info['authors'].append(maintainer)
        
        # Get URLs
        package_info['homepage'] = dist.metadata.get('Home-page')
        project_urls = dist.metadata.get('Project-URL')
        if project_urls:
            for url_line in project_urls:
                if 'source' in url_line.lower() or 'repository' in url_line.lower():
                    package_info['source_url'] = url_line.split(', ', 1)[1] if ', ' in url_line else url_line
                    break
        
        # Extract license information
        license_text = dist.metadata.get('License')
        if license_text and license_text.strip() and license_text.strip().upper() not in ['UNKNOWN', 'NONE']:
            package_info['license_text'] = license_text
            package_info['copyright_notices'] = extract_copyright_info(license_text)
        
        # Get license from classifiers
        classifiers = dist.metadata.get_all('Classifier') or []
        for classifier in classifiers:
            if classifier.startswith('License ::'):
                parts = classifier.split(' :: ')
                if len(parts) >= 3:
                    package_info['license_name'] = normalize_license_name(parts[2])
                    break
        
        # Try to find LICENSE files in package
        if hasattr(dist, 'files') and dist.files:
            for file in dist.files:
                if file.name.upper() in [n.upper() for n in LICENSE_FILE_NAMES]:
                    try:
                        license_content = file.read_text()
                        if license_content and not package_info['license_text']:
                            package_info['license_text'] = license_content
                            package_info['copyright_notices'].extend(extract_copyright_info(license_content))
                        if not package_info['license_name']:
                            package_info['license_name'] = infer_license_from_text(license_content)
                    except Exception:
                        continue
                        
    except Exception:
        pass
    
    # Validate compliance
    is_compliant, issues = validate_license_compliance(
        package_info['license_name'], 
        package_info['license_text'], 
        package_info['copyright_notices']
    )
    package_info['compliance_status'] = 'compliant' if is_compliant else 'issues'
    package_info['compliance_issues'] = issues if not is_compliant else []
    
    return package_info
    """Normalize license names for consistency."""
    if not license_name or license_name.lower() in ['unknown', 'none', '']:
        return None
    
    # Check for exact mapping
    if license_name in LICENSE_MAPPINGS:
        return LICENSE_MAPPINGS[license_name]
    
    # Fuzzy matching for common variations
    license_lower = license_name.lower()
    
    if 'apache' in license_lower:
        if '2.0' in license_lower or 'apache-2.0' in license_lower:
            return 'Apache-2.0'
        return 'Apache-2.0'  # Default to 2.0
    
    if 'mit' in license_lower:
        return 'MIT'
    
    if 'bsd' in license_lower:
        if '2-clause' in license_lower:
            return 'BSD-2-Clause'
        elif '3-clause' in license_lower:
            return 'BSD-3-Clause'
        return 'BSD-3-Clause'  # Default to 3-clause
    
    if 'gpl' in license_lower:
        if 'lgpl' in license_lower or 'lesser' in license_lower:
            return 'LGPL-3.0+'
        if 'v3' in license_lower or '3.0' in license_lower:
            return 'GPL-3.0'
        if 'v2' in license_lower or '2.0' in license_lower:
            return 'GPL-2.0'
        return 'GPL-3.0'  # Default to v3
    
    if 'mozilla' in license_lower or 'mpl' in license_lower:
        return 'MPL-2.0'
    
    if 'isc' in license_lower:
        return 'ISC'
    
    return license_name  # Return original if no mapping found

def verify_license_consistency(github_license, pypi_license):
    """Verify consistency between GitHub and PyPI license information."""
    if not github_license or not pypi_license:
        return True  # Can't verify if one is missing
    
    github_normalized = normalize_license_name(github_license)
    pypi_normalized = normalize_license_name(pypi_license)
    
    if github_normalized == pypi_normalized:
        return True
    
    # Check for common aliases
    aliases = {
        'Apache-2.0': ['Apache Software License', 'Apache License'],
        'MIT': ['MIT License'],
        'BSD-3-Clause': ['BSD License', 'BSD'],
        'GPL-3.0': ['GNU General Public License (GPL)', 'GPL'],
        'PSF-2.0': ['Python Software Foundation License']
    }
    
    for canonical, alias_list in aliases.items():
        if ((github_normalized == canonical and pypi_license in alias_list) or
            (pypi_normalized == canonical and github_license in alias_list)):
            return True
    
    return False

def prompt_user():
    print("Please enter the following details for the EULA:")
    software_name = input("Software Name: ").strip()
    
    # Get dynamic version from git
    dynamic_version = get_version_string()
    software_version = input(f"Software Version [{dynamic_version}]: ").strip()
    if not software_version:
        software_version = dynamic_version
        
    developer_name = input("Developer Name [PI & Other Tales Inc.]: ").strip()
    if not developer_name:
        developer_name = "PI & Other Tales Inc."
    developer_address = input("Developer Address [8 The Green, Dover, Delaware 19901 United States]: ").strip()
    if not developer_address:
        developer_address = "8 The Green, Dover, Delaware 19901 United States"
    developer_email = input("Developer Email [hello@othertales.co]: ").strip()
    if not developer_email:
        developer_email = "hello@othertales.co"
    return software_name, software_version, developer_name, developer_address, developer_email

def get_local_modules(base_dir):
    """Get all local module names from the project."""
    local_modules = set()
    
    # Get all Python files in root directory (without .py extension)
    for file in os.listdir(base_dir):
        if file.endswith('.py') and file != '__init__.py':
            module_name = file[:-3]  # Remove .py extension
            local_modules.add(module_name)
    
    # Get all directories with __init__.py (packages) or any .py files
    for root, dirs, files in os.walk(base_dir):
        # Skip virtual environment and special directories
        dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git', 'node_modules', '.tox']]
        
        # Check if directory contains Python files
        has_py_files = any(f.endswith('.py') for f in files)
        
        if '__init__.py' in files or has_py_files:
            # Convert directory path to module name
            rel_path = os.path.relpath(root, base_dir)
            if rel_path != '.':
                module_name = rel_path.replace(os.path.sep, '.')
                local_modules.add(module_name)
                # Also add parent modules
                parts = module_name.split('.')
                for i in range(len(parts)):
                    local_modules.add('.'.join(parts[:i+1]))
    
    return local_modules

def extract_imports_from_code(base_dir):
    imports = set()
    file_count = 0
    
    # First, get all local modules
    local_modules = get_local_modules(base_dir)
    print(f"  Found {len(local_modules)} local modules: {', '.join(sorted(local_modules))}")
    
    for root, dirs, files in os.walk(base_dir):
        # Skip virtual environment directories
        dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git', 'node_modules', '.tox']]
        
        for file in files:
            if file.endswith(".py"):
                file_count += 1
                file_path = os.path.join(root, file)
                print(f"  Scanning {file_path}...")
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for n in node.names:
                                    module_name = n.name.split('.')[0]
                                    # Skip if it's a local module
                                    if module_name not in local_modules:
                                        imports.add(module_name)
                            elif isinstance(node, ast.ImportFrom) and node.module:
                                module_name = node.module.split('.')[0]
                                # Skip if it's a local module or relative import
                                if not node.level and module_name not in local_modules:
                                    imports.add(module_name)
                    except SyntaxError:
                        print(f"    Warning: Skipping {file_path} (syntax error)")
    
    # Also skip Python standard library modules
    if hasattr(sys, 'stdlib_module_names'):
        stdlib_modules = set(sys.stdlib_module_names)
        imports = imports - stdlib_modules
        print(f"  Excluded {len(stdlib_modules)} standard library modules")
    else:
        # Fallback for older Python versions - list common stdlib modules
        common_stdlib = {
            'os', 'sys', 're', 'json', 'time', 'datetime', 'math', 'random',
            'collections', 'itertools', 'functools', 'operator', 'typing',
            'pathlib', 'io', 'string', 'textwrap', 'copy', 'pickle',
            'subprocess', 'threading', 'multiprocessing', 'asyncio',
            'urllib', 'http', 'email', 'html', 'xml', 'csv', 'sqlite3',
            'logging', 'warnings', 'unittest', 'doctest', 'pdb',
            'argparse', 'configparser', 'hashlib', 'hmac', 'secrets',
            'uuid', 'socket', 'ssl', 'select', 'platform', 'locale',
            'codecs', 'encodings', 'base64', 'binascii', 'struct',
            'array', 'queue', 'heapq', 'bisect', 'weakref', 'types',
            'contextlib', 'abc', 'enum', 'dataclasses', 'importlib',
            'pkgutil', 'inspect', 'ast', 'dis', 'traceback', 'linecache',
            'shutil', 'tempfile', 'glob', 'fnmatch', 'stat', 'fileinput',
            'gzip', 'bz2', 'lzma', 'zipfile', 'tarfile', 'zlib',
            'builtins', '__future__', 'gc', 'atexit', 'signal'
        }
        imports = imports - common_stdlib
        print(f"  Excluded {len(common_stdlib)} known standard library modules")
    
    print(f"  Scanned {file_count} Python files, found {len(imports)} third-party imports")
    return sorted(imports)

def fetch_github_repo(package_name):
    try:
        response = make_request_with_retry(f"https://pypi.org/pypi/{package_name}/json")
        data = response.json()
        
        # Try multiple sources for GitHub URL
        possible_urls = [
            data['info'].get('project_urls', {}).get('Source', ''),
            data['info'].get('project_urls', {}).get('Homepage', ''),
            data['info'].get('project_urls', {}).get('Repository', ''),
            data['info'].get('project_urls', {}).get('Bug Tracker', ''),
            data['info'].get('home_page', ''),
            data['info'].get('download_url', ''),
        ]
        
        for repo_url in possible_urls:
            if repo_url and "github.com" in repo_url:
                # Clean up URL and extract owner/repo
                repo_url = repo_url.replace('https://', '').replace('http://', '')
                repo_url = repo_url.replace('www.', '').replace('.git', '')
                repo_url = repo_url.split('#')[0].split('?')[0]  # Remove anchors and query params
                parts = repo_url.split("github.com/")[-1].split("/")
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]
                    return f"{owner}/{repo}".strip("/")
    except Exception:
        return None
    return None

def fetch_github_license(repo):
    try:
        url = f"{GITHUB_API_BASE}/{repo}/license"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        response = make_request_with_retry(url, headers=headers)
        
        if response and response.ok:
            data = response.json()
            license_type = data['license']['spdx_id']
            # Get license text with retry
            license_response = make_request_with_retry(data['download_url'])
            if license_response:
                license_text = license_response.text
                return normalize_license_name(license_type), license_text
    except Exception as e:
        print(f"    GitHub API error: {str(e)}")
        return None, None
    return None, None

def fetch_local_package_license(package_name):
    """Fetch license from locally installed package using importlib.metadata."""
    try:
        # Try to get distribution metadata
        dist = importlib.metadata.distribution(package_name)
        
        # Try multiple metadata fields
        license_text = dist.metadata.get('License')
        if license_text and license_text.strip() and license_text.strip().upper() not in ['UNKNOWN', 'NONE']:
            # Try to determine license type from classifiers
            license_type = None
            classifiers = dist.metadata.get_all('Classifier') or []
            for classifier in classifiers:
                if classifier.startswith('License ::'):
                    parts = classifier.split(' :: ')
                    if len(parts) >= 3:
                        license_type = normalize_license_name(parts[2])
                        break
            
            if not license_type and license_text:
                # Try to infer from license text
                license_type = infer_license_from_text(license_text)
            
            return license_type, license_text
        
        # Try to find LICENSE file in package location
        if hasattr(dist, 'files') and dist.files:
            for file in dist.files:
                if file.name.upper() in [n.upper() for n in LICENSE_FILE_NAMES]:
                    try:
                        license_content = file.read_text()
                        if license_content:
                            license_type = infer_license_from_text(license_content)
                            return license_type, license_content
                    except Exception:
                        continue
                        
    except Exception:
        pass
    
    return None, None

def infer_license_from_text(text):
    """Infer license type from license text content."""
    if not text:
        return None
        
    text_lower = text.lower()
    
    # Common license detection patterns
    patterns = {
        'MIT': ['mit license', 'permission is hereby granted, free of charge'],
        'Apache-2.0': ['apache license', 'version 2.0', 'www.apache.org/licenses/'],
        'BSD-3-Clause': ['bsd 3-clause', 'redistribution and use in source and binary forms'],
        'BSD-2-Clause': ['bsd 2-clause', 'simplified bsd license'],
        'GPL-3.0': ['gnu general public license', 'version 3', 'gpl-3', 'gplv3'],
        'GPL-2.0': ['gnu general public license', 'version 2', 'gpl-2', 'gplv2'],
        'LGPL-3.0': ['gnu lesser general public license', 'lgpl', 'version 3'],
        'ISC': ['isc license', 'permission to use, copy, modify'],
        'MPL-2.0': ['mozilla public license', 'version 2.0', 'mpl-2.0'],
        'CC0-1.0': ['cc0', 'public domain', 'no copyright'],
        'Unlicense': ['unlicense', 'public domain', 'no conditions whatsoever'],
    }
    
    for license_type, keywords in patterns.items():
        if all(keyword in text_lower for keyword in keywords):
            return license_type
    
    # Fallback: check for common license URLs
    url_patterns = {
        'opensource.org/licenses/MIT': 'MIT',
        'opensource.org/licenses/Apache-2.0': 'Apache-2.0',
        'opensource.org/licenses/BSD-3-Clause': 'BSD-3-Clause',
        'gnu.org/licenses/gpl-3.0': 'GPL-3.0',
        'mozilla.org/MPL/2.0': 'MPL-2.0',
    }
    
    for url, license_type in url_patterns.items():
        if url in text:
            return license_type
    
    return None

def fetch_github_raw_license(repo):
    """Fetch license file directly from GitHub raw content."""
    try:
        base_url = f"https://raw.githubusercontent.com/{repo}"
        
        # Try main/master branch
        for branch in ['main', 'master']:
            for filename in LICENSE_FILE_NAMES[:8]:  # Try most common names
                url = f"{base_url}/{branch}/{filename}"
                try:
                    response = make_request_with_retry(url, timeout=3)
                    if response and response.ok:
                        license_text = response.text
                        license_type = infer_license_from_text(license_text)
                        return license_type, license_text
                except Exception:
                    continue
                    
    except Exception:
        pass
    
    return None, None

def fetch_pypi_license(package_name):
    """Fetch license information directly from PyPI."""
    try:
        response = make_request_with_retry(f"https://pypi.org/pypi/{package_name}/json")
        data = response.json()
        
        info = data['info']
        license_text = info.get('license', '') or ''  # Ensure it's never None
        
        # Extract license type from classifiers
        license_type = 'Unknown'
        classifiers = info.get('classifiers', [])
        for classifier in classifiers:
            if classifier.startswith('License ::'):
                # Extract license name from classifier
                parts = classifier.split(' :: ')
                if len(parts) >= 3:
                    license_type = parts[2]
                    break
        
        # If no license text but have classifier, use classifier
        if not license_text.strip() and license_type != 'Unknown':
            license_text = f"Licensed under {license_type}"
        
        # Skip if no useful license information
        if not license_text.strip() or license_text.strip().upper() in ['UNKNOWN', 'NONE', '']:
            return None, None
        
        # Normalize license type    
        normalized_type = normalize_license_name(license_type)
        if not normalized_type:
            return None, None
            
        return normalized_type, license_text
        
    except Exception as e:
        print(f"    PyPI API error: {str(e)}")
        return None, None

def detect_repository_visibility():
    """Detect if the repository is public or private based on various indicators."""
    # Check if there's a GitHub remote and if it's accessible
    try:
        result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
        if result.returncode == 0 and 'github.com' in result.stdout:
            # Extract the repository URL
            for line in result.stdout.split('\n'):
                if 'github.com' in line and 'fetch' in line:
                    repo_url = line.split()[1]
                    # Try to access the repository
                    try:
                        response = requests.head(repo_url, timeout=5)
                        if response.status_code == 200:
                            print(f"    Repository appears to be public: {repo_url}")
                            return 'public'
                        else:
                            print(f"    Repository appears to be private or inaccessible: {repo_url}")
                            return 'private'
                    except requests.RequestException:
                        print("    Could not determine repository visibility from URL")
                        break
    except subprocess.CalledProcessError:
        pass
    
    # Check for open source license indicators
    open_source_indicators = []
    
    # Check if there are open source license files
    license_files = []
    for filename in ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING', 'COPYRIGHT']:
        if Path(filename).exists():
            license_files.append(filename)
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if any(oss_license in content for oss_license in 
                          ['mit license', 'apache license', 'bsd license', 'gpl', 'mozilla public']):
                        open_source_indicators.append(f"Open source license found in {filename}")
            except Exception:
                pass
    
    # Check README for open source badges or indicators
    readme_files = ['README.md', 'README.rst', 'README.txt', 'README']
    for readme in readme_files:
        if Path(readme).exists():
            try:
                with open(readme, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'MIT' in content and 'img.shields.io' in content:
                        open_source_indicators.append("MIT license badge found in README")
                    if 'opensource.org' in content:
                        open_source_indicators.append("Open source reference found in README")
                    if 'Research Status: Experimental' in content:
                        open_source_indicators.append("Research/experimental status suggests open source")
            except Exception:
                pass
    
    # Check package.json or pyproject.toml for license indicators
    if Path('pyproject.toml').exists():
        try:
            with open('pyproject.toml', 'r', encoding='utf-8') as f:
                content = f.read()
                if 'license' in content.lower() and any(oss in content.lower() for oss in ['mit', 'apache', 'bsd']):
                    open_source_indicators.append("Open source license found in pyproject.toml")
        except Exception:
            pass
    
    # If we found open source indicators, assume public
    if open_source_indicators:
        print(f"    Open source indicators found:")
        for indicator in open_source_indicators:
            print(f"      - {indicator}")
        return 'public'
    
    # Default to private if no clear indicators
    print("    No clear public repository indicators found, assuming private")
    return 'private'

def build_eula(software_name, software_version, developer_name, developer_address, developer_email, modules_info):
    current_year = datetime.now().year
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Detect repository visibility to determine EULA type
    repo_visibility = detect_repository_visibility()
    
    if repo_visibility == 'public':
        # Softer EULA for public repositories - allows research and non-commercial use
        eula = f"""END USER LICENSE AGREEMENT (Research and Non-Commercial Use)
Last updated {current_date}

{software_name} is licensed to You (End-User) by {developer_name}, located at {developer_address} ("Licensor"), for research, educational, and non-commercial use only under the terms of this License Agreement.

IMPORTANT: This software is provided for research, educational, and personal development purposes. Commercial use requires a separate commercial license.

By downloading, accessing, or using {software_name} ("Licensed Application"), You indicate that You agree to be bound by all of the terms and conditions of this License Agreement.

1. THE APPLICATION

{software_name} ("Licensed Application") is a research framework created to provide professional-grade PCB design automation functionality using artificial intelligence and machine learning techniques. It is designed for research, educational, and non-commercial development purposes.

The Licensed Application incorporates advanced natural language processing, hardware knowledge representation, and automated design rule verification to demonstrate novel approaches to AI-driven hardware design systems.

2. SCOPE OF LICENSE - RESEARCH AND NON-COMMERCIAL USE

2.1 PERMITTED USES: You are granted a non-exclusive license to use the Licensed Application for:
   - Academic research and educational purposes
   - Personal learning and skill development
   - Non-commercial open source projects
   - Proof-of-concept and prototype development
   - Scientific publication and academic collaboration

2.2 COMMERCIAL USE RESTRICTION: You may NOT use the Licensed Application for:
   - Commercial products or services
   - Revenue-generating activities
   - Production systems in commercial environments
   - Consulting or professional services
   - Any activity that generates direct or indirect commercial benefit

2.3 MODIFICATION AND DISTRIBUTION: You may:
   - Modify the Licensed Application for your permitted use cases
   - Share modifications with the research community
   - Contribute improvements back to the project
   - Create derivative works for research purposes

2.4 ATTRIBUTION REQUIREMENT: When using or referencing this software in research, publications, or presentations, You must:
   - Provide appropriate citation and attribution to {developer_name}
   - Include a reference to the original software and its research objectives
   - Acknowledge the experimental nature of the research framework

3. COMMERCIAL LICENSE

3.1 For commercial use, including but not limited to production systems, commercial products, or revenue-generating activities, You must obtain a separate commercial license from {developer_name}.

3.2 Contact {developer_name} at {developer_address} for commercial licensing inquiries.

4. WARRANTY AND DISCLAIMER

4.1 RESEARCH SOFTWARE: This Licensed Application is provided "AS IS" for research purposes. It is experimental software that may contain bugs, incomplete features, or other limitations.

4.2 NO WARRANTY: {developer_name} makes no warranties, express or implied, regarding the Licensed Application's performance, reliability, or fitness for any particular purpose.

4.3 LIMITATION OF LIABILITY: {developer_name} shall not be liable for any damages arising from the use of this research software.

5. RESEARCH COLLABORATION

5.1 {developer_name} encourages collaboration and welcomes contributions from the research community.

5.2 Contributions, feedback, and improvements are welcomed and may be incorporated into future versions of the Licensed Application.

6. TERMINATION

6.1 This license remains in effect until terminated.

6.2 {developer_name} may terminate this license if You violate any terms, particularly the commercial use restrictions.

6.3 Upon termination, You must cease all use of the Licensed Application and destroy all copies.

7. APPLICABLE LAW

This License Agreement is governed by the laws of United States.

8. CONTACT INFORMATION

For general inquiries, commercial licensing, or research collaboration:

{developer_name}
{developer_address}
Email: {developer_email}

"""
    else:
        # Full commercial EULA for private repositories
        eula = f"""END USER LICENSE AGREEMENT
Last updated {current_date}

{software_name} is licensed to You (End-User) by {developer_name}, located at {developer_address} ("Licensor"), for use only under the terms of this License Agreement. We are registered in United States and have our registered office at {developer_address}.

By downloading the Licensed Application from official distribution channels, and any update thereto (as permitted by this License Agreement), You indicate that You agree to be bound by all of the terms and conditions of this License Agreement.

{developer_name} is solely responsible for the Licensed Application and the content thereof.

{software_name} is licensed to You for use only under the terms of this License Agreement. The Licensor reserves all rights not expressly granted to You.

1. THE APPLICATION

{software_name} ("Licensed Application") is professional software created to provide advanced functionality and customized solutions.

The Licensed Application is not tailored to comply with industry-specific regulations (Health Insurance Portability and Accountability Act (HIPAA), Federal Information Security Management Act (FISMA), etc.), so if your interactions would be subjected to such laws, you may not use this Licensed Application. You may not use the Licensed Application in a way that would violate the Gramm-Leach-Bliley Act (GLBA).

2. SCOPE OF LICENSE

2.1 You are given a non-transferable, non-exclusive, non-sublicensable license to install and use the Licensed Application on devices that You (End-User) own or control.

2.2 This license will also govern any updates of the Licensed Application provided by Licensor that replace, repair, and/or supplement the first Licensed Application, unless a separate license is provided for such update.

2.3 You may not share or make the Licensed Application available to third parties, sell, rent, lend, lease or otherwise redistribute the Licensed Application without {developer_name}'s prior written consent.

2.4 You may not reverse engineer, translate, disassemble, integrate, decompile, remove, modify, combine, create derivative works or updates of, adapt, or attempt to derive the source code of the Licensed Application, or any part thereof without {developer_name}'s prior written consent.

2.5 You may not copy or alter the Licensed Application or portions thereof. You may create and store copies only on devices that You own or control for backup keeping under the terms of this license.

2.6 Violations of the obligations mentioned above may be subject to prosecution and damages.

2.7 Licensor reserves the right to modify the terms and conditions of licensing.

3. TECHNICAL REQUIREMENTS

3.1 The Licensed Application requires version {software_version} or higher. Licensor recommends using the latest version.

3.2 Licensor attempts to keep the Licensed Application updated. You are not granted rights to claim such an update.

3.3 You acknowledge that it is Your responsibility to confirm that Your device satisfies the technical specifications.

3.4 Licensor reserves the right to modify the technical specifications as appropriate.

4. MAINTENANCE AND SUPPORT

4.1 The Licensor is solely responsible for providing any maintenance and support services for this Licensed Application. You can reach the Licensor at {developer_address}.

5. USE OF DATA

You acknowledge that Licensor may periodically collect and use technical data and related information about your device, system, and application software for purposes of providing services related to the Licensed Application.

6. LIABILITY

6.1 Licensor's responsibility in the case of violation of obligations and tort shall be limited to intent and gross negligence. Liability shall be limited to foreseeable, contractually typical damages.

6.2 Licensor takes no accountability or responsibility for any damages caused due to a breach of duties. You are required to make use of backup functions to avoid data loss.

7. WARRANTY

7.1 Licensor warrants that the Licensed Application is free of spyware, trojan horses, viruses, or any other malware at the time of Your download.

7.2 No warranty is provided for the Licensed Application that has been modified, handled inappropriately, or used inappropriately.

7.3 You are required to inspect the Licensed Application immediately after installing it and notify {developer_name} about issues discovered without delay.

8. CONTACT INFORMATION

For general inquiries, complaints, questions or claims concerning the Licensed Application, please contact:

{developer_name}
{developer_address}
Email: {developer_email}

9. TERMINATION

The license is valid until terminated by {developer_name} or by You. Your rights under this license will terminate automatically if You fail to adhere to any term(s) of this license. Upon termination, You shall stop all use of the Licensed Application and destroy all copies.

10. APPLICABLE LAW

This License Agreement is governed by the laws of United States.

=========================
OPEN SOURCE COMPONENTS AND LICENSES
=========================

This software incorporates open source components. Each component is subject to its own license terms, which must be complied with when using this software.

"""
    
    # Add comprehensive open source component information with proper attribution
    compliance_warnings = []
    copyleft_components = []
    
    for mod in sorted(modules_info):
        # Get enhanced package information
        if isinstance(modules_info[mod], tuple) and len(modules_info[mod]) >= 3:
            # Legacy format - convert to enhanced format
            license_name, license_text, source_desc = modules_info[mod]
            package_info = {
                'name': mod,
                'license_name': license_name,
                'license_text': license_text,
                'copyright_notices': extract_copyright_info(license_text) if license_text else [],
                'compliance_status': 'unknown',
                'compliance_issues': [],
                'version': 'Unknown',
                'authors': [],
                'homepage': None,
                'source_url': None
            }
        else:
            package_info = modules_info[mod]
        
        if not package_info.get('license_name') or not package_info.get('license_text'):
            continue
            
        license_name = package_info['license_name']
        license_text = package_info['license_text']
        copyright_notices = package_info.get('copyright_notices', [])
        
        # Check for compliance issues
        if package_info.get('compliance_status') == 'issues':
            compliance_warnings.extend(package_info.get('compliance_issues', []))
        
        # Track copyleft licenses
        requirements = LICENSE_REQUIREMENTS.get(license_name, {})
        if requirements.get('copyleft'):
            copyleft_components.append(f"{mod} ({license_name})")
        
        # Get version information
        try:
            component_version = importlib.metadata.version(mod)
        except importlib.metadata.PackageNotFoundError:
            component_version = package_info.get('version', 'Unknown')
        
        # Build comprehensive attribution section
        eula += f"\n{'-'*50}\n"
        eula += f"Component: {mod}\n"
        eula += f"Version: {component_version}\n"
        eula += f"License: {license_name}\n"
        
        # Add authors if available
        authors = package_info.get('authors', [])
        if authors:
            eula += f"Authors: {', '.join(authors)}\n"
        
        # Add homepage if available
        homepage = package_info.get('homepage')
        if homepage:
            eula += f"Homepage: {homepage}\n"
        
        # Add source URL if available
        source_url = package_info.get('source_url')
        if source_url:
            eula += f"Source: {source_url}\n"
        
        # Add copyright notices
        if copyright_notices:
            eula += f"\nCopyright Notices:\n"
            for notice in copyright_notices:
                eula += f"  {notice}\n"
        
        # Add license requirements notice
        if requirements:
            if requirements.get('requires_attribution'):
                eula += f"\nATTRIBUTION REQUIRED: This component requires attribution in derivative works.\n"
            if requirements.get('requires_source_disclosure'):
                eula += f"SOURCE DISCLOSURE REQUIRED: This component requires source code disclosure for derivative works.\n"
            if requirements.get('patent_grant'):
                eula += f"PATENT GRANT: This license includes patent protection.\n"
        
        eula += f"\nLicense Text:\n{license_text}\n"
        eula += f"{'-'*50}\n"
    
    # Add compliance warnings if any
    if compliance_warnings:
        eula += f"\n\n{'='*50}\n"
        eula += f"LICENSE COMPLIANCE NOTICES\n"
        eula += f"{'='*50}\n\n"
        eula += "IMPORTANT: The following compliance issues were identified:\n\n"
        for warning in compliance_warnings:
            eula += f"⚠️  {warning}\n"
        eula += "\nPlease ensure all license requirements are met before distributing this software.\n"
    
    # Add copyleft license notice if any
    if copyleft_components:
        eula += f"\n\n{'='*50}\n"
        eula += f"COPYLEFT LICENSE NOTICE\n"
        eula += f"{'='*50}\n\n"
        eula += "The following components use copyleft licenses that may require source code disclosure:\n\n"
        for component in copyleft_components:
            eula += f"• {component}\n"
        eula += "\nEnsure compliance with copyleft requirements when distributing this software.\n"
    
    # Add supported license information
    eula += f"\n\n{'='*50}\n"
    eula += f"GITHUB-SUPPORTED OPEN SOURCE LICENSES\n"
    eula += f"{'='*50}\n\n"
    eula += "This software supports and validates compliance with the following GitHub-approved open source licenses:\n\n"
    
    for license_id in sorted(GITHUB_SUPPORTED_LICENSES):
        eula += f"• {license_id}\n"
    
    eula += f"\nFor more information about these licenses, visit: https://choosealicense.com/\n"
    
    # Add version and copyright information at the end
    eula += f"\n\n{'='*50}\n"
    eula += f"SOFTWARE INFORMATION\n"
    eula += f"{'='*50}\n\n"
    eula += f"Licensed Application: {software_name}\n"
    eula += f"Version: {software_version}\n"
    eula += f"Generated: {current_date}\n"
    eula += f"Copyright © {current_year} {developer_name}. All Rights Reserved.\n"
    eula += f"\nThis license document was automatically generated to ensure compliance with all open source license requirements.\n"
    
    return eula

def generate_build_metadata(targets=None):
    """Compile target modules and persist build metadata for the Rich UI."""
    targets = targets or ["cli_interface.py", "narrator_gpt.py"]
    
    for target in targets:
        try:
            compiled = compileall.compile_file(target, force=True, quiet=1)
            if not compiled:
                print(f"Warning: Failed to compile target: {target}")
        except OSError as exc:
            print(f"Warning: Could not compile {target}: {exc}")
    
    compile_command = [sys.executable, "-m", "compileall", *targets]
    compile_command_str = " ".join(shlex.quote(part) for part in compile_command)
    
    timestamp = datetime.now(timezone.utc)
    build_number = int(timestamp.timestamp())
    
    build_info = {
        "build_number": build_number,
        "generated_at": timestamp.isoformat(),
        "compile_command": compile_command_str,
        "targets": targets
    }
    
    try:
        with BUILD_INFO_PATH.open("w", encoding="utf-8") as fh:
            json.dump(build_info, fh, indent=2)
        print(f"Build metadata written to {BUILD_INFO_PATH}")
    except OSError as exc:
        print(f"Warning: Unable to write build metadata: {exc}")
    
    print(f"Suggested compile command to reproduce build: {compile_command_str}")
    return build_info

def get_comment_syntax(file_extension):
    """Get the appropriate comment syntax for different file types."""
    comment_map = {
        '.py': '#',
        '.sh': '#',
        '.bash': '#',
        '.yml': '#',
        '.yaml': '#',
        '.toml': '#',
        '.ini': '#',
        '.cfg': '#',
        '.js': '//',
        '.ts': '//',
        '.jsx': '//',
        '.tsx': '//',
        '.java': '//',
        '.c': '//',
        '.cpp': '//',
        '.cc': '//',
        '.cxx': '//',
        '.h': '//',
        '.hpp': '//',
        '.cs': '//',
        '.go': '//',
        '.rs': '//',
        '.swift': '//',
        '.kt': '//',
        '.php': '//',
        '.rb': '#',
        '.pl': '#',
        '.r': '#',
        '.sql': '--',
        '.html': '<!--',
        '.xml': '<!--',
        '.css': '/*',
        '.scss': '//',
        '.sass': '//',
        '.less': '//',
        '.md': '<!--',
        '.tex': '%',
        '.lua': '--',
        '.vim': '"',
        '.ps1': '#',
        '.bat': 'REM',
        '.cmd': 'REM',
    }
    return comment_map.get(file_extension.lower())

def get_source_files(base_dir="."):
    """Find all source code files in the project."""
    source_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.cc', 
        '.cxx', '.h', '.hpp', '.cs', '.go', '.rs', '.swift', '.kt', '.php', 
        '.rb', '.pl', '.r', '.sql', '.html', '.xml', '.css', '.scss', 
        '.sass', '.less', '.md', '.tex', '.lua', '.vim', '.ps1', '.bat', 
        '.cmd', '.sh', '.bash', '.yml', '.yaml', '.toml', '.ini', '.cfg'
    }
    
    source_files = []
    exclude_dirs = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', 
                   '.tox', '.pytest_cache', '.coverage', 'dist', 'build', 
                   '.eggs', '*.egg-info'}
    
    for root, dirs, files in os.walk(base_dir):
        # Remove excluded directories from search
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix in source_extensions:
                source_files.append(file_path)
    
    return sorted(source_files)

def has_copyright_notice(file_path):
    """Check if file already has a copyright notice."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1000)  # Check first 1000 characters
            return 'Copyright' in content or '©' in content
    except Exception:
        return False

def add_copyright_to_file(file_path, developer_name):
    """Add copyright notice to a single file."""
    current_year = datetime.now().year
    copyright_text = f"Copyright © {current_year} {developer_name}. All Rights Reserved."
    
    comment_prefix = get_comment_syntax(file_path.suffix)
    if not comment_prefix:
        print(f"  Skipping {file_path}: Unknown file type")
        return False
    
    # Handle special cases
    if comment_prefix == '<!--':
        copyright_line = f"<!-- {copyright_text} -->\n"
    elif comment_prefix == '/*':
        copyright_line = f"/* {copyright_text} */\n"
    else:
        copyright_line = f"{comment_prefix} {copyright_text}\n"
    
    try:
        # Read existing content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file is empty or only whitespace
        if not content.strip():
            new_content = copyright_line
        else:
            # Handle shebang lines for scripts
            lines = content.split('\n')
            insert_index = 0
            
            # Check for shebang
            if lines and lines[0].startswith('#!'):
                insert_index = 1
                if insert_index < len(lines):
                    # Insert after shebang, before any other content
                    lines.insert(insert_index, copyright_line.rstrip())
                else:
                    lines.append(copyright_line.rstrip())
            else:
                # Insert at the very beginning
                lines.insert(0, copyright_line.rstrip())
            
            new_content = '\n'.join(lines)
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
        
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return False

def add_copyright_headers(developer_name):
    """Add copyright headers to all source files in the project."""
    print(f"\nAdding copyright headers to source files...")
    print(f"Developer: {developer_name}")
    
    source_files = get_source_files()
    
    if not source_files:
        print("No source files found.")
        return
    
    print(f"Found {len(source_files)} source files")
    
    processed = 0
    skipped = 0
    errors = 0
    
    for file_path in source_files:
        if has_copyright_notice(file_path):
            print(f"  Skipping {file_path}: Already has copyright notice")
            skipped += 1
            continue
        
        print(f"  Adding copyright to {file_path}")
        if add_copyright_to_file(file_path, developer_name):
            processed += 1
        else:
            errors += 1
    
    print(f"\nCopyright insertion complete:")
    print(f"  Processed: {processed} files")
    print(f"  Skipped (already had copyright): {skipped} files")
    print(f"  Errors: {errors} files")

def get_github_token():
    """Get GitHub token from environment variables."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise ValueError("GITHUB_TOKEN not found in environment variables. Please set it in your .env file.")
    return token

def fetch_github_repositories():
    """Fetch all repositories for the authenticated user including organization repositories."""
    token = get_github_token()
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    repositories = []
    
    # Get user repositories
    print("Fetching user repositories...")
    page = 1
    while True:
        url = f"https://api.github.com/user/repos?type=all&sort=updated&per_page=100&page={page}"
        response = make_request_with_retry(url, headers=headers)
        if not response or response.status_code != 200:
            break
        
        repos = response.json()
        if not repos:
            break
        
        repositories.extend(repos)
        print(f"  Found {len(repos)} repositories on page {page}")
        page += 1
    
    # Get organization repositories
    print("Fetching organization memberships...")
    orgs_response = make_request_with_retry("https://api.github.com/user/orgs", headers=headers)
    if orgs_response and orgs_response.status_code == 200:
        orgs = orgs_response.json()
        print(f"  Found {len(orgs)} organizations")
        
        for org in orgs:
            org_name = org['login']
            print(f"  Fetching repositories for organization: {org_name}")
            
            page = 1
            while True:
                url = f"https://api.github.com/orgs/{org_name}/repos?type=all&sort=updated&per_page=100&page={page}"
                response = make_request_with_retry(url, headers=headers)
                if not response or response.status_code != 200:
                    break
                
                org_repos = response.json()
                if not org_repos:
                    break
                
                repositories.extend(org_repos)
                print(f"    Found {len(org_repos)} repositories on page {page}")
                page += 1
    
    # Filter out forks and archived repositories (optional)
    active_repos = [repo for repo in repositories if not repo.get('fork', True) and not repo.get('archived', False)]
    
    print(f"\nTotal repositories found: {len(repositories)}")
    print(f"Active (non-fork, non-archived) repositories: {len(active_repos)}")
    
    return active_repos

def git_operations(repo_url, repo_name, work_dir):
    """Perform git operations: clone, process, commit, and push."""
    token = get_github_token()
    
    # Clone with token authentication
    auth_url = repo_url.replace('https://github.com/', f'https://{token}@github.com/')
    clone_dir = work_dir / repo_name
    
    try:
        print(f"  Cloning {repo_name}...")
        result = subprocess.run(
            ['git', 'clone', auth_url, str(clone_dir)],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            print(f"    Failed to clone: {result.stderr}")
            return False
        
        # Change to repository directory
        original_dir = os.getcwd()
        os.chdir(clone_dir)
        
        try:
            # Check if there are any changes needed
            source_files = get_source_files('.')
            if not source_files:
                print(f"    No source files found in {repo_name}")
                return True
            
            # Process repository (generate EULA and add copyright headers)
            print(f"  Processing {repo_name}...")
            process_repository_batch(repo_name)
            
            # Check for changes
            result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
            if not result.stdout.strip():
                print(f"    No changes to commit in {repo_name}")
                return True
            
            # Add all changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Commit changes
            commit_message = f"Add EULA and copyright headers\n\n- Generated comprehensive EULA\n- Added copyright headers to all source files\n- Automated by mdgen.py"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # Push changes
            print(f"  Pushing changes to {repo_name}...")
            result = subprocess.run(['git', 'push'], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"    Failed to push: {result.stderr}")
                return False
            
            print(f"  ✓ Successfully processed and pushed {repo_name}")
            return True
            
        finally:
            os.chdir(original_dir)
    
    except subprocess.TimeoutExpired:
        print(f"    Timeout while cloning {repo_name}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"    Git operation failed for {repo_name}: {e}")
        return False
    except Exception as e:
        print(f"    Error processing {repo_name}: {e}")
        return False

def update_readme_badge():
    """Update README file with EULA badge."""
    readme_files = []
    
    # Look for common README file names
    for readme_name in ['README.md', 'README.rst', 'README.txt', 'README', 'readme.md', 'readme.rst', 'readme.txt', 'readme']:
        if Path(readme_name).exists():
            readme_files.append(Path(readme_name))
    
    if not readme_files:
        print("    No README file found to update")
        return
    
    # Use the first README file found (usually README.md)
    readme_path = readme_files[0]
    
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # New EULA badge
        new_badge = "[![EULA](https://img.shields.io/badge/EULA-PI%20%26%20Other%20Tales%2C%20Inc.-purple)](https://othertales.co/eula)"
        
        lines = content.split('\n')
        updated = False
        title_found = False
        
        for i, line in enumerate(lines):
            # Track when we find the title
            if line.startswith('#') and not title_found:
                title_found = True
                continue
            
            # If we've found the title, look for existing badges
            if title_found and not updated:
                # Check if current line contains badges (shields.io, img.shields.io patterns)
                if ('![' in line and 'img.shields.io' in line) or ('[![' in line and 'img.shields.io' in line):
                    # Check if it's an existing EULA/License badge
                    if ('EULA' in line or 'License' in line or 'license' in line):
                        # Replace existing EULA/License badge
                        lines[i] = new_badge
                        updated = True
                        print(f"    Updated existing EULA/License badge in {readme_path}")
                        break
                    else:
                        # Add EULA badge to the same line (inline with other badges)
                        lines[i] = f"{new_badge}\n{line}"
                        updated = True
                        print(f"    Added EULA badge inline with existing badges in {readme_path}")
                        break
                
                # If we find an empty line after the title and there were no badges yet, insert here
                elif line.strip() == '' and i > 0:
                    lines.insert(i, new_badge)
                    updated = True
                    print(f"    Added EULA badge after title in {readme_path}")
                    break
                
                # If we find content that's not a badge and not empty, insert badge before it
                elif line.strip() and not line.startswith('#') and not ('![' in line or '[![' in line):
                    lines.insert(i, new_badge)
                    lines.insert(i + 1, '')  # Add empty line after badge
                    updated = True
                    print(f"    Added EULA badge before content in {readme_path}")
                    break
        
        # If no good insertion point was found, add after the first heading
        if not updated and title_found:
            for i, line in enumerate(lines):
                if line.startswith('#'):
                    lines.insert(i + 1, '')
                    lines.insert(i + 2, new_badge)
                    lines.insert(i + 3, '')
                    updated = True
                    print(f"    Added EULA badge after title in {readme_path}")
                    break
        
        # If no heading found, insert at the very beginning
        if not updated:
            lines.insert(0, new_badge)
            lines.insert(1, '')
            print(f"    Added EULA badge at top of {readme_path}")
        
        # Write the updated content back
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            
    except Exception as e:
        print(f"    Error updating README badge: {e}")

def process_repository_batch(repo_name):
    """Process a single repository in batch mode (no prompts)."""
    global license_cache
    
    # Use repository name as software name
    software_name = repo_name
    software_version = "1.0.0"  # Default version
    dev_name = "PI & Other Tales Inc."
    dev_address = "8 The Green, Dover, Delaware 19901 United States"
    dev_email = "hello@othertales.co"
    
    print(f"    Scanning for third-party modules...")
    third_party_modules = extract_imports_from_code(".")
    
    modules_info = {}
    if third_party_modules:
        print(f"    Processing {len(third_party_modules)} third-party modules...")
        for module in third_party_modules:
            # Check cache first
            if module in license_cache:
                # Convert legacy cache format to enhanced format if needed
                cached_data = license_cache[module]
                if isinstance(cached_data, tuple) and len(cached_data) >= 3:
                    license_name, license_text, source_desc = cached_data
                    package_info = get_enhanced_package_info(module)
                    package_info.update({
                        'license_name': license_name,
                        'license_text': license_text,
                        'copyright_notices': extract_copyright_info(license_text) if license_text else []
                    })
                    modules_info[module] = package_info
                else:
                    modules_info[module] = cached_data
                continue
            
            # Get comprehensive package information (simplified for batch processing)
            package_info = get_enhanced_package_info(module)
            
            # If local package info is insufficient, try external sources
            if not package_info.get('license_name') or not package_info.get('license_text'):
                # Try PyPI as fallback
                pypi_license_name, pypi_license_text = fetch_pypi_license(module)
                if pypi_license_name and pypi_license_text:
                    package_info['license_name'] = pypi_license_name
                    package_info['license_text'] = pypi_license_text
                    package_info['copyright_notices'].extend(extract_copyright_info(pypi_license_text))
            
            # Validate compliance
            if package_info.get('license_name') and package_info.get('license_text'):
                is_compliant, issues = validate_license_compliance(
                    package_info['license_name'], 
                    package_info['license_text'], 
                    package_info['copyright_notices']
                )
                package_info['compliance_status'] = 'compliant' if is_compliant else 'issues'
                package_info['compliance_issues'] = issues
                
                # Remove duplicates from copyright notices
                package_info['copyright_notices'] = list(set(package_info['copyright_notices']))
                
                modules_info[module] = package_info
                
                # Cache the enhanced package info (convert to legacy format for cache compatibility)
                license_cache[module] = (
                    package_info['license_name'], 
                    package_info['license_text'], 
                    f"enhanced package info (compliance: {package_info['compliance_status']})"
                )
    
    # Generate EULA
    eula_text = build_eula(software_name, software_version, dev_name, dev_address, dev_email, modules_info)
    
    with open("LICENSE", "w", encoding="utf-8") as f:
        f.write(eula_text)
    
    # Add copyright headers
    add_copyright_headers(dev_name)
    
    # Update README with EULA badge
    update_readme_badge()
    
    # Generate license compliance report
    if modules_info:
        print("    Generating license compliance report...")
        generate_license_compliance_report(modules_info)
    
    # Generate build metadata if applicable
    try:
        generate_build_metadata()
    except Exception:
        pass  # Skip if no build targets found

def batch_process_repositories():
    """Process all GitHub repositories in batch mode."""
    print("Starting batch repository processing...")
    
    try:
        repositories = fetch_github_repositories()
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    if not repositories:
        print("No repositories found to process.")
        return
    
    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir)
        print(f"Working directory: {work_dir}")
        
        successful = 0
        failed = 0
        
        for i, repo in enumerate(repositories, 1):
            repo_name = repo['name']
            repo_url = repo['clone_url']
            
            print(f"\n[{i}/{len(repositories)}] Processing repository: {repo_name}")
            print(f"  URL: {repo_url}")
            
            try:
                if git_operations(repo_url, repo_name, work_dir):
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  Error processing {repo_name}: {e}")
                failed += 1
        
        print(f"\n" + "="*50)
        print(f"Batch processing complete!")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total: {len(repositories)}")

def generate_license_compliance_report(modules_info, output_file="LICENSE_COMPLIANCE_REPORT.md"):
    """Generate a comprehensive license compliance report."""
    current_date = datetime.now().strftime("%B %d, %Y")
    
    report = f"""# License Compliance Report

Generated: {current_date}

This report provides a comprehensive analysis of all open source components used in this software and their license compliance status.

## Summary

"""
    
    total_components = len(modules_info)
    compliant_components = sum(1 for info in modules_info.values() 
                              if isinstance(info, dict) and info.get('compliance_status') == 'compliant')
    issues_components = sum(1 for info in modules_info.values() 
                           if isinstance(info, dict) and info.get('compliance_status') == 'issues')
    
    report += f"- **Total Components**: {total_components}\n"
    report += f"- **Compliant Components**: {compliant_components}\n"
    report += f"- **Components with Issues**: {issues_components}\n"
    report += f"- **Compliance Rate**: {(compliant_components/total_components*100):.1f}%\n\n"
    
    # License distribution
    license_counts = {}
    copyleft_licenses = []
    permissive_licenses = []
    
    for module, info in modules_info.items():
        if isinstance(info, dict):
            license_name = info.get('license_name', 'Unknown')
        else:
            license_name = info[0] if isinstance(info, tuple) and len(info) > 0 else 'Unknown'
        
        license_counts[license_name] = license_counts.get(license_name, 0) + 1
        
        requirements = LICENSE_REQUIREMENTS.get(license_name, {})
        if requirements.get('copyleft'):
            copyleft_licenses.append(f"{module} ({license_name})")
        elif license_name in LICENSE_REQUIREMENTS:
            permissive_licenses.append(f"{module} ({license_name})")
    
    report += f"## License Distribution\n\n"
    for license_name, count in sorted(license_counts.items(), key=lambda x: x[1], reverse=True):
        report += f"- **{license_name}**: {count} components\n"
    
    # Compliance issues
    if issues_components > 0:
        report += f"\n## ⚠️ Compliance Issues\n\n"
        for module, info in modules_info.items():
            if isinstance(info, dict) and info.get('compliance_status') == 'issues':
                report += f"### {module}\n\n"
                for issue in info.get('compliance_issues', []):
                    report += f"- {issue}\n"
                report += "\n"
    
    # Copyleft notice
    if copyleft_licenses:
        report += f"\n## 🔄 Copyleft Licenses\n\n"
        report += "The following components use copyleft licenses that may require source code disclosure:\n\n"
        for component in copyleft_licenses:
            report += f"- {component}\n"
        report += "\n**Action Required**: Ensure compliance with copyleft requirements when distributing this software.\n\n"
    
    # Detailed component information
    report += f"\n## Detailed Component Information\n\n"
    
    for module in sorted(modules_info.keys()):
        info = modules_info[module]
        
        if isinstance(info, dict):
            license_name = info.get('license_name', 'Unknown')
            license_text = info.get('license_text', '')
            copyright_notices = info.get('copyright_notices', [])
            version = info.get('version', 'Unknown')
            authors = info.get('authors', [])
            homepage = info.get('homepage')
            source_url = info.get('source_url')
            compliance_status = info.get('compliance_status', 'unknown')
        else:
            # Legacy format
            license_name, license_text, source_desc = info if isinstance(info, tuple) else ('Unknown', '', 'Unknown')
            copyright_notices = extract_copyright_info(license_text) if license_text else []
            version = 'Unknown'
            authors = []
            homepage = None
            source_url = None
            compliance_status = 'unknown'
        
        report += f"### {module}\n\n"
        report += f"- **Version**: {version}\n"
        report += f"- **License**: {license_name}\n"
        report += f"- **Compliance Status**: {'✅ Compliant' if compliance_status == 'compliant' else '⚠️ Issues' if compliance_status == 'issues' else '❓ Unknown'}\n"
        
        if authors:
            report += f"- **Authors**: {', '.join(authors)}\n"
        
        if homepage:
            report += f"- **Homepage**: {homepage}\n"
        
        if source_url:
            report += f"- **Source**: {source_url}\n"
        
        if copyright_notices:
            report += f"- **Copyright Notices**:\n"
            for notice in copyright_notices:
                report += f"  - {notice}\n"
        
        # License requirements
        requirements = LICENSE_REQUIREMENTS.get(license_name, {})
        if requirements:
            report += f"- **License Requirements**:\n"
            if requirements.get('requires_attribution'):
                report += f"  - ✅ Attribution required\n"
            if requirements.get('requires_source_disclosure'):
                report += f"  - ⚠️ Source disclosure required\n"
            if requirements.get('patent_grant'):
                report += f"  - 🛡️ Patent grant included\n"
            if requirements.get('copyleft'):
                report += f"  - 🔄 Copyleft license\n"
        
        report += "\n"
    
    # GitHub supported licenses
    report += f"\n## GitHub Supported Licenses\n\n"
    report += "This software validates compliance with the following GitHub-approved open source licenses:\n\n"
    
    for license_id in sorted(GITHUB_SUPPORTED_LICENSES):
        used_count = license_counts.get(license_id, 0)
        if used_count > 0:
            report += f"- ✅ **{license_id}** ({used_count} components)\n"
        else:
            report += f"- {license_id}\n"
    
    report += f"\nFor more information about these licenses, visit: https://choosealicense.com/\n"
    
    # Footer
    report += f"\n---\n\n"
    report += f"*This compliance report was automatically generated by mdgen.py to ensure adherence to all open source license requirements.*\n"
    
    # Write report to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"License compliance report saved to {output_file}")
    except Exception as e:
        print(f"Error saving compliance report: {e}")
    
    return report

def main():
    """Main function that supports both interactive and batch modes."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate EULA and add copyright headers')
    parser.add_argument('--batch', action='store_true', 
                       help='Process all GitHub repositories in batch mode')
    parser.add_argument('--batch-repos', nargs='+', 
                       help='Process specific repositories in batch mode')
    
    args = parser.parse_args()
    
    # Load cache if available
    global license_cache
    cache_file = Path('.mdgen_cache.json')
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                license_cache = {k: (v['name'], v['text'], v['source']) for k, v in cache_data.items()}
                print(f"Loaded license cache with {len(license_cache)} entries")
        except Exception as e:
            print(f"Warning: Could not load cache: {e}")
            license_cache = {}
    
    # Check if batch mode is requested
    if args.batch:
        batch_process_repositories()
        return
    elif args.batch_repos:
        batch_process_specific_repositories(args.batch_repos)
        return
    
    # Interactive mode (original functionality)
    software_name, software_version, dev_name, dev_address, dev_email = prompt_user()
    print("\nScanning source files and extracting imports...")
    third_party_modules = extract_imports_from_code(".")
    
    if not third_party_modules:
        print("\nNo third-party modules found. Only local modules detected.")
        modules_info = {}
        verification_warnings = []
    else:
        print(f"\nThird-party modules to check: {', '.join(third_party_modules)}")
        modules_info = {}
        verification_warnings = []
        print(f"\nFetching license information for {len(third_party_modules)} modules...")
        
        for i, module in enumerate(third_party_modules, 1):
            print(f"  [{i}/{len(third_party_modules)}] Checking {module}...")
            
            # Check cache first
            if module in license_cache:
                print(f"    Using cached license information")
                # Convert legacy cache format to enhanced format if needed
                cached_data = license_cache[module]
                if isinstance(cached_data, tuple) and len(cached_data) >= 3:
                    license_name, license_text, source_desc = cached_data
                    package_info = get_enhanced_package_info(module)
                    package_info.update({
                        'license_name': license_name,
                        'license_text': license_text,
                        'copyright_notices': extract_copyright_info(license_text) if license_text else []
                    })
                    modules_info[module] = package_info
                else:
                    modules_info[module] = cached_data
                continue
            
            # Get comprehensive package information
            print(f"    Gathering comprehensive package information...")
            package_info = get_enhanced_package_info(module)
            
            # If local package info is insufficient, try external sources
            if not package_info.get('license_name') or not package_info.get('license_text'):
                print(f"    Local package info incomplete, checking external sources...")
                
                # Try PyPI API
                pypi_license_name, pypi_license_text = fetch_pypi_license(module)
                if pypi_license_name and pypi_license_text and not package_info.get('license_text'):
                    package_info['license_name'] = pypi_license_name
                    package_info['license_text'] = pypi_license_text
                    package_info['copyright_notices'].extend(extract_copyright_info(pypi_license_text))
                    print(f"    Found PyPI license: {pypi_license_name}")
                
                # Try GitHub if available
                repo = fetch_github_repo(module)
                if repo and (not package_info.get('license_name') or not package_info.get('license_text')):
                    print(f"    Found GitHub repo: {repo}")
                    package_info['source_url'] = f"https://github.com/{repo}"
                    
                    # Try GitHub API first
                    github_license_name, github_license_text = fetch_github_license(repo)
                    if github_license_name and github_license_text:
                        if not package_info.get('license_text'):
                            package_info['license_name'] = github_license_name
                            package_info['license_text'] = github_license_text
                            package_info['copyright_notices'].extend(extract_copyright_info(github_license_text))
                        print(f"    Found GitHub API license: {github_license_name}")
                    
                    # Try raw GitHub content as fallback
                    elif not package_info.get('license_text'):
                        raw_license_name, raw_license_text = fetch_github_raw_license(repo)
                        if raw_license_name and raw_license_text:
                            package_info['license_name'] = raw_license_name
                            package_info['license_text'] = raw_license_text
                            package_info['copyright_notices'].extend(extract_copyright_info(raw_license_text))
                            print(f"    Found GitHub raw license: {raw_license_name}")
            
            # Validate compliance
            if package_info.get('license_name') and package_info.get('license_text'):
                is_compliant, issues = validate_license_compliance(
                    package_info['license_name'], 
                    package_info['license_text'], 
                    package_info['copyright_notices']
                )
                package_info['compliance_status'] = 'compliant' if is_compliant else 'issues'
                package_info['compliance_issues'] = issues
                
                if not is_compliant:
                    verification_warnings.extend([f"{module}: {issue}" for issue in issues])
                    print(f"    ⚠️ Compliance issues found: {len(issues)} issues")
                else:
                    print(f"    ✓ License compliance validated")
                
                # Remove duplicates from copyright notices
                package_info['copyright_notices'] = list(set(package_info['copyright_notices']))
                
                modules_info[module] = package_info
                
                # Cache the enhanced package info (convert to legacy format for cache compatibility)
                license_cache[module] = (
                    package_info['license_name'], 
                    package_info['license_text'], 
                    f"enhanced package info (compliance: {package_info['compliance_status']})"
                )
                
                print(f"    ✓ Complete package information gathered for {module}")
            else:
                print(f"    ❌ No license information available for {module}")
                verification_warnings.append(f"{module}: No license information available from any source")
    
    # Report verification warnings
    if verification_warnings:
        print(f"\n⚠ License verification warnings:")
        for warning in verification_warnings:
            print(f"  - {warning}")
    
    print(f"\n{len(modules_info)} third-party components found with known licenses.")
    
    # Save cache for future runs
    cache_file = Path('.mdgen_cache.json')
    try:
        with open(cache_file, 'w') as f:
            # Convert cache to JSON-serializable format
            cache_data = {k: {'name': v[0], 'text': v[1], 'source': v[2]} for k, v in license_cache.items()}
            json.dump(cache_data, f, indent=2)
        print(f"License cache saved to {cache_file}")
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")
    
    eula_text = build_eula(software_name, software_version, dev_name, dev_address, dev_email, modules_info)

    with open("LICENSE", "w", encoding="utf-8") as f:
        f.write(eula_text)
    print("\nLicense information generated and saved as LICENSE")

    build_info = generate_build_metadata()
    print(f"Rich UI build number updated to {build_info.get('build_number')}")
    
    # Add copyright headers to all source files
    add_copyright_headers(dev_name)
    
    # Update README with EULA badge
    update_readme_badge()
    
    # Generate comprehensive license compliance report
    if modules_info:
        print("\nGenerating license compliance report...")
        generate_license_compliance_report(modules_info)
        print("License compliance report generated successfully.")

def batch_process_specific_repositories(repo_names):
    """Process specific repositories by name."""
    print(f"Processing specific repositories: {', '.join(repo_names)}")
    
    try:
        all_repositories = fetch_github_repositories()
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Filter to only the requested repositories
    repositories = [repo for repo in all_repositories if repo['name'] in repo_names]
    
    not_found = set(repo_names) - {repo['name'] for repo in repositories}
    if not_found:
        print(f"Warning: Repositories not found: {', '.join(not_found)}")
    
    if not repositories:
        print("No matching repositories found to process.")
        return
    
    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir)
        print(f"Working directory: {work_dir}")
        
        successful = 0
        failed = 0
        
        for i, repo in enumerate(repositories, 1):
            repo_name = repo['name']
            repo_url = repo['clone_url']
            
            print(f"\n[{i}/{len(repositories)}] Processing repository: {repo_name}")
            print(f"  URL: {repo_url}")
            
            try:
                if git_operations(repo_url, repo_name, work_dir):
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  Error processing {repo_name}: {e}")
                failed += 1
        
        print(f"\n" + "="*50)
        print(f"Batch processing complete!")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total: {len(repositories)}")

if __name__ == "__main__":
    main()
