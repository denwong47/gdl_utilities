from typing import Any, Dict, List, Iterable, Union
import numpy as np
import pandas as pd

def generate_conditional_parameters(row = None, conditional_column = None):
    _skip = (conditional_column,)
    _header = f'''IF {conditional_column}=\'{row[conditional_column]}\' THEN\n'''
    _set_parameter = '\t{parameter}\t=\t{value}\n'
    _footer = 'ENDIF\n\n'
    _return = ''
    _return += _header
    _return += _footer
    return _return


def reverse_vertices_direction(lines = None, status_column = None):
    '''
    Reverse a Polyline direction in GDL etc.
    '''
    pass

