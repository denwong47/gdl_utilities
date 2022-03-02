# Recovered
from datetime import date, datetime
from typing import Any, Dict, Generator, Iterable, List, Tuple, Union
from types import ModuleType

# try:
# from tqdm import tqdm
# except (ImportError, ModuleNotFoundError):
# tqdm = lambda x: x

import numpy as np
import pandas as pd

BUILTIN_GROUP_NAME = "Built-in Properties"
GROUP_PROPERTY_SEPARATOR = ">>>"
PROPERTY_BRANCH_DELIMITER = "::"

CLASSIFICATION_DATE_FORMAT = "%Y-%m-%d"

GUID_COLUMN_NAME = "element_guid"

try:
	import archicad
	from archicad import ACConnection
except (ImportError, ModuleNotFoundError):
	archicad = None
	ACConnection = None

class ACConnectionModuleNotFound(ModuleNotFoundError):
	def __bool__(self):
		return False
	__nonzero__ = __bool__
	
class ACConnectionFailed(RuntimeError):
	def __bool__(self):
		return False
	__nonzero__ = __bool__
	
	alive = False


class PropertyValue(dict):
	"""
	Extension of dict.
	
	Commonly has a structure of
	{
		"constructor":class,
		"value": [Scalar Value
					OR
				  In case of Enums: PropertyValue],
		"args":{
			[...kwargs to feed into constructor]
		}
	}
	
	The main point of this is for its .reconstruct() method, which allows for ElementPropertyValue to be rebuilt.
	"""
	@property
	def constructor(self):
		return self.get("constructor", None)
	
	@constructor.setter
	def constructor(self, value):
		self["constructor"] = value
	
	@property
	def value(self):
		"""
		Find the human readable value of itself.
		
		Useful when there is nested wrappers in its ["value"] key.
		"""
		
		_value = self.get("value", None)
		
		if (isinstance(_value, PropertyValue)):
			return _value.value
		else:
			return _value
		
	@value.setter
	def value(self, value):
		"""
		TODO UNTESTED
		Feed the human readable value into the right place.
		
		Useful when there is nested wrappers in its ["value"] key.
		It does not matter if value is a list - that is dealt with at reconstruction time, not now.
		"""
		
		_value = self.get("value", None)
		
		if (isinstance(_value, PropertyValue)):
			_value.value = value
		else:
			self["value"] = value
	
	def reconstruct(self, value:Any=None):
		_value_arg_mapper = {
			archicad.Types.DisplayValueEnumId: "displayValue",
			archicad.Types.EnumValueIdWrapper: "enumValueId",
			archicad.Types.NonLocalizedValueEnumId: "nonLocalizedValue",
			archicad.Types.NotAvailablePropertyValue: None,
			archicad.Types.NotEvaluatedPropertyValue: None,
			archicad.Types.UserUndefinedPropertyValue: None,
			None:"value",
		}
	
		"""
		TODO REMOVE THIS STR LITERAL WHEN DONE
		
		# Example structures:
		'Built-in Properties.Category>>>ShowOnRenovationFilter': {
			'constructor': <class 'archicad.releases.ac25.b3000types.NormalSingleEnumPropertyValue'>,
				'value': {
					'constructor': <class 'archicad.releases.ac25.b3000types.NonLocalizedValueEnumId'>,
					'value': 'AllRelevantFilters',
					'args': {
						'type': 'nonLocalizedValue'
					}
				},
			'args': {
				'type': 'singleEnum',
				'status': 'normal'
			}
		},
		
		'GENERAL RATINGS>>>Security Rating': {
			'constructor': <class 'archicad.releases.ac25.b3000types.NormalMultiEnumPropertyValue'>,
			'value': {
				'constructor': <class 'archicad.releases.ac25.b3000types.EnumValueIdWrapper'>,
				'value': {
					'constructor': <class 'archicad.releases.ac25.b3000types.DisplayValueEnumId'>,
					'value': 	[
								'PAS 24:2012',
								'Building Regulations Part Q'
								],
					'args': {
						'type': 'displayValue'
					}
				},
				'args': {
			
				}
			},
			'args': {
				'type': 'multiEnum',
				'status': 'normal'
			}
		}
		"""
		
		_value_arg = _value_arg_mapper.get(
			self.constructor,
				_value_arg_mapper.get(None, None)
			)
		
		_value = self.get("value", None) # Do not use self.value - as this will iterate through the branch!!
		
		# If this is not the end of branch, pass the value reconstruction to the branch
		
		# If this is the end of the branch, the proposed value is a list, iterated it
		if (not isinstance(_value, PropertyValue) and \
			isinstance(value, list)):
			value = [
				self.reconstruct(value=_item) for _item in value
			]
		
			# This finishes the constructor - we only need [ construct, construct, ... ] not construct( value= [ construct, construct, ... ])
			return value
		
		else:
			if (isinstance(_value, PropertyValue)):
				# Special cases where the next branch MUST be a list
				if (issubclass(_value.constructor, (
					archicad.Types.EnumValueIdWrapper,
				))):
					if (not isinstance(value, (list, tuple))):
						value = [value, ]
						
					value = [
						_value.reconstruct(value=_item) for _item in value
					]
				else:
					value = _value.reconstruct(value=value)
			
			_kwargs = self.get("args", {})
			
			if (_value_arg):
				_kwargs[_value_arg] = value
			
			# print (self.constructor, _kwargs)
			return self.constructor(
				**_kwargs
			)
		

class ElementsPropertyValues(pd.DataFrame):

	"""
	Subclass of pandas DataFrame, to allow for a list of PropertyValue to be embedded.
	This allows the DataFrame to be aware of the details on how to reconstruct the List[ElementPropertyValue].
	"""
	
	_metadata = [
		"property_structure",
	]
	
	@property
	def _constructor(self):
		return ElementsPropertyValues
	
@pd.api.extensions.register_dataframe_accessor("export")
class _PandasExt():
	"""
	export accessors
	
	Allow ElementsPropertyValues.export.element_property_values() etc.
	"""
		
	def __init__(self, df):
		if (isinstance(df, ElementsPropertyValues)):
			self._obj = df
		else:
			raise ValueError("export accessor must be used with ElementsPropertyValues class of DataFrames.")
	
	def element_ids(
		self,
	):
		"""
		Get list of ElementId from the GUIDs stored in GUID_COLUMN_NAME.
		"""
		return (
			archicad.Types.ElementId(_guid) for _guid in self._obj.index
		)
	
	def property_userids(
		self,
	):
		"""
		Get a list of PropertyUserId - these are local instances, not checked via connection.
		"""
		return (
			connector.get_property_userid_from_column_name(
				property_column_name=_col
			) for _col in self._obj.columns
		)
	
	def property_ids(
		self,
	):
		"""
		Get a list of PropertyId, ready to be used with element_property_values.
		"""
		return [
			_property_id_array_item.propertyId \
				for _property_id_array_item in \
					connector.commands.GetPropertyIds(
						list(self.property_userids())
			)
		]
	
	def element_property_values(
		self,
	):
		"""
		Get a list of ElementPropertyValue, ready to be used with SetPropertyValuesOfElements.
		"""
		_element_ids = self.element_ids()
		_property_ids = self.property_ids()
		
		_element_property_values = []
		
		for _row_id, _element_id in enumerate(_element_ids):
			for _col_id, _property_id in enumerate(_property_ids):
				_raw_value = self._obj.iat[_row_id, _col_id]
				if (isinstance(_raw_value, np.generic)):
					_raw_value = _raw_value.item()
		
				# This selects the property_structure by column name; so if the DataFrame is trimmed down it will still function.
				_property_value = self._obj.property_structure[self._obj.columns[_col_id]].reconstruct(
					_raw_value
				)
				
				if (not isinstance(_property_value, (
					connector.types.NotAvailablePropertyValue,
					connector.types.NotEvaluatedPropertyValue,
				))):
					_element_property_values.append(
						connector.types.ElementPropertyValue(
							_element_id,
							_property_id,
							_property_value
						)
					)
		
		return _element_property_values
	
	def to_archicad(
		self,
	):
		"""
		Push data to ArchiCAD.
		"""
		_element_property_values = self.element_property_values()

		
		return connector.commands.SetPropertyValuesOfElements(
			_element_property_values
		)
	

class connection():
	"""
	Singleton class that creates gdl_utilities.ac_connector.
	Automatically initialise when module loaded, but does not complain if ArchiCAD not found.
	"""

	_instance = None

	handle = None
	commands = None
	types = None
	utilities = None

	def __new__(cls, *args, **kwargs):
		if (isinstance(archicad, ModuleType)):
			if (cls._instance is None):
				if (ACConnection.connect()):
					cls._instance = super().__new__(cls, *args, **kwargs)
				else:
					return ACConnectionFailed(f"Connecion to ArchiCAD failed: is ArchiCAD open, running and idle?")

			return cls._instance
		else:
			return ACConnectionModuleNotFound("archicad Module cannot be imported - check that it is installed in the current environment through 'python3 -m pip instal archicad'.")

	def __init__(self):
		if (not self.alive):
			self.handle = ACConnection.connect()

		if (not self.handle):
			raise ACConnectionFailed(f"Connecion to ArchiCAD failed: ACConnection returned [{repr(self.handle)}].")
		else:
			self.commands = self.handle.commands
			self.types = self.handle.types
			self.utilities = self.handle.utilities

	@property
	def version(self):
		return self.commands.GetProductInfo()

	@property
	def info(self):
		_version = self.version
		return f"ARCHICAD {_version[0]} {_version[2]} Build {_version[1]}"

	@staticmethod
	def str_compare(case_sensitive:bool=True):
		if (case_sensitive):
			return lambda s1, s2: s1==s2
		else:
			return lambda s1, s2: s1.lower()==s2.lower()

	@property
	def alive(self):
		return self.commands.IsAlive() if self.commands else False

	def alive_only(func):
		def wrapper(self, *args, **kwargs):
			if (self.alive):
				return func(self, *args, **kwargs)
			else:
				return ACConnectionFailed(f"Connecion to ArchiCAD failed: ACConnection returned [{repr(self.handle)}].")

		return wrapper

	@alive_only
	def iter_properties(
		self,
	)->Generator[
		Tuple[tuple, str, archicad.Types.PropertyUserId],
		None,
		None
	]:
		"""
		Generator to iterate through all available Properties.
		Yields group_name:tuple, property_name:str, property:archicad.Types.PropertyUserId:
		"""

		for _property in self.commands.GetAllPropertyNames():
			yield (*self.property_names(_property), _property)

	def property_names(
		self,
		property:Any,
	)->Tuple[tuple, str]:
		"""
		Get Group Names and Property Name, return as Tuple.
		"""

		if (isinstance(property, self.types.UserDefinedPropertyUserId)):
			_property_id = property.localizedName
			_group_name, _property_name, = zip(_property_id)
		else:
			_property_id = property.nonLocalizedName
			_group_name = (BUILTIN_GROUP_NAME, _property_id.split("_", 1)[0])
			_property_name = (_property_id.split("_", 1)[1],)

		return _group_name, _property_name

	def property_column_name(
		self,
		property:Any,
	):
		_group_name, _property_name = self.property_names(property)

		return f"{PROPERTY_BRANCH_DELIMITER.join(_group_name)}{GROUP_PROPERTY_SEPARATOR}{PROPERTY_BRANCH_DELIMITER.join(_property_name)}"

	def get_property_userid_from_column_name(
		self,
		property_column_name:str,
	):
		_group_name, _property_name = property_column_name.split(GROUP_PROPERTY_SEPARATOR, 1)

		if (_group_name[:len(BUILTIN_GROUP_NAME)] == BUILTIN_GROUP_NAME):
			# Built-In Property
			_group_name = _group_name.split(PROPERTY_BRANCH_DELIMITER, 1)[1]

			return self.types.BuiltInPropertyUserId(
				nonLocalizedName=f"{_group_name}_{_property_name}"
			)
		else:
			# User Defined Property
			return self.types.UserDefinedPropertyUserId(
				localizedName=[
					_group_name,
					_property_name,
				]
			)

	@alive_only
	def find_properties_userid_by_group(
		self,
		group_name:Union[None, str] = None,
		case_sensitive:bool = True,
	):
		"""
		Find Properties user ID by Group Name
		Yields List[archicad.Types.PropertyUserId]

		Use find_properties_id_by_group() instead for GetPropertyValuesOfElements().
		"""
		if (isinstance(group_name, (tuple, list))):
			if (len(group_name) > 0):
				group_name = list(group_name)
				if (group_name[0]) is None:
					group_name[0] = BUILTIN_GROUP_NAME
					group_name = ".".join(group_name)
				else:
					group_name = ""

		if (group_name is None):
			group_name = BUILTIN_GROUP_NAME

		str_eq = self.str_compare(case_sensitive=case_sensitive)

		for _group_name, _property_name, _property in self.iter_properties():
			"""
			Currently this is a pretty bad matching -
			It is a simple string comparison using . as separators.
			If the requested group_name is same as _joint_group_name, it is deemed to match
			If the requested group_name is shorter than _joint_group_name, and the next character is a separator, it is deemed to match
			Otherwise its not a match.

			TODO this probably needs to be rewritten to an iterable match
			"""

			_joint_group_name = ".".join(_group_name)
			if (str_eq(_joint_group_name[:len(group_name)], group_name) or \
				group_name == ""
			):

				if (0 < len(group_name) < len(_joint_group_name)):
					if (_joint_group_name[len(group_name):len(group_name)+1] != "."):
						continue

				yield _property

	@alive_only
	def find_properties_id_by_group(
		self,
		group_name:Union[None, str] = None,
		case_sensitive:bool = True,
	):
		"""
		Find Properties ID by Group Name
		Yields List[archicad.Types.PropertyId]

		Use find_properties_id_by_group() instead for GetPropertyValuesOfElements().
		"""
		return self.get_property_id_by_property_user_id(self.find_properties_userid_by_group(group_name, case_sensitive=case_sensitive))

	def get_property_id_by_property_user_id(
		self,
		property_userid:Iterable[archicad.Types.PropertyUserId],
	):
		return self.commands.GetPropertyIds(list(property_userid))

	@alive_only
	def iter_classifications(
		self,
	)->Generator[
		archicad.Types.ClassificationId,
		None,
		None
	]:
		"""
		Generator to iterate through all Classifications.
		"""
		for _class in self.commands.GetAllClassificationSystems():
			yield _class

	@alive_only
	def find_classification_system(
		self,
		name:str,
		class_date:Union[None, str, date]=None,
		case_sensitive:bool=True,
	)->Union[
		archicad.Types.ClassificationSystemId,
		None
	]:
		"""
		Find Classification System by string;
		if class_date is not specified, defaults to the newest found.
		"""

		_return = None
		_highest_date = None

		if (isinstance(class_date, str)):
			class_date = datetime.strptime(class_date, CLASSIFICATION_DATE_FORMAT).date()


		str_eq = self.str_compare(case_sensitive=case_sensitive)

		for _class in self.iter_classifications():

			_class_name = _class.name
			_class_date = datetime.strptime(_class.date, CLASSIFICATION_DATE_FORMAT).date()

			if (str_eq(_class_name, name)):
			# Name Matched

				if (class_date):
					if (_class_date == class_date):
						return _class
				else:
					# class_date not specified, go for highest date
					if (_highest_date):
						if (_highest_date < _class_date):
							_highest_date = _class_date
							_return = _class
					else:
						_highest_date = _class_date

		return _return

	@alive_only
	def find_classification(
		self,
		system:Union[
			archicad.Types.ClassificationSystemId,
			archicad.Types.ClassificationSystem,
		],
		name:str,
	)->Union[
		archicad.Types.ClassificationId,
		None
	]:
		"""
		Find classification item in tree.
		Different from FindClassificationItemInSystem that in returns ClassificationItemId instead of ClassificationItemInTree.
		"""
		
		_return = None

		if (isinstance(system, self.types.ClassificationSystem)):
			system = system.classificationSystemId

		for _system_tree in self.commands.GetAllClassificationsInSystem(system):
			_classification_ids = self.utilities.FindInClassificationItemTree(_system_tree.classificationItem, lambda c: c.id == name)
			assert len(_classification_ids) <= 1
			if _classification_ids:
				return _classification_ids[0].classificationItemId

		return None

	def elements_join(
		self,
		join:str="intersect",
		*args:Iterable[archicad.Types.ElementIdArrayItem],
	):
		_return_elements = None
		_return_guids = None

		for _elements in args:
			if (_return_elements is None):
				_return_elements = _elements
			else:
				_guids = [
					_element.elementId.guid for _element in _elements
				]

				if (join == "intersect"):
					_new_return_elements = []
				else:
					_new_return_elements = _return_elements

				for _element, _guid in zip(_elements, _guids):
					if (
						(_guid in _return_guids and join == "intersect") or \
						(_guid not in _return_guids and join == "union")
					):
						_new_return_elements.append(_element)

				_return_elements = _new_return_elements

			# recalculate guids
			_return_guids = [
				_element.elementId.guid for _element in _return_elements
			]

		return _return_elements

	@alive_only
	def iter_elements(
		self,
		classification:archicad.Types.ClassificationId=None,
		element_type:str=None,
	):
		"""
		Iterated through elements in a single classification
		"""
		_elements = None

		if (classification):
			_elements_by_classification = self.commands.GetElementsByClassification(
				classification,
			)

			# print (f"{len(_elements_by_classification)=}")

			if (_elements is None):
				_elements = _elements_by_classification
			else:
				_elements = self.elements_join("intersect", _elements_by_classification, _elements)

		if (element_type):
			_elements_by_type = self.commands.GetElementsByType(
				element_type,
			)

			# print (f"{len(_elements_by_type)=}")
			if (_elements is None):
				_elements = _elements_by_type
			else:
				_elements = self.elements_join("intersect", _elements_by_type, _elements)

		if (_elements):
			for _element in _elements:
				yield _element

	def get_property_value(
		self,
		property_value_wrapper:archicad.Types.PropertyValueWrapper
	):
		"""
		Find the human readable property value from a PropertyValueWrapper.

		It could be hidden inside nested Wrappers in case of Enums etc; hence this function.
		"""

		_unpacked_property = self.unpack_property_value(
			property_value_wrapper
		)

		_value = _unpacked_property.value

		return _value

	def unpack_property_value(
		self,
		property_value_wrapper:Union[
			archicad.Types.PropertyValueWrapper,
			archicad.Types.EnumValueId,
		]
	):
		"""
		Extract a property value into a dictionary representation in PropertyValue class.

		Returning PropertyValue consists of 3 main keys:
		{
		"constructor": the subclass of NormalOrUserUndefinedPropertyValue for reconstruction,
		"value": scalar value or list or another nested PropertyValue object,
		"args": keyworded arguments to pass into constructor upon reconstruction.
		}
		"""

		if (hasattr(property_value_wrapper, "propertyValue")):
			# Unpack if its a wrapper.
			_property_value = property_value_wrapper.propertyValue
		else:
			# This function calls itself if an Enum value is found, so property_value_wrapper can be unwrapped.
			_property_value = property_value_wrapper

		_type = type(_property_value)

		_typical_args = (
			# "value",
			# "nonLocalizedValue",
			# "displayValue",
			"type",
			"status",
		)
		_args = {}

		for _arg in _typical_args:
			if (_attr := getattr(_property_value, _arg, None)):
				_args[_arg] = _attr

		if (isinstance(_property_value, (
			self.types.NotAvailablePropertyValue,
			self.types.NotEvaluatedPropertyValue,
			self.types.UserUndefinedPropertyValue,
		))):
			_value = None

		elif (isinstance(_property_value, (
			self.types.NormalSingleEnumPropertyValue,
		))):
			_value = self.unpack_property_value(
				_property_value.value
			)

		elif (isinstance(_property_value, (
			self.types.NormalMultiEnumPropertyValue,
		))):
			_listvalues = [
				self.unpack_property_value(
					_listitem
				) for _listitem in _property_value.value
			]

			if (len(_listvalues) > 0):
				_value = _listvalues[0]
				_value.value = [
					_listvalue.value for _listvalue in _listvalues
				]
			else:
				_value = []

		elif (isinstance(_property_value, (
			self.types.EnumValueIdWrapper,
		))):
			_value = self.unpack_property_value(
				_property_value.enumValueId
			)

		elif (isinstance(_property_value, (
			self.types.NonLocalizedValueEnumId,
		))):
			_value = _property_value.nonLocalizedValue

		elif (isinstance(_property_value, (
			self.types.DisplayValueEnumId,
		))):
			_value = _property_value.displayValue

		elif (isinstance(_property_value, (
			self.types.NormalAngleListPropertyValue,
			self.types.NormalAnglePropertyValue,
			self.types.NormalAreaListPropertyValue,
			self.types.NormalAreaPropertyValue,
			self.types.NormalBooleanListPropertyValue,
			self.types.NormalBooleanPropertyValue,
			self.types.NormalIntegerListPropertyValue,
			self.types.NormalIntegerPropertyValue,
			self.types.NormalLengthListPropertyValue,
			self.types.NormalLengthPropertyValue,
			self.types.NormalNumberListPropertyValue,
			self.types.NormalNumberPropertyValue,
			self.types.NormalStringListPropertyValue,
			self.types.NormalStringPropertyValue,
			self.types.NormalVolumeListPropertyValue,
			self.types.NormalVolumePropertyValue,
		))):
			_value = _property_value.value
		else:
			raise RuntimeError("Unexpected Property Value Type {_type} encountered: author of module needs to add type to function!")

		return PropertyValue({
			"constructor": _type,
			"value": _value,
			"args": _args,
		})

	def property_value_wrapper_to_records(
		self,
		elements_ids:List[archicad.Types.ElementId],
		property_userids:List[archicad.Types.PropertyId],
		wrapper:archicad.Types.PropertyValuesWrapper,
	)->List[Dict[str,Any]]:

		"""
		Map a PropertyValuesWrapper from GetPropertyValuesOfElements to List[ElementId] and List[PropertyId] to create records.
		"""

		_records = []
		_type_map = {}

		for _element_id, _property_values in zip(elements_ids, wrapper):
			# Element Level

			_record = {
				GUID_COLUMN_NAME:_element_id.elementId.guid,
			}

			for _property_userid, _property_value in zip(property_userids, _property_values.propertyValues):
				# Property Level

				_key = self.property_column_name(_property_userid)
				_value = self.get_property_value(_property_value)

				if (not _type_map[_key]["value"] if (_type_map.get(_key, None)) else True):
					_type = self.unpack_property_value(_property_value)
					# del (_type["value"])

					if (_type):
						_type_map[_key] = _type

				_record[_key] = _value

			# Add to record at Element Level
			_records.append(_record)

		return _records, _type_map

	def property_value_wrapper_to_dataframe(
		self,
		element_ids:List[archicad.Types.ElementId],
		property_userids:List[archicad.Types.PropertyUserId],
		wrapper:archicad.Types.PropertyValuesWrapper,
	)->ElementsPropertyValues:
		"""
		Map a PropertyValuesWrapper from GetPropertyValuesOfElementComponents to List[ElementId] and List[PropertyId] to create pandas DataFrame.
		"""

		_records, _type_map = self.property_value_wrapper_to_records(
			elements_ids=element_ids,
			property_userids=property_userids,
			wrapper=wrapper
		)

		_df = ElementsPropertyValues.from_records(
			data=_records,
			# property_structure=_type_map,
			index=GUID_COLUMN_NAME,
		)

		_df.property_structure = _type_map

		return _df

	@alive_only
	def get_element_property_dataframe(
		self,
		element_ids:List[archicad.Types.ElementId],
		property_userids:List[archicad.Types.PropertyUserId],
	)->ElementsPropertyValues:
		property_ids = self.commands.GetPropertyIds(property_userids)

		return self.property_value_wrapper_to_dataframe(
			element_ids,
			property_userids,
			self.commands.GetPropertyValuesOfElements(
				element_ids,
				property_ids,
			),
		)

	def summarise_transaction_results(
		self,
		results:List[archicad.Types.ExecutionResult],
	)->Dict[str, int]:
		_summary = {}

		for _result in results:
			if (isinstance(_result, self.types.SuccessfulExecutionResult)):
				_code = 0
				_msg = "Success"
			else:
				_code = _result.error.code
				_msg = _result.error.message

			_key = (_code, _msg)
			_summary[_key] = _summary.get(_key, 0) + 1

		return _summary



# Initialise Singleton instance of connection()
connector = connection()