# IWS-Modelling-Methods-Repo
This repo is associated with the publication entitled "How to Model Intermittent Water Supply: Comparing Modelling Choices and Their Impact on Inequality" 

## Directory
**Running Methods** Contains Jupyter notebooks for running prepared .inp files for all modelling methods as well as .py scripts for batch runs of the same methods  
**Conversion Files** Contains notebooks for converting .inp files of "normal" EPANET files into .inp files of selected methods  
**Network Files** Contains all the EPANET and EPA-SWMM .inp files for the 3 networks, with 8 methods each, using 2 supply durations each (48 total files)  
**Reproducing-Figures-Tables** Contains scripts used to generate the figures in the paper
  
### Naming Convention  
Network Input and Output files are named according to the 
  
#### Network Names
**Network1** : File uses Network 1 (Campisano, 2019)  
**Network2** : File uses Network 2 (Bragalli, 2012)  
**Network3** : File uses Network 3 (Bragalli, 2012)
  
#### Supply Durations
**_4hr** : Supply duration of 4 hrs / day for this file (input, results… etc.)  
**_12hr** : Supply duration of 12 hrs / day for this file (input, results… etc.)  
  
#### Method Names
**_PDA** : A vanilla EPANET .inp file with demands assigned to nodes. Serves as the input for Conversion Files  
**_CV-Tank** : An IWS EPANET .inp file using the CV-Tank method  
**_PSV-Tank** : An IWS EPANET .inp file using the PSV-Tank method  
**_CV-Res** :  An IWS EPANET .inp file using the CV-Res method  
**_FCV-EM** : An IWS EPANET .inp file using the FCV-EM method  
**_FCV-Res** : An IWS EPANET .inp file using the FCV-Res method  
**_Outlet-Outfall** : An IWS EPA-SWMM .inp file using the Outlet-Outfall method  
**_Outlet-Storage** : An IWS EPA-SWMM .inp file using the Outlet-Storage method
  
#### Output types
**_TimeSeries.csv**: Results file produced by running any of the methods. Contains a time series of the satisfaction ratio for all consumers in a given network  
**_Means.csv**: Results file produced by running any of the methods. Contains a time series of the mean satisfaction in a given network  
**_Medians.csv**: Results file produced by running any of the methods. Contains a time series of the median satisfaction ratio  in a given network  
**_XXthPercentile.csv**:  Results file produced by running any of the methods. Contains a time series of the XXth (e.g., 10th) Percentile satisfaction ratio in a given network  
**_Demands.csv**: Contains the demand rates for all consumers in a given network. Required for some methods to function  
  
#### Extensions:
**.inp** EPANET or EPA-SWMM input file  
**.csv** Comma-Separated Values file. The output format we used for our postprocessed results  
**.out** EPA-SWMM output file. Intermediate product created by EPA-SWMM which we process further into our interpretable results  

#### Examples
**Network1_4hr_CV-Tank.inp** is an input file using EPANET IWS method CV-Tank running in Network for 4 hours of supply per day  
**Network2_12hr_Outlet-Outfall_Means.csv** is a results file containing a time series of the satisfaction ratio in Network 2 when supplied for 12 hours a day modelled using the SWMM IWS method Outlet-Outfall  
  
## Conversion Files:
This folder contains notebooks that convert a Vanilla EPANET file with demands assigned to their original demand nodes (with the analysis option selected as PDA)  
to any of the 6 EPANET methods and the 2 SWMM methods in this study. We ran these files for you and generated all input files used for this study, (48 Total files: 8 methods x 3 networks x 2 supply durations), so to reproduce the results in this study, there is no need to run these again, but feel absolutely free to do so!  
These files take .inp EPANET files (labeled with _PDA.inp at the end of their name). The conversion will work with any .inp file, but the naming convention will be broken.  

## Reprouducing-Figures-Tables:
This folder contains notebooks that reproduce Figures 2, 4, and 5 as well as Table S-5  
To be able to run these notebooks and reproduce the figures