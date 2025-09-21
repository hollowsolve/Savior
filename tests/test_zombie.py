import pytest
import tempfile
from pathlib import Path

from savior.zombie import ZombieScanner, CodeAnalyzer, DynamicUsageDetector


class TestZombieScanner:
    @pytest.fixture
    def test_project(self):
        """Create a test project with dead code"""
        temp_dir = Path(tempfile.mkdtemp(prefix='zombie_test_'))

        # Create Python file with dead code
        python_code = '''
def used_function():
    return "I'm used!"

def dead_function():
    return "I'm never called"

class UsedClass:
    def method(self):
        pass

class DeadClass:
    def __init__(self):
        self.value = 42

# Use some functions
result = used_function()
obj = UsedClass()
'''
        (temp_dir / 'main.py').write_text(python_code)

        # Create JavaScript file with dead code
        js_code = '''
function usedFunction() {
    return "I'm used!";
}

function deadFunction() {
    return "I'm never called";
}

const arrowFunc = () => console.log("Arrow");
const deadArrow = () => console.log("Dead arrow");

// Use some functions
usedFunction();
arrowFunc();
'''
        (temp_dir / 'app.js').write_text(js_code)

        yield temp_dir

        import shutil
        shutil.rmtree(temp_dir)

    def test_scan_project(self, test_project):
        """Test scanning for dead code"""
        scanner = ZombieScanner(test_project)
        zombies = scanner.scan_project()

        assert 'functions' in zombies
        assert 'classes' in zombies
        assert 'total_lines' in zombies

        # Check that dead functions are found
        dead_func_names = [z['name'] for z in zombies['functions']]
        assert 'dead_function' in dead_func_names or 'deadFunction' in dead_func_names

        # Check that dead classes are found
        dead_class_names = [z['name'] for z in zombies['classes']]
        assert 'DeadClass' in dead_class_names

    def test_confidence_scoring(self, test_project):
        """Test confidence-based scanning"""
        scanner = ZombieScanner(test_project)
        zombies = scanner.scan_with_confidence()

        assert 'definite' in zombies
        assert 'probable' in zombies
        assert 'possible' in zombies

        # Dead functions should have high confidence
        for item in zombies['definite']:
            assert item['confidence'] >= 0.8

    def test_dynamic_usage_detection(self):
        """Test detection of dynamic usage"""
        detector = DynamicUsageDetector()

        code = '''
getattr(obj, 'dynamic_method')()
eval('another_function()')
api_endpoint = "/api/process_data"
'''

        definitions = {'dynamic_method', 'another_function', 'process_data'}
        dynamic_refs = detector.scan_for_dynamic_usage(code, definitions)

        assert 'dynamic_method' in dynamic_refs['definite']
        assert 'another_function' in dynamic_refs['definite']
        assert 'process_data' in dynamic_refs['probable'] or 'process_data' in dynamic_refs['possible']

    def test_api_endpoint_detection(self, test_project):
        """Test API endpoint detection"""
        flask_code = '''
from flask import Flask
app = Flask(__name__)

@app.route('/api/users')
def get_users():
    return {"users": []}

@app.post('/api/data')
def process_data():
    return {"status": "ok"}

def not_an_endpoint():
    return "regular function"
'''
        (test_project / 'api.py').write_text(flask_code)

        scanner = ZombieScanner(test_project)
        scanner.analyzer.analyze_python_file(test_project / 'api.py')

        # API endpoints should be detected
        assert 'get_users' in scanner.analyzer.api_endpoints
        assert 'process_data' in scanner.analyzer.api_endpoints
        assert 'not_an_endpoint' not in scanner.analyzer.api_endpoints

    def test_generate_report(self, test_project):
        """Test report generation"""
        scanner = ZombieScanner(test_project)
        zombies = scanner.scan_project()
        report = scanner.generate_report(zombies)

        assert '🧟 ZOMBIE CODE SCAN REPORT' in report
        assert 'Total dead code:' in report
        assert 'Files affected:' in report


class TestCodeAnalyzer:
    def test_python_analysis(self):
        """Test Python code analysis"""
        temp_dir = Path(tempfile.mkdtemp())
        test_file = temp_dir / 'test.py'
        test_file.write_text('''
def my_function():
    pass

class MyClass:
    def method(self):
        pass

my_function()
obj = MyClass()
''')

        analyzer = CodeAnalyzer(temp_dir)
        result = analyzer.analyze_python_file(test_file)

        assert 'my_function' in result['definitions']
        assert 'MyClass' in result['definitions']
        assert 'my_function' in analyzer.references
        assert 'MyClass' in analyzer.references

        import shutil
        shutil.rmtree(temp_dir)

    def test_javascript_analysis(self):
        """Test JavaScript code analysis"""
        temp_dir = Path(tempfile.mkdtemp())
        test_file = temp_dir / 'test.js'
        test_file.write_text('''
function myFunction() {
    return true;
}

const myArrow = () => false;

class MyClass {
    constructor() {}
}

myFunction();
new MyClass();
''')

        analyzer = CodeAnalyzer(temp_dir)
        result = analyzer.analyze_javascript_file(test_file)

        assert 'myFunction' in result['definitions']
        assert 'myArrow' in result['definitions']
        assert 'MyClass' in result['definitions']

        import shutil
        shutil.rmtree(temp_dir)