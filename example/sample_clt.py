import json
import logging


import gdl_utilities

logging.basicConfig(level=logging.INFO)

_conn = gdl_utilities.ac_connector
logging.debug(f"AC Connector is a [{type(_conn).__name__}] object.")

if (_conn.alive):
    _uniclass2015 = _conn.find_classification_system("Uniclass 2015")
    _clt_class = _conn.find_classification(_uniclass2015, "Pr_20_65_60_17")

    _clt_class_desc = _conn.commands.GetDetailsOfClassificationItems([_clt_class,])[0].classificationItem
    logging.info(f"Found Classification Branch [{_clt_class_desc.id} {_clt_class_desc.name}] under [{_uniclass2015.name}, {_uniclass2015.version}].") 

    _clt_elements = list(_conn.iter_elements(
        classification=_clt_class,
        element_type="Object",
    ))
    logging.info(f"Found [{len(_clt_elements):6,}] Object elements fitting the criteria.") 

    # 4 types of properties
    if (True):
        _clt_element_userid = list(_conn.find_properties_userid_by_group((None, "IdAndCategories"), False))
        _clt_reno_userid = list(_conn.find_properties_userid_by_group((None, "Category"), False))
        _clt_props_userid = list(_conn.find_properties_userid_by_group("CLT Fabrication", False))
        _clt_ratings_userid = list(_conn.find_properties_userid_by_group("General Ratings", False))
        _clt_workflow_userid = list(_conn.find_properties_userid_by_group("WORKFLOW", False))

    _clt_props_userid = _clt_element_userid + _clt_reno_userid + _clt_props_userid + _clt_ratings_userid + _clt_workflow_userid

    logging.info(f"Assembled [{len(_clt_props_userid):6,}] property ids to request from ArchiCAD.") 

    _df = _conn.get_element_property_dataframe(
        _clt_elements,
        _clt_props_userid,
    )

    logging.info(f"Retrieved DataFrame of shape [{_df.shape}], type [{type(_df).__name__}], containing columns:") 
    for _col in _df.columns:
        logging.info(f"    - {_col}")

    
    _type_map = _df.property_structure

    logging.debug(f"Type Mapping generated:\n{json.dumps(_type_map, indent=4, default=str)}")

    # _df['CLT FABRICATION>>>Notes for element'] = ""
    _df['WORKFLOW>>>Status'] = "Proposed, ordered pending delivery"
    _df['WORKFLOW>>>Projected Leadtime (days)'] = _df.apply(lambda _row: 18+_row['CLT FABRICATION>>>LOR-No.']*2, axis=1)
    _df['CLT FABRICATION>>>Notes for element'] = _df.apply(lambda _row: f"{_row['CLT FABRICATION>>>Label']} approved for Manufacture 2022-03-01, DW. To be delivered on 2022-03-{19+_row['CLT FABRICATION>>>LOR-No.']*2}.", axis=1)

    logging.info("Pushing data to ArchiCAD...")
    _summary = _conn.summarise_transaction_results(
        _df.export.to_archicad()
    )

    logging.info("Results:")
    for _key, _value in zip(_summary, _summary.values()):
        logging.info (f"    [{_key[0]:4}] {_key[1]:120s} {_value:6,}")
    
else:
    raise (_conn)