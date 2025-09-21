"""Zombie (dead code) detection commands for Savior CLI."""

import click
import json
from pathlib import Path
from colorama import Fore, Style

from ..zombie import ZombieScanner, QuarantineManager, RuntimeTracer
from ..cli_utils import (
    print_success,
    print_error,
    print_warning,
    print_info,
    print_header,
    confirm_action
)


@click.group()
def zombie():
    """🧟 Dead code detection and removal."""
    pass


@zombie.command('scan')
@click.option('--verbose', is_flag=True, help='Show detailed analysis')
@click.option('--json', 'json_output', help='Export results to JSON file')
def zombie_scan(verbose, json_output):
    """Find unused functions and classes in your code."""
    project_dir = Path.cwd()
    scanner = ZombieScanner(project_dir)

    click.echo(f"{Fore.MAGENTA}🧟 Starting ZOMBIE scan...")
    click.echo(f"   Analyzing your codebase for dead code...\n")

    results = scanner.scan()

    # Calculate stats
    total_dead_lines = sum(result['lines'] for result in results['dead_functions'])
    total_dead_lines += sum(result['lines'] for result in results['dead_classes'])
    files_affected = len(set(r['file'] for r in results['dead_functions'] + results['dead_classes']))

    # Display header
    click.echo(f"{Fore.MAGENTA}{'='*60}")
    click.echo(f"{Fore.MAGENTA}🧟 ZOMBIE CODE SCAN REPORT")
    click.echo(f"{Fore.MAGENTA}{'='*60}")
    click.echo(f"Total dead code: {Fore.RED}{total_dead_lines} lines")
    click.echo(f"Files affected: {Fore.YELLOW}{files_affected}")
    click.echo()

    # Display dead functions
    if results['dead_functions']:
        click.echo(f"{Fore.YELLOW}📦 Dead Functions ({len(results['dead_functions'])})")
        click.echo(f"{Fore.YELLOW}{'-'*40}")
        for func in results['dead_functions'][:10 if not verbose else None]:
            click.echo(f"  • {Fore.RED}{func['name']} {Fore.WHITE}({func['lines']} lines)")
            click.echo(f"    {func['file']}:{func['line']}")
        if len(results['dead_functions']) > 10 and not verbose:
            click.echo(f"  ... and {len(results['dead_functions']) - 10} more")
        click.echo()

    # Display dead classes
    if results['dead_classes']:
        click.echo(f"{Fore.YELLOW}🏗️ Dead Classes ({len(results['dead_classes'])})")
        click.echo(f"{Fore.YELLOW}{'-'*40}")
        for cls in results['dead_classes'][:10 if not verbose else None]:
            click.echo(f"  • {Fore.RED}{cls['name']} {Fore.WHITE}({cls['lines']} lines)")
            click.echo(f"    {cls['file']}:{cls['line']}")
        if len(results['dead_classes']) > 10 and not verbose:
            click.echo(f"  ... and {len(results['dead_classes']) - 10} more")
        click.echo()

    # Summary
    total_dead = len(results['dead_functions']) + len(results['dead_classes'])
    click.echo(f"{Fore.YELLOW}⚠️  Found {total_dead} potential zombie definitions")
    click.echo(f"   {total_dead_lines} lines of potentially dead code")

    # Export to JSON if requested
    if json_output:
        output_path = Path(json_output)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print_success(f"Results exported to {output_path}")


@zombie.command('check')
@click.argument('name')
def zombie_check(name):
    """Check if specific function or class is dead."""
    project_dir = Path.cwd()
    scanner = ZombieScanner(project_dir)

    click.echo(f"Checking '{name}'...\n")

    # Find definitions
    definitions = scanner._find_definitions()
    found = None
    for def_info in definitions:
        if def_info['name'] == name:
            found = def_info
            break

    if not found:
        print_warning(f"'{name}' not found in codebase")
        return

    # Check if it's referenced
    is_referenced = scanner._is_referenced(name, found['file'])

    print_success(f"'{name}' is defined in:")
    click.echo(f"  • {found['file']}:{found['line']}")
    click.echo()

    if is_referenced:
        print_success(f"'{name}' is referenced in the codebase - NOT dead code")
    else:
        print_warning(f"'{name}' is never referenced - might be dead code!")


@zombie.command('stats')
def zombie_stats():
    """Show dead code statistics for the project."""
    project_dir = Path.cwd()
    scanner = ZombieScanner(project_dir)

    click.echo(f"{Fore.CYAN}Analyzing code statistics...\n")

    # Count total lines of code
    total_lines = 0
    py_files = list(project_dir.glob('**/*.py'))
    for file in py_files:
        if '.savior' not in str(file) and '__pycache__' not in str(file):
            try:
                total_lines += len(file.read_text().splitlines())
            except:
                pass

    # Run scan
    results = scanner.scan()

    # Calculate dead lines
    dead_lines = sum(r['lines'] for r in results['dead_functions'])
    dead_lines += sum(r['lines'] for r in results['dead_classes'])

    # Calculate percentage
    dead_percentage = (dead_lines / total_lines * 100) if total_lines > 0 else 0

    # Display stats
    print_header("Code Statistics")
    click.echo(f"Total Python files: {len(py_files)}")
    click.echo(f"Total lines of code: {total_lines:,}")
    click.echo(f"Dead functions: {len(results['dead_functions'])}")
    click.echo(f"Dead classes: {len(results['dead_classes'])}")
    click.echo(f"Dead lines: {dead_lines:,}")
    click.echo(f"\n{Fore.YELLOW}Dead code percentage: {dead_percentage:.1f}%")

    # Health assessment
    if dead_percentage < 5:
        print_success("✨ Excellent! Your codebase is very clean")
    elif dead_percentage < 10:
        print_info("👍 Good! Minor cleanup could help")
    elif dead_percentage < 20:
        print_warning("⚠️ Consider removing dead code")
    else:
        print_error("🧟 High amount of dead code detected!")


@zombie.command('quarantine')
@click.option('--restore', is_flag=True, help='Restore from quarantine')
def zombie_quarantine(restore):
    """Move dead code to quarantine or restore it."""
    project_dir = Path.cwd()
    manager = QuarantineManager(project_dir)

    if restore:
        # Restore from quarantine
        quarantined = manager.list_quarantined()
        if not quarantined:
            print_warning("No quarantined code found")
            return

        click.echo(f"{Fore.CYAN}Quarantined items:")
        for i, item in enumerate(quarantined, 1):
            click.echo(f"  {i}. {item['name']} ({item['type']})")
            click.echo(f"     From: {item['original_file']}")
            click.echo(f"     Date: {item['quarantined_date']}")

        choice = click.prompt('Which item to restore? (0 to cancel)', type=int)
        if choice > 0 and choice <= len(quarantined):
            item = quarantined[choice - 1]
            if manager.restore_from_quarantine(item['id']):
                print_success(f"Restored {item['name']} to {item['original_file']}")
            else:
                print_error("Failed to restore item")
    else:
        # Move to quarantine
        scanner = ZombieScanner(project_dir)
        results = scanner.scan()

        total_dead = len(results['dead_functions']) + len(results['dead_classes'])
        if total_dead == 0:
            print_info("No dead code found to quarantine")
            return

        click.echo(f"{Fore.YELLOW}Found {total_dead} dead code items")

        if confirm_action("Move all dead code to quarantine?"):
            quarantined = 0

            for func in results['dead_functions']:
                if manager.quarantine_code(func):
                    quarantined += 1
                    click.echo(f"  Quarantined: {func['name']}")

            for cls in results['dead_classes']:
                if manager.quarantine_code(cls):
                    quarantined += 1
                    click.echo(f"  Quarantined: {cls['name']}")

            print_success(f"Moved {quarantined} items to quarantine")
            click.echo(f"  Quarantine location: {manager.quarantine_dir}")


@zombie.command('trace')
@click.option('--duration', default=60, help='Tracing duration in seconds')
def zombie_trace(duration):
    """Trace runtime execution to find truly dead code."""
    project_dir = Path.cwd()
    tracer = RuntimeTracer(project_dir)

    click.echo(f"{Fore.CYAN}Starting runtime tracing...")
    click.echo(f"Duration: {duration} seconds")
    click.echo(f"\n{Fore.YELLOW}Run your application now to trace execution...")

    tracer.start_tracing()

    # Wait for specified duration
    import time
    for i in range(duration):
        remaining = duration - i
        click.echo(f"\r{Fore.CYAN}Tracing... {remaining} seconds remaining", nl=False)
        time.sleep(1)

    click.echo()  # New line

    coverage = tracer.stop_tracing()

    # Display results
    print_header("Runtime Trace Results")

    executed = coverage['executed_functions']
    not_executed = coverage['not_executed']

    click.echo(f"Functions executed: {len(executed)}")
    click.echo(f"Functions NOT executed: {len(not_executed)}")

    if not_executed:
        click.echo(f"\n{Fore.YELLOW}Potentially dead functions (not executed):")
        for func in not_executed[:20]:
            click.echo(f"  • {func}")
        if len(not_executed) > 20:
            click.echo(f"  ... and {len(not_executed) - 20} more")

    # Save trace report
    report_file = project_dir / '.savior' / 'trace_report.json'
    report_file.parent.mkdir(exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(coverage, f, indent=2, default=str)

    print_info(f"Full trace report saved to {report_file}")