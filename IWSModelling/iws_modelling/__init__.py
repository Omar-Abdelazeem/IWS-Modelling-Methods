"""
The IWSModelling Package contains two modules:

Convert_Method
--------------- 
Contains methods for converting "normal" EPANET input files into EPANET and EPA-SWMM input files that model IWS in 7 other methods

Run_Method
---------------
Contains methods to run IWS EPANET and EPA-SWMM files of 8 different methods and process and format the results
"""

from .Convert_Method import to_CVRes
from .Convert_Method import to_CVTank
from .Convert_Method import to_FCVEM
from .Convert_Method import to_FCVRes
from .Convert_Method import to_Outlet_Outfall
from .Convert_Method import to_Outlet_Storage
from .Convert_Method import to_PSVTank
from .Convert_Method import change_duration
from .Convert_Method import to_all

from .Run_Method import CVRes
from .Run_Method import CVTank
from .Run_Method import FCV
from .Run_Method import PDA
from .Run_Method import PSVTank
from .Run_Method import OutletOutfall
from .Run_Method import OutletStorage


__version__ = '1.0.0'