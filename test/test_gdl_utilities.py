import os, sys

import unittest

from datetime import datetime
import random
import secrets
import time as timer
import warnings

import numpy as np
import pandas as pd

from file_io import file

import gdl_utilities
from gdl_utilities.gsm_commands import convert_operation, convert_library_parts, GSMConvertSuccess, convert_gsm_archicad_versions
from gdl_utilities.ac_commands import start_archicad, kill_archicad
from gdl_utilities import ac_connector
from gdl_utilities.ac_connection import GROUP_PROPERTY_SEPARATOR

TEST_PLN_FILE = "./sandbox/TEST-GDU-ZZ-ZZ-M3-A-0001_UnitTest.pln"
TEST_PLN_LOCK = TEST_PLN_FILE + ".lck"

SHOW_PROGRESS = False

_ac_handler = None

class TestGDLUtilities(unittest.TestCase):

    @classmethod
    def get_testcase_pickle_name(cls, function_name, testcase_id=1):
        return f"testcase_test_{function_name:s}_{testcase_id:02d}"

    @classmethod
    def setUpClass(cls) -> None:
        global _ac_handler
        
        super().setUpClass()

        os.chdir(os.path.dirname(sys.argv[0]))

        if (not ac_connector.alive):
            if (os.path.exists(TEST_PLN_LOCK)):
                os.remove(TEST_PLN_LOCK)

            if (os.path.exists(TEST_PLN_FILE)):
                _ac_handler = start_archicad(
                    25,
                    "./sandbox/TEST-GDU-ZZ-ZZ-M3-A-0001_UnitTest.pln"
                )
            else:
                print(f"Test PLN file [{TEST_PLN_FILE}] not found. Check working directory.")

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()

        _result = kill_archicad(_ac_handler)

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
                    "show_progress":SHOW_PROGRESS,
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

    def test_ac_connector(self) -> None:
        
        if (ac_connector.wait_till_alive(
            timeout=180
        )):
            # ArchiCAD report itself as live.
            # Normally it will still be loading stuff for a while; so lets wait around for a bit more.
            timer.sleep(16)

            """
            Fetch Uniclass Classification
            And check type
            """

            _uniclass2015 = ac_connector.find_classification_system("Uniclass 2015")
            self.assertIsInstance(_uniclass2015, ac_connector.types.ClassificationSystem)


            """
            Fetch Uniclass Classification Items
            And check type
            """

            _chair_class = ac_connector.find_classification(_uniclass2015, "Pr_40_50_12_71")
            _piano_class = ac_connector.find_classification(_uniclass2015, "Pr_40_30_55")
            _fridge_class = ac_connector.find_classification(_uniclass2015, "Ss_40_15_25")
            _wall_class = ac_connector.find_classification(_uniclass2015, "EF_25_10")
            self.assertIsInstance(_chair_class, ac_connector.types.ClassificationItemId)
            self.assertIsInstance(_piano_class, ac_connector.types.ClassificationItemId)
            self.assertIsInstance(_fridge_class, ac_connector.types.ClassificationItemId)
            self.assertIsInstance(_wall_class, ac_connector.types.ClassificationItemId)

            

            """
            Fetch Elements using Classification Items and Object Types

            Then check against anticipated count
            """

            _chair_count = 162
            _piano_count = 32
            _fridge_count = 144
            _wall_count = 4

            _chair_elements = list(ac_connector.iter_elements(
                classification=_chair_class,
                element_type="Object",
            ))
            self.assertEqual(len(_chair_elements), _chair_count)

            _piano_elements = list(ac_connector.iter_elements(
                classification=_piano_class,
                element_type="Object",
            ))
            self.assertEqual(len(_piano_elements), _piano_count)

            _fridge_elements = list(ac_connector.iter_elements(
                classification=_fridge_class,
                element_type="Object",
            ))
            self.assertEqual(len(_fridge_elements), _fridge_count)

            _wall_elements = list(ac_connector.iter_elements(
                classification=_wall_class,
                element_type="Wall", # These are walls!
            ))
            self.assertEqual(len(_wall_elements), _wall_count)
            

            
            """
            Generate Property User Ids
            And check counts
            """
            _count_prop_identity_userid = 15
            _count_prop_testgroup_userid = 6

            _prop_identity_userid = list(
                ac_connector.find_properties_userid_by_group((None, "IdAndCategories"), True)
            )
            _prop_testgroup_userid = list(
                ac_connector.find_properties_userid_by_group("Test Group", False)
            )

            self.assertEqual(len(_prop_identity_userid), _count_prop_identity_userid)
            self.assertEqual(len(_prop_testgroup_userid), _count_prop_testgroup_userid)

            _all_props = _prop_identity_userid + _prop_testgroup_userid

            """
            Element Properties
            Check Shape
            """
            get_chair_props = lambda : ac_connector.get_element_property_dataframe(
                _chair_elements,
                _all_props,
            )

            _chair_df_ac = get_chair_props()

            self.assertEqual(
                _chair_df_ac.shape,
                (
                    _chair_count,
                    _count_prop_identity_userid+_count_prop_testgroup_userid,
                )
            )



            """
            Randomise Values
            """

            _enum_options = [
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4",
                "Option 5",
            ]
        
            def _randomise(row):
                row[f"TEST GROUP{GROUP_PROPERTY_SEPARATOR}Last Populated"]          =   datetime.utcnow().isoformat()
                row[f"TEST GROUP{GROUP_PROPERTY_SEPARATOR}String Property"]         =   secrets.token_urlsafe(200)
                row[f"TEST GROUP{GROUP_PROPERTY_SEPARATOR}Integer Property"]        =   secrets.randbelow(65535)
                row[f"TEST GROUP{GROUP_PROPERTY_SEPARATOR}Float Property"]          =   secrets.randbelow(65535) / (1+secrets.randbelow(255))
                row[f"TEST GROUP{GROUP_PROPERTY_SEPARATOR}Single Enum Property"]    =   secrets.choice(_enum_options)
                row[f"TEST GROUP{GROUP_PROPERTY_SEPARATOR}Multiple Enum Property"]  =   random.sample(
                    population = _enum_options,
                    k = secrets.randbelow(len(_enum_options)),
                )
                return row

            _chair_df_new = _chair_df_ac.apply(
                _randomise,
                axis=1
            )
            # _chair_df_new.property_structure = _chair_df.property_structure
            

            # print(_chair_df_new.iloc[0, :])
            """
            Push to ArchiCAD
            """
            _return = _chair_df_new.export.to_archicad()

            _result = ac_connector.summarise_transaction_results(
                _return
            )
            
            self.assertTrue(
                (0, "Success") in _result.keys()
            )

            """
            Load DataFrame back from ArchiCAD
            and assert equal to what we injected
            """
            _chair_df_ac = get_chair_props()

            pd.testing.assert_frame_equal(
                _chair_df_ac,
                _chair_df_new
            )

        else:
            # ArchiCAD is still not live after 3 minutes
            warnings.warn(
                RuntimeWarning(
                    "ArchiCAD did not come alive in time for unittest to run; skipping test."
                )
            )

if __name__ == "__main__":
    unittest.main()