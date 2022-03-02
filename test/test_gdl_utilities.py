import os
import unittest

import pickle

import inspect
import numpy as np

import gdl_utilities
from gdl_utilities.gsm_commands import convert_operation, convert_library_parts, GSMConvertSuccess, convert_gsm_archicad_versions

from file_io import file

from execute_timer import execute_timer

class TestGDLUtilities(unittest.TestCase):

    @classmethod
    def get_testcase_pickle_name(cls, function_name, testcase_id=1):
        return f"testcase_test_{function_name:s}_{testcase_id:02d}"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def conduct_tests(
        self,
        func,
        tests:dict,
        ):

        for _test in tests:
            if (issubclass(_test["answer"], Exception) if (isinstance(_test["answer"], type)) else False):
                with self.assertRaises(Exception) as context:
                    func(
                        **_test["args"]
                    )

                self.assertTrue(isinstance(context.exception, _test["answer"]))
            elif (isinstance(_test["answer"], type)):
                self.assertTrue(isinstance(func(**_test["args"]), _test["answer"]))
            elif (isinstance(_test["answer"], np.ndarray)):
                if (_test["answer"].dtype in (
                    np.float_,
                    np.float16,
                    np.float32,
                    np.float64,
                    np.float128,
                    np.longfloat,
                    np.half,
                    np.single,
                    np.double,
                    np.longdouble,
                )):
                    _assertion = np.testing.assert_allclose
                else:
                    _assertion = np.testing.assert_array_equal

                _assertion(
                    func(
                        **_test["args"]
                    ),
                    _test["answer"],
                )
            else:
                self.assertEqual(
                    func(
                        **_test["args"]
                    ),
                    _test["answer"],
                )
    
    def test_convert_library_parts(self) -> None:

        _tests = [
            {
                # Standard Logic test
                "args":{
                    "source_path":file("sandbox/gs_general_door_macro.gsm", is_dir=False, script_dir=True).abspath(),
                    "version":23,
                    "operation":convert_operation.GSM_TO_XML,
                    "password":"graphisoft",
                    "dest_path":None,
                },
                "answer":GSMConvertSuccess,
            },
            {
                # Standard Logic test
                "args":{
                    "source_path":file("sandbox/gs_general_door_macro.xml", is_dir=False, script_dir=True).abspath(),
                    "version":23,
                    "operation":convert_operation.XML_TO_GSM,
                    "password":"graphisoft",
                    "dest_path":None,
                },
                "answer":GSMConvertSuccess,
            },
            {
                # Standard Logic test
                "args":{
                    "source_path":file("sandbox/test_obj_Test123.gsm", is_dir=False, script_dir=True).abspath(),
                    "version":19,
                    "operation":convert_operation.GSM_TO_XML,
                    "password":"Test123",
                    "dest_path":None,
                    "show_progress":True,
                },
                "answer":GSMConvertSuccess,
            },
        ]

        self.conduct_tests(
            gdl_utilities.gsm_commands.convert_library_parts,
            _tests,
        )

    def test_convert_gsm_archicad_versions(self) -> None:
        _tests = [

        ]

        self.conduct_tests(
            gdl_utilities.gsm_commands.convert_gsm_archicad_versions,
            _tests,
        )

if __name__ == "__main__":
    unittest.main()