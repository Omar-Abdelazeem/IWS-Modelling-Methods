# IWS-Modelling-Methods-Repo
This repo is associated with the publication titles "How to Model Intermittent Water Supply: Comparing Modelling Choices and Their Impact on Inequality" 
  
### Required Packages  
The notebooks in this repository use the following packages, make sure that these packages are installed within the environment used to run these files:  
**WNTR** Water Network Tool For Resilience: Used to run EPANET files  
**PYSWMM** Used to Run EPA-SWMM files  
**Pandas**  
**Numpy**  
**timeit** For timing execution of input files  
**re** for using regular expressions  
**matplotlib** For plotting and visualisation  

## Directory
**Running Methods** Contains Jupyter notebooks for running prepared .inp files for all modelling methods   
**Conversion Files** Contains notebooks for converting .inp files of "normal" EPANET files into .inp files of selected methods  
**Network Files** Contains all the EPANET and EPA-SWMM .inp files for the 3 networks, with 8 methods each, using 2 supply durations each (48 total files)  
**Reproducing-Figures-Tables** Contains scripts used to generate the figures in the paper
  
### Naming Convention  
Network Input and Output files are named using standardised fragments. Each notebook (Running, Conversion or Figure) is internally consistent, i.e., it will still work fine with files not named according to convention. However, we encourage the use of the naming convention since it matches the notebook names and thus will reduce chance of using the wrong notebook.  
  
The naming convention is : Network Name_Supply Duration_Method Name_Result Type_extension
The standardised fragments are as follows:  
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
  
#### Result types
Result types are only added to result files
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

**Network1_4hr_CV-Tank.inp** is an input file using EPANET IWS method CV-Tank running in Network 1 for 4 hours of supply per day  
**Network2_12hr_Outlet-Outfall_Means.csv** is a results file containing a time series of the satisfaction ratio in Network 2 when supplied for 12 hours a day modelled using the SWMM IWS method Outlet-Outfall  
  
## Running Methods:
This folder contains notebooks for each of the eight methods compared in this study. It also generates files containing the processed results of each run which were used to generate the figures in this study.  
EPA-SWMM files take longer to run and their output files are sizeable (.out files can be on the order of 100s of MBs) (on the order of tens of minutes depending on the machine you're using), EPANET files are rather speedy  
Auxiliary files included in this folder labelled "_Pressures" process the output into pressure values rather than satisfaction ratio. These files were used to generate the results used in Figure S-6.  
  
## Conversion Files:
This folder contains notebooks that convert a Vanilla EPANET file with demands assigned to their original demand nodes (with the analysis option selected as PDA)  
to any of the 6 EPANET methods and the 2 SWMM methods in this study. We ran these files for you and generated all input files used for this study, (48 Total files: 8 methods x 3 networks x 2 supply durations), so to reproduce the results in this study, there is no need to run these again, but feel absolutely free to do so!  
These files take .inp EPANET files (labeled with _PDA.inp at the end of their name). The conversion will work with any .inp file, but the naming convention will be broken.  
Conversion of EPANET to EPASWMM takes longer to run due to the discretization creating a lot of pipes and nodes  
  
## Network Files  
This folder contains the .inp files for all networks, methods and supply durations. We supplied 48 files in the repo (8 methods, 3 networks, 2 supply durations) and organized them into 3 folders by test network  
Processed results are also saved to this folder by default unless the path is changed  
This folder also contains some helper files needed to migrate some information between the conversion notebook to the running notebook  
  
## Reprouducing-Figures-Tables:
This folder contains notebooks that reproduce Figures 2, 4, and 5 as well as Table S-5  
To be able to run these notebooks and reproduce the figures, first run each method file for both supply durations. These files will automatically generate files for the results. The following is a description of the folder's content:  
**Figure2.ipynb** reproduces Figure 2 - mean satisfction ratio using EPANET methods -of the main text by default. It can also create its corresponding supplementary figures S-4 and S-5 by following the instructions in the notebook. It can also be repurposed to create similar figures using any "_Means.csv" file.  
**Figure4.ipynb** reproduces Figure 4 - Mean and Range of Satisfaction ratios in volume vs flow restricted methods - of the main text by default. It can also create its corresponding supplementary figures S-7 and S-8 by following the instructions in the notebook. It can also be repurposed to create similar figures using any "_Means.csv", "_XXthPercentile.csv" and ""YYth percentile.csv" files  
**Figure5.ipynb** reproduces Figure 5 - Mean and range of satisfaction ratios in flow and volume restricted methods: filling vs non-filling - of the main text by default. It can also create its corresponding supplementary figures S-9 and S-10 by following the instructions in the notebook. It can also be repurposed to create similar figures using any "_Means.csv", "_XXthPercentile.csv" and ""YYth percentile.csv" files  
**Table S-5.ipynb** reproduces Table S-5 - execution time of each EPANET method - by default  
**Figure3** In this subfolder: we provide 2 csv files with the input data underlying the contours in Figure 3 as well as the .shp layers we created in QGIS. The input CSVs can be loaded as layers in QGIS and contoured using the same bins to reproduce the figure