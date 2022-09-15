### RUNNING A SIMPLE TANK METHOD SIMULATION YES THANK YOU WHAT DID YOU LEARN
import wntr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import timeit

net_list=['N3a_SimpleTank_4hr.inp']

timess=pd.DataFrame(index=net_list,columns=['Time (ms)'])
plots=list()
skp_plots=False
niter=100
fullsrs=[]
totals=pd.DataFrame(columns=net_list)
rsvrs=['269','270','271','272']
fulldemand=21525.70518
tenth=pd.DataFrame()
Median=pd.DataFrame()
ninety=pd.DataFrame()
mean=pd.DataFrame()



for net in net_list:
    
    inp_file='/Users/omaraliamer/Desktop/UofT/Papers/Clean Network Files/SWMM/Final Files/'+net
    wn = wntr.network.WaterNetworkModel(inp_file)
    
    # wntr.graphics.plot_network(wn, title='Network')
    
    stmt="inp_file='/Users/omaraliamer/Desktop/UofT/Papers/Clean Network Files/SWMM/Final Files/"
    stmt=stmt+net+"'"
    stmt=stmt+'''
wn = wntr.network.WaterNetworkModel(inp_file) 
wntr.sim.EpanetSimulator(wn)
    '''
    timess['Time (ms)'][net]=np.round(timeit.timeit(stmt=stmt,setup='import wntr',number=niter)/niter*1000,decimals=2)
    print('Time taken for ',net,' is ',timess['Time (ms)'][net],' milliseconds per run')
    
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()
    values=[]
    timesrs=pd.DataFrame()
    
    for i in range(0,241):
        tit='Head at ' + str(i) + ' hours'
        values.append(results.node['pressure'].loc[i*60, :])
        timesrs[str(i)]=values[i]
        timesrsT=timesrs.T
        timesrsT=timesrsT.filter(regex='Tank\D+',axis=1)
        columns=list(timesrsT.columns)
        
    for row in timesrsT.index:
        trgt=timesrsT.loc[row,:]
        tenth.loc[row,net]=np.percentile(trgt,10)*100
        Median.loc[row,net]=np.percentile(trgt,50)*100
        ninety.loc[row,net]=np.percentile(trgt,90)*100 
        mean.loc[row,net]=np.nanmean(trgt)*100
        
    timesrsT['Total']=timesrsT.sum(axis=1)/245
    totals[net]=timesrsT["Total"]*100
timesrsT.to_csv('/Users/omaraliamer/Desktop/UofT/Papers/Clean Network Files/SWMM/Final Files/STMIndvd3_4hr.csv')
totals.to_csv('/Users/omaraliamer/Desktop/UofT/Papers/Clean Network Files/SWMM/Final Files/STMResults3_4hr.csv')
tenth.to_csv('/Users/omaraliamer/Desktop/UofT/Papers/Clean Network Files/SWMM/Final Files/STM10th3_4hr.csv')
Median.to_csv('/Users/omaraliamer/Desktop/UofT/Papers/Clean Network Files/SWMM/Final Files/STM50th3_4hr.csv')
ninety.to_csv('/Users/omaraliamer/Desktop/UofT/Papers/Clean Network Files/SWMM/Final Files/STM90th3_4hr.csv')
mean.to_csv('/Users/omaraliamer/Desktop/UofT/Papers/Clean Network Files/SWMM/Final Files/STMmean3_4hr.csv')


# xaxis=np.arange(0,14.0001,1/60)
# fig, ax=plt.subplots()
# ax.set_title('10th, 50th & 90th Percentile Users')
# ax.set_xlim(0, 12)
# ax.set_ylim(0, 100)
# ax.set_xticks(np.arange(0, 13, 4))
# ax.set_xticks(np.arange(0, 13, 1), minor=True)
# ax.set_yticks(np.arange(0, 101, 25))
# # ax.set_aspect(.04)
# line1, =ax.plot(xaxis,Median['N2a_SimpleTank.inp'], c='tab:blue', label='Normal')
# line2, =ax.plot(xaxis,tenth['N2a_SimpleTank.inp'],c='tab:blue',linestyle='--')
# line3, =ax.plot(xaxis,ninety['N2a_SimpleTank.inp'],c='tab:blue',linestyle='--')
# # line4, =ax.plot(xaxis,Median['N2a_SimpleTank_75%P.inp'], c='orange', label='75% Pressure')
# # line5, =ax.plot(xaxis,tenth['N2a_SimpleTank_75%P.inp'],c='orange',linestyle='--')
# # line6, =ax.plot(xaxis,ninety['N2a_SimpleTank_75%P.inp'],c='orange',linestyle='--')
# line7, =ax.plot(xaxis,Median['N2a_SimpleTank_50%P.inp'], c='tab:orange', label='50% Pressure')
# line8, =ax.plot(xaxis,tenth['N2a_SimpleTank_50%P.inp'],c='tab:orange',linestyle='--')
# line9, =ax.plot(xaxis,ninety['N2a_SimpleTank_50%P.inp'],c='tab:orange',linestyle='--')
# # line10, =ax.plot(xaxis,Median['N2a_SimpleTank_25%P.inp'], c='tab:green', label='25% Pressure')
# # line11, =ax.plot(xaxis,tenth['N2a_SimpleTank_25%P.inp'],c='tab:green',linestyle='--')
# # line12, =ax.plot(xaxis,ninety['N2a_SimpleTank_25%P.inp'],c='tab:green',linestyle='--')
# ax.grid(b=True,which='both')
# ax.spines['top'].set_visible(False)
# ax.spines['right'].set_visible(False)
# plt.ylabel('% Volume Satisfied')
# plt.xlabel('Time (hr)')
# # ax.legend(handles=[line1,line7,line10],loc='lower right')
# plt.savefig('/Users/omaraliamer/Desktop/UofT/Papers/Clean Network Files/SWMM/Final Files/Percentile Users STM Net 3.png',dpi=300)
# plt.show() 

# fig, ax= plt.subplots()
# for net in net_list:
#   lower=np.array(abs(tenth[net]-Median[net]))
#   upper=np.array(abs(ninety[net]-Median[net]))
#   yerror=np.vstack((lower,upper))  
#   plt.errorbar(xaxis, Median[net], yerr=yerror,elinewidth=1,capsize=5,errorevery=60)
# plt.savefig('%Percentiles Satisfied STM.png',dpi=300)
