from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import SimpleNamespace


sys.dont_write_bytecode = True
script = Path(__file__).parents[1] / "imageroot/bin/bbs-admin-initialized"
loader = SourceFileLoader("bbs_admin_initialized", str(script))
spec = spec_from_file_location("bbs_admin_initialized", script, loader=loader)
module = module_from_spec(spec)
spec.loader.exec_module(module)


def run_with(returncode, stdout):
    return lambda *args, **kwargs: SimpleNamespace(
        returncode=returncode, stdout=stdout
    )


assert module.initialized(run_with(0, "1\n")) is True
assert module.initialized(run_with(0, "0\n")) is False
assert module.initialized(run_with(1, "")) is None
assert module.initialized(run_with(0, "unexpected")) is None
