# IWS-Modelling-Methods-Repo
This repo is associated with the publication entitled "How to Model Intermittent Water Supply: Comparing Modelling Choices and Their Impact on Inequality" 

## Directory
**Running Methods** Contains Jupyter notebooks for running prepared .inp files for all modelling methods as well as .py scripts for batch runs of the same methods  
**Conversion Files** Contains notebooks for converting .inp files of "normal" EPANET files into .inp files of selected methods  
**Network Files** Contains all the EPANET and EPA-SWMM .inp files for the 3 networks, with 8 methods each, using 2 supply durations each (48 total files)  
**Reproducing-Figures-Tables** Contains scripts used to generate the figures in the paper

### Naming Convention  
**_PDA** suffix: A vanilla EPANET .inp file with demands assigned to nodes. Serves as the input for Conversion Files  
**_CV-Tank** suffix: An IWS EPANET .inp file using the CV-Tank method  
**_PSV-Tank** suffix: An IWS EPANET .inp file using the PSV-Tank method  
**_CV-Res** suffix:  An IWS EPANET .inp file using the CV-Res method  
**_FCV-EM** suffix: An IWS EPANET .inp file using the FCV-EM method  
**_FCV-Res** suffix: An IWS EPANET .inp file using the FCV-Res method  

## Conversion Files:
This folder contains notebooks that convert a Vanilla EPANET file with demands assigned to their original demand nodes (with the analysis option selected as PDA)  
to any of the 6 EPANET methods and the 2 SWMM methods in this study. We ran these files for you and generated all input files used for this study, (48 Total files: 8 methods x 3 networks x 2 supply durations), so to reproduce the results in this study, there is no need to run these again, but feel absolutely free to do so!  
These files take .inp EPANET files (labeled with _PDA.inp at the end of their name). The conversion will work with any .inp file, but the naming convention will be broken.  

## Reprouducing-Figures-Tables:
This folder contains notebooks that reproduce Figures 2, 4, and 5 as well as Table S-5  
To be able to run these notebooks and reproduce the figures