import shell
from typing import Union


from gdl_utilities.ac_connection import connector as ac_connector

class ACCommandShellError(RuntimeError):
    def __bool__(self):
        return False
    __nonzero__ = __bool__

class ACNotRunning(ACCommandShellError):
    pass

class ACCommandSuccess():
    def __bool__(self):
        return True
    __nonzero__ = __bool__

    def __init__(
        self,
        pid:int,
        version:int=None,
        file_name:str=None,
    ):
        self.version = version
        self.file_name = file_name
        self.pid = pid
    
    def __repr__(
        self,
    ):
        return f"{type(self).__name__}(\n\tversion={repr(self.version)},\n\tfile_name={repr(self.file_name)},\n\tpid={repr(self.pid)}\n)"

class ACStartSuccess(ACCommandSuccess):
    pass

class ACKillSuccess(ACCommandSuccess):
    pass

_app_name_new = "ARCHICAD {version:d}"
_app_name_old = "ArchiCAD {version:d}"

def render_command(
    version:int=25,
    file_name:str=None,
    new_window:bool=True,
):
    """
    Create command list for starting ArchiCAD
    """

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
    """
    Use macOS shell command open to call ArchiCAD of the desired version.
    file_name can be passed to open local files.
    
    Return Exception instance if failed;
    Return ACStartSuccess instance if success which includes the pid as a variable.
    """

    _command_startac = render_command(
        version=version,
        file_name=file_name,
    )

    _command_pgrep = [
        "pgrep",
        "-n",
        "ARCHICAD" if version>=22 else "ArchiCAD",
    ]

    _result = shell.run(_command_startac, safe_mode=False) # The command path contains spaces - we can't just split it

    if (isinstance(_result, Exception)):
        _stderr = _result.stderr
        return ACCommandShellError("Shell command returned Code {:d}: {:s}".format(
            _result.exit_code,
            _stderr.strip()
        ))
    else:
        _result = shell.run(_command_pgrep, safe_mode=True)

        if (isinstance(_result, Exception)):
            pid = None
        else:
            pid = int(_result)

        return ACStartSuccess(
            pid=pid,
            version=version,
            file_name=file_name,
        )

def kill_archicad(
    pid: Union[
        ACStartSuccess,
        int,
    ]
):
    """
    Kill a process using either an integer pid or a ACStartSuccess object.
    """
    
    if (isinstance(pid, ACStartSuccess)):
        version = pid.version
        file_name = pid.file_name
        pid = pid.pid
    elif (isinstance(pid, ACCommandShellError)):
        return ACNotRunning(
            "Provided PID stated that the command failed to run. No ArchiCAD to kill."
        )
    else:
        version = None
        file_name = None

    _command_kill = [
        "kill",
        str(pid)
    ]

    _result = shell.run(_command_kill, safe_mode=False)

    if (isinstance(_result, Exception)):
        _stderr = _result.stderr
        return ACCommandShellError("Shell command returned Code {:d}: {:s}".format(
            _result.exit_code,
            _stderr.strip()
        ))
    else:
        return ACKillSuccess(
            pid=pid,
            version=version,
            file_name=file_name,
        )


