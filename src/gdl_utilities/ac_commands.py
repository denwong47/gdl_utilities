import shell


class ACStartShellError(RuntimeError):
    def __bool__(self):
        return False
    __nonzero__ = __bool__

class ACStartSuccess():
    def __bool__(self):
        return True
    __nonzero__ = __bool__

    def __init__(self, version:int, file_name:str):
        self.version = version
        self.file_name = file_name

_app_name_new = "ARCHICAD {version:d}"
_app_name_old = "ArchiCAD {version:d}"

def render_command(
    version:int=25,
    file_name:str=None,
    new_window:bool=True,
):
    _command_base = ["open", ]

    if (new_window):
        _command_base.append("-n")
    
    _command_base.append("-a")
    
    _app_name = _app_name_new if (version >=22) else _app_name_old
    _app_name = _app_name.format(
        version=version
    )

    _command_base.append(_app_name)

    if (isinstance(file_name, str)):
        _command_base.append(file_name)

    return _command_base

def start_archicad(
    version:int=25,
    file_name:str=None,
):
    _command = render_command(
        version=version,
        file_name=file_name,
    )

    _result = shell.run(_command, safe_mode=False) # The command path contains spaces - we can't just split it

    if (isinstance(_result, Exception)):
        _stderr = _result.stderr
        return ACStartShellError("Shell command returned Code {:d}: {:s}".format(
            _result.exit_code,
            _stderr.strip()
        ))
    else:
        return ACStartSuccess(version=version, file_name=file_name)