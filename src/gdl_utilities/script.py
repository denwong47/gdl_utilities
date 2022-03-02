from typing import Any, Dict, List, Iterable, Union
import numpy as np
import pandas as pd

def generate_conditional_parameters(row:pd.Series, conditional_column = None):
    _skip = (conditional_column,)
    _header = f'''IF {conditional_column}=\'{row[conditional_column]}\' THEN\n'''
    _set_parameter = '\t{parameter}\t=\t{value}\n'
    _footer = 'ENDIF\n\n'
    _return = ''
    _return += _header
    for _index, _item in row.iteritems():
        if (not _index in _skip):
            # TODO expand repr() into something more bespoke, in case a Python object pops up
            _return += _set_parameter.format(
                parameter=_index,
                value=repr(_item),
            )
    _return += _footer
    return _return


def reverse_vertices_direction(lines = None, status_column = None):
    '''
    Reverse a Polyline direction in GDL etc.
    '''
    pass

