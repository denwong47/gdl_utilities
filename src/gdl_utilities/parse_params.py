import site
site.addsitedir("./paths")

# import xml.etree.ElementTree as ET
import re
from lxml import etree as ET
import pandas as pd
from tqdm import tqdm

import collections

from file_io import file
from essentials import dict_iter

dir_path = "./XMLs"
object_type_var = "ap_objectType"

_object_type_id = f"_{object_type_var:s}_id"
_object_type_name = f"_{object_type_var:s}_name"
_object_type_img = f"_{object_type_var:s}_img"

def parseParameter(xmlNode):
    # print (ET.tostring(xmlNode, encoding="UTF-8", xml_declaration=False))
    if (not xmlNode.tag is ET.Comment):
        _node_xml = ET.tostring(xmlNode, encoding="UTF-8", xml_declaration=False)

        # THIS SECTION IS FOR A WEIRD BUG IN LXML THAT CAPTURED A LOT MORE INFORMATION THAN IT SHOULD
        _full_tag_pattern = re.compile(f"\s*(<{xmlNode.tag}\s[\s\S]+?</{xmlNode.tag}>)[\s\S]+$")
        _match = _full_tag_pattern.match(_node_xml.decode("UTF-8"))
        if (_match): 
            _node_xml = _match.group(1).encode("UTF-8")
        # //WEIRD SECTION

        _return = (
            xmlNode.attrib.get("Name", "#INVALID_NAME"),
            {
                "type":xmlNode.tag,
                "description":xmlNode.find("Description").text,
                "value":xmlNode.find("value").text if xmlNode.find("value") else None,
                "node_xml":_node_xml,
            }
        )
    else:
        _return = (None, None)
    return _return

def parseParametersInDir(dir_path):
    _dir = file(dir_path, is_dir=True)
    _dir_tree = _dir.dir_tree(sub_directories=False)

    _objects = {}
    _return = {}
    _parser = ET.XMLParser(strip_cdata=False)

    # _re_strip_name = re.compile(r"(?:Beam|Column|Cold-Formed|Hot-Finished|\d{2}.xml)", flags=re.IGNORECASE)

    # _descriptor_subs = {
    #     "Z":"Z",
    #     "Universal Bearing Piles":"UBP",
    #     "Universal Beams":"UB",
    #     "Universal Columns":"UC",
    #     "Unequal Angles":"UA",
    #     "Equal Angles":"EQA",
    #     "Parallel Flange Channels":"PFC",
    # }

    _re_strip_name = re.compile(r"(?:\d{2}.xml)", flags=re.IGNORECASE)

    _descriptor_subs = {
        # "Z":"Z",
        # "Universal Bearing Piles":"UBP",
        # "Universal Beams":"UB",
        # "Universal Columns":"UC",
        # "Unequal Angles":"UA",
        # "Equal Angles":"EQA",
        # "Parallel Flange Channels":"PFC",
    }

    _pbar = tqdm(total=len(_dir_tree))
    for _file_path, _file in dict_iter(_dir_tree):
        _pbar.set_description(f"Processing {_file_path}...")
        if (_file_path.lower().endswith(".xml")):
            _xml = _file.read(output=str)
            # print (_file.name())
            _tree = ET.fromstring(_xml, parser=_parser)

            

            _object_name = _file.name().replace(".xml", "")

            _descriptor = _file.name()
            for _descriptor_sub in _descriptor_subs:
                _descriptor = _descriptor.replace(_descriptor_sub, _descriptor_subs[_descriptor_sub])

            _descriptor = _re_strip_name.sub("", _descriptor)
            _descriptor = _descriptor.strip()

            _objects[_object_name] = {
                "descriptor":_descriptor,
                "parameters":[]
            }

            if (_tree is not None):
                _paramsection = _tree.find("ParamSection")
                _parameters = _paramsection.find("Parameters")

                for _parameter in _parameters:
                    _param_name, _param_dict = parseParameter(_parameter)
                
                    if (_param_name):
                        _objects[_object_name]["parameters"].append(_param_name.lower())

                        # Do not add to list if name is duplicated
                        if (not _param_name.lower() in [ _existing_params.lower() for _existing_params in _return ]):
                            _return[_param_name] = _param_dict

        _pbar.update(1)

    _pbar.close()

    _df = pd.DataFrame.from_dict(_return, orient="index")
    _sorted_objects = collections.OrderedDict(sorted(_objects.items()))
    return _sorted_objects, _df


def paramVarDeclaration(objects):
    
    _declaration_elements = ""

    _declaration_element = """
    {_object_type_id:s}[_id]        = _id
    {_object_type_name:s}[_id]      = "{object_name:s}"
    {_object_type_img:s}[_id]        = ""
    IF {object_type_var:s}=_id THEN !{object_name:s}
        ap_profilePrefix = "{profile_prefix:s}"
        CALL "{object_name:s}" PARAMETERS ALL
    ENDIF
    _id = _id+1
    
    """

    for _object_name in objects:
        _declaration_elements += _declaration_element.format(
            profile_prefix = objects[_object_name]["descriptor"],
            object_type_var = object_type_var,
            _object_type_id = _object_type_id,
            _object_type_name = _object_type_name,
            _object_type_img = _object_type_img,
            object_name = _object_name,
        )


    _declaration_parent = f"""
    ! === Master Script ==

    DIM {_object_type_id:s}[{len(objects)}]
    DIM {_object_type_name:s}[{len(objects)}]
    DIM {_object_type_img:s}[{len(objects)}]

    _id = 1
    {_declaration_elements:s}
    """

    return _declaration_parent


def paramVarLocking(objects:dict, parameters:pd.DataFrame):

    _return = f"""
    ! === Parameter Script ==
    VALUES{{2}} "{object_type_var:s}" {_object_type_id:s}, {_object_type_name:s}
    """

    for _id, _object_name in enumerate(objects):
        _indices = pd.Series(parameters.index)
        
        _non_parameters = _indices.loc[~_indices.str.lower().isin(objects[_object_name]["parameters"])].apply(lambda name:f"\"{name:s}\"")
        if (_non_parameters.shape[0] > 0):
            _lock_parameters = "LOCK " + ",\n                 ".join(list(_non_parameters))

            _declaration_parent = """
            IF {object_type_var}={_id} THEN !{object_name}
                {_lock_parameters}
            ENDIF
            """

            _return += _declaration_parent.format(
                object_type_var=object_type_var,
                object_name=_object_name,
                _id=_id+1,
                _lock_parameters = _lock_parameters,
            )

    return _return

def paramVarXMLDeclarations(parameters:pd.DataFrame):
    _bytes = b"""		<Integer Name="ap_objectType">
			<Description><![CDATA["Profile Type"]]></Description>
			<Value>40</Value>
		</Integer>
        <Length Name="ap_elementLength">
			<Description><![CDATA["Element Length"]]></Description>
			<Flags>
				<ParFlg_Hidden/>
			</Flags>
			<Value>2</Value>
		</Length>
		<Boolean Name="ap_customiseSchedule">
			<Description><![CDATA["Customise Schedule Information"]]></Description>
			<Value>0</Value>
		</Boolean>
		<String Name="ap_profilePrefix">
			<Description><![CDATA["Profile Prefix"]]></Description>
			<Flags>
				<ParFlg_Hidden/>
			</Flags>
			<Value><![CDATA["Z"]]></Value>
		</String>
		<String Name="ap_profileName">
			<Description><![CDATA["Profile Name"]]></Description>
			<Value><![CDATA["Z 70x160, 21.6kg/m"]]></Value>
		</String>
        <String Name="ap_productCode">
			<Description><![CDATA["Product Code"]]></Description>
			<Value><![CDATA[""]]></Value>
		</String>
		<String Name="ap_productName">
			<Description><![CDATA["Product Name"]]></Description>
			<Value><![CDATA[""]]></Value>
		</String>
		<String Name="ap_productFamily">
			<Description><![CDATA["Product Family"]]></Description>
			<Value><![CDATA[""]]></Value>
		</String>
		<String Name="ap_scheduleSize">
			<Description><![CDATA["Size on Schedule"]]></Description>
			<Value><![CDATA[""]]></Value>
		</String>
		<String Name="ap_productType">
			<Description><![CDATA["Product Type"]]></Description>
			<Value><![CDATA["Structural Steel"]]></Value>
		</String>
		<String Name="ap_scheduleName">
			<Description><![CDATA["Name on Schedule"]]></Description>
			<Value><![CDATA[""]]></Value>
		</String>
		<String Name="ap_steelGrading">
			<Description><![CDATA["Steel Grading"]]></Description>
			<Value><![CDATA[""]]></Value>
		</String>
        <String Name="ap_companyName">
			<Description><![CDATA["Company Name"]]></Description>
			<Flags>
				<ParFlg_Hidden/>
			</Flags>
			<Value><![CDATA["WORK Limited"]]></Value>
		</String>
		<String Name="ap_disclaimer">
			<Description><![CDATA["Disclaimer"]]></Description>
			<Flags>
				<ParFlg_Hidden/>
			</Flags>
			<Value><![CDATA["(c) denny.wong@denwong.com, London 2021. Programmed for Work Limited."]]></Value>
		</String>"""
    for _node_xml in list(parameters["node_xml"]):
        _bytes += _node_xml

    return _bytes

if (__name__ == "__main__"):
    _dir = file(dir_path, is_dir=True)
    _file_masterscript = _dir.child("masterscript.gdl", is_dir=False)
    _file_paramscript = _dir.child("paramscript.gdl", is_dir=False)
    _file_paramxml = _dir.child("paramsection.gdlxml", is_dir=False)

    _objects, _df_params = parseParametersInDir(dir_path)

    print (f"{len(_df_params.index)}No. parameters processed.")

    _file_masterscript.write(paramVarDeclaration(_objects))
    _file_paramscript.write(paramVarLocking(_objects, _df_params))
    _file_paramxml.write(paramVarXMLDeclarations(_df_params))

    print ("Done")