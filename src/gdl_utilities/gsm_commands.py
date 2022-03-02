import enum
import itertools
import re
import warnings


import shlex

from file_io import file
import gdl_utilities.xml
import shell



class GSMConvertShellError(RuntimeError):
    def __bool__(self):
        return False
    __nonzero__ = __bool__

class GSMOperationNotSupported(RuntimeError):
    def __bool__(self):
        return False
    __nonzero__ = __bool__

class GSMNoArchiCADInstalled(RuntimeWarning):
    def __bool__(self):
        return False
    __nonzero__ = __bool__

class GSMConvertSuccess():
    def __bool__(self):
        return file(self.dest_path).exists()
    __nonzero__ = __bool__

    def __init__(self, version:int, dest_path:str):
        self.version = version
        self.dest_path = dest_path

version_map = {
    19:31,
    20:33,
    21:35,
    22:37,
    23:39,
    24:41,
    25:43,
}

_app_path_new = "/Applications/GRAPHISOFT/ARCHICAD\ {version:d}/ARCHICAD\ {version:d}.app"
_app_path_old = "/Applications/GRAPHISOFT/ArchiCAD\ {version:d}/ArchiCAD\ {version:d}.app"

_command_base_new = _app_path_new+"/Contents/MacOS/LP_XMLConverter.app/Contents/MacOS/LP_XMLConverter {command:s}{password:s} {source_path:s} {dest_path:s}"
_command_base_old = _app_path_old+"/Contents/MacOS/LP_XMLConverter.app/Contents/MacOS/LP_XMLConverter {command:s}{password:s} {source_path:s} {dest_path:s}"

def get_versions_available():
    _versions_iter = range(1,99)
    _results = map(check_version_available, _versions_iter)

    return tuple(itertools.compress(_versions_iter, _results))
        
def check_version_available(version:int)->bool:
    _app_path = _app_path_new if version>=22 else _app_path_old
    _app_path = _app_path.replace("\ ", " ")
    return file(_app_path.format(version=version), is_dir=True).exists()

# =================================

versions_available = get_versions_available()

if (not versions_available):
    warnings.warn("No ArchiCAD installation found.", GSMNoArchiCADInstalled)

# =================================

class convert_operation(enum.Enum):
    GSM_TO_XML = "Convert GSMs to XMLs"
    XML_TO_GSM = "Convert XMLs to GSMs"
    VERSION_CONVERT = "Convert GSM version in place"

def render_command(
    source_path:str,
    version:int=25,
    command:str="l2x",
    password:str=None,
    dest_path:str=None,
):
    if (command in ("l2x", "x2l") and dest_path is None):
        dest_path = source_path
    elif (command in ("libpart2xml") and dest_path is None):
        dest_path = source_path.replace(".gsm", ".xml")
    elif (command in ("xml2libpart") and dest_path is None):
        dest_path = source_path.replace(".xml", ".gsm")

    if (not version in versions_available):
        version = 25

    if (password is not None):
        password = f" -password {shlex.quote(password):s}"
    else:
        password = ""

    if (version >= 22):
        _command_base = _command_base_new
    else:
        _command_base = _command_base_old

    return _command_base.format(
        version=version,
        command=command,
        password=password,
        source_path=shlex.quote(source_path),
        dest_path=shlex.quote(dest_path),
    )


def execute_command(
    source_path:str,
    version:int=25,
    command:str="l2x",
    password:str="",
    dest_path:str=None,
    show_progress=False,
):
    _command = render_command(
        version=version,
        command=command,
        password=password,
        source_path=source_path,
        dest_path=dest_path,
    )
    if (show_progress): print (f"Command to be run: {_command:s}")
    _result = shell.run(_command, safe_mode=False) # The command path contains spaces - we can't just split it

    if (isinstance(_result, Exception)):
        _stderr = _result.stderr
        return GSMConvertShellError("Shell command returned Code {:d}: {:s}".format(
            _result.exit_code,
            _stderr.strip()
        ))
    else:
        return GSMConvertSuccess(version=version, dest_path=dest_path)

def change_gsm_versions(path:str, dest_version:int=23):
    _xmlfile = file(path, is_dir=False)
    _contents = _xmlfile.read(output=str)

    _gsm_version = version_map[dest_version]

    _re_statement = re.compile(
        r'<Symbol (?P<attributes>[^>]+)Version="(?P<version>\d{2})">'
    )

    for _group in _re_statement.finditer(_contents):
        _contents = _contents[:_group.span()[0]] + \
                    "<Symbol {:s}Version=\"{:d}\">".format(_group.group("attributes"), _gsm_version) + \
                    _contents[_group.span()[1]:]
        break # There is only one anyway

    return _xmlfile.write(
        gdl_utilities.xml.strip_invalid_characters(_contents),
    )


def convert_gsm_archicad_versions(
    path:str,
    source_version:int=25,
    dest_version:int=23,
    password:str=None,
    show_progress=False,
):
    _temp = file.temp(prefix="gsm_convert_")

    _result = execute_command(
        source_path=path,
        version=source_version,
        command="libpart2xml",
        password=password,
        dest_path=_temp.abspath(),
        show_progress=show_progress,
    )

    if (not isinstance(_result, Exception)):
        if (show_progress): print ("File converted to XML.")
        _result = change_gsm_versions(
            path=_temp.abspath(),
            dest_version=dest_version,
        )
        if (_result):
            if (show_progress): print ("GSM Version changed.")
            _result = execute_command(
                            source_path=_temp.abspath(),
                            version=dest_version,
                            command="xml2libpart",
                            password=password,
                            dest_path=path,
                            show_progress=show_progress,
                        )
            
            if (not isinstance(_result, Exception)):
                _return = GSMConvertSuccess(version=dest_version, dest_path=path)
            else:
                _return = _result
        else:
            if (show_progress): print ("GSM Version change failed.")
            _return = _result
    else:
        if (show_progress): print ("File failed to convert to XML.")
        _return = _result


    if (_temp.isreadable()):
        _temp.delete()

    print (_return)
    return _return


def convert_library_parts(
    source_path:str,
    version:int,
    operation:convert_operation,
    password:str=None,
    dest_path:str=None,
    show_progress:bool=False,
):
    _source_file = file(source_path, is_dir=None)
    _isfile = _source_file.isFile
    
    if (operation is convert_operation.GSM_TO_XML):
        _command = "libpart2xml" if _isfile else "l2x"
    elif (operation is convert_operation.XML_TO_GSM):
        _command = "xml2libpart" if _isfile else "x2l"
    else:
        return GSMOperationNotSupported(f"{operation} is not a valid operation for convert_library_parts")

    _result = execute_command(
        source_path=source_path,
        version=version,
        command=_command,
        password=password,
        dest_path=dest_path,
        show_progress=show_progress,
    )

    return _result

if (__name__ == "__main__"):
    pass
