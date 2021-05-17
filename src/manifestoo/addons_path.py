import ast
import os
import subprocess
import tempfile
from configparser import ConfigParser
from pathlib import Path
from typing import List, Optional

from .utils import comma_split


class AddonsPath(List[Path]):
    def __str__(self) -> str:
        return ", ".join(str(item) for item in self)

    @classmethod
    def from_addons_path(cls, addons_path: str) -> "AddonsPath":
        return AddonsPath(Path(item) for item in comma_split(addons_path))

    @classmethod
    def from_odoo_cfg(cls, odoo_cfg_path: Path) -> "AddonsPath":
        config = ConfigParser()
        config.read(odoo_cfg_path)
        addons_path = config.get("options", "addons_path", fallback=None)
        if not addons_path:
            return AddonsPath()
        return cls.from_addons_path(addons_path)

    ADDONS_PATH_SCRIPT = b"""\
    import sys
    try:
        import openerp as odoo
    except ImportError:
        import odoo

    with open(sys.argv[1], "wb") as f:
        f.write(repr(odoo.addons.__path__).encode("utf-8"))
    """

    @classmethod
    def from_import_odoo(cls, python: str) -> "AddonsPath":
        script = tempfile.NamedTemporaryFile(delete=False)
        try:
            script.write(cls.ADDONS_PATH_SCRIPT)
            script.close()
            output = tempfile.NamedTemporaryFile(delete=False)
            try:
                output.close()
                r = subprocess.call(
                    [python, script.name, output.name],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    env=os.environ,
                )
                if r != 0:
                    return AddonsPath()
                addons_paths = ast.literal_eval(Path(output.name).read_text())
                return AddonsPath(Path(item) for item in addons_paths)
            finally:
                os.unlink(output.name)
        finally:
            os.unlink(script.name)

    @classmethod
    def from_cli_options(
        cls,
        addons_path: Optional[str],
        addons_path_from_import_odoo: bool,
        addons_path_python: str,
        addons_path_from_odoo_cfg: Optional[Path],
    ) -> "AddonsPath":
        res = AddonsPath()
        if addons_path:
            res.extend(cls.from_addons_path(addons_path))
        if addons_path_from_import_odoo:
            res.extend(cls.from_import_odoo(addons_path_python))
        if addons_path_from_odoo_cfg:
            res.extend(cls.from_odoo_cfg(addons_path_from_odoo_cfg))
        return res
