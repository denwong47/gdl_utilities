# gdl_utilities
 Utilities for GDL developers.

 These are an incomplete set of tools that were built during my time as an architect for a London based contractor - or whatever that was salvagable from the run-and-forget codes that was built under immense time stress. Just as I start to properly package up the methods and classes, I also reached a point where my data engineering experience had become a career of its own, and I quit architecture and ArchiCAD as a result.

 In all likelihood I will never be returning to ArchiCAD again and going forward I would be less and less able to maintain this repo. So feel free to take ideas from it; but no functionality is guaranteed on your system.

 ```
 IMPORTANT: Built for macOS only - paths will need adjusting for Windows.
 ```

 Used with AC19-25. (AC Connection: AC24-25)


 
 ### Project Status
 ```
 Unfinished, End of Development
 ```

 # Modules

 ## gdl_utilities.ac_commands
 Methods to start and kill instances of ArchiCAD.

 ## gdl_utilities.ac_connection
 Pulling and pushing data to and from an open ArchiCAD instance using Python Connection.
 
 Require [ARCHICAD Python Interface](https://pypi.org/project/archicad/).

 ## gdl_utilities.gsm_commands
 Python interface for shell commands to [LP_XMLConverter](https://gdl.graphisoft.com/tips-and-tricks/how-to-use-the-lp_xmlconverter-tool).

 ## gdl_utilities.parse_params
 Parse GDL parameters in XML files produced by [LP_XMLConverter](https://gdl.graphisoft.com/tips-and-tricks/how-to-use-the-lp_xmlconverter-tool).

 ## gdl_utilities.script
 Methods relating to generation of GDL scripts.

 ## gdl_utilities.xml
 Utilities for XML parsing, namely removal of illegal characters which will be rejected by [LP_XMLConverter](https://gdl.graphisoft.com/tips-and-tricks/how-to-use-the-lp_xmlconverter-tool).
