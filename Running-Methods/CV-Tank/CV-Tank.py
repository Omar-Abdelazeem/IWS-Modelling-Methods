
import wntr  
import numpy as np 
import pandas as pd
import matplotlib as mpl
from matplotlib import figure
import matplotlib.pyplot as plt
import timeit 
import re

 # Replace with appropriate path and filename
 # Run this script from the root of the repository IWS-MODELLING-METHODS-REPO or change the path to relative
directory='../../Network-Files/Network 3/'
filenames=['Network3_12hr_CV-Tank.inp','Network3_4hr_CV-Tank.inp']
for filename in filenames:
    name_only=filename[0:-4]
    print(name_only)
    abs_path=directory+filename
    # create network model from input file
    network = wntr.network.WaterNetworkModel(abs_path)

    ## Extract Supply Duration from .inp file
    supply_duration=int(network.options.time.duration/60)    # in minutes

    # run simulation
    sim = wntr.sim.EpanetSimulator(network)
    # store results of simulation
    results=sim.run_sim()

    timesrs=pd.DataFrame()
    timesrs[0]=results.node['pressure'].loc[0,:]
    for i in range(1,supply_duration+1):
        # Extract Node Pressures from Results
        timesrs=pd.concat([timesrs,results.node['pressure'].loc[i*60,:]],axis=1)

    # Transpose DataFrame such that indices are time (sec) and Columns are each Node
    timesrs=timesrs.T
    # Filter DataFrame for Columns that contain Data for demand nodes only i.e., Tanks in STM
    timesrs=timesrs.filter(regex='Tank\D+',axis=1)

    # Intialize Series for storing statistics
    mean=pd.Series(dtype='float64')
    median=pd.Series(dtype='float64')
    low_percentile=pd.Series(dtype='float64')
    high_percentile=pd.Series(dtype='float64')

    # Set the percentile values to be calculated
    low_percent_val=10   # Range 0 to 100 ONLY
    high_percent_val=90  # Range 0 to 100 ONLY

    # Loop over each row (time step) in the results and calculate values of mean, median, low and high percentiles
    for row in timesrs.index:
        mean.loc[row]=np.mean(timesrs.loc[row,:])*100
        low_percentile.loc[row]=np.percentile(timesrs.loc[row,:],low_percent_val)*100
        median.loc[row]=np.percentile(timesrs.loc[row,:],50)*100
        high_percentile.loc[row]=np.percentile(timesrs.loc[row,:],high_percent_val)*100