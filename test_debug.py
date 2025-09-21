from click.testing import CliRunner
from savior.commands.restore import list as list_backups

runner = CliRunner()
result = runner.invoke(list_backups)
print(f"Exit code: {result.exit_code}")
print(f"Output: {result.output}")
print(f"Exception: {result.exception}")
if result.exception:
    import traceback
    traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)