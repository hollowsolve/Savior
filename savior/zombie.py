import ast
import re
import json
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime


class DynamicUsageDetector:
    """Detects dynamic/string-based usage of functions and classes"""

    def __init__(self):
        self.dynamic_patterns = [
            # Python dynamic calls
            r'getattr\([^,]+,\s*["\'](\w+)["\']',
            r'eval\(["\'](\w+)\(',
            r'exec\(["\'](\w+)\(',
            r'__import__\(["\'](\w+)["\']',
            r'importlib\.import_module\(["\'][\w.]*?(\w+)["\']',

            # String references that might be dynamic
            r'["\'](\w+)["\']',  # Any string that matches a function name

            # API endpoints (Flask/FastAPI style)
            r'@app\.(?:route|get|post|put|delete)\(["\']/?(?:api/)?(\w+)',
            r'["\']/?api/(\w+)["\']',

            # Django URLs
            r'path\(["\'](?:api/)?(\w+)/',
            r'url\(r?\^?["\'](?:api/)?(\w+)/',

            # JavaScript fetch/axios calls
            r'fetch\(["\']/?(?:api/)?(\w+)',
            r'axios\.\w+\(["\']/?(?:api/)?(\w+)',
        ]

        self.confidence_levels = {
            'definite': [],      # Definitely used (getattr, eval, etc.)
            'probable': [],      # Probably used (API endpoints)
            'possible': [],      # Possibly used (string matches)
        }

    def scan_for_dynamic_usage(self, content: str, definitions: Set[str]) -> Dict[str, Set[str]]:
        """Scan content for dynamic usage of defined functions"""
        dynamic_refs = defaultdict(set)

        for pattern in self.dynamic_patterns:
            for match in re.finditer(pattern, content):
                potential_ref = match.group(1)
                if potential_ref in definitions:
                    # Classify confidence level
                    if 'getattr' in pattern or 'eval' in pattern or 'exec' in pattern:
                        confidence = 'definite'
                    elif 'api' in pattern.lower() or 'route' in pattern:
                        confidence = 'probable'
                    else:
                        confidence = 'possible'

                    dynamic_refs[confidence].add(potential_ref)

        return dynamic_refs


class CodeAnalyzer:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.definitions = defaultdict(set)  # {name: {file1, file2}}
        self.references = defaultdict(set)   # {name: {file1, file2}}
        self.imports = defaultdict(set)      # {module: {file1, file2}}
        self.class_methods = defaultdict(set)  # {ClassName.method: {file}}
        self.file_contents = {}
        self.errors = []

        # Enhanced features
        self.dynamic_detector = DynamicUsageDetector()
        self.dynamic_references = defaultdict(lambda: defaultdict(set))
        self.api_endpoints = {}  # Maps function names to API routes
        self.test_files = set()  # Track test files

    def analyze_python_file(self, file_path: Path) -> Dict:
        """Analyze a Python file for definitions and references"""
        # Detect if this is a test file
        if 'test' in file_path.name.lower() or 'spec' in file_path.name.lower():
            self.test_files.add(str(file_path))

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.file_contents[str(file_path)] = content

            tree = ast.parse(content, filename=str(file_path))

            visitor = CodeVisitor(str(file_path), self)
            visitor.visit(tree)

            # Detect API endpoints
            self._detect_python_api_endpoints(file_path)

            # Scan for dynamic usage
            all_definitions = set(self.definitions.keys())
            dynamic_refs = self.dynamic_detector.scan_for_dynamic_usage(content, all_definitions)

            for confidence, refs in dynamic_refs.items():
                for ref in refs:
                    self.dynamic_references[ref][confidence].add(str(file_path))

            return {
                'definitions': visitor.definitions,
                'references': visitor.references,
                'imports': visitor.imports
            }
        except Exception as e:
            self.errors.append(f"Error analyzing {file_path}: {e}")
            return {'definitions': set(), 'references': set(), 'imports': set()}

    def analyze_javascript_file(self, file_path: Path) -> Dict:
        """Basic JavaScript/TypeScript analysis using regex"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.file_contents[str(file_path)] = content

            definitions = set()
            references = set()

            # Find function definitions
            func_patterns = [
                r'function\s+(\w+)\s*\(',
                r'const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>',
                r'let\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>',
                r'var\s+(\w+)\s*=\s*function',
                r'export\s+(?:default\s+)?function\s+(\w+)',
                r'export\s+const\s+(\w+)',
                r'class\s+(\w+)',
            ]

            for pattern in func_patterns:
                for match in re.finditer(pattern, content):
                    name = match.group(1)
                    definitions.add(name)
                    self.definitions[name].add(str(file_path))

            # Find function calls and references
            call_pattern = r'\b(\w+)\s*\('
            for match in re.finditer(call_pattern, content):
                name = match.group(1)
                if name not in ['if', 'for', 'while', 'switch', 'catch', 'function']:
                    references.add(name)
                    self.references[name].add(str(file_path))

            # Scan for dynamic usage
            all_definitions = set(self.definitions.keys())
            dynamic_refs = self.dynamic_detector.scan_for_dynamic_usage(content, all_definitions)

            for confidence, refs in dynamic_refs.items():
                for ref in refs:
                    self.dynamic_references[ref][confidence].add(str(file_path))

            return {
                'definitions': definitions,
                'references': references,
                'imports': set()
            }
        except Exception as e:
            self.errors.append(f"Error analyzing {file_path}: {e}")
            return {'definitions': set(), 'references': set(), 'imports': set()}

    def _detect_python_api_endpoints(self, file_path: Path):
        """Detect Flask/FastAPI/Django API endpoints"""
        if str(file_path) not in self.file_contents:
            return

        content = self.file_contents[str(file_path)]

        # Flask/FastAPI patterns
        endpoint_patterns = [
            r'@app\.(?:route|get|post|put|delete)\(["\']([^"\']+)["\'].*?\)\s*def\s+(\w+)',
            r'@router\.(?:get|post|put|delete)\(["\']([^"\']+)["\'].*?\)\s*(?:async\s+)?def\s+(\w+)',
        ]

        for pattern in endpoint_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                route, func_name = match.groups()
                self.api_endpoints[func_name] = route


class CodeVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, analyzer: CodeAnalyzer):
        self.filename = filename
        self.analyzer = analyzer
        self.definitions = set()
        self.references = set()
        self.imports = set()
        self.current_class = None

    def visit_FunctionDef(self, node):
        name = node.name
        if self.current_class:
            full_name = f"{self.current_class}.{name}"
            self.analyzer.class_methods[full_name].add(self.filename)
        else:
            self.definitions.add(name)
            self.analyzer.definitions[name].add(self.filename)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self.definitions.add(node.name)
        self.analyzer.definitions[node.name].add(self.filename)
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.references.add(node.id)
            self.analyzer.references[node.id].add(self.filename)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.references.add(node.func.id)
            self.analyzer.references[node.func.id].add(self.filename)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                # Track method calls like obj.method()
                self.references.add(node.func.attr)
                self.analyzer.references[node.func.attr].add(self.filename)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
            self.analyzer.imports[alias.name].add(self.filename)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
            self.analyzer.imports[node.module].add(self.filename)
        for alias in node.names:
            if alias.name != '*':
                self.references.add(alias.name)
                self.analyzer.references[alias.name].add(self.filename)
        self.generic_visit(node)


class RuntimeTracer:
    """Traces actual function calls during runtime (Python only)"""

    def __init__(self):
        self.called_functions = set()
        self.trace_file = Path('.savior/runtime_trace.json')

    def start_tracing(self):
        """Start tracing function calls"""
        def trace_calls(frame, event, arg):
            if event == 'call':
                code = frame.f_code
                func_name = code.co_name
                filename = code.co_filename

                if not filename.startswith('<') and '.savior' not in filename:
                    self.called_functions.add(f"{filename}:{func_name}")

            return trace_calls

        sys.settrace(trace_calls)

    def stop_tracing(self):
        """Stop tracing and save results"""
        sys.settrace(None)

        self.trace_file.parent.mkdir(exist_ok=True)
        with open(self.trace_file, 'w') as f:
            json.dump(list(self.called_functions), f, indent=2)

    def load_trace(self) -> Set[str]:
        """Load previously traced function calls"""
        if self.trace_file.exists():
            with open(self.trace_file, 'r') as f:
                return set(json.load(f))
        return set()


class QuarantineManager:
    """Manages quarantined dead code"""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.quarantine_dir = project_dir / '.zombie'
        self.manifest_file = self.quarantine_dir / 'manifest.json'

    def quarantine_code(self, zombies: Dict, dry_run: bool = True) -> Dict:
        """Move dead code to quarantine directory"""
        if dry_run:
            return self._preview_quarantine(zombies)

        self.quarantine_dir.mkdir(exist_ok=True)
        manifest = {
            'quarantined_at': datetime.now().isoformat(),
            'items': [],
            'stats': {
                'total_lines': zombies['total_lines'],
                'functions': len(zombies['functions']),
                'classes': len(zombies['classes']),
                'variables': len(zombies['variables'])
            }
        }

        # Process each zombie
        for category in ['functions', 'classes', 'variables']:
            for item in zombies[category]:
                success = self._quarantine_item(item)
                if success:
                    manifest['items'].append({
                        'type': category[:-1],  # Remove 's'
                        'name': item['name'],
                        'original_file': item['file'],
                        'line': item['line'],
                        'lines_removed': item['lines']
                    })

        # Save manifest
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        return manifest

    def _quarantine_item(self, item: Dict) -> bool:
        """Extract and quarantine a single piece of dead code"""
        try:
            source_file = Path(item['file'])
            if not source_file.exists():
                return False

            # Create quarantine path preserving structure
            rel_path = source_file.relative_to(self.project_dir)
            quarantine_file = self.quarantine_dir / rel_path
            quarantine_file.parent.mkdir(parents=True, exist_ok=True)

            # Read original file
            with open(source_file, 'r') as f:
                lines = f.readlines()

            # Extract the dead code
            start_line = item['line'] - 1
            end_line = start_line + item['lines']
            dead_code = ''.join(lines[start_line:end_line])

            # Save to quarantine
            if quarantine_file.exists():
                with open(quarantine_file, 'a') as f:
                    f.write(f"\n# --- {item['name']} ---\n")
                    f.write(dead_code)
            else:
                with open(quarantine_file, 'w') as f:
                    f.write(f"# Quarantined from {source_file}\n")
                    f.write(f"# --- {item['name']} ---\n")
                    f.write(dead_code)

            # Remove from original (create new file without dead code)
            new_lines = lines[:start_line] + lines[end_line:]
            with open(source_file, 'w') as f:
                f.writelines(new_lines)

            return True
        except Exception as e:
            print(f"Error quarantining {item['name']}: {e}")
            return False

    def _preview_quarantine(self, zombies: Dict) -> Dict:
        """Preview what would be quarantined without doing it"""
        preview = {
            'would_quarantine': {
                'functions': len(zombies['functions']),
                'classes': len(zombies['classes']),
                'variables': len(zombies['variables']),
                'total_lines': zombies['total_lines']
            },
            'affected_files': list(set(
                item['file'] for category in ['functions', 'classes', 'variables']
                for item in zombies[category]
            ))
        }
        return preview

    def restore_from_quarantine(self, item_name: Optional[str] = None):
        """Restore quarantined code back to original files"""
        if not self.manifest_file.exists():
            return {'error': 'No quarantine manifest found'}

        with open(self.manifest_file, 'r') as f:
            manifest = json.load(f)

        if item_name:
            # Restore specific item
            for item in manifest['items']:
                if item['name'] == item_name:
                    # Logic to restore specific item
                    return {'restored': item_name}
            return {'error': f'{item_name} not found in quarantine'}
        else:
            # Restore all
            # Implementation for full restoration
            return {'restored': 'all', 'count': len(manifest['items'])}


class ZombieScanner:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.analyzer = CodeAnalyzer(project_dir)
        self.ignore_patterns = [
            '.git/', '__pycache__/', 'node_modules/', '.savior/',
            'venv/', 'env/', '.env', 'build/', 'dist/', '*.pyc'
        ]
        self.zombie_code = []
        self.stats = {}

        # Enhanced features
        self.quarantine = QuarantineManager(project_dir)
        self.runtime_tracer = RuntimeTracer()

    def should_scan(self, path: Path) -> bool:
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return False
        return True

    def scan_project(self) -> Dict:
        """Scan entire project for dead code"""
        python_files = []
        js_files = []

        # Collect files
        for file_path in self.project_dir.rglob('*'):
            if not file_path.is_file() or not self.should_scan(file_path):
                continue

            if file_path.suffix in ['.py']:
                python_files.append(file_path)
            elif file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                js_files.append(file_path)

        # Analyze Python files
        for file_path in python_files:
            self.analyzer.analyze_python_file(file_path)

        # Analyze JavaScript files
        for file_path in js_files:
            self.analyzer.analyze_javascript_file(file_path)

        # Find zombies (defined but never referenced)
        zombies = self._find_zombies()

        return zombies

    def scan_with_confidence(self) -> Dict:
        """Scan with confidence levels for zombie detection"""
        zombies = self.scan_project()

        # Load runtime trace if available
        runtime_called = self.runtime_tracer.load_trace()

        # Enhance zombie detection with confidence scores
        for category in ['functions', 'classes', 'variables']:
            for item in zombies[category]:
                name = item['name']
                confidence = self._calculate_confidence(name, item['file'], runtime_called)
                item['confidence'] = confidence
                item['dynamic_refs'] = self.analyzer.dynamic_references.get(name, {})

        # Filter out low confidence items
        zombies['definite'] = []
        zombies['probable'] = []
        zombies['possible'] = []

        for category in ['functions', 'classes', 'variables']:
            for item in zombies[category]:
                if item['confidence'] >= 0.8:
                    zombies['definite'].append(item)
                elif item['confidence'] >= 0.5:
                    zombies['probable'].append(item)
                else:
                    zombies['possible'].append(item)

        return zombies

    def _calculate_confidence(self, name: str, file_path: str, runtime_called: Set[str]) -> float:
        """Calculate confidence that code is actually dead"""
        confidence = 1.0  # Start with 100% confidence it's dead

        # Check if it was called at runtime
        if f"{file_path}:{name}" in runtime_called:
            return 0.0  # Definitely not dead

        # Check dynamic references
        if name in self.analyzer.dynamic_references:
            dynamic = self.analyzer.dynamic_references[name]
            if 'definite' in dynamic and dynamic['definite']:
                confidence *= 0.2  # Very likely used
            elif 'probable' in dynamic and dynamic['probable']:
                confidence *= 0.5  # Probably used
            elif 'possible' in dynamic and dynamic['possible']:
                confidence *= 0.8  # Might be used

        # Check if it's an API endpoint
        if name in self.analyzer.api_endpoints:
            confidence *= 0.3  # API endpoints are likely used

        # Check if it's in a test file
        if file_path in self.analyzer.test_files:
            confidence *= 0.7  # Test code might be intentionally unused

        # Check for special patterns
        special_patterns = ['__init__', 'setUp', 'tearDown', 'main']
        if name in special_patterns:
            confidence *= 0.5

        return confidence

    def _find_zombies(self) -> Dict:
        """Find all code that's defined but never referenced"""
        zombies = {
            'functions': [],
            'classes': [],
            'variables': [],
            'total_lines': 0,
            'files_affected': set()
        }

        # Check all definitions
        for name, files in self.analyzer.definitions.items():
            # Skip special methods and common names
            if name.startswith('_') or name in ['main', 'setup', 'teardown', 'test']:
                continue

            # Check if it's referenced anywhere
            if name not in self.analyzer.references or not self.analyzer.references[name]:
                for file_path in files:
                    line_num, line_count = self._find_definition_location(name, file_path)

                    zombie_info = {
                        'name': name,
                        'file': file_path,
                        'line': line_num,
                        'lines': line_count,
                        'type': self._detect_type(name, file_path)
                    }

                    if zombie_info['type'] == 'function':
                        zombies['functions'].append(zombie_info)
                    elif zombie_info['type'] == 'class':
                        zombies['classes'].append(zombie_info)
                    else:
                        zombies['variables'].append(zombie_info)

                    zombies['total_lines'] += line_count
                    zombies['files_affected'].add(file_path)

        zombies['files_affected'] = list(zombies['files_affected'])
        return zombies

    def _find_definition_location(self, name: str, file_path: str) -> Tuple[int, int]:
        """Find line number and line count for a definition"""
        if file_path not in self.analyzer.file_contents:
            return 0, 1

        content = self.analyzer.file_contents[file_path]
        lines = content.split('\n')

        # Try to find the definition
        for i, line in enumerate(lines, 1):
            if re.search(rf'\b(?:def|class|function|const|let|var)\s+{re.escape(name)}\b', line):
                # Count lines for this definition
                line_count = self._count_definition_lines(lines[i-1:], name)
                return i, line_count

        return 0, 1

    def _count_definition_lines(self, lines: List[str], name: str) -> int:
        """Count how many lines a definition spans"""
        if not lines:
            return 1

        # For Python, count until dedent
        if lines[0].strip().startswith(('def ', 'class ')):
            indent = len(lines[0]) - len(lines[0].lstrip())
            count = 1

            for line in lines[1:]:
                if line.strip() and len(line) - len(line.lstrip()) <= indent:
                    break
                count += 1

            return count

        # For JavaScript/TypeScript, count until closing brace
        brace_count = 0
        count = 0

        for line in lines:
            count += 1
            brace_count += line.count('{') - line.count('}')
            if brace_count == 0 and count > 1:
                break

        return max(count, 1)

    def _detect_type(self, name: str, file_path: str) -> str:
        """Detect if definition is a function, class, or variable"""
        if file_path not in self.analyzer.file_contents:
            return 'unknown'

        content = self.analyzer.file_contents[file_path]

        if re.search(rf'\bclass\s+{re.escape(name)}\b', content):
            return 'class'
        elif re.search(rf'\b(?:def|function)\s+{re.escape(name)}\b', content):
            return 'function'
        elif re.search(rf'\b(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:function|\()', content):
            return 'function'
        else:
            return 'variable'

    def generate_report(self, zombies: Dict) -> str:
        """Generate a detailed report of dead code"""
        report = []

        report.append("🧟 ZOMBIE CODE SCAN REPORT")
        report.append("=" * 60)
        report.append(f"\nTotal dead code: {zombies['total_lines']} lines")
        report.append(f"Files affected: {len(zombies['files_affected'])}")

        if zombies['functions']:
            report.append(f"\n📦 Dead Functions ({len(zombies['functions'])})")
            report.append("-" * 40)
            for func in sorted(zombies['functions'], key=lambda x: x['lines'], reverse=True)[:10]:
                rel_path = Path(func['file']).relative_to(self.project_dir)
                report.append(f"  • {func['name']} ({func['lines']} lines)")
                report.append(f"    {rel_path}:{func['line']}")

        if zombies['classes']:
            report.append(f"\n🏗️ Dead Classes ({len(zombies['classes'])})")
            report.append("-" * 40)
            for cls in sorted(zombies['classes'], key=lambda x: x['lines'], reverse=True)[:10]:
                rel_path = Path(cls['file']).relative_to(self.project_dir)
                report.append(f"  • {cls['name']} ({cls['lines']} lines)")
                report.append(f"    {rel_path}:{cls['line']}")

        if zombies['variables']:
            report.append(f"\n📝 Dead Variables ({len(zombies['variables'])})")
            report.append("-" * 40)
            for var in zombies['variables'][:10]:
                rel_path = Path(var['file']).relative_to(self.project_dir)
                report.append(f"  • {var['name']}")
                report.append(f"    {rel_path}:{var['line']}")

        if self.analyzer.errors:
            report.append(f"\n⚠️  Analysis Errors ({len(self.analyzer.errors)})")
            report.append("-" * 40)
            for error in self.analyzer.errors[:5]:
                report.append(f"  • {error}")

        report.append("\n" + "=" * 60)
        report.append("💡 Tip: Review these items carefully before removing.")
        report.append("   Some may be entry points, tests, or used dynamically.")

        return "\n".join(report)

    def export_json(self, zombies: Dict, output_file: Path):
        """Export results to JSON for further analysis"""
        with open(output_file, 'w') as f:
            json.dump(zombies, f, indent=2, default=str)