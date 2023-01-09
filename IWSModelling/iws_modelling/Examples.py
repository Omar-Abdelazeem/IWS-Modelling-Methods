import iws_modelling as iws

# Change this path based on your working directory. Choose the file "Network1.inp" in the resources folder or an EPANET input file of your choosing
path='resources/Network1.inp'

# Changes the supply duration of the chosen file to 8 hours and 0 minutes and scales the demands accordingly
# path=iws.change_duration(path,8,0)
# # returns the path of the 8hr supply file back into path

# #Convert this file into an IWS file that uses the CV-Tank method assuming a minimum pressure of 0 m and a desired pressure of 10 m
# path=iws.to_Outlet_Storage(path,0,10,20)
# print(path)
# #Returns the path of the converted input file

# #Execute the file we just produced
# timeseries,mean,low,high=iws.OutletStorage(path,True)

# these lines can also be chained like:
timeseries,mean,low,hugh=iws.OutletStorage(iws.to_Outlet_Storage(iws.change_duration(path,8,00),0,10,20),True)