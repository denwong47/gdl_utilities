import re
import os
import sys

illegal_unicode_characters = [
    (0, 8),
    (11, 12),
    (14, 31),
    (127, 132),
    (134, 159),
    (64976, 64991),
    (65534, 65535)]
if sys.maxunicode >= 65536:
    illegal_unicode_characters.extend([
        (131070, 131071),
        (196606, 196607),
        (262142, 262143),
        (327678, 327679),
        (393214, 393215),
        (458750, 458751),
        (524286, 524287),
        (589822, 589823),
        (655358, 655359),
        (720894, 720895),
        (786430, 786431),
        (851966, 851967),
        (917502, 917503),
        (983038, 983039),
        (1048574, 1048575),
        (1114110, 1114111)])

def strip_invalid_characters(xml_text = None):
    _illegal_ranges = [fr'{chr(low)}-{chr(high)}' for (low, high) in illegal_unicode_characters]
    _xml_illegal_character_regex = '[' + ''.join(_illegal_ranges) + ']'
    _illegal_xml_chars_re = re.compile(_xml_illegal_character_regex)
    return re.sub(_illegal_xml_chars_re, '', xml_text)
