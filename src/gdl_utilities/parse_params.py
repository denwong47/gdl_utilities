
import re
from enum import Enum
from typing import Any, Dict, Iterable, List, Union
from lxml import etree as ET
import pandas as pd
from tqdm import tqdm

import collections

from file_io import file

dir_path = "./XMLs"
object_type_var = "ap_objectType"

_object_type_id = f"_{object_type_var:s}_id"
_object_type_name = f"_{object_type_var:s}_name"
_object_type_img = f"_{object_type_var:s}_img"

def reset_node(node:ET.Element):
    for _subnode in node.iterchildren():
        node.remove(_subnode)

def set_child_value(
    node:ET.Element,
    key:str,
    value:Any,
    attrs:Dict[str,Any]={},
):
    _child_node = node.find(key)

    if (_child_node is None):
        if (value is None):
            return
    else:
        if (value is None):
            node.remove(_child_node)
            return

    _child_node = ET.Element(
                    key,
                    attrib=attrs,
                )
            
    _child_node.text = value

    set_child_node(
        node,
        _child_node
    )


def set_child_node(
    node:ET.Element,
    child:ET.Element,
):
    _child_node = node.find(child.tag)

    if (_child_node is None):
        node.append(child)
    else:
        node.replace(_child_node, child)

def iter_xmls(
    dir_path:str,
    sub_directories:bool=False,
):
    _dir = file(dir_path, is_dir=True)
    _dir_tree = _dir.dir_tree(sub_directories=sub_directories, flatten=sub_directories)

    for _file_path, _file in zip(_dir_tree, _dir_tree.values()):
        if (_file_path.lower().endswith(".xml")):
            yield _file

class GDLScriptType(Enum):
    SCRIPT_3D               = "Script_3D"
    SCRIPT_2D               = "Script_2D"
    SCRIPT_MASTER           = "Script_1D"
    SCRIPT_PROPERTIES       = "Script_PR"
    SCRIPT_UI               = "Script_UI"
    SCRIPT_PARAMETERS       = "Script_VL"
    SCRIPT_FORWARD_MIGRATE  = "Script_FWM"
    SCRIPT_BACKWARD_MIGRATE = "Script_BWM"


class GDLXMLFile():
    def __init__(
        self,
        name:str,
        node:ET.Element,
    ):
        self.name                   =   name
        self._node                  =   node

        self.script_3D              =   GDLScript.from_node(node.find(GDLScriptType.SCRIPT_3D.value), kind=GDLScriptType.SCRIPT_3D)
        self.script_2D              =   GDLScript.from_node(node.find(GDLScriptType.SCRIPT_2D.value), kind=GDLScriptType.SCRIPT_2D)
        self.script_master          =   GDLScript.from_node(node.find(GDLScriptType.SCRIPT_MASTER.value), kind=GDLScriptType.SCRIPT_MASTER)
        self.script_properties      =   GDLScript.from_node(node.find(GDLScriptType.SCRIPT_PROPERTIES.value), kind=GDLScriptType.SCRIPT_PROPERTIES)
        self.script_ui              =   GDLScript.from_node(node.find(GDLScriptType.SCRIPT_UI.value), kind=GDLScriptType.SCRIPT_UI)
        self.script_parameters      =   GDLScript.from_node(node.find(GDLScriptType.SCRIPT_PARAMETERS.value), kind=GDLScriptType.SCRIPT_PARAMETERS)
        self.script_forward_migrate =   GDLScript.from_node(node.find(GDLScriptType.SCRIPT_FORWARD_MIGRATE.value), kind=GDLScriptType.SCRIPT_FORWARD_MIGRATE)
        self.script_backward_migrate=   GDLScript.from_node(node.find(GDLScriptType.SCRIPT_BACKWARD_MIGRATE.value), kind=GDLScriptType.SCRIPT_BACKWARD_MIGRATE)

        _paramsection = node.find("ParamSection")
        _parameters = _paramsection.find("Parameters")

        self.parameters = GDLParameters()

        for _parameter in _parameters:
            _param_name, _param_dict = parseParameter(_parameter)
        
            if (_param_name):
                self.parameters.append(_param_dict)


    @classmethod
    def from_file(
        cls,
        xmlfile:file,
    ):
        _parser = ET.XMLParser(strip_cdata=False)

        _xml = xmlfile.read(output=str)
        
        _tree = ET.fromstring(_xml, parser=_parser)
        _object_name = xmlfile.name().replace(".xml", "")

        return cls(
            name=_object_name,
            node=_tree,
        )


    def replace_child(
        self,
        old_element:ET.Element,
        new_element:ET.Element,
    ):
        if (old_element is not None):
            self._node.replace(old_element, new_element)
        else:
            self._node.append(new_element)

    
    @property
    def node(
        self
    ):
        self.replace_child( self._node.find(GDLScriptType.SCRIPT_3D.value),                 self.script_3D.node)
        self.replace_child( self._node.find(GDLScriptType.SCRIPT_2D.value),                 self.script_2D.node)
        self.replace_child( self._node.find(GDLScriptType.SCRIPT_MASTER.value),             self.script_master.node)
        self.replace_child( self._node.find(GDLScriptType.SCRIPT_PROPERTIES.value),         self.script_properties.node)
        self.replace_child( self._node.find(GDLScriptType.SCRIPT_UI.value),                 self.script_ui.node)
        self.replace_child( self._node.find(GDLScriptType.SCRIPT_PARAMETERS.value),         self.script_parameters.node)
        self.replace_child( self._node.find(GDLScriptType.SCRIPT_FORWARD_MIGRATE.value),    self.script_forward_migrate.node)
        self.replace_child( self._node.find(GDLScriptType.SCRIPT_BACKWARD_MIGRATE.value),   self.script_backward_migrate.node)

        _paramsection = self._node.find("ParamSection")
        _parameters = _paramsection.find("Parameters")
        
        _paramsection.replace(_parameters, self.parameters.node)

        return self._node

    @property
    def node_xml(self):
        return ET.tostring(
            self.node,
            encoding="UTF-8",
            xml_declaration=False
        )

class GDLScript():
    def __init__(
        self,
        kind:GDLScriptType,
        attrs:dict,
        script:str,
        *args,
        **kwargs
    ):
        self.kind = kind
        self.attrs = attrs
        self.script = script
        super().__init__(*args, **kwargs)

    def __str__(
        self,
    ):
        return self.script

    @classmethod
    def from_node(
        cls,
        node:ET.Element,
        kind:GDLScriptType=GDLScriptType.SCRIPT_MASTER,
        *args,
        **kwargs,
    )->"GDLScript":

        if (node is not None):
            try:
                _kind = GDLScriptType(node.tag)
            except ValueError as e:
                raise ValueError(f"{node.tag} is not a valid GDL Script tag.")

            _attrs = node.attrib
            _script = node.text
        else:
            _kind = kind
            _attrs = {
                "SectVersion":"20",
                "SectionFlags":"0",
                "SubIdent":"0",
            }
            _script = ""

        return cls(
            kind = _kind,
            attrs = _attrs,
            script = _script,
            *args,
            **kwargs,
        )

    @property
    def node(
        self,
    )->ET.Element:
        _node = ET.Element(
            self.kind.value,
            attrib = self.attrs,
        )

        _node.text = ET.CDATA(str(self))
        
        return _node

    @property
    def node_xml(self):
        return ET.tostring(
            self.node,
            encoding="UTF-8",
            xml_declaration=False
        )


class GDLCopyright():
    # TODO Find out what types of licenses there are
    """
    <Copyright SectVersion="1" SectionFlags="0" SubIdent="0">
        <Author>denny.wong@denwong.com; Programmed for WORK Ltd 2022</Author>
        <License>
            <Type>CC BY</Type>
            <Version>4.0</Version>
        </License>
    </Copyright>
    """
    pass

class GDLParameter(dict):

    name = None
    
    def __init__(self, name:str, *args, **kwargs):
        self.name = name
        
        super().__init__(*args, **kwargs)

        if (not self.get("node_xml", None) and self.type and self.name):
            _node = ET.Element(
                self.type,
                attrib = {
                    "Name":self.name,
                }
            )

            if (self.description is not None):
                _subnode = ET.SubElement(_node, "Description")
                _subnode.text = ET.CDATA(f'"{self["description"]}"')

            if (self.fix):
                _subnode = ET.SubElement(_node, "Fix")

            if (self.flags):
                _subnode = ET.SubElement(_node, "Flags")
                _flagsubnodes = list(map(
                    lambda tag: ET.SubElement(_subnode, tag),
                    self.flags,
                ))
            
            if (self.value is not None):
                _subnode = ET.SubElement(_node, "Value")
                _subnode.text = ET.CDATA(f'"{self.value}"') if (self.is_string) else self.value

            
            self["node_xml"] = ET.tostring(
                _node
            )

    @property
    def is_string(self):
        return self.type.title() in (
            "Title",
            "String"
        )

    @property
    def node(self):
        _parser = ET.XMLParser(strip_cdata=False)
        _node = ET.fromstring(
            self.get("node_xml"),
            parser=_parser
        )

        _node.tag = self["type"]
        _node.set("Name", self.name)

        # <Description/>
        set_child_value(
            _node,
            "Description",
            ET.CDATA(f'"{self["description"]}"')
        )

        # <Fix/>
        _fixnode = _node.find("Fix")
        if (_fixnode is None and self.fix):
            _fixnode = ET.SubElement(
                _node, "Fix"
            )
        elif (_fixnode is not None and not self.fix):
            _node.remove(_fixnode)

        # <Flags>
        _flagsnode = _node.find("Flags")
        if (_flagsnode is None and self.flags):
            _flagsnode = ET.SubElement(
                _node, "Flags"
            )
        
        if (self.flags):
            reset_node(_flagsnode)

            _flagsubnodes = list(map(
                lambda tag: ET.SubElement(_flagsnode, tag),
                self.flags,
            ))


        # <Value>
        set_child_value(
            _node,
            "Value",
            (ET.CDATA(f'"{self["value"]}"') if (self.is_string) else self["value"]) if (self.value is not None) else None
        )


        # <ArrayValues>
        if (self.array is not None):
            set_child_node(
                _node,
                self.array,
            )
        else:
            set_child_value(
                _node,
                "ArrayValues",
                None,
            )
        
        return _node
    
    @property
    def node_xml(self):
        return ET.tostring(
            self.node,
            encoding="UTF-8",
            xml_declaration=False
        )

    def __setattr__(self, key, value):
        if (key in self.keys()):
            self[key] = value
        else:
            super().__setattr__(key, value)
    
    def __getattr__(self, key, default=None):
        return self.get(key, default)


class GDLParameters(list):
    def insert(
        self,
        i:int,
        elem:Union[
            GDLParameter,
            Iterable[GDLParameter],
        ],
    )->None:
        if (not isinstance(elem, list)):
            elem = [elem, ]

        elem.reverse()

        _elements = type(self)(elem)    # Exahust all generators etc

        for _element in _elements:
            super().insert(i, _element)

    @property
    def node(
        self,
        replace:ET.Element=None,
    )->ET.Element:
        if (replace is not None):
            reset_node(replace)
            _node = replace
        else:
            _node = ET.Element(
                "Parameters",
            )
        
        for _param in self:
            _node.append(_param.node)
        
        return _node

    @property
    def node_xml(self)->bytes:
        return ET.tostring(
            self.node,
            encoding="UTF-8",
            xml_declaration=False
        )

    def find(
        self,
        **kwargs,
    ):
        _result = type(self)()

        for _param in self:
            _found = True
            for _key, _value in zip(kwargs.keys(), kwargs.values()):
                if (getattr(_param, _key, None) != _value):
                    _found = False
                    break
        
            if (_found):
                _result.append(_param)

        return _result

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
            GDLParameter(
                name=xmlNode.attrib.get("Name", "#INVALID_NAME"),
                **{
                    "type":xmlNode.tag,
                    "description":xmlNode.find("Description").text.strip('"'),
                    "value":None if (xmlNode.find("Value") is None) else xmlNode.find("Value").text.strip('"'),
                    "array":None if (xmlNode.find("ArrayValues") is None) else xmlNode.find("ArrayValues"),
                    "fix":xmlNode.find("Fix") is not None,
                    "flags":[] if (xmlNode.find("Flags") is None) else [ _flag.tag for _flag in xmlNode.find("Flags").iterchildren() ],
                    "node_xml":_node_xml,
                }
            )
        )
    else:
        _return = (None, None)
    return _return


# TODO To be reviewed and replaced with class based implementation above
def parseParametersInFile(
    xmlfile:file,
    output:type=dict,
):
    _parser = ET.XMLParser(strip_cdata=False)

    _xml = xmlfile.read(output=str)
    
    _tree = ET.fromstring(_xml, parser=_parser)

    _object_name = xmlfile.name().replace(".xml", "")

    _return = {
        "name": _object_name,
        "file": xmlfile,
        "parameters":{} if (issubclass(output, dict)) else GDLParameters()
    }

    if (_tree is not None):
        _paramsection = _tree.find("ParamSection")
        _parameters = _paramsection.find("Parameters")

        for _parameter in _parameters:
            _param_name, _param_dict = parseParameter(_parameter)
        
            if (_param_name):
                if (issubclass(output, dict)):
                    _return["parameters"][_param_name] = _param_dict
                else:
                    _return["parameters"].append(_param_dict)

    return _return    



# TODO To be reviewed and replaced with class based implementation above
def parseParametersInDir(dir_path:str):
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
    for _file_path, _file in zip(_dir_tree, _dir_tree.values()):
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

# if (__name__ == "__main__"):
#     _dir = file(dir_path, is_dir=True)
#     _file_masterscript = _dir.child("masterscript.gdl", is_dir=False)
#     _file_paramscript = _dir.child("paramscript.gdl", is_dir=False)
#     _file_paramxml = _dir.child("paramsection.gdlxml", is_dir=False)

#     _objects, _df_params = parseParametersInDir(dir_path)

#     print (f"{len(_df_params.index)}No. parameters processed.")

#     _file_masterscript.write(paramVarDeclaration(_objects))
#     _file_paramscript.write(paramVarLocking(_objects, _df_params))
#     _file_paramxml.write(paramVarXMLDeclarations(_df_params))

#     print ("Done")