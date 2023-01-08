# iws_modelling
The iws_modelling package was developed for modelling Intermittent Water Supply Networks in python using different modelling methods that utilize the solver engines of EPANET and EPA-SWMM  
This package contains two main modules: Convert_Method and Run_Method for converting between methods and executing input files respectively  
  
### Major Dependencies and Environment  
The modules of this package use the following packages, make sure that these packages are installed within the environment used when using this package:  
**WNTR** Water Network Tool For Resilience: Used to run EPANET files  
**PYSWMM** Used to Run EPA-SWMM files  
**Pandas**  
**Numpy**
**matplotlib** For plotting and visualisation    
**timeit** For timing execution of input files  
**re** for using regular expressions  
  
Alternatively, we provide the IWSModellingReqs.yml environment which includes all dependencies along with the iws_modelling package itself

## Directory
**iws_modelling**: main package directory, contains the package's modules:  
    **Convert_Method.py** module for converting a normal PDA EPANET input file into any of the different IWS methods  
    **Run_Method.py** module for executing and processing and IWS EPANET or EPASWMM file  
**Examples.py** python script containing tutorial examples for using the package's modules and methods  
**LICENSE**
**pyproject.toml**  
**README_PKG.md** this file  
**requirements.txt** list of required dependencies
**IWSModellingReqs.yml** python environment containing all required dependencies including the iws_modelling package itself
  
## Module Overview  
### Convert_Method:   
this module contains python functions for converting a "normal" EPANET file into any of the eight following IWS modelling assumptions:  
**to_CVTank** converts to a volume-restricted CV-Tank EPANET input file  
**to_PSVTank** converts to a volume-restricted PSV-Tank EPANET input file  
**to_CVRes** converts to an unrestricted CV-Res EPANET input file  
**to_FCVRes** converts to a flow-restricted FCV-Res EPANET input file  
**to_FCVEM** converts to a flow-restricted FCV-EM EPANET input file  
**to_Outlet_Outfall** converts to a flow-restricted Outlet-Outfall EPA-SWMM input file (models the filling phase)  
**to_Outlet_Storage** converts to a volume-restricted Outlet-Storage EPA-SWMM input file (models the filling phase)  
  
### Run_Method:  
this module contains python functions for executing and processing IWS EPANET and EPA-SWMM input files:  
**CVTank** executes and processes a volume-restricted CV-Tank EPANET input file  
**PSVTank** executes and processes a volume-restricted PSV-Tank EPANET input file  
**CVRes** executes and processes an unrestricted CV-Res EPANET input file  
**FCV** executes and processes flow-restricted FCV-Res and FCV-EM EPANET input files  
**PDA** executes and processes a flow-restricted EPANET-PDA input file  
**OutletOutfall** executes and processess a flow-restricted Outlet-Outfall EPA-SWMM input file  
**OutletStorage** executes and processes a volume-restricted Outlet-Storage EPA-SWMM input file  
  
Additional Details can be found in the docstring for each function