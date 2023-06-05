"""
The Run_Method Module contains methods to execute and process the output of IWS EPANET and EPA-SWMM Files
using one of the  eight methods we studied
"""
global wntr,np,pd,re,math,mpl,figure,plt,timeit,pyswmm,LinkAttribute,NodeAttribute,datetime
global simplefilter

import wntr
import numpy as np 
import pandas as pd
import re
import math
import matplotlib as mpl
from matplotlib import figure
import matplotlib.pyplot as plt
import timeit 
import pyswmm
from swmm.toolkit.shared_enum import LinkAttribute,NodeAttribute
from warnings import simplefilter
import datetime

def CVRes(path:str,output:str='S',low_percentile:int=10,high_percentile:int=90,save_outputs:bool=True,time_execution:bool=False,n_iterations:int=100,plots=True):
    """
    Executes an IWS EPANET file that uses the unrestricted method CV-Res.

    Parameters
    -----------
    path (str): path to input file (relative, but will handle full absolute paths)

    output (str): specify output to process. Default: Satisfaction Ratio. Other supported outputs include 'P' for Pressure  

    low_percentile (int): value for the low percentile statistic (default 10th percentile) representing disadvantaged consumers  

    high_percentile (int): value for the high percentile statistic (default 90th percentile) representing disadvantaged consumers  

    save_outputs (bool): Save processed output and statistices (mean, median an percentiles) as CSV files. Default: True.  

    time_execution (bool): Optionally times the execution of the EPANET file. default= False  

    n_iterations (int): number of iterations for averaging execution time. Default=100  

    plots (bool): Display mean and range plots. default: True


    Returns: timesrs_processed, mean, low_percentile_series, high_percentile_series

    timesrs_processed: Pandas DataFrame of size TxN where T is the number of timesteps and N is the number of demand (non-zero) nodes 
    in the network. Contains the values for the selected output: Satisfaction Ratio (S) or Pressures (P) for each demand node at each time step  

    mean: Pandas Series of size Tx1 where T is the number of timesteps. Mean output values for each timestep  

    low_percentile_series: Pandas Series of size Tx1. The XXth percentile output values for each timestep. XX is determined by function input: low_percentile  

    high_percentile_series: Pandas Series of size Tx1. The YYth percentile output values for each timestep. YY is determined by function input: high_percentile
    """
    assert 0 < low_percentile <100, "Percentile must be between 0 and 100"
    assert 0 < high_percentile <100, "Percentile must be between 0 and 100"
    assert output in ['S','P'], "Specify Supported Output Type: S for Satisfaction or P for Pressures"
    assert n_iterations>0, "Specify a positive integer"

    name_only=path.split("/")[-1][0:-4]
    print("Selected File: ",name_only)

    # create network model from input file
    network = wntr.network.WaterNetworkModel(path)
    Hmin=network.options.hydraulic.minimum_pressure
    Hdes=network.options.hydraulic.required_pressure

    demand_links=[]        #list of pipes connected to demand nodes only
    lengths=[]
    diameters=[]
    hwcoeff=[]

    for link in network.links():
        if re.search('^PipeforNode',link[1].name):
            demand_links.append(link[1].name)
            lengths.append(link[1].length)
            diameters.append(link[1].diameter)
            hwcoeff.append(link[1].roughness)
    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)

    lengths=np.array(lengths)
    diameters=np.array(diameters)
    hwcoeff=np.array(hwcoeff)

    head_diff=Hdes-Hmin
    desired_demands=(head_diff/lengths*hwcoeff**1.852*diameters**4.8704/10.67)**0.54

    # run simulation
    sim = wntr.sim.EpanetSimulator(network)
    # store results of simulation
    results=sim.run_sim()

    if time_execution:
        __time_simulation__(path,n_iterations)

    timesrs_output=pd.DataFrame()

    if output=='S':
        timesrs_output[0]=results.link['flowrate'].loc[0,:]
        for i in range(1,supply_duration+1):
            # Extract Node Pressures from Results
            timesrs_output=pd.concat([timesrs_output,results.link['flowrate'].loc[i*60,:]],axis=1)

        # Transpose DataFrame such that indices are time (sec) and Columns are each Node
        timesrs_output=timesrs_output.T
        # Filter DataFrame for Columns that contain Data for demand nodes only i.e., Tanks in STM
        timesrs_output=timesrs_output.filter(demand_links)

        # Calculates the total demand volume in the specified supply cycle
        desired_volumes=[]
        # Loop over each desired demand
        for demand in desired_demands:
            # Append the corresponding desired volume (cum) = demand (LPS) *60 sec/min * supply duration (min) / 1000 (L/cum)
            desired_volumes.append(float(demand)*60*float(supply_duration))

        # Combine demands (LPS) to their corresponding desired volume (cum)
        desired_volumes=dict(zip(demand_links,desired_volumes))

        # Initalized DataFrame for storing volumes received by each demand node as a timeseries
        timesrs_processed=pd.DataFrame(index=timesrs_output.index,columns=desired_volumes.keys())
        # Set Initial volume for all consumers at 0
        timesrs_processed.iloc[0,:]=0

        # Loop over consumers and time steps to add up volumes as a percentage of total desired volume (Satisfaction Ratio)
        for timestep in list(timesrs_processed.index)[1:]:
            for node in timesrs_processed.columns:
                # Cummulatively add the percent satisfaction ratio (SR) increased each time step
                ## SR at time t = SR at time t-1 + demand at time t-1 (cms) *60 seconds per time step/ Desired Demand Volume (cum)
                timesrs_processed.at[timestep,node]=timesrs_processed.at[timestep-60,node]+timesrs_output.at[timestep-60,node]*60/desired_volumes[node]*100
    elif output=='P':
        timesrs_output[0]=results.node['pressure'].loc[0,:]
        for i in range(1,supply_duration+1):

            # Extract Node Pressures from Results
            timesrs_output=pd.concat([timesrs_output,results.node['pressure'].loc[i*60,:]],axis=1)

        # Transpose DataFrame such that indices are time (sec) and Columns are each Node
        timesrs_output=timesrs_output.T
        # Filter DataFrame for Columns that contain Data for demand nodes only i.e., Tanks in STM
        node_list=[]
        for column in timesrs_output.columns:
            if re.search('^AR',column):
                node_list.append(column[2:])
        # Filter DataFrame for Columns that contain Data for demand nodes only i.e., Tanks in STM
        timesrs_processed=timesrs_output.filter(node_list,axis=1)
    
    mean,low_percentile_series,median,high_percentile_series=__get_stats__(timesrs_processed,low_percentile,high_percentile)
    
    if save_outputs==True:
    # Saves Entire Results DataFrame as Filename_TimeSeries.csv in the same path
        timesrs_processed.to_csv(path[0:-4]+"_TimeSeries.csv")

        # Saves Mean Satisfaction with time as Filename_Means.csv in the same path
        mean.to_csv(path[0:-4]+"_Means.csv")

        # Saves Median Satisfaction with time as Filename_Medians.csv in the same path
        median.to_csv(path[0:-4]+"_Medians.csv")

        # Saves the specified low percentile (XX) values with time as Filename_XXthPercentile.csv in the same path
        low_percentile_series.to_csv(path[0:-4]+"_"+str(low_percentile)+"thPercentile.csv")

        # Saves the specified high percentile (YY) values with time as Filename_YYthPercentile.csv in the same path
        high_percentile_series.to_csv(path[0:-4]+"_"+str(high_percentile)+"thPercentile.csv")

    if plots:
        mpl.rcParams['figure.dpi'] = 450
        font = {'family' : 'Times',
                'weight' : 'bold',
                'size'   : 3}
        mpl.rc('font', **font)
        mpl.rc('xtick', labelsize=3)
        mpl.rcParams['axes.linewidth'] = 0.5

        # Prepping an xaxis with hr format
        supply_duration_hr=supply_duration/60
        xaxis=np.arange(0,supply_duration_hr+0.00001,1/60)

        fig,ax=__plot_mean__(xaxis,mean,output,'#fee090',high_percentile_series)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show

        fig,ax=__plot_mean__(xaxis,mean,output,'#fee090',high_percentile_series)
        plt.fill_between(xaxis, y1=low_percentile_series, y2=high_percentile_series, alpha=0.4, color='#fee090', edgecolor=None)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show
    return timesrs_processed,mean,low_percentile_series,high_percentile_series

            
def CVTank(path:str,output:str='S',low_percentile:int=10,high_percentile:int=90,save_outputs:bool=True,time_execution:bool=False,n_iterations:int=100,plots=True):
    """
    Executes an IWS EPANET file that uses the volume-restricted method CV-Res.

    Parameters
    -----------
    path (str): path to input file (relative, but will handle full absolute paths) 

    output (str): specify output to process. Default: Satisfaction Ratio. Other supported outputs include 'P' for Pressure  

    low_percentile (int): value for the low percentile statistic (default 10th percentile) representing disadvantaged consumers  

    high_percentile (int): value for the high percentile statistic (default 90th percentile) representing disadvantaged consumers  

    save_outputs: Save processed output and statistices (mean, median an percentiles) as CSV files. Default: True.  

    time_execution (Boolean): Optionally times the execution of the EPANET file. default= False  

    n_iterations (int): number of iterations for averaging execution time. Default=100  

    plots (bool): Display mean and range plots. default: True


    Returns: timesrs_processed, mean, low_percentile_series, high_percentile_series

    timesrs_processed: Pandas DataFrame of size TxN where T is the number of timesteps and N is the number of demand (non-zero) nodes 
    in the network. Contains the values for the selected output: Satisfaction Ratio (S) or Pressures (P) for each demand node at each time step  

    mean: Pandas Series of size Tx1 where T is the number of timesteps. Mean output values for each timestep  

    low_percentile_series: Pandas Series of size Tx1. The XXth percentile output values for each timestep. XX is determined by function input: low_percentile  

    high_percentile_series: Pandas Series of size Tx1. The YYth percentile output values for each timestep. YY is determined by function input: high_percentile
    """

    assert 0 < low_percentile <high_percentile, "Percentile must be between 0 and 100"
    assert 0 < high_percentile <100, "Percentile must be between 0 and 100"
    assert output in ['S','P'], "Specify Supported Output Type: S for Satisfaction or P for Pressures"
    assert n_iterations>0, "Specify a positive integer"

    name_only=path.split("/")[-1][0:-4]
    print("Selected File: ",name_only)

    # create network model from input file
    network = wntr.network.WaterNetworkModel(path)

    ## Extract Supply Duration from .inp file
    supply_duration=int(network.options.time.duration/60)    # in minutes

    # run simulation
    sim = wntr.sim.EpanetSimulator(network)
    # store results of simulation
    results=sim.run_sim()

    if time_execution:
        __time_simulation__(path,n_iterations)
    
    timesrs_output=pd.DataFrame()
    timesrs_output[0]=results.node['pressure'].loc[0,:]
    for i in range(1,supply_duration+1):
        # Extract Node Pressures from Results
        timesrs_output=pd.concat([timesrs_output,results.node['pressure'].loc[i*60,:]],axis=1)
    # Transpose DataFrame such that indices are time (sec) and Columns are each Node
    timesrs_output=timesrs_output.T

    if output=='S':
        timesrs_processed=timesrs_output.filter(regex='Tank\D+',axis=1)*100
    elif output=='P':
        node_list=[]
        for column in timesrs_output.columns:
            if re.search('^Tank',column):
                node_list.append(column[11:])
        timesrs_processed=timesrs_output.filter(node_list,axis=1)
    
    mean,low_percentile_series,median,high_percentile_series=__get_stats__(timesrs_processed,low_percentile,high_percentile)
    
    if save_outputs==True:
    # Saves Entire Results DataFrame as Filename_TimeSeries.csv in the same path
        timesrs_processed.to_csv(path[0:-4]+"_TimeSeries.csv")

        # Saves Mean Satisfaction with time as Filename_Means.csv in the same path
        mean.to_csv(path[0:-4]+"_Means.csv")

        # Saves Median Satisfaction with time as Filename_Medians.csv in the same path
        median.to_csv(path[0:-4]+"_Medians.csv")

        # Saves the specified low percentile (XX) values with time as Filename_XXthPercentile.csv in the same path
        low_percentile_series.to_csv(path[0:-4]+"_"+str(low_percentile)+"thPercentile.csv")

        # Saves the specified high percentile (YY) values with time as Filename_YYthPercentile.csv in the same path
        high_percentile_series.to_csv(path[0:-4]+"_"+str(high_percentile)+"thPercentile.csv")
    if plots:
        mpl.rcParams['figure.dpi'] = 450
        font = {'family' : 'Times',
                'weight' : 'bold',
                'size'   : 3}
        mpl.rc('font', **font)
        mpl.rc('xtick', labelsize=3)
        mpl.rcParams['axes.linewidth'] = 0.5

        # Prepping an xaxis with hr format
        supply_duration_hr=supply_duration/60
        xaxis=np.arange(0,supply_duration_hr+0.00001,1/60)

        fig,ax=__plot_mean__(xaxis,mean,output,'#d73027',high_percentile_series)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show
    
        fig,ax=__plot_mean__(xaxis,mean,output,'#d73027',high_percentile_series)
        plt.fill_between(xaxis, y1=low_percentile_series, y2=high_percentile_series, alpha=0.4, color='#d73027', edgecolor=None)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show    
    return timesrs_processed,mean,low_percentile_series,high_percentile_series


def PSVTank(path:str,output:str='S',low_percentile:int=10,high_percentile:int=90,save_outputs:bool=True,time_execution:bool=False,n_iterations:int=100,plots:bool=True):
    """
    Executes an IWS EPANET file that uses the volume-restricted method PSV-Res.

    Parameters
    -----------
    path (str): path to input file (relative, but will handle full absolute paths)

    output (str): specify output to process. Default: Satisfaction Ratio. Other supported outputs include 'P' for Pressure  

    low_percentile (int): value for the low percentile statistic (default 10th percentile) representing disadvantaged consumers  

    high_percentile (int): value for the high percentile statistic (default 90th percentile) representing disadvantaged consumers  

    save_outputs: Save processed output and statistices (mean, median an percentiles) as CSV files. Default: True.  

    time_execution (Boolean): Optionally times the execution of the EPANET file. default= False  

    n_iterations (int): number of iterations for averaging execution time. Default=100  

    plots (bool): Display mean and range plots. default: True


    Returns: timesrs_processed, mean, low_percentile_series, high_percentile_series

    timesrs_processed: Pandas DataFrame of size TxN where T is the number of timesteps and N is the number of demand (non-zero) nodes 
    in the network. Contains the values for the selected output: Satisfaction Ratio (S) or Pressures (P) for each demand node at each time step  

    mean: Pandas Series of size Tx1 where T is the number of timesteps. Mean output values for each timestep  

    low_percentile_series: Pandas Series of size Tx1. The XXth percentile output values for each timestep. XX is determined by function input: low_percentile  

    high_percentile_series: Pandas Series of size Tx1. The YYth percentile output values for each timestep. YY is determined by function input: high_percentile
    """

    assert 0 < low_percentile <high_percentile, "Percentile must be between 0 and 100 and percentiles should not be equal"
    assert 0 < high_percentile <100, "Percentile must be between 0 and 100 and percentiles should not be equal"
    assert output in ['S','P'], "Specify Supported Output Type: S for Satisfaction or P for Pressures"
    assert n_iterations>0, "Specify a positive integer"

    name_only=path.split("/")[-1][0:-4]
    print("Selected File: ",name_only)

    # create network model from input file
    network = wntr.network.WaterNetworkModel(path)

    ## Extract Supply Duration from .inp file
    supply_duration=int(network.options.time.duration/60)    # in minutes

    # run simulation
    sim = wntr.sim.EpanetSimulator(network)
    # store results of simulation
    results=sim.run_sim()

    if time_execution:
        __time_simulation__(path,n_iterations)
    
    timesrs_output=pd.DataFrame()
    timesrs_output[0]=results.node['pressure'].loc[0,:]
    for i in range(1,supply_duration+1):
        # Extract Node Pressures from Results
        timesrs_output=pd.concat([timesrs_output,results.node['pressure'].loc[i*60,:]],axis=1)

    # Transpose DataFrame such that indices are time (sec) and Columns are each Node
    timesrs_output=timesrs_output.T
    # Filter DataFrame for Columns that contain Data for demand nodes only i.e., Tanks in STM
    if output=='S':
        timesrs_processed=timesrs_output.filter(regex='AT\D+',axis=1)*100
    elif output=='P':
        node_list=[]
        for node in timesrs_output.columns:
            if re.search("AT\D+",node):
                node_list.append(node[9:])
        timesrs_processed=timesrs_output.filter(node_list,axis=1)

    mean,low_percentile_series,median,high_percentile_series=__get_stats__(timesrs_processed,low_percentile,high_percentile)

    
    if save_outputs==True:
    # Saves Entire Results DataFrame as Filename_TimeSeries.csv in the same path
        timesrs_processed.to_csv(path[0:-4]+"_TimeSeries.csv")

        # Saves Mean Satisfaction with time as Filename_Means.csv in the same path
        mean.to_csv(path[0:-4]+"_Means.csv")

        # Saves Median Satisfaction with time as Filename_Medians.csv in the same path
        median.to_csv(path[0:-4]+"_Medians.csv")

        # Saves the specified low percentile (XX) values with time as Filename_XXthPercentile.csv in the same path
        low_percentile_series.to_csv(path[0:-4]+"_"+str(low_percentile)+"thPercentile.csv")

        # Saves the specified high percentile (YY) values with time as Filename_YYthPercentile.csv in the same path
        high_percentile_series.to_csv(path[0:-4]+"_"+str(high_percentile)+"thPercentile.csv")
    if plots:
        mpl.rcParams['figure.dpi'] = 450
        font = {'family' : 'Times',
                'weight' : 'bold',
                'size'   : 3}
        mpl.rc('font', **font)
        mpl.rc('xtick', labelsize=3)
        mpl.rcParams['axes.linewidth'] = 0.5

        # Prepping an xaxis with hr format
        supply_duration_hr=supply_duration/60
        xaxis=np.arange(0,supply_duration_hr+0.00001,1/60)

        fig,ax=__plot_mean__(xaxis,mean,output,'#fc8d59',high_percentile_series)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show
    
        fig,ax=__plot_mean__(xaxis,mean,output,'#fc8d59',high_percentile_series)
        plt.fill_between(xaxis, y1=low_percentile_series, y2=high_percentile_series, alpha=0.4, color='#fc8d59', edgecolor=None)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show    
    return timesrs_processed,mean,low_percentile_series,high_percentile_series


def FCV(path:str,output:str='S',low_percentile:int=10,high_percentile:int=90,save_outputs:bool=True,time_execution:bool=False,n_iterations:int=100,plots=True):
    """
    Executes an IWS EPANET file that uses the flow-restricted methods FCV-Res & FCV-EM.

    Parameters
    -----------
    path (str): path to input file (relative, but will handle full absolute paths)

    output (str): specify output to process. Default: Satisfaction Ratio. Other supported outputs include 'P' for Pressure  

    low_percentile (int): value for the low percentile statistic (default 10th percentile) representing disadvantaged consumers  

    high_percentile (int): value for the high percentile statistic (default 90th percentile) representing disadvantaged consumers  

    save_outputs: Save processed output and statistices (mean, median an percentiles) as CSV files. Default: True.  

    time_execution (Boolean): Optionally times the execution of the EPANET file. default= False  

    n_iterations (int): number of iterations for averaging execution time. Default=100  

    plots (bool): Display mean and range plots. default: True

    Returns: timesrs_processed, mean, low_percentile_series, high_percentile_series

    timesrs_processed: Pandas DataFrame of size TxN where T is the number of timesteps and N is the number of demand (non-zero) nodes 
    in the network. Contains the values for the selected output: Satisfaction Ratio (S) or Pressures (P) for each demand node at each time step  

    mean: Pandas Series of size Tx1 where T is the number of timesteps. Mean output values for each timestep  

    low_percentile_series: Pandas Series of size Tx1. The XXth percentile output values for each timestep. XX is determined by function input: low_percentile  

    high_percentile_series: Pandas Series of size Tx1. The YYth percentile output values for each timestep. YY is determined by function input: high_percentile
    """

    assert 0 < low_percentile <high_percentile, "Percentile must be between 0 and 100"
    assert 0 < high_percentile <100, "Percentile must be between 0 and 100"
    assert output in ['S','P'], "Specify Supported Output Type: S for Satisfaction or P for Pressures"
    assert n_iterations>0, "Specify a positive integer"

    name_only=path.split("/")[-1][0:-4]
    print("Selected File: ",name_only)

    demand_valves=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)

    # Iterates over the junction list in the Network object
    for valve in network.valves():

        # For all nodes that have non-zero demands
        if valve[1].setting != 0:
            # Record node ID (name) and its desired demand (base_demand) in CMS
            demand_valves.append(valve[1].name)
            desired_demands.append(valve[1].setting)

    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)

    # run simulation
    sim = wntr.sim.EpanetSimulator(network)
    # store results of simulation
    results=sim.run_sim()

    if time_execution:
        __time_simulation__(path,n_iterations)

    timesrs_output=pd.DataFrame()
    timesrs_output[0]=results.link['flowrate'].loc[0,:]
    if output=='S':
        for i in range(1,supply_duration+1):
            # Extract Node Pressures from Results
            timesrs_output=pd.concat([timesrs_output,results.link['flowrate'].loc[i*60,:]],axis=1)
        # Transpose DataFrame such that indices are time (sec) and Columns are each Node
        timesrs_output=timesrs_output.T
        # Filter DataFrame for Columns that contain Data for demand nodes only
        timesrs_output=timesrs_output[demand_valves]
        # Calculates the total demand volume in the specified supply cycle
        desired_volumes=[]
        # Loop over each desired demand
        for demand in desired_demands:
            # Append the corresponding desired volume (cum) = demand (LPS) *60 sec/min * supply duration (min) / 1000 (L/cum)
            desired_volumes.append(float(demand)*60*float(supply_duration))
        # Combine demands (LPS) to their corresponding desired volume (cum)
        desired_volumes=dict(zip(demand_valves,desired_volumes))
        # Initalized DataFrame for storing volumes received by each demand node as a timeseries
        timesrs_processed=pd.DataFrame(index=timesrs_output.index,columns=desired_volumes.keys())
        # Set Initial volume for all consumers at 0
        timesrs_processed.iloc[0,:]=0
        # Loop over consumers and time steps to add up volumes as a percentage of total desired volume (Satisfaction Ratio)
        for timestep in list(timesrs_processed.index)[1:]:
            for node in timesrs_processed.columns:
                # Cummulatively add the percent satisfaction ratio (SR) increased each time step
                ## SR at time t = SR at time t-1 + demand at time t-1 (cms) *60 seconds per time step/ Desired Demand Volume (cum)
                timesrs_processed.at[timestep,node]=timesrs_processed.at[timestep-60,node]+timesrs_output.at[timestep-60,node]*60/desired_volumes[node]*100
    elif output=='P':
        for i in range(1,supply_duration+1):
            # Extract Node Pressures from Results
            timesrs_output=pd.concat([timesrs_output,results.node['pressure'].loc[i*60,:]],axis=1)
        # Transpose DataFrame such that indices are time (sec) and Columns are each Node
        timesrs_output=timesrs_output.T
        # Filter DataFrame for Columns that contain Data for demand nodes only
        node_list=[]
        for valve in demand_valves:
            node_list.append(valve[10:])
        timesrs_processed=timesrs_output[node_list]

    mean,low_percentile_series,median,high_percentile_series=__get_stats__(timesrs_processed,low_percentile,high_percentile)
    
    if save_outputs==True:
    # Saves Entire Results DataFrame as Filename_TimeSeries.csv in the same path
        timesrs_processed.to_csv(path[0:-4]+"_TimeSeries.csv")

        # Saves Mean Satisfaction with time as Filename_Means.csv in the same path
        mean.to_csv(path[0:-4]+"_Means.csv")

        # Saves Median Satisfaction with time as Filename_Medians.csv in the same path
        median.to_csv(path[0:-4]+"_Medians.csv")

        # Saves the specified low percentile (XX) values with time as Filename_XXthPercentile.csv in the same path
        low_percentile_series.to_csv(path[0:-4]+"_"+str(low_percentile)+"thPercentile.csv")

        # Saves the specified high percentile (YY) values with time as Filename_YYthPercentile.csv in the same path
        high_percentile_series.to_csv(path[0:-4]+"_"+str(high_percentile)+"thPercentile.csv")
    if plots:
        mpl.rcParams['figure.dpi'] = 450
        font = {'family' : 'Times',
                'weight' : 'bold',
                'size'   : 3}
        mpl.rc('font', **font)
        mpl.rc('xtick', labelsize=3)
        mpl.rcParams['axes.linewidth'] = 0.5

        # Prepping an xaxis with hr format
        supply_duration_hr=supply_duration/60
        xaxis=np.arange(0,supply_duration_hr+0.00001,1/60)

        fig,ax=__plot_mean__(xaxis,mean,output,'#91bfdb',high_percentile_series)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show
    
        fig,ax=__plot_mean__(xaxis,mean,output,'#91bfdb',high_percentile_series)
        plt.fill_between(xaxis, y1=low_percentile_series, y2=high_percentile_series, alpha=0.4, color='#91bfdb', edgecolor=None)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show 
    return timesrs_processed,mean,low_percentile_series,high_percentile_series


def PDA(path:str,output:str='S',low_percentile:int=10,high_percentile:int=90,save_outputs:bool=True,time_execution:bool=False,n_iterations:int=100,plots=True):
    """
    Executes an IWS EPANET file that uses the flow-restricted method EPANET-PDA.

    Parameters
    -----------
    path (str): path to input file (relative, but will handle full absolute paths) 

    output (str): specify output to process. Default: Satisfaction Ratio. Other supported outputs include 'P' for Pressure  

    low_percentile (int): value for the low percentile statistic (default 10th percentile) representing disadvantaged consumers  

    high_percentile (int): value for the high percentile statistic (default 90th percentile) representing disadvantaged consumers  

    save_outputs: Save processed output and statistices (mean, median an percentiles) as CSV files. Default: True.  

    time_execution (Boolean): Optionally times the execution of the EPANET file. default= False  

    n_iterations (int): number of iterations for averaging execution time. Default=100  

    plots (bool): Display mean and range plots. default: True

    Returns: timesrs_processed, mean, low_percentile_series, high_percentile_series

    timesrs_processed: Pandas DataFrame of size TxN where T is the number of timesteps and N is the number of demand (non-zero) nodes 
    in the network. Contains the values for the selected output: Satisfaction Ratio (S) or Pressures (P) for each demand node at each time step  

    mean: Pandas Series of size Tx1 where T is the number of timesteps. Mean output values for each timestep  

    low_percentile_series: Pandas Series of size Tx1. The XXth percentile output values for each timestep. XX is determined by function input: low_percentile  

    high_percentile_series: Pandas Series of size Tx1. The YYth percentile output values for each timestep. YY is determined by function input: high_percentile
    """

    assert 0 < low_percentile <high_percentile, "Percentile must be between 0 and 100"
    assert 0 < high_percentile <100, "Percentile must be between 0 and 100"
    assert output in ['S','P'], "Specify Supported Output Type: S for Satisfaction or P for Pressures"
    assert n_iterations>0, "Specify a positive integer"

    name_only=path.split("/")[-1][0:-4]
    print("Selected File: ",name_only)

    demand_nodes=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)

    # Iterates over the junction list in the Network object
    for node in network.junctions():

        # For all nodes that have non-zero demands
        if node[1].base_demand != 0:
            # Record node ID (name) and its desired demand (base_demand) in CMS
            demand_nodes.append(node[1].name)
            desired_demands.append(node[1].base_demand)

    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)

    # run simulation
    sim = wntr.sim.EpanetSimulator(network)
    # store results of simulation
    results=sim.run_sim()

    if time_execution:
        __time_simulation__(path,n_iterations)

    timesrs_output=pd.DataFrame()
    if output=='S':
        for i in range(0,supply_duration+1):
            # Extract Node Pressures from Results
            timesrs_output=pd.concat([timesrs_output,results.node['demand'].loc[i*60,:]],axis=1)
        # Transpose DataFrame such that indices are time (sec) and Columns are each Node
        timesrs_output=timesrs_output.T
        # Filter DataFrame for Columns that contain Data for demand nodes only
        timesrs_output=timesrs_output[demand_nodes]
        # Calculates the total demand volume in the specified supply cycle
        desired_volumes=[]
        # Loop over each desired demand
        for demand in desired_demands:
            # Append the corresponding desired volume (cum) = demand (LPS) *60 sec/min * supply duration (min) / 1000 (L/cum)
            desired_volumes.append(float(demand)*60*float(supply_duration))
        # Combine demands (LPS) to their corresponding desired volume (cum)
        desired_volumes=dict(zip(demand_nodes,desired_volumes))
        # Initalized DataFrame for storing volumes received by each demand node as a timeseries
        timesrs_processed=pd.DataFrame(index=timesrs_output.index,columns=desired_volumes.keys())
        # Set Initial volume for all consumers at 0
        timesrs_processed.iloc[0,:]=0
        # Loop over consumers and time steps to add up volumes as a percentage of total desired volume (Satisfaction Ratio)
        for timestep in list(timesrs_processed.index)[1:]:
            for node in timesrs_processed.columns:
                # Cummulatively add the percent satisfaction ratio (SR) increased each time step
                ## SR at time t = SR at time t-1 + demand at time t-1 (cms) *60 seconds per time step/ Desired Demand Volume (cum)
                timesrs_processed.at[timestep,node]=timesrs_processed.at[timestep-60,node]+timesrs_output.at[timestep-60,node]*60/desired_volumes[node]*100
    elif output=='P':
        for i in range(0,supply_duration+1):
            # Extract Node Pressures from Results
            timesrs_output=pd.concat([timesrs_output,results.node['pressure'].loc[i*60,:]],axis=1)
        # Transpose DataFrame such that indices are time (sec) and Columns are each Node
        timesrs_output=timesrs_output.T
        timesrs_processed=timesrs_output[demand_nodes]

    mean,low_percentile_series,median,high_percentile_series=__get_stats__(timesrs_processed,low_percentile,high_percentile)
    
    if save_outputs==True:
    # Saves Entire Results DataFrame as Filename_TimeSeries.csv in the same path
        timesrs_processed.to_csv(path[0:-4]+"_TimeSeries.csv")

        # Saves Mean Satisfaction with time as Filename_Means.csv in the same path
        mean.to_csv(path[0:-4]+"_Means.csv")

        # Saves Median Satisfaction with time as Filename_Medians.csv in the same path
        median.to_csv(path[0:-4]+"_Medians.csv")

        # Saves the specified low percentile (XX) values with time as Filename_XXthPercentile.csv in the same path
        low_percentile_series.to_csv(path[0:-4]+"_"+str(low_percentile)+"thPercentile.csv")

        # Saves the specified high percentile (YY) values with time as Filename_YYthPercentile.csv in the same path
        high_percentile_series.to_csv(path[0:-4]+"_"+str(high_percentile)+"thPercentile.csv")
    if plots:
        mpl.rcParams['figure.dpi'] = 450
        font = {'family' : 'Times',
                'weight' : 'bold',
                'size'   : 3}
        mpl.rc('font', **font)
        mpl.rc('xtick', labelsize=3)
        mpl.rcParams['axes.linewidth'] = 0.5

        # Prepping an xaxis with hr format
        supply_duration_hr=supply_duration/60
        xaxis=np.arange(0,supply_duration_hr+0.00001,1/60)

        fig,ax=__plot_mean__(xaxis,mean,output,'#4575b4',high_percentile_series)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show
    
        fig,ax=__plot_mean__(xaxis,mean,output,'#4575b4',high_percentile_series)
        plt.fill_between(xaxis, y1=low_percentile_series, y2=high_percentile_series, alpha=0.4, color='#4575b4', edgecolor=None)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show
    return timesrs_processed,mean,low_percentile_series,high_percentile_series


def OutletOutfall(path:str,ran_before:bool,output:str='S',low_percentile:int=10,high_percentile:int=90,save_outputs:bool=True,plots=True):
    """
    Executes an IWS EPA-SWMM file that uses the flow-restricted method Outlet-Outfall.

    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    output (str): specify output to process. Default: Satisfaction Ratio. Other supported outputs include 'P' for Pressure  

    ran_before (bool): Set to True to skip executing the SWMM .inp file IF you executed the .inp file before (uses the saved .out file instead)  

    low_percentile (int): value for the low percentile statistic (default 10th percentile) representing disadvantaged consumers  

    high_percentile (int): value for the high percentile statistic (default 90th percentile) representing disadvantaged consumers  

    save_outputs: Save processed output and statistices (mean, median an percentiles) as CSV files. Default: True.  

    plots (bool): Display mean and range plots. default: True

    Returns: timesrs_processed, mean, low_percentile_series, high_percentile_series

    timesrs_processed: Pandas DataFrame of size TxN where T is the number of timesteps and N is the number of demand (non-zero) nodes 
    in the network. Contains the values for the selected output: Satisfaction Ratio (S) or Pressures (P) for each demand node at each time step  

    mean: Pandas Series of size Tx1 where T is the number of timesteps. Mean output values for each timestep  

    low_percentile_series: Pandas Series of size Tx1. The XXth percentile output values for each timestep. XX is determined by function input: low_percentile  

    high_percentile_series: Pandas Series of size Tx1. The YYth percentile output values for each timestep. YY is determined by function input: high_percentile
    """
    assert 0 < low_percentile <high_percentile, "Percentile must be between 0 and 100"
    assert 0 < high_percentile <100, "Percentile must be between 0 and 100"
    assert output in ['S','P'], "Specify Supported Output Type: S for Satisfaction or P for Pressures"

    simplefilter(action="ignore", category=pd.errors.PerformanceWarning)
    name_only=path.split('/')[-1][0:-4]
    print("Selected File: ",name_only)

    sim=pyswmm.Simulation(inputfile=path, outputfile=path[0:-4]+".out")

    links=pyswmm.links.Links(sim)   #object containing links in the network model
    demand_links=[]                 # Empty list for storing link ids
    demand_nodes=[]                 # Empty list for storing node ids
    for link in links:
        # if link starts with OUT then it's an outlet and store its id
        if re.search('^Outlet',link.linkid):
            demand_links.append(link.linkid)
            demand_nodes.append(link.linkid[6:])

    if ran_before==False:
        stp=0       #steps counter
        every=1000  #Interval of printing current time

        # runs the simulation step by step
        with sim as sim:
            for step in sim:
                if stp%every==0:
                    print('Current Simulation Time is >> ',sim.current_time)
                stp+=1
                pass

    timesrs_output=pd.DataFrame()  #Empty Dataframe to store demand rates
    swtch=True              # switch variable for upcoming condition

    if output=='S':
        # Reads the output file created above
        with pyswmm.Output(path[0:-4]+".out") as out:
            # loops through each link in output file
            for link in out.links:

                # One time only. Gets the timesteps (the keys in the output series dictionary) and stores them to be used as index
                if swtch:
                    # link_series produces a dictionary with the keys corresponding to timestamps and values contain the value of the selected variable (FLOW_RATE) at each timestamp
                    index=pd.Series(out.link_series(link,LinkAttribute.FLOW_RATE).keys())
                    timesrs_output.loc[:,"time"]=index
                    swtch=False
                # If link id is in the prepared list of demand links (outlets)
                if link in demand_links:
                    # gets the values of the flow rate series dictionary and stores as a Pandas Series
                    timesrs_output.loc[:,link]=out.link_series(link,LinkAttribute.FLOW_RATE).values()
    elif output=='P':
        # Reads the output file created above
        with pyswmm.Output(path[0:-4]+".out") as out:
            # loops through each link in output file
            for node in out.nodes:

                # One time only. Gets the timesteps (the keys in the output series dictionary) and stores them to be used as index
                if swtch:
                    # link_series produces a dictionary with the keys corresponding to timestamps and values contain the value of the selected variable (FLOW_RATE) at each timestamp
                    index=pd.Series(out.node_series(node,NodeAttribute.INVERT_DEPTH).keys())
                    timesrs_output.loc[:,"time"]=index
                    swtch=False
                # If link id is in the prepared list of demand links (outlets)
                if node in demand_nodes:
                    # gets the values of the flow rate series dictionary and stores as a Pandas Series
                    timesrs_output.loc[:,node]=out.node_series(node,NodeAttribute.INVERT_DEPTH).values()

    # Stores the start time stamp of the simulation
    start_time=index[0]
    # List to store index of time in seconds (0 added as the missing initial time step)
    new_index=[]

    # Loops through old index (datetime)
    for time in index:
        # Gets time difference in seconds
        timesec=(time-start_time).seconds
        # Appends time in seconds to new index
        new_index.append(timesec+10)

    timesrs_output["time"]=new_index
    timesrs_output.set_index("time",inplace=True)
    ### Formatting the DataFrame to add a zero row at the beginning (for the initial time step) and fix index and column names
    timesrs_output.loc[0,:]=0
    timesrs_output.sort_index(inplace=True)

    supply_duration=new_index[-1]/60
    reporting_step=new_index[1]-new_index[0]

    if output=='S':
        # Calculates the total demand volume in the specified supply cycle
        desired_volumes=[]
        demand_rates=pd.read_csv(path[0:-4]+"_Demands.csv")
        demand_rates.set_index("ID",inplace=True)

        # Loop over each desired demand
        for demand in demand_rates["Demand"]:
            # Append the corresponding desired volume (cum) = demand (LPS) *60 sec/min * supply duration (hr) / 1000 (L/cum)
            desired_volumes.append(float(demand)*60*float(supply_duration))

        # Combine demands (LPS) to their corresponding desired volume (cum)
        desired_volumes=dict(zip(demand_links,desired_volumes))

        # Initalized DataFrame for storing volumes received by each demand node as a timeseries
        timesrs_processed=pd.DataFrame(index=timesrs_output.index,columns=desired_volumes.keys())
        # Set Initial volume for all consumers at 0
        timesrs_processed.iloc[0,:]=0

        # Loop over consumers and time steps to add up volumes as a percentage of total desired volume (Satisfaction Ratio)
        for timestep in list(timesrs_processed.index)[1:]:
            for node in timesrs_processed.columns:
                # Cummulatively add the percent satisfaction ratio (SR) increased each time step
                ## SR at time t = SR at time t-1 + demand at time t-1 (cms) *60 seconds per time step/ Desired Demand Volume (cum)
                timesrs_processed.at[timestep,node]=timesrs_processed.at[timestep-reporting_step,node]+timesrs_output.at[timestep-reporting_step,node]*reporting_step/1000/desired_volumes[node]*100
    elif output=='P': timesrs_processed=timesrs_output

    mean,low_percentile_series,median,high_percentile_series=__get_stats__(timesrs_processed,low_percentile,high_percentile)
    
    if save_outputs==True:
    # Saves Entire Results DataFrame as Filename_TimeSeries.csv in the same path
        timesrs_processed.to_csv(path[0:-4]+"_TimeSeries.csv")

        # Saves Mean Satisfaction with time as Filename_Means.csv in the same path
        mean.to_csv(path[0:-4]+"_Means.csv")

        # Saves Median Satisfaction with time as Filename_Medians.csv in the same path
        median.to_csv(path[0:-4]+"_Medians.csv")

        # Saves the specified low percentile (XX) values with time as Filename_XXthPercentile.csv in the same path
        low_percentile_series.to_csv(path[0:-4]+"_"+str(low_percentile)+"thPercentile.csv")

        # Saves the specified high percentile (YY) values with time as Filename_YYthPercentile.csv in the same path
        high_percentile_series.to_csv(path[0:-4]+"_"+str(high_percentile)+"thPercentile.csv")
    
    if plots:
        mpl.rcParams['figure.dpi'] = 450
        font = {'family' : 'Times',
                'weight' : 'bold',
                'size'   : 3}
        mpl.rc('font', **font)
        mpl.rc('xtick', labelsize=3)
        mpl.rcParams['axes.linewidth'] = 0.5

        # Prepping an xaxis with hr format
        xaxis=list(timesrs_processed.index)
        xaxis=[x/3600 for x in xaxis]

        fig,ax=__plot_mean__(xaxis,mean,output,'#DE8D08',high_percentile_series)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show
    
        fig,ax=__plot_mean__(xaxis,mean,output,'#DE8D08',high_percentile_series)
        plt.fill_between(xaxis, y1=low_percentile_series, y2=high_percentile_series, alpha=0.4, color='#DE8D08', edgecolor=None)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show

    return timesrs_processed,mean,low_percentile_series,high_percentile_series


def OutletStorage(path:str,ran_before:bool,output:str='S',low_percentile:int=10,high_percentile:int=90,save_outputs:bool=True,plots=True):
    """

    Executes an IWS EPA-SWMM file that uses the volume-restricted method Outlet-Storage.


    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    output (str): specify output to process. Default: Satisfaction Ratio. Other supported outputs include 'P' for Pressure  
    
    ran_before (bool): Set to True to skip executing the SWMM .inp file IF you executed the .inp file before (uses the saved .out file instead)  
    
    low_percentile (int): value for the low percentile statistic (default 10th percentile) representing disadvantaged consumers  
    
    high_percentile (int): value for the high percentile statistic (default 90th percentile) representing disadvantaged consumers  
    
    save_outputs: Save processed output and statistices (mean, median an percentiles) as CSV files. Default: True.  
    
    plots (bool): Display mean and range plots. default: True


    Returns: timesrs_processed, mean, low_percentile_series, high_percentile_series

    timesrs_processed: Pandas DataFrame of size TxN where T is the number of timesteps and N is the number of demand (non-zero) nodes 
    in the network. Contains the values for the selected output: Satisfaction Ratio (S) or Pressures (P) for each demand node at each time step

    mean: Pandas Series of size Tx1 where T is the number of timesteps. Mean output values for each timestep

    low_percentile_series: Pandas Series of size Tx1. The XXth percentile output values for each timestep. XX is determined by function input: low_percentile

    high_percentile_series: Pandas Series of size Tx1. The YYth percentile output values for each timestep. YY is determined by function input: high_percentile
    """
    assert 0 < low_percentile <high_percentile, "Percentile must be between 0 and 100"
    assert 0 < high_percentile <100, "Percentile must be between 0 and 100"
    assert output in ['S','P'], "Specify Supported Output Type: S for Satisfaction or P for Pressures"

    simplefilter(action="ignore", category=pd.errors.PerformanceWarning)
    name_only=path.split('/')[-1][0:-4]
    print("Selected File: ",name_only)

    sim=pyswmm.Simulation(inputfile=path, outputfile=path[0:-4]+".out")

    nodes=pyswmm.nodes.Nodes(sim)
    tankids=[]
    for node in nodes:
        if re.search('StorageforNode',node.nodeid):
            tankids.append(node.nodeid)
    demand_node_ids=[x[14:] for x in tankids]

    if ran_before==False:
        stp=0       #steps counter
        every=1000  #Interval of printing current time

        # runs the simulation step by step
        with sim as sim:
            for step in sim:
                if stp%every==0:
                    print('Current Simulation Time is >> ',sim.current_time)
                stp+=1
                pass

    Tank_Depths=pd.DataFrame()   #Empty Dataframe to store water depth in tanks
    Node_Depths=pd.DataFrame()   #Empty Dataframe to store water depth in nodes
    swtch=True                   # switch variable for upcoming condition

    # Reads the output file created above
    with pyswmm.Output(path[0:-4]+".out") as out:
        # loops through each node in output file
        for node in out.nodes:

            # One time only. Gets the timesteps (the keys in the output series dictionary) and stores them to be used as index
            if swtch:
            # node_series produces a dictionary with the keys corresponding to timestamps and values contain the value of the selected variable (FLOW_RATE) at each timestamp
                index=pd.Series(out.node_series(node,NodeAttribute.INVERT_DEPTH).keys())
                Tank_Depths.loc[:,"time"]=index
                swtch=False
            
            # If node id is in the prepared list of demand nodes (tanks)
            if node in tankids:
                Tank_Depths.loc[:,node]=pd.Series(out.node_series(node,NodeAttribute.INVERT_DEPTH).values())  
            elif node in demand_node_ids:
                Node_Depths.loc[:,node]=pd.Series(out.node_series(node,NodeAttribute.INVERT_DEPTH).values())

    # Stores the start time stamp of the simulation
    start_time=index[0]
    # List to store index of time in seconds (0 added as the missing initial time step)
    new_index=[]

    # Loops through old index (datetime)
    for time in index:
        # Gets time difference in seconds
        timesec=(time-start_time).seconds
        # Appends time in seconds to new index
        new_index.append(timesec+10)

    Tank_Depths["time"]=new_index
    Tank_Depths.set_index("time",inplace=True)
    Tank_Depths[Tank_Depths>1]=1

    Node_Depths["time"]=new_index
    Node_Depths.set_index("time",inplace=True)

    ### Formatting the DataFrame to add a zero row at the beginning (for the initial time step) and fix index and column names
    Tank_Depths.loc[0,:]=0
    Tank_Depths.sort_index(inplace=True)

    Node_Depths.loc[0,:]=0
    Node_Depths.sort_index(inplace=True)
    Node_Depths.columns=Tank_Depths.columns

    # Calculates supply duration in minutes from the last entry in the new index (seconds)
    supply_duration=new_index[-1]/60
    reporting_step=new_index[1]-new_index[0]

    if output=='S':
        timesrs_processed=Tank_Depths*100
    elif output=='P':
        timesrs_processed=Node_Depths

    mean,low_percentile_series,median,high_percentile_series=__get_stats__(timesrs_processed,low_percentile,high_percentile)
    
    if save_outputs==True:
    # Saves Entire Results DataFrame as Filename_TimeSeries.csv in the same path
        timesrs_processed.to_csv(path[0:-4]+"_TimeSeries.csv")

        # Saves Mean Satisfaction with time as Filename_Means.csv in the same path
        mean.to_csv(path[0:-4]+"_Means.csv")

        # Saves Median Satisfaction with time as Filename_Medians.csv in the same path
        median.to_csv(path[0:-4]+"_Medians.csv")

        # Saves the specified low percentile (XX) values with time as Filename_XXthPercentile.csv in the same path
        low_percentile_series.to_csv(path[0:-4]+"_"+str(low_percentile)+"thPercentile.csv")

        # Saves the specified high percentile (YY) values with time as Filename_YYthPercentile.csv in the same path
        high_percentile_series.to_csv(path[0:-4]+"_"+str(high_percentile)+"thPercentile.csv")
    
    if plots:
        mpl.rcParams['figure.dpi'] = 450
        font = {'family' : 'Times',
                'weight' : 'bold',
                'size'   : 3}
        mpl.rc('font', **font)
        mpl.rc('xtick', labelsize=3)
        mpl.rcParams['axes.linewidth'] = 0.5

        # Prepping an xaxis with hr format
        xaxis=list(timesrs_processed.index)
        xaxis=[x/3600 for x in xaxis]

        fig,ax=__plot_mean__(xaxis,mean,output,'#383371',high_percentile_series)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show
    
        fig,ax=__plot_mean__(xaxis,mean,output,'#383371',high_percentile_series)
        plt.fill_between(xaxis, y1=low_percentile_series, y2=high_percentile_series, alpha=0.4, color='#383371', edgecolor=None)
        plt.xlabel('Supply Time (hr)')
        if output=='S':
            plt.ylabel('Satisfaction Ratio (%)')
        elif output=='P':
            plt.ylabel('Nodal Pressure (m)')
        plt.show

    return timesrs_processed,mean,low_percentile_series,high_percentile_series
    

def __time_simulation__(abs_path:str,n_iterations:int):
    """
    Times the execution of an EPANET file for a given number of iterations

    abs_path (str): input file path
    n_iterations (int): number of iterations to time execution
    """
    # Statement to be timed: read filename, create network model, run network simulation
    timed_lines='inp_file='+"'"+abs_path+"'"
    timed_lines=timed_lines+'''
    wn = wntr.network.WaterNetworkModel(inp_file) 
    wntr.sim.EpanetSimulator(wn)
    '''

    # Time and average over number of iterations
    time=np.round(timeit.timeit(stmt=timed_lines,setup='import wntr',number=n_iterations)/n_iterations*1000,decimals=2)
    print("Time taken for ",file,' is ', time, 'milliseconds per run')


def __plot_mean__(xaxis,mean,output,color,high_p):
    fig, ax=plt.subplots()
    # Change figure size (and aspect ratio) by adjusting height and width here
    fig.set_figwidth(1.5)
    fig.set_figheight(1)
    if output=='S':
        ax.set_title('Average Demand Satisfaction with Time')
    elif output=='P':
        ax.set_title('Average Pressure with Time')
    ax.set_xlim(0,max(xaxis))
    ax.set_ylim(0,max(high_p))
    ax.set_xticks(np.arange(0,max(xaxis)+1,4))
    ax.set_xticks(np.arange(0,max(xaxis)+1,1),minor=True)
    ax.set_yticks(np.arange(0,max(high_p)+1,10))
    ax.tick_params(width=0.5)
    # Data to be plotted: Mean as a percentage 
    # Change color by changing the string next to c= and linewidth by value
    line1,=ax.plot(xaxis,mean, c=color,linewidth=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    return fig, ax


def __get_stats__(timesrs,low_percentile,high_percentile):
    # Intialize Series for storing statistics
    mean=pd.Series(dtype='float64')
    median=pd.Series(dtype='float64')
    low_percentile_series=pd.Series(dtype='float64')
    high_percentile_series=pd.Series(dtype='float64')

    # Loop over each row (time step) in the results and calculate values of mean, median, low and high percentiles
    for row in timesrs.index:
        mean.loc[row]=np.mean(timesrs.loc[row,:])
        low_percentile_series.loc[row]=np.percentile(timesrs.loc[row,:],low_percentile)
        median.loc[row]=np.percentile(timesrs.loc[row,:],50)
        high_percentile_series.loc[row]=np.percentile(timesrs.loc[row,:],high_percentile)
    
    return mean,low_percentile_series,median,high_percentile_series