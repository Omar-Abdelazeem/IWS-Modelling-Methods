import iws_modelling as iws
import re
import pathlib

## This script is intended to facilitate the process of reproducing the figures included in our study
#  The script runs all 48 Input files in the Network-Files folder, to produce all the data required for reproducing main text and supplementary figures
#  For more details on how these input files are processed, or how they were generated see the notebooks in Running-Methods and Conversion-Files respectively
#  For more details on the package used in this script (iws_modelling), refer to the REAMDE_PKG.md file in IWSModelling folder

# Navigate to Network-Files directory from your working directoy. Leave as "" if working directory is Network-Files
dir=""
networks=['Network 1/Network1','Network 2/Network2']
durations=['_8hr']
methods=['_PDA','_FCV-EM','_FCV-Res','_PSV-Tank','_CV-Tank','_CV-Res','_Outlet-Outfall','_Outlet-Storage']
xtension='.inp'

for network in networks:
    for duration in durations:
        for method in methods:
            path_str=dir+network+duration+method+xtension
            path_obj=pathlib.Path(path_str)
            print(path_str)
            if re.search('PDA',path_str):
                iws.PDA(path_obj,plots=False)
            elif re.search('FCV',path_str):
                iws.FCV(path_obj,plots=False)
            elif re.search('PSV',path_str):
                iws.Run_Method.PSVTank(path_obj,plots=False)
            elif re.search('CV-Tank',path_str):
                iws.CVTank(path_obj,plots=False)
            elif re.search('CV-Res',path_str):
                iws.CVRes(path_obj,plots=False)
            elif re.search('Outfall',path_str):
                iws.OutletOutfall(path_obj,False,plots=False)
            elif re.search('Storage',path_str):
                iws.OutletStorage(path_obj,False,plots=False)

# Note that this will take a long time to run due to the SWMM simulations