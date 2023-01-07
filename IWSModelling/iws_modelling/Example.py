from Convert_Method import change_duration
from Run_Method import *
import Run_Method
import pandas as pd

pd.DataFrame()

dir='../Network-Files/Network 3/'
file='Network3_4hr_Outlet-Storage.inp'
timesrs,mean,low,high =OutletStorage(dir,file,True,output='P')
