global wntr,np,pd,re,math

import wntr
import numpy as np 
import pandas as pd
import re
import math 


def to_CVTank(path:str,Hmin:float,Hdes:float):
    """
    Converts an EPANET Input file to an EPANET input file that uses the volume-restricted method CV-Tank

    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    Hmin (float): Value of the minimum pressure Hmin used for Pressure-Dependent Analysis (PDA)  

    Hdes (float): Value of the desired pressure Hmin used for Pressure-Dependent Analysis (PDA)


    Returns: path of produced file. Saves produced file in same directory as input file
    """

    assert 0<=Hmin<=Hdes, "Hmin must be smaller than Hdes"

    file=path.split("/")[-1]
    name_only=file[0:-4]
    if len(path.split("/"))>1:
        dir=path.rsplit("/",1)[0]+"/"
    else:dir=""
    print("Selected File: ",name_only)
    pressure_diff=Hdes-Hmin 

    demand_nodes=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations
    elevations=[]         # For storing elevations of demand nodes
    xcoordinates=[]       # For storing x coordinates of demand nodes
    ycoordinates=[]       # For storing y coordinates of demand nodes
    all_nodes=[]          # For storing list of node ids of all nodes
    all_elevations=[]     # For storing elevations of all nodes
    ## MAYBE SAVE ALL NODE IDS IN DATAFRAME WITH ELEVATION AND BASE DEMAND AND THEN FILTER DATA FRAME LATER FOR DEMAND NODES ONLY

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)
    assert network.options.hydraulic.demand_model=='PDA', "Please use EPANET or edit the inp file to set demand model as PDA"
    # Iterates over the junction list in the Network object
    for node in network.junctions():
        all_nodes.append(node[1].name)
        all_elevations.append(node[1].elevation)
        # For all nodes that have non-zero demands
        if node[1].base_demand != 0:
            # Record node ID (name), desired demand (base_demand) in CMS, elevations, x and y coordinates
            demand_nodes.append(node[1].name)
            desired_demands.append(node[1].base_demand)
            elevations.append(node[1].elevation)
            xcoordinates.append(node[1].coordinates[0])
            ycoordinates.append(node[1].coordinates[1])


    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)

    # Adds the phrase TankforNode to each node id and stores it as a tank id
    tankids=['TankforNode'+str(id) for id in demand_nodes] 
    # Calculate desired demand volumes and then calculates the diameters of the simple tanks
    volumes=[demand* 60 * supply_duration for demand in desired_demands]
    diameters_tanks=[round(np.sqrt(volume * 4 / np.pi),4) for volume in volumes]
    # List of zeros for each tank to be used as the values for Initial Level, Minimum Level, and Minimum Volume 
    zeros=[0.0000] *len(tankids)
    # Sets Maximum levels for all tanks as 1
    MaxLevel=[1.0000]*len(tankids)
    # No Volume curve is assigned to any of the tanks
    VolCurve=['    ']*len(tankids)
    # Semicolons to end each tank line
    semicolons=[';']*len(tankids)
    # Assemble all lists into a dataframe where each row is the definition for one simple tank
    tanks_section=pd.DataFrame(list(zip(tankids,elevations,zeros,zeros,MaxLevel,diameters_tanks,zeros,VolCurve,semicolons)))
    # Exports the tank section as a list of strings where each entry is a line of the tanks section
    tanks_section=tanks_section.to_string(header=False,index=False,col_space=10).splitlines()
    
    # Adds the phrase PipeforNode to each node id and stores it as a pipe id
    pipeids=['PipeforNode'+str(id) for id in demand_nodes]
    # Calculates the length of each pipe to simulate the head-flow relationship
    lengths=[round(pressure_diff*130**1.852*0.05**4.87/10.67/(demand)**1.852 , 4) for demand in desired_demands]
    # Sets all diameters to 1 m (1000 mm)
    diameters_pipes=[50]*len(pipeids)
    # Sets all Hazen-Williams Coefficients as 130
    hazen=[130]*len(pipeids)
    # Sets all created pipes to work as Check Valved to prevent backflow
    status=['CV']*len(pipeids)
    # Assemble all lists into a dataframe where each row is the definition for one simple tank
    pipes_addendum=pd.DataFrame(list(zip(pipeids,demand_nodes,tankids,lengths,diameters_pipes,hazen,zeros,status,semicolons)))
    # Exports the pipe section as a list of strings where each entry is a line of the pipes section
    pipes_addendum=pipes_addendum.to_string(header=False,index=False,col_space=10).splitlines()

    # Translates the tanks by a 100 m in both axes 
    xcoordinates=[x+2 for x in xcoordinates]
    ycoordinates=[y+2 for y in ycoordinates]

    # Assemble all lists into a dataframe where each row is the coordinates for one simple tank
    coordinates_add=pd.DataFrame(list(zip(tankids,xcoordinates,ycoordinates)))
    # Exports the coordinate section as a list of strings where each entry is a line of the coordinates section
    coordinates_add=coordinates_add.to_string(header=False,index=False,col_space=10).splitlines()
    
    # List of zero base demands for all nodes
    zerodemands=[0]*len(all_nodes)
    # White space indicating no patterns
    pattern=['     ']*len(all_nodes)
    semicolons=[';']*len(all_nodes)
    nodes=pd.DataFrame(list(zip(all_nodes,all_elevations,zerodemands,pattern,semicolons)))
    nodes=nodes.to_string(header=False,index=False).splitlines()

    # opens .inp file to read
    file=open(path,'r')
    lines=[]            # list to store all lines in the .inp file
    linecount=0         # Counter for the number of lines
    junctions_marker=0  # To store the line number at which the junctions section starts
    tanks_marker=0      # To store the line number at which the tanks section starts
    pipes_marker=0      # To store the line number at which the pumps section starts
    coords_marker=0     # To store the line number at which the vertices section starts
    demand_model=0  # To detect demand model line

    # Loops over each line in the input file 
    for line in file:
        # Record the position of the phrase [JUNCTIONS] and add 2 to skip the header line
        if re.search('\[JUNCTIONS\]',line):
            junctions_marker=linecount+2
        # Record the position of the phrase [TANKS] and add 2 to skip the header line
        if re.search('\[TANKS\]',line):
            tanks_marker=linecount+2
        # Record the position of the phrase [PUMPS] and subtract 1 to add pipes to the end of the pipe section
        if re.search('\[PUMPS\]',line):
            pipes_marker=linecount-1
        # Record the position of the phrase [Vertices] and subtract 1 to add Tank cooridnates to the end of the coordinates section
        if re.search('\[VERTICES\]',line):
            coords_marker=linecount-1
        if re.search('Demand Model',line):
            demand_model=linecount
        linecount+=1
        # Store all lines in a list
        lines.append(line)
    file.close()

    # Translate the pipes marker by the length of the tank section that will be added before it (as it will displace all subsequent lines)
    pipes_marker+=len(tanks_section)
    # Translate the coordinates marker by the length of the added tanks and pipes
    coords_marker+=len(tanks_section)+len(pipes_addendum)

    # Inserts the created sections in their appropriate location in the list of lines
    if demand_model:
        lines[demand_model+1]=" Minimum Pressure   "+str(Hmin)
        lines[demand_model+2]=" Required Pressure  "+str(Hdes)
        demand_model+=len(pipes_addendum)+len(tanks_section)

    lines[junctions_marker:junctions_marker+len(nodes)]=nodes
    lines[tanks_marker:tanks_marker]=tanks_section
    lines[pipes_marker:pipes_marker]=pipes_addendum
    lines[coords_marker:coords_marker]=coordinates_add

    # Opens a new file in the same directory to write the modified network .inp file in
    new_file_name=dir+name_only+'_CV-Tank.inp'
    file=open(new_file_name,'w')
    c=0     #line counter

    # All lines added by this script are missing a new line character at the end, the conditional statements below add the new line character for these lines only and writes all lines to the file
    for line in lines:
        if c>=junctions_marker and c<=junctions_marker+len(nodes):
            file.write(line+'\n')
        elif c>=tanks_marker and c<=tanks_marker+len(tanks_section):
            file.write(line+'\n')
        elif c>=pipes_marker and c<=pipes_marker+len(pipes_addendum):
            file.write(line+'\n')
        elif c>=coords_marker and c<=coords_marker+len(coordinates_add):
            file.write(line+'\n')
        elif c>=demand_model and c<=demand_model+2:
            file.write(line+'\n')
        else: file.write(line)    
        c+=1
    file.close()
    return new_file_name


def to_CVRes(path:str,Hmin:float,Hdes:float):
    """
    Converts an EPANET Input file to an EPANET input file that uses the unrestricted method CV-Reservoir (CV-Res)


    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    Hmin (float): Value of the minimum pressure Hmin used for Pressure-Dependent Analysis (PDA)  

    Hdes (float): Value of the desired pressure Hmin used for Pressure-Dependent Analysis (PDA)


    Returns: path of produced file. Saves produced file in same directory as input file
    """

    assert 0<=Hmin<=Hdes, "Hmin must be smaller than Hdes"

    file=path.split("/")[-1]
    name_only=file[0:-4]
    if len(path.split("/"))>1:
        dir=path.rsplit("/",1)[0]+"/"
    else:dir=""
    print("Selected File: ",name_only)
    pressure_diff=Hdes-Hmin 

    pressure_diff=Hdes-Hmin  
    demand_nodes=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations
    elevations=[]         # For storing elevations of demand nodes
    xcoordinates=[]       # For storing x coordinates of demand nodes
    ycoordinates=[]       # For storing y coordinates of demand nodes
    all_nodes=[]          # For storing list of node ids of all nodes
    all_elevations=[]     # For storing elevations of all nodes
    ## MAYBE SAVE ALL NODE IDS IN DATAFRAME WITH ELEVATION AND BASE DEMAND AND THEN FILTER DATA FRAME LATER FOR DEMAND NODES ONLY

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)
    assert network.options.hydraulic.demand_model=='PDA', "Please use EPANET to set demand model as PDA"

    # Iterates over the junction list in the Network object
    for node in network.junctions():
        all_nodes.append(node[1].name)
        all_elevations.append(node[1].elevation)
        # For all nodes that have non-zero demands
        if node[1].base_demand != 0:
            # Record node ID (name), desired demand (base_demand) in CMS, elevations, x and y coordinates
            demand_nodes.append(node[1].name)
            desired_demands.append(node[1].base_demand)
            elevations.append(node[1].elevation)
            xcoordinates.append(node[1].coordinates[0])
            ycoordinates.append(node[1].coordinates[1])



    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)
    # Adds "AR" to each demand node id to be used as ID for AR
    reservoirids=["AR"+str(id) for id in demand_nodes]
    # Calculates the elevation of the AR
    reservoir_elevs=[elevation + Hmin for elevation in elevations ]
    # No Patterns are assigned to any of the ARs
    reservoir_patterns=["    "]*len(reservoirids)
    # Semicolons to end each line
    semicolons=[";"]*len(reservoirids)
    # Dataframe with all the required fields for AR [ID   Elevation   Pattern   ;]
    added_reservoirs=pd.DataFrame(list(zip(reservoirids,reservoir_elevs,reservoir_patterns,semicolons)))
    # Exports the added reservoirs as a list of strings where each entry is a line of the reservoirs section
    added_reservoirs=added_reservoirs.to_string(header=False,index=False).splitlines()

    # Adds the phrase PipeforNode to each node id and stores it as a pipe id
    pipeids=['PipeforNode'+str(id) for id in demand_nodes]
    # Calculates the length of each pipe to simulate the head-flow relationship
    lengths=[round(pressure_diff*130**1.852*0.05**4.87/10.67/(demand)**1.852,4) for demand in desired_demands]
    # Sets all diameters to 1 m (1000 mm)
    diameters_pipes=[50]*len(pipeids)
    # Sets all Hazen-Williams Coefficients as 130
    hazen=[130]*len(pipeids)
    # Sets all created pipes to work as Check Valved to prevent backflow
    status=['CV']*len(pipeids)
    # sets all minor loss to 0
    minorloss=[0]*len(pipeids)
    # Assemble all lists into a dataframe where each row is the definition for one simple tank
    added_pipes=pd.DataFrame(list(zip(pipeids,demand_nodes,reservoirids,lengths,diameters_pipes,hazen,minorloss,status,semicolons)))
    # Exports the pipe section as a list of strings where each entry is a line of the pipes section
    added_pipes=added_pipes.to_string(header=False,index=False,col_space=10).splitlines()

    # Translates the tanks by a 100 m in both axes 
    xcoordinates=[x+2 for x in xcoordinates]
    ycoordinates=[y+2 for y in ycoordinates]

    # Assemble all lists into a dataframe where each row is the coordinates for one simple tank
    added_coordinates=pd.DataFrame(list(zip(reservoirids,xcoordinates,ycoordinates)))
    # Exports the coordinate section as a list of strings where each entry is a line of the coordinates section
    added_coordinates=added_coordinates.to_string(header=False,index=False,col_space=10).splitlines()

    # List of zero base demands for all nodes
    zerodemands=[0]*len(all_nodes)
    # White space indicating no patterns
    pattern=['     ']*len(all_nodes)
    semicolons=[';']*len(all_nodes)
    nodes=pd.DataFrame(list(zip(all_nodes,all_elevations,zerodemands,pattern,semicolons)))
    nodes=nodes.to_string(header=False,index=False).splitlines()

    # opens .inp file to read
    file=open(path,'r')
    lines=[]            # list to store all lines in the .inp file
    linecount=0         # Counter for the number of lines
    junctions_marker=0  # To store the line number at which the junctions section starts
    reservoirs_marker=0 # To store the line number at which the reservoir section ends
    pipes_marker=0      # To store the line number at which the pumps section starts
    coords_marker=0     # To store the line number at which the vertices section starts

    # Loops over each line in the input file 
    for line in file:
        # Record the position of the phrase [JUNCTIONS] and add 2 to skip the header line
        if re.search('\[JUNCTIONS\]',line):
            junctions_marker=linecount+2
        # Record the position of the phrase [TANKS] and subtract 1 for the end of the reservoirs section
        if re.search('\[TANKS\]',line):
            reservoirs_marker=linecount-1
        # Record the position of the phrase [PUMPS] and subtract 1 to add pipes to the end of the pipe section
        if re.search('\[PUMPS\]',line):
            pipes_marker=linecount-1
        # Record the position of the phrase [Vertices] and subtract 1 to add Tank cooridnates to the end of the coordinates section
        if re.search('\[VERTICES\]',line):
            coords_marker=linecount-1
        if re.search('Demand Model',line):
            demand_model=linecount
        linecount+=1
        # Store all lines in a list
        lines.append(line)
    file.close()

    # Translate the pipes marker by the length of the tank section that will be added before it (as it will displace all subsequent lines)
    pipes_marker+=len(added_reservoirs)
    # Translate the coordinates marker by the length of the added tanks and pipes
    coords_marker+=len(added_reservoirs)+len(added_pipes)

    # Inserts the created sections in their appropriate location in the list of lines
    if demand_model:
        lines[demand_model+1]=" Minimum Pressure   "+str(Hmin)
        lines[demand_model+2]=" Required Pressure  "+str(Hdes)
        demand_model+=len(added_reservoirs)+len(added_pipes)
    lines[junctions_marker:junctions_marker+len(nodes)]=nodes
    lines[reservoirs_marker:reservoirs_marker]=added_reservoirs
    lines[pipes_marker:pipes_marker]=added_pipes
    lines[coords_marker:coords_marker]=added_coordinates

    # Opens a new file in the same directory to write the modified network .inp file in
    new_file_name=dir+name_only+'_CV-Res.inp'
    file=open(new_file_name,'w')
    c=0     #line counter

    # All lines added by this script are missing a new line character at the end, the conditional statements below add the new line character for these lines only and writes all lines to the file
    for line in lines:
        if c>=junctions_marker and c<=junctions_marker+len(nodes):
            file.write(line+'\n')
        elif c>=reservoirs_marker and c<=reservoirs_marker+len(added_reservoirs):
            file.write(line+'\n')
        elif c>=pipes_marker and c<=pipes_marker+len(added_pipes):
            file.write(line+'\n')
        elif c>=coords_marker and c<=coords_marker+len(added_coordinates):
            file.write(line+'\n')
        elif c>=demand_model and c<=demand_model+2:
            file.write(line+'\n')
        else: file.write(line)    
        c+=1
    file.close()
    return new_file_name


def to_FCVEM(path:str,Hmin:float,Hdes:float):
    """
    Converts an EPANET Input file to an EPANET input file that uses the flow-restricted method FCV-Emitter (FCV-EM)

    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    Hmin (float): Value of the minimum pressure Hmin used for Pressure-Dependent Analysis (PDA)  

    Hdes (float): Value of the desired pressure Hmin used for Pressure-Dependent Analysis (PDA)


    Returns: path of produced file. Saves produced file in same directory as input file
    """

    assert 0<=Hmin<=Hdes, "Hmin must be smaller than Hdes"

    file=path.split("/")[-1]
    name_only=file[0:-4]
    if len(path.split("/"))>1:
        dir=path.rsplit("/",1)[0]+"/"
    else:dir=""    
    print("Selected File: ",name_only)
    pressure_diff=Hdes-Hmin 

    demand_nodes=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations
    elevations=[]         # For storing elevations of demand nodes
    xcoordinates=[]       # For storing x coordinates of demand nodes
    ycoordinates=[]       # For storing y coordinates of demand nodes
    all_nodes=[]          # For storing list of node ids of all nodes
    all_elevations=[]     # For storing elevations of all nodes
    ## MAYBE SAVE ALL NODE IDS IN DATAFRAME WITH ELEVATION AND BASE DEMAND AND THEN FILTER DATA FRAME LATER FOR DEMAND NODES ONLY

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)
    assert network.options.hydraulic.demand_model=='PDA', "Please use EPANET to set demand model as PDA"

    # Iterates over the junction list in the Network object
    for node in network.junctions():
        all_nodes.append(node[1].name)
        all_elevations.append(node[1].elevation)
        # For all nodes that have non-zero demands
        if node[1].base_demand != 0:
            # Record node ID (name), desired demand (base_demand) in CMS, elevations, x and y coordinates
            demand_nodes.append(node[1].name)
            desired_demands.append(node[1].base_demand)
            elevations.append(node[1].elevation)
            xcoordinates.append(node[1].coordinates[0])
            ycoordinates.append(node[1].coordinates[1])

    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)

    # Adds "EM" to each demand node id to be used as ID for the corresponding emitter
    emitterids=["EM"+str(id) for id in demand_nodes]
    # Calculates the emitter coefficients 
    emitter_coeffs=[demand*1000/np.sqrt(pressure_diff) for demand in desired_demands]
    # Semicolons to end each line
    semicolons=[";"]*len(emitterids)
    # Dataframe with all the required fields for Emitters [ID   Coefficient   ;]
    added_emitters=pd.DataFrame(list(zip(emitterids,emitter_coeffs,semicolons)))
    # Exports the added reservoirs as a list of strings where each entry is a line of the reservoirs section
    added_emitters=added_emitters.to_string(header=False,index=False).splitlines()

    # Adds the phrase "AN1forNode" to each node id as the id of the first artificial node (AN) added to each demand node
    anodeids=["ANforNode"+str(id) for id in demand_nodes]
    # Sets the base demand for all added nodes as 0
    base_demands=[0]*len(anodeids)
    # No demand pattern is assigned to any demand node
    demand_patterns=["     "]*len(anodeids)
    # Semicolons to end each line
    semicolons=[";"]*len(anodeids)
    # Dataframe with all the required fields for AN1 [ID   Elevation   Demand   Pattern   ;]
    added_nodes=pd.DataFrame(list(zip(anodeids,elevations,base_demands,demand_patterns,semicolons)))
    #DataFrame with the emitter nodes
    emitter_nodes=pd.DataFrame(list(zip(emitterids,elevations,base_demands,demand_patterns,semicolons)))
    # append emitter nodes to artificial nodes
    added_nodes=pd.concat([added_nodes,emitter_nodes])
    # Exports the added junctions as a list of strings where each entry is a line of the junctions section
    added_nodes=added_nodes.to_string(header=False,index=False,col_space=10).splitlines()

    # Adds the phrase PipeforNode to each node id and stores it as a pipe id
    pipeids=['Pipe1forNode'+str(id) for id in demand_nodes]
    # sets minor loss coefficients to zero
    minorloss=[0]*len(pipeids)
    # Sets all lengths to 0.1 m
    lengths=[0.1]*len(pipeids)
    # Sets all diameters to 1 m (1000 mm)
    diameters_pipes=[350]*len(pipeids)
    # Sets all Hazen-Williams Coefficients as 130
    hazen=[130]*len(pipeids)
    # Sets all created pipes to work as Check Valved to prevent backflow
    status=['CV']*len(pipeids)
    # list of semicolons
    semicolons=[";"]*len(pipeids)
    # Assemble all lists into a dataframe where each row is the definition for one simple reservoir
    # Data frame with all required fields [ID   Node1   Node2   Length   Diameter   Roughness   MinorLoss   Status   ;]
    added_pipes=pd.DataFrame(list(zip(pipeids,demand_nodes,anodeids,lengths,diameters_pipes,hazen,minorloss,status,semicolons)))
    # Exports the pipe section as a list of strings where each entry is a line of the pipes section
    added_pipes=added_pipes.to_string(header=False,index=False,col_space=10).splitlines()

    # Adds the phrase APSVforNode to each node id and stores it as a PSV valve id
    valveids=["FCVforNode"+str(id) for id in demand_nodes]
    # From nodes are the original demand nodes and to nodes are the artificial nodes
    # Sets all valve diameters to 12 (will not affect head loss across valve)
    valve_diameters=[12.0000]*len(valveids)
    # Sets the type of all valves to Flow-Control Valves
    valve_types=["FCV"]*len(valveids)
    # Sets the valve setting for each valve to the base demand of the original demand nodes (converts back to LPS)
    valve_settings=[demand*1000 for demand in desired_demands]
    # Sets the minor loss coefficient across the valve to 0
    valve_minor_loss=["0.0000"]*len(valveids)
    # Semicolons at the end of each line
    semicolons=[';']*len(valveids)
    # Data frame with all required fields [ID   Node1   Node2   Diameter   Type   Setting   MinorLoss   ;]
    added_valves=pd.DataFrame(list(zip(valveids,anodeids,emitterids,valve_diameters,valve_types,valve_settings,valve_minor_loss,semicolons)))
    added_valves=added_valves.to_string(header=False,index=False,col_space=10).splitlines()

    # Set preferred translation distance for [AN1,AN2,AT] where AN is Artificial Node and AT is the Artifical Tank
    x_direct_distance=[30,60]
    y_driect_distance=[-30,0]
    # Translates the reservoirs by a 100 m in both axes 
    anode_xcoord=[x+x_direct_distance[0] for x in xcoordinates]
    emitter_xcoord =[x+x_direct_distance[1] for x in xcoordinates]
    anode_ycoord=[y+y_driect_distance[0] for y in ycoordinates]
    emitter_ycoord =[y+y_driect_distance[1] for y in ycoordinates]

    added_xcoordinates=anode_xcoord+emitter_xcoord
    added_ycoordinates=anode_ycoord+emitter_ycoord
    ids_coords=anodeids+emitterids

    # Assemble all lists into a dataframe where each row is the coordinates for one artificial reservoir or node
    added_coordinates=pd.DataFrame(list(zip(ids_coords,added_xcoordinates,added_ycoordinates)))
    # Exports the coordinate section as a list of strings where each entry is a line of the coordinates section
    added_coordinates=added_coordinates.to_string(header=False,index=False,col_space=10).splitlines()

    # List of zero base demands for all nodes
    zerodemands=[0]*len(all_nodes)
    # White space indicating no patterns
    pattern=['     ']*len(all_nodes)
    semicolons=[';']*len(all_nodes)
    original_nodes=pd.DataFrame(list(zip(all_nodes,all_elevations,zerodemands,pattern,semicolons)))
    original_nodes=original_nodes.to_string(header=False,index=False,col_space=10).splitlines()

    # opens .inp file to read
    file=open(path,'r')
    lines=[]            # list to store all lines in the .inp file
    linecount=0         # Counter for the number of lines
    junctions_marker=0  # To store the line number at which the junctions section starts
    emitters_marker=0   # To store the line number at which the emitter section starts
    pipes_marker=0      # To store the line number at which the pumps section starts
    valves_marker=0     # to store the line number at which the valves section
    coords_marker=0     # To store the line number at which the vertices section starts
    exponent_line=0     # To store the line number of teh emitter exponent option

    # Loops over each line in the input file 
    for line in file:
        # Record the position of the phrase [JUNCTIONS] and add 2 to skip the header line
        if re.search('\[JUNCTIONS\]',line):
            junctions_marker=linecount+2
        # Record the position of the phrase [TANKS] and add 2 to skip the header line
        if re.search('\[EMITTERS\]',line):
            emitters_marker=linecount+2
        # Record the position of the phrase [PUMPS] and subtract 1 to add pipes to the end of the pipe section
        if re.search('\[PUMPS\]',line):
            pipes_marker=linecount-1
        # Record the position of the phrase [VALVES] and add 2 to skip the header line
        if re.search('\[VALVES\]',line):
            valves_marker=linecount+2
        # Record the position of the phrase [Vertices] and subtract 1 to add Tank cooridnates to the end of the coordinates section
        if re.search('\[VERTICES\]',line):
            coords_marker=linecount-1
        if re.search('Emitter Exponent',line):
            exponent_line=linecount
        if re.search('Demand Model',line):
            demand_model=linecount
        linecount+=1
        # Store all lines in a list
        lines.append(line)
    file.close()


    # Translate the pipes marker by the length of the added nodes that will be added before it (as it will displace all subsequent lines)
    pipes_marker+=len(added_nodes)
    # Translate the valves marker by the length of the added nodes, pipes
    valves_marker+=len(added_pipes)+len(added_nodes)
    # Translate the emitters marker by the length of the added nodes, pipes and valves
    emitters_marker+=len(added_valves)+len(added_pipes)+len(added_nodes)
    # Translate the coordinates marker by the length of the added tanks, pipes and valves
    coords_marker+=len(added_emitters)+len(added_pipes)+len(added_valves)+len(added_nodes)

    # Inserts the created sections in their appropriate location in the list of lines
    if demand_model:
        lines[demand_model+1]=" Minimum Pressure   "+str(Hmin)
        lines[demand_model+2]=" Required Pressure  "+str(Hdes)
        demand_model+=len(added_nodes)+len(added_pipes)+len(added_valves)+len(added_emitters)
    lines[exponent_line]="Emitter Exponent      0.5000\n"
    lines[junctions_marker:junctions_marker+len(original_nodes)]=original_nodes
    lines[junctions_marker+len(original_nodes):junctions_marker+len(original_nodes)]=added_nodes
    lines[pipes_marker:pipes_marker]=added_pipes
    lines[valves_marker:valves_marker]=added_valves
    lines[emitters_marker:emitters_marker]=added_emitters
    lines[coords_marker:coords_marker]=added_coordinates

    # Opens a new file in the same directory to write the modified network .inp file in
    new_file_name=dir+name_only+'_FCV-EM.inp'
    file=open(new_file_name,'w')
    c=0     #line counter

    # All lines added by this script are missing a new line character at the end, the conditional statements below add the new line character for these lines only and writes all lines to the file
    for line in lines:
        if c>=junctions_marker and c<=junctions_marker+len(original_nodes)+len(added_nodes):
            file.write(line+'\n')
        elif c>=emitters_marker and c<=emitters_marker+len(added_emitters):
            file.write(line+'\n')
        elif c>=pipes_marker and c<=pipes_marker+len(added_pipes):
            file.write(line+'\n')
        elif c>=valves_marker and c<=valves_marker+len(added_valves):
            file.write(line+'\n')
        elif c>=coords_marker and c<=coords_marker+len(added_coordinates):
            file.write(line+'\n')
        elif c>=demand_model and c<=demand_model+2:
            file.write(line+'\n')
        else: file.write(line)    
        c+=1
    file.close()
    return new_file_name


def to_FCVRes(path:str,Hmin:float,Hdes:float):
    """
    Converts an EPANET Input file to an EPANET input file that uses the flow-restricted method FCV-Reservoir (FCV-Res)

    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    Hmin (float): Value of the minimum pressure Hmin used for Pressure-Dependent Analysis (PDA)  

    Hdes (float): Value of the desired pressure Hmin used for Pressure-Dependent Analysis (PDA)


    Returns: path of produced file. Saves produced file in same directory as input file
    """

    assert 0<=Hmin<=Hdes, "Hmin must be smaller than Hdes"

    file=path.split("/")[-1]
    name_only=file[0:-4]
    if len(path.split("/"))>1:
        dir=path.rsplit("/",1)[0]+"/"
    else:dir=""    
    print("Selected File: ",name_only)
    pressure_diff=Hdes-Hmin 

    demand_nodes=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations
    elevations=[]         # For storing elevations of demand nodes
    xcoordinates=[]       # For storing x coordinates of demand nodes
    ycoordinates=[]       # For storing y coordinates of demand nodes
    all_nodes=[]          # For storing list of node ids of all nodes
    all_elevations=[]     # For storing elevations of all nodes

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)
    assert network.options.hydraulic.demand_model=='PDA', "Please use EPANET to set demand model as PDA"

    # Iterates over the junction list in the Network object
    for node in network.junctions():
        all_nodes.append(node[1].name)
        all_elevations.append(node[1].elevation)
        # For all nodes that have non-zero demands
        if node[1].base_demand != 0:
            # Record node ID (name), desired demand (base_demand) in CMS, elevations, x and y coordinates
            demand_nodes.append(node[1].name)
            desired_demands.append(node[1].base_demand)
            elevations.append(node[1].elevation)
            xcoordinates.append(node[1].coordinates[0])
            ycoordinates.append(node[1].coordinates[1])

    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)

    # Adds "AR" to each demand node id to be used as ID for AR
    reservoirids=["AR"+str(id) for id in demand_nodes]
    # Calculates the elevation of the AR
    reservoir_elevs=[elevation + Hmin for elevation in elevations ]
    # No Patterns are assigned to any of the ARs
    reservoir_patterns=["    "]*len(reservoirids)
    # Semicolons to end each line
    semicolons=[";"]*len(reservoirids)
    # Dataframe with all the required fields for AR [ID   Elevation   Pattern   ;]
    added_reservoirs=pd.DataFrame(list(zip(reservoirids,reservoir_elevs,reservoir_patterns,semicolons)))
    # Exports the added reservoirs as a list of strings where each entry is a line of the reservoirs section
    added_reservoirs=added_reservoirs.to_string(header=False,index=False).splitlines()

    # Adds the phrase "AN1forNode" to each node id as the id of the first artificial node (AN) added to each demand node
    anodeids=["ANforNode"+str(id) for id in demand_nodes]
    # Sets the base demand for all added nodes as 0
    base_demands=[0]*len(anodeids)
    # No demand pattern is assigned to any demand node
    demand_patterns=["     "]*len(anodeids)
    # Dataframe with all the required fields for AN1 [ID   Elevation   Demand   Pattern   ;]
    added_nodes=pd.DataFrame(list(zip(anodeids,elevations,base_demands,demand_patterns,semicolons)))
    # Exports the added junctions as a list of strings where each entry is a line of the junctions section
    added_nodes=added_nodes.to_string(header=False,index=False,col_space=10).splitlines()

    # Adds the phrase PipeforNode to each node id and stores it as a pipe id
    pipeids=['Pipe1forNode'+str(id) for id in demand_nodes]
    # Calculates the minor loss coefficient of each pipe to simulate the head-flow relationship
    minorloss=[pressure_diff*9.81*np.pi**2*0.35**4/(8*demand**2) for demand in desired_demands]
    # Sets all lengths to 0.1 m
    lengths=[0.1]*len(pipeids)
    # Sets all diameters to 1 m (1000 mm)
    diameters_pipes=[350]*len(pipeids)
    # Sets all Hazen-Williams Coefficients as 130
    hazen=[130]*len(pipeids)
    # Sets all created pipes to work as Check Valved to prevent backflow
    status=['CV']*len(pipeids)
    # list of semicolons
    semicolons=[";"]*len(pipeids)
    # Assemble all lists into a dataframe where each row is the definition for one simple reservoir
    # Data frame with all required fields [ID   Node1   Node2   Length   Diameter   Roughness   MinorLoss   Status   ;]
    added_pipes=pd.DataFrame(list(zip(pipeids,anodeids,reservoirids,lengths,diameters_pipes,hazen,minorloss,status,semicolons)))
    # Exports the pipe section as a list of strings where each entry is a line of the pipes section
    added_pipes=added_pipes.to_string(header=False,index=False,col_space=10).splitlines()

    # Adds the phrase APSVforNode to each node id and stores it as a PSV valve id
    valveids=["FCVforNode"+str(id) for id in demand_nodes]
    # From nodes are the original demand nodes and to nodes are the artificial nodes
    # Sets all valve diameters to 12 (will not affect head loss across valve)
    valve_diameters=[12.0000]*len(valveids)
    # Sets the type of all valves to Flow-Control Valves
    valve_types=["FCV"]*len(valveids)
    # Sets the valve setting for each valve to the base demand of the original demand nodes (converts back to LPS)
    valve_settings=[demand*1000 for demand in desired_demands]
    # Sets the minor loss coefficient across the valve to 0
    valve_minor_loss=["0.0000"]*len(valveids)
    # Semicolons at the end of each line
    semicolons=[';']*len(valveids)
    # Data frame with all required fields [ID   Node1   Node2   Diameter   Type   Setting   MinorLoss   ;]
    added_valves=pd.DataFrame(list(zip(valveids,demand_nodes,anodeids,valve_diameters,valve_types,valve_settings,valve_minor_loss,semicolons)))
    added_valves=added_valves.to_string(header=False,index=False,col_space=10).splitlines()

    # Set preferred translation distance for [AN1,AN2,AT] where AN is Artificial Node and AT is the Artifical Tank
    x_direct_distance=[-30,-60]
    y_driect_distance=[30,0]
    # Translates the reservoirs by a 100 m in both axes 
    anode_xcoord=[x+x_direct_distance[0] for x in xcoordinates]
    reservoir_xcoord =[x+x_direct_distance[1] for x in xcoordinates]
    anode_ycoord=[y+y_driect_distance[0] for y in ycoordinates]
    reservoir_ycoord =[y+y_driect_distance[1] for y in ycoordinates]

    added_xcoordinates=anode_xcoord+reservoir_xcoord
    added_ycoordinates=anode_ycoord+reservoir_ycoord
    ids_coords=anodeids+reservoirids

    # Assemble all lists into a dataframe where each row is the coordinates for one artificial reservoir or node
    added_coordinates=pd.DataFrame(list(zip(ids_coords,added_xcoordinates,added_ycoordinates)))
    # Exports the coordinate section as a list of strings where each entry is a line of the coordinates section
    added_coordinates=added_coordinates.to_string(header=False,index=False,col_space=10).splitlines()

    # List of zero base demands for all nodes
    zerodemands=[0]*len(all_nodes)
    # White space indicating no patterns
    pattern=['     ']*len(all_nodes)
    semicolons=[';']*len(all_nodes)
    original_nodes=pd.DataFrame(list(zip(all_nodes,all_elevations,zerodemands,pattern,semicolons)))
    original_nodes=original_nodes.to_string(header=False,index=False,col_space=10).splitlines()

    # opens .inp file to read
    file=open(path,'r')
    lines=[]            # list to store all lines in the .inp file
    linecount=0         # Counter for the number of lines
    junctions_marker=0  # To store the line number at which the junctions section starts
    reservoirs_marker=0 # To store the line number at which the reservoir section ends
    pipes_marker=0      # To store the line number at which the pumps section starts
    valves_marker=0     # to store the line number at which the valves section
    coords_marker=0     # To store the line number at which the vertices section starts

    # Loops over each line in the input file 
    for line in file:
        # Record the position of the phrase [JUNCTIONS] and add 2 to skip the header line
        if re.search('\[JUNCTIONS\]',line):
            junctions_marker=linecount+2
        # Record the position of the phrase [TANKS] and subtract 1 for the end of the reservoirs section
        if re.search('\[TANKS\]',line):
            reservoirs_marker=linecount-1
        # Record the position of the phrase [PUMPS] and subtract 1 to add pipes to the end of the pipe section
        if re.search('\[PUMPS\]',line):
            pipes_marker=linecount-1
        # Record the position of the phrase [VALVES] and add 2 to skip the header line
        if re.search('\[VALVES\]',line):
            valves_marker=linecount+2
        # Record the position of the phrase [Vertices] and subtract 1 to add Tank cooridnates to the end of the coordinates section
        if re.search('\[VERTICES\]',line):
            coords_marker=linecount-1
        if re.search('Demand Model',line):
            demand_model=linecount
        linecount+=1
        # Store all lines in a list
        lines.append(line)
    file.close()

    # Translate the reservoirs marker by the length of the added nodes (ANs) that will be added before it (as it will displace all subsequent lines)
    reservoirs_marker+=len(added_nodes)
    # Translate the pipes marker by the length of the reservoir section and the added nodesthat will be added before it (as it will displace all subsequent lines)
    pipes_marker+=len(added_reservoirs)+len(added_nodes)
    # Translate the coordinates marker by the length of the added reservoirs, pipes and nodes
    valves_marker+=len(added_reservoirs)+len(added_pipes)+len(added_nodes)
    # Translate the coordinates marker by the length of the added tanks, pipes, nodes and valves
    coords_marker+=len(added_reservoirs)+len(added_pipes)+len(added_valves)+len(added_nodes)

    # Inserts the created sections in their appropriate location in the list of lines
    if demand_model:
        lines[demand_model+1]=" Minimum Pressure   "+str(Hmin)
        lines[demand_model+2]=" Required Pressure  "+str(Hdes)
        demand_model+=len(added_nodes)+len(added_pipes)+len(added_valves)+len(added_reservoirs)
    lines[junctions_marker:junctions_marker+len(original_nodes)]=original_nodes
    lines[junctions_marker+len(original_nodes):junctions_marker+len(original_nodes)]=added_nodes
    lines[reservoirs_marker:reservoirs_marker]=added_reservoirs
    lines[pipes_marker:pipes_marker]=added_pipes
    lines[valves_marker:valves_marker]=added_valves
    lines[coords_marker:coords_marker]=added_coordinates

    # Opens a new file in the same directory to write the modified network .inp file in
    new_file_name=dir+name_only+'_FCV-Res.inp'
    file=open(new_file_name,'w')
    c=0     #line counter

    # All lines added by this script are missing a new line character at the end, the conditional statements below add the new line character for these lines only and writes all lines to the file
    for line in lines:
        if c>=junctions_marker and c<=junctions_marker+len(original_nodes)+len(added_nodes):
            file.write(line+'\n')
        elif c>=reservoirs_marker and c<=reservoirs_marker+len(added_reservoirs):
            file.write(line+'\n')
        elif c>=pipes_marker and c<=pipes_marker+len(added_pipes):
            file.write(line+'\n')
        elif c>=valves_marker and c<=valves_marker+len(added_valves):
            file.write(line+'\n')
        elif c>=coords_marker and c<=coords_marker+len(added_coordinates):
            file.write(line+'\n')
        elif c>=demand_model and c<=demand_model+2:
            file.write(line+'\n')
        else: file.write(line)    
        c+=1
    file.close()
    return new_file_name


def to_PSVTank(path:str,Hmin:float,Hdes:float):
    """
    Converts an EPANET Input file to an EPANET input file that uses the volume-restricted method PSV-Tank

    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    Hmin (float): Value of the minimum pressure Hmin used for Pressure-Dependent Analysis (PDA)  

    Hdes (float): Value of the desired pressure Hmin used for Pressure-Dependent Analysis (PDA)


    Returns: path of produced file. Saves produced file in same directory as input file
    """

    assert 0<=Hmin<=Hdes, "Hmin must be smaller than Hdes"

    file=path.split("/")[-1]
    name_only=file[0:-4]
    if len(path.split("/"))>1:
        dir=path.rsplit("/",1)[0]+"/"
    else:dir=""    
    print("Selected File: ",name_only)
    pressure_diff=Hdes-Hmin 

    demand_nodes=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations
    elevations=[]         # For storing elevations of demand nodes
    xcoordinates=[]       # For storing x coordinates of demand nodes
    ycoordinates=[]       # For storing y coordinates of demand nodes
    all_nodes=[]          # For storing list of node ids of all nodes
    all_elevations=[]     # For storing elevations of all nodes

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)
    assert network.options.hydraulic.demand_model=='PDA', "Please use EPANET to set demand model as PDA"

    # Iterates over the junction list in the Network object
    for node in network.junctions():
        all_nodes.append(node[1].name)
        all_elevations.append(node[1].elevation)
        # For all nodes that have non-zero demands
        if node[1].base_demand != 0:
            # Record node ID (name), desired demand (base_demand) in CMS, elevations, x and y coordinates
            demand_nodes.append(node[1].name)
            desired_demands.append(node[1].base_demand)
            elevations.append(node[1].elevation)
            xcoordinates.append(node[1].coordinates[0])
            ycoordinates.append(node[1].coordinates[1])

    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)

    # Adds the phrase TankforNode to each node id and stores it as a tank id
    tankids=['ATforNode'+str(id) for id in demand_nodes] 
    # Calculate desired demand volumes and then calculates the diameters of the simple tanks
    volumes=[demand* 60 * supply_duration for demand in desired_demands]
    diameters_tanks=[round(np.sqrt(volume * 4 / np.pi),4) for volume in volumes]
    # Calculates the elevations of the ATs as the elevation of their original demand node - 1 m
    tank_elevations=[elevation-1 for elevation in elevations]
    # List of zeros for each tank to be used as the values for Initial Level, Minimum Level, and Minimum Volume 
    zeros=[0.0000] *len(tankids)
    # Sets Maximum levels for all tanks as 1
    MaxLevel=[1.0000]*len(tankids)
    # No Volume curve is assigned to any of the tanks
    VolCurve=['    ']*len(tankids)
    # Semicolons to end each tank line
    semicolons=[';']*len(tankids)
    # Assemble all lists into a dataframe where each row is the definition for one simple tank
    # Required fields in EPANET .inp [ID   Elevation   InitLevel   MinLevel   MaxLevel    Diameter   MinVol    VolCurve   ;]
    tanks_section=pd.DataFrame(list(zip(tankids,tank_elevations,zeros,zeros,MaxLevel,diameters_tanks,zeros,VolCurve,semicolons)))
    # Exports the tank section as a list of strings where each entry is a line of the tanks section
    added_tanks=tanks_section.to_string(header=False,index=False,col_space=10).splitlines()

    # Adds the phrase "AN1forNode" to each node id as the id of the first artificial node (AN) added to each demand node
    node1ids=["AN1forNode"+str(id) for id in demand_nodes]
    # Adds the phrase "AN2forNode" to each node id as the id of the second artificial node (AN) added to each demand node
    node2ids=["AN2forNode"+str(id) for id in demand_nodes]
    # Sets the base demand for all added nodes as 0
    base_demands=[0]*len(node1ids)
    # No demand pattern is assigned to any demand node
    demand_patterns=["     "]*len(node1ids)
    # Dataframe with all the required fields for AN1 [ID   Elevation   Demand   Pattern   ;]
    nodes1=pd.DataFrame(list(zip(node1ids,elevations,base_demands,demand_patterns,semicolons)))
    # Dataframe with all the required fields for AN2 [ID   Elevation   Demand   Pattern   ;]
    nodes2=pd.DataFrame(list(zip(node2ids,elevations,base_demands,demand_patterns,semicolons)))
    # Joins both dataframes into one dataframe with all the added nodes
    added_nodes=pd.concat([nodes1,nodes2])
    # Exports the added junctions section as a list of strings where each entry is a line of the junctions section
    added_nodes=added_nodes.to_string(header=False,index=False,col_space=10).splitlines()

    # Adds the phrase PipeforNode to each node id and stores it as a pipe id
    pipeids=['Pipe1forNode'+str(id) for id in demand_nodes]
    length=len(pipeids)
    pipeids.extend(['Pipe2forNode'+str(id) for id in demand_nodes])
    # From nodes
    from_node=demand_nodes+node2ids
    # to nodes
    to_node=node1ids+tankids
    # Calculates the minor loss coefficient of each pipe to simulate the head-flow relationship
    minorloss=[round( pressure_diff*9.81*np.pi**2*0.35**4/(8*demand**2) , 4) for demand in desired_demands]
    minorloss.extend([0]*length)
    # Sets all lengths to 0.1 m
    lengths=[0.1]*len(pipeids)
    # Sets all diameters to 1 m (1000 mm)
    diameters_pipes=[350]*len(pipeids)
    # Sets all Hazen-Williams Coefficients as 130
    hazen=[130]*len(pipeids)
    # Sets all created pipes to work as Check Valved to prevent backflow
    status=['CV']*len(pipeids)
    # list of semicolons
    semicolons=[";"]*len(pipeids)
    # Assemble all lists into a dataframe where each row is the definition for one simple tank
    # Data frame with all required fields [ID   Node1   Node2   Length   Diameter   Roughness   MinorLoss   Status   ;]
    added_pipes=pd.DataFrame(list(zip(pipeids,from_node,to_node,lengths,diameters_pipes,hazen,minorloss,status,semicolons)))
    # Exports the pipe section as a list of strings where each entry is a line of the pipes section
    added_pipes=added_pipes.to_string(header=False,index=False,col_space=10).splitlines()

    # Adds the phrase APSVforNode to each node id and stores it as a PSV valve id
    valveids=["APSVforNode"+str(id) for id in demand_nodes]
    # From nodes are the first artificial nodes (node1ids) and to nodes are the second artificial nodes (node2ids)
    # Sets all valve diameters to 12 (will not affect head loss across valve)
    valve_diameters=[12.0000]*len(valveids)
    # Sets the type of all valves to Pressure-Sustaining Valves
    valve_types=["PSV"]*len(valveids)
    # Sets the valve setting (the pressure to sustain upstream of the valve in this case) to 0 (Atmospheric pressure to simulate a tank filling from the top)
    valve_settings=["0.0000"]*len(valveids)
    # Sets the minor loss coefficient across the valve to 0
    valve_minor_loss=["0.0000"]*len(valveids)
    # Semicolons at the end of each line
    semicolons=[';']*len(valveids)
    # Data frame with all required fields [ID   Node1   Node2   Diameter   Type   Setting   MinorLoss   ;]
    added_valves=pd.DataFrame(list(zip(valveids,node1ids,node2ids,valve_diameters,valve_types,valve_settings,valve_minor_loss,semicolons)))
    added_valves=added_valves.to_string(header=False,index=False,col_space=10).splitlines()

    # Set preferred translation distance for [AN1,AN2,AT] where AN is Artificial Node and AT is the Artifical Tank
    x_direct_distance=[20,40,60]
    y_driect_distance=[-20,0,-20]
    # Translates the tanks by a 100 m in both axes 
    node1_xcoord=[x+x_direct_distance[0] for x in xcoordinates]
    node2_xcoord=[x+x_direct_distance[1] for x in xcoordinates]
    tank_xcoord =[x+x_direct_distance[2] for x in xcoordinates]
    node1_ycoord=[y+y_driect_distance[0] for y in ycoordinates]
    node2_ycoord=[y+y_driect_distance[1] for y in ycoordinates]
    tank_ycoord =[y+y_driect_distance[2] for y in ycoordinates]

    added_xcoordinates=node1_xcoord+node2_xcoord+tank_xcoord
    added_ycoordinates=node1_ycoord+node2_ycoord+tank_ycoord
    ids_coords=node1ids+node2ids+tankids

    # Assemble all lists into a dataframe where each row is the coordinates for one simple tank
    added_coordinates=pd.DataFrame(list(zip(ids_coords,added_xcoordinates,added_ycoordinates)))
    # Exports the coordinate section as a list of strings where each entry is a line of the coordinates section
    added_coordinates=added_coordinates.to_string(header=False,index=False,col_space=10).splitlines()

    # List of zero base demands for all nodes
    zerodemands=[0]*len(all_nodes)
    # White space indicating no patterns
    pattern=['     ']*len(all_nodes)
    semicolons=[';']*len(all_nodes)
    original_nodes=pd.DataFrame(list(zip(all_nodes,all_elevations,zerodemands,pattern,semicolons)))
    original_nodes=original_nodes.to_string(header=False,index=False,col_space=10).splitlines()

    # opens .inp file to read
    file=open(path,'r')
    lines=[]            # list to store all lines in the .inp file
    linecount=0         # Counter for the number of lines
    junctions_marker=0  # To store the line number at which the junctions section starts
    tanks_marker=0      # To store the line number at which the tanks section starts
    pipes_marker=0      # To store the line number at which the pumps section starts
    valves_marker=0     # to store the line number at which the valves section
    coords_marker=0     # To store the line number at which the vertices section starts

    # Loops over each line in the input file 
    for line in file:
        # Record the position of the phrase [JUNCTIONS] and add 2 to skip the header line
        if re.search('\[JUNCTIONS\]',line):
            junctions_marker=linecount+2
        # Record the position of the phrase [TANKS] and add 2 to skip the header line
        if re.search('\[TANKS\]',line):
            tanks_marker=linecount+2
        # Record the position of the phrase [PUMPS] and subtract 1 to add pipes to the end of the pipe section
        if re.search('\[PUMPS\]',line):
            pipes_marker=linecount-1
        # Record the position of the phrase [VALVES] and add 2 to skip the header line
        if re.search('\[VALVES\]',line):
            valves_marker=linecount+2
        # Record the position of the phrase [Vertices] and subtract 1 to add Tank cooridnates to the end of the coordinates section
        if re.search('\[VERTICES\]',line):
            coords_marker=linecount-1
        if re.search('Demand Model',line):
            demand_model=linecount
        linecount+=1
        # Store all lines in a list
        lines.append(line)
    file.close()

    # Translate the tanks marker by the length of the added nodes (ANs) that will be added before it (as it will displace all subsequent lines)
    tanks_marker+=len(added_nodes)
    # Translate the pipes marker by the length of the tank section that will be added before it (as it will displace all subsequent lines)
    pipes_marker+=len(added_tanks)+len(added_nodes)
    # Translate the coordinates marker by the length of the added tanks, pipes and valves
    valves_marker+=len(added_tanks)+len(added_pipes)+len(added_nodes)
    # Translate the coordinates marker by the length of the added tanks, pipes and valves
    coords_marker+=len(added_tanks)+len(added_pipes)+len(added_valves)+len(added_nodes)

    # Inserts the created sections in their appropriate location in the list of lines
    if demand_model:
        lines[demand_model+1]=" Minimum Pressure   "+str(Hmin)
        lines[demand_model+2]=" Required Pressure  "+str(Hdes)
        demand_model+=len(added_nodes)+len(added_pipes)+len(added_valves)+len(added_tanks)
    lines[junctions_marker:junctions_marker+len(original_nodes)]=original_nodes
    lines[junctions_marker+len(original_nodes):junctions_marker+len(original_nodes)]=added_nodes
    lines[tanks_marker:tanks_marker]=added_tanks
    lines[pipes_marker:pipes_marker]=added_pipes
    lines[valves_marker:valves_marker]=added_valves
    lines[coords_marker:coords_marker]=added_coordinates

    # Opens a new file in the same directory to write the modified network .inp file in
    new_file_name=dir+name_only+'_PSV-Tank.inp'
    file=open(new_file_name,'w')
    c=0     #line counter

    # All lines added by this script are missing a new line character at the end, the conditional statements below add the new line character for these lines only and writes all lines to the file
    for line in lines:
        if c>=junctions_marker and c<=junctions_marker+len(original_nodes)+len(added_nodes):
            file.write(line+'\n')
        elif c>=tanks_marker and c<=tanks_marker+len(added_tanks):
            file.write(line+'\n')
        elif c>=pipes_marker and c<=pipes_marker+len(added_pipes):
            file.write(line+'\n')
        elif c>=valves_marker and c<=valves_marker+len(added_valves):
            file.write(line+'\n')
        elif c>=coords_marker and c<=coords_marker+len(added_coordinates):
            file.write(line+'\n')
        elif c>=demand_model and c<=demand_model+2:
            file.write(line+'\n')
        else: file.write(line)    
        c+=1
    file.close()
    return new_file_name


def to_Outlet_Outfall(path:str,Hmin:float,Hdes:float,del_x_max:float):
    """
    Converts an EPANET Input file to an EPA-SWMM input file that uses a flow-restricted method (Outlet-Outfall)

    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    Hmin (float): Value of the minimum pressure Hmin used for Pressure-Dependent Analysis (PDA)

    Hdes (float): Value of the desired pressure Hmin used for Pressure-Dependent Analysis (PDA)

    del_x_max (float): Maximum pipe length used for discretizing larger pipes. 
    Input arbitrarily high value for no discretization

    Returns: path of produced file. Saves produced file in same directory as input file
    """
    file=path.split("/")[-1]
    name_only=file[0:-4]
    if len(path.split("/"))>1:
        dir=path.rsplit("/",1)[0]+"/"
    else:dir=""    
    print("Selected File: ",name_only)
    pressure_diff=Hdes-Hmin 

    demand_nodes=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations
    elevations=[]         # For storing elevations of demand nodes
    coords=dict()         # For storing coordinates corresponding to each node as a tuple with the id as key
    all_nodes=[]          # For storing list of node ids of all nodes
    all_elevations=[]     # For storing elevations of all nodes
    ## MAYBE SAVE ALL NODE IDS IN DATAFRAME WITH ELEVATION AND BASE DEMAND AND THEN FILTER DATA FRAME LATER FOR DEMAND NODES ONLY

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)

    # Iterates over the junction list in the Network object
    for node in network.junctions():
        all_nodes.append(node[1].name)
        all_elevations.append(node[1].elevation)
        coords[node[1].name]=node[1].coordinates
        # For all nodes that have non-zero demands
        if node[1].base_demand != 0:
            # Record node ID (name), desired demand (base_demand) in CMS, elevations, x and y coordinates
            demand_nodes.append(node[1].name)
            desired_demands.append(node[1].base_demand)
            elevations.append(node[1].elevation)
            

    conduit_ids= []       # To store IDs of the original pipes in the EPANET file
    conduit_from= []      # To store the origin node for each pipe
    conduit_to= []        # To store the destination node for each pipe
    conduit_lengths= []   # To store pipe lengths
    conduit_diameters= [] # To store pipe diameters

    # Loop over each link in the EPANET model
    for link in network.links():

        # Extract and store each of the aforementioned properties
        conduit_ids.append(link[1].name)
        conduit_from.append(link[1].start_node_name)
        conduit_to.append(link[1].end_node_name)
        conduit_lengths.append(link[1].length)
        conduit_diameters.append(link[1].diameter)

    reservoir_ids=[]      # To store the source reservoirs' IDs
    reservoir_heads={}    # To store the total head of each reservoir indexed by ID
    reservoir_coords={}   # To store the coordinates as tuple (x,y) indexed by ID

    # Loops over each reservoir
    for reservoir in network.reservoirs():
        reservoir_ids.append(reservoir[1].name)
        reservoir_heads[reservoir_ids[-1]]=reservoir[1].base_head
        reservoir_coords[reservoir_ids[-1]]=reservoir[1].coordinates


    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)
    supply_hh=str(supply_duration//60)     # The hour value of the supply duration (quotient of total supply in minutes/ 60)
    supply_mm=str(supply_duration%60)      # The minute value of the supply duration (remainder)

    # Corrects the formatting of the HH:MM by adding a 0 if it is a single digit: if minutes =4 -> 04
    if len(supply_mm)<2:
        supply_mm='0'+supply_mm
    if len(supply_hh)<2:
        supply_hh='0'+supply_hh

    # Dataframe aggregating all node information gathered from the EPANET file
    junctions=pd.DataFrame(zip(all_nodes,all_elevations,coords.values()),columns=["ID","Elevation","Coordinates"])
    # Set the junction ID as the index of the Dataframe
    junctions.set_index("ID",inplace=True)

    # Dataframe aggregating all conduit information gathered from the EPANET file
    conduits=pd.DataFrame(zip(conduit_ids,conduit_from,conduit_to,conduit_lengths,conduit_diameters),columns=["ID","from node","to node","Length","diameter"])
    # Set the conduit ID as the index
    conduits.set_index("ID",inplace=True)

    # Loop over each conduit in the original file
    for conduit in conduits.index:

        length=conduits["Length"][conduit]  #Stores the length of the current conduit for shorthand

        # If the conduit is bigger than the maximum allowable length (delta x), we will break it down into smaller pipes
        if length>del_x_max:
            # Number of smaller pipes is calculated from 
            n_parts=math.ceil(length/del_x_max)
            # Calculate the length of each part 
            part_length=length/n_parts
            # Start node ID (for shorthand)
            start_node=conduits["from node"][conduit]
            # End node ID (for shorthand)
            end_node=conduits["to node"][conduit]
            # If the start node is a reservoir
            if start_node in reservoir_ids:
                # MAke the start elevation the same as the end but add 1 (since reservoirs don't have ground elevation in EPANET)
                start_elevation=junctions.at[end_node,"Elevation"]+1
            # Otherwise make the start elevation equal to the elevation of the start node
            else: start_elevation=junctions.at[start_node,"Elevation"]
            
            # If the end node is a reservoir
            if end_node in reservoir_ids:
                # MAke the end elevation the same as the start but subtract 1 (since reservoirs don't have ground elevation in EPANET)
                end_elevation=start_elevation-1
            # Make the end elevation equal to the elevation of the end node
            else: end_elevation=junctions.at[end_node,"Elevation"]
            # Calculate the uniform drop (or rise) in elevation for all the intermediate nodes about to be created when this pipe is broken into several smaller ones
            unit_elev_diff=(end_elevation-start_elevation)/n_parts

            # if the starting node is a reservoir
            if start_node in reservoir_ids:
                # Get coordinates from reservoir data
                start_x=reservoir_coords[start_node][0]
                start_y=reservoir_coords[start_node][1]
            else:
                # Get the coordinates from the junction data
                start_x=junctions.at[start_node,"Coordinates"][0]
                start_y=junctions.at[start_node,"Coordinates"][1]
            
            # If the end node is a reservoir
            if end_node in reservoir_ids:
                # Get the coordinates from the reservoir data
                end_x=reservoir_coords[end_node][0]
                end_y=reservoir_coords[end_node][1]
            else:
                # Get them from the junctions data
                end_x=junctions.at[end_node,"Coordinates"][0]
                end_y=junctions.at[end_node,"Coordinates"][1]
                
            # Calculate the unit difference in x and y coordinates for this pipe and its segments
            unit_x_diff=(end_x-start_x)/n_parts
            unit_y_diff=(end_y-start_y)/n_parts


    # THIS LOOP GENERATES THE SMALLER PIPES TO REPLACE THE ORIGINAL LONG PIPE
            # For each part to be created
            for part in np.arange(1,n_parts+1):

                # CREATING THE LINKS
                # Create the ID for the new smaller pipe as OriginPipeID-PartNumber
                new_id=conduit+"-"+str(part)
                # Set the new pipe's diameter equal to the original one
                conduits.at[new_id,"diameter"]=conduits["diameter"][conduit]
                # Set the start node as OriginStartNode-NewNodeNumber-OriginEndNode  as in the first intermediate nodes between node 13 and 14 will be named 13-1-14
                conduits.at[new_id,"from node"]=start_node+"-"+str(part-1)+"-"+end_node
                # if this is the first part, use the original start node 
                if part==1:
                    conduits.at[new_id,"from node"]=start_node
                # Set the end node as OriginStartNode-NewNodeNumber+1-OriginEndNode  as in the second intermediate nodes between node 13 and 14 will be named 13-2-14
                conduits.at[new_id,"to node"]=start_node+"-"+str(part)+"-"+end_node
                # If this is the last part, use the original end node as the end node
                if part==n_parts:
                    conduits.at[new_id,"to node"]=end_node
                # Set the new pipe's length to the length of each part
                conduits.at[new_id,"Length"]=part_length

                # if this is NOT the last part (as the last pipe segment joins a pre-existing node and does not need a node to be created)
                if part<n_parts:
                    # Create a new node at the end of this pipe segment whose elevation is translated from the start elevation using the unit slope and the part number
                    junctions.at[conduits.at[new_id,"to node"],"Elevation"]=start_elevation+part*unit_elev_diff
                    # Calculate the coordinates for the new node using the unit difference in x and y coordinates
                    junctions.at[conduits.at[new_id,"to node"],"Coordinates"]=(start_x+part*unit_x_diff,start_y+part*unit_y_diff)

            # After writing the new smaller pipes, delete the original pipe (since it is now redundant)
            conduits.drop(conduit,inplace=True)

    MaxDepth=[0]*len(junctions)
    InitDepth=MaxDepth
    SurDepth=[100] * len(junctions)  # High value to prevent surcharging
    Aponded=InitDepth

    # Creates dataframe with each row representing one line from the junctions section
    junctions_section=pd.DataFrame(list(zip(junctions.index,junctions["Elevation"],MaxDepth,InitDepth,SurDepth,Aponded)))
    # Converts the dataframe into a list of lines in the junctions section
    junctions_section=junctions_section.to_string(header=False,index=False,col_space=10).splitlines()
    # adds a new line character to the end of each line in the section
    junctions_section=[line+'\n' for line in junctions_section]

    # Add Outfall to each demand node ID
    outfall_ids=["Outfall"+str(id) for id in demand_nodes]
    # Same as the demand nodes
    outfall_elevations=elevations
    # Free outfalls
    outfall_type=["FREE"]*len(outfall_ids)
    # Blank Stage Data
    stage_data=["   "]*len(outfall_ids)
    # Not gated
    outfall_gated=["NO"]*len(outfall_ids)

    # Creates dataframe with each row representing one line from the outfalls section
    outfall_section=pd.DataFrame(zip(outfall_ids,outfall_elevations,outfall_type,stage_data,outfall_gated))
    # Converts the dataframe into a list of lines in the outfalls section
    outfall_section=outfall_section.to_string(header=False,index=False,col_space=10).splitlines()
    # adds a new line character to the end of each line in the section
    outfall_section=[line+'\n' for line in outfall_section]

    reservoir_elevations=[0]*len(reservoir_ids)
    MaxDepth=[max(100,max(reservoir_heads.values())+10)]*len(reservoir_ids)
    InitDepth=reservoir_heads.values()
    reservoir_shape=["FUNCTIONAL"]*len(reservoir_ids)
    reservoir_coeff=[0]*len(reservoir_ids)
    reservoir_expon=[0]*len(reservoir_ids)
    reservoir_const=[1000000]*len(reservoir_ids)
    reservoir_fevap=reservoir_expon
    reservoir_psi=reservoir_fevap

    storage_section=pd.DataFrame(zip(reservoir_ids,reservoir_elevations,MaxDepth,InitDepth,reservoir_shape,reservoir_coeff,reservoir_expon,reservoir_const,reservoir_fevap,reservoir_psi))
    storage_section=storage_section.to_string(header=False,index=False,col_space=10).splitlines()
    storage_section=[line+'\n' for line in storage_section]

    roughness=[0.011]*len(conduits)
    conduit_zeros=[0]*len(conduits)

    conduits_section=pd.DataFrame(zip(conduits.index,conduits["from node"],conduits["to node"],conduits["Length"],roughness,conduit_zeros,conduit_zeros,conduit_zeros,conduit_zeros))
    conduits_section=conduits_section.to_string(header=False,index=False,col_space=10).splitlines()
    conduits_section=[line+'\n' for line in conduits_section]

    outlet_ids = ["Outlet"+id for id in demand_nodes]
    outlet_from = demand_nodes
    outlet_to = outfall_ids
    outlet_offset=[0]*len(outlet_ids)
    outlet_type=["TABULAR/DEPTH"]*len(outlet_ids)
    outlet_qtable=[str(round(demand*1000000)) for demand in desired_demands]  # To generate unique Table IDs for each demand rate (not demand node) i.e., juncitons with the same demand are assigned the same outlet curve
    outlet_expon=["    "]*len(outlet_ids)
    outlet_gated=["YES"]*len(outlet_ids)

    outlets=pd.DataFrame(list(zip(outlet_ids,outlet_from,outlet_to,outlet_offset,outlet_type,outlet_qtable,outlet_expon,outlet_gated)))
    outlet_section=outlets.to_string(header=False,index=False,col_space=10).splitlines()
    outlet_section=[line+'\n' for line in outlet_section]

    shape=["FORCE_MAIN"]*len(conduits.index)
    hwcoeffs=[130]*len(shape)
    geom3=[0]*len(shape)
    geom4=geom3
    nbarrels=[1]*len(shape)

    xsections_section=pd.DataFrame(zip(conduits.index,shape,conduits["diameter"],hwcoeffs,geom3,geom4,nbarrels))
    xsections_section=xsections_section.to_string(header=False,index=False, col_space=10).splitlines()
    xsections_section=[line+'\n' for line in xsections_section]

    table_ids=list(set(outlet_qtable))   # removes duplicates from list
    curves_name=[]
    curves_type=[]
    curves_x=[]
    curves_y=[]
    for table in table_ids:
        demand=int(table)/1000                # in LPS
        for depth in np.arange(0,11,1):
            curves_name.append(table)
            if depth==0:
                curves_type.append("Rating")
            else: curves_type.append(" ")
            curves_x.append(depth)
            curves_y.append(demand*np.sqrt((depth-Hmin)/(Hdes-Hmin)))
        curves_name.append(";")
        curves_type.append(" ")
        curves_x.append(" ")
        curves_y.append(" ")

    curves=pd.DataFrame(list(zip(curves_name,curves_type,curves_x,curves_y)))
    curves_section=curves.to_string(header=False,index=False,col_space=10).splitlines()
    curves_section=[line+'\n' for line in curves_section]

    coords_demand= { node: coords[node] for node in demand_nodes}
    coords_ids=list(junctions.index)+reservoir_ids+outfall_ids

    coords_x1=[coord[0] for coord in junctions["Coordinates"]]
    coords_x2=[coord[0] for coord in reservoir_coords.values()]
    coords_x3=[coord[0] +20 for coord in coords_demand.values()]
    coords_x=coords_x1+coords_x2+coords_x3

    coords_y1=[coord[1] for coord in junctions["Coordinates"]]
    coords_y2=[coord[1] for coord in reservoir_coords.values()]
    coords_y3=[coord[1] +20 for coord in coords_demand.values()]
    coords_y=coords_y1+coords_y2+coords_y3

    coordinate_section=pd.DataFrame(zip(coords_ids,coords_x,coords_y))
    coordinate_section=coordinate_section.to_string(header=False,index=False,col_space=10).splitlines()
    coordinate_section=[line+'\n' for line in coordinate_section]

    #Setting View Dimensions
    x_left=min(coords_x)-max(coords_x)/4
    x_right=max(coords_x)+max(coords_x)/4
    y_down=min(coords_y)-max(coords_y)/4
    y_up=max(coords_y)+max(coords_y)/4
    dimensions_line=str(x_left)+" "+str(y_down)+" "+str(x_right)+" "+str(y_up)+"\n"

    # opens .inp file to read
    file=__swmm_template__()
    lines=[]              # list to store all lines in the .inp file
    linecount=0           # Counter for the number of lines
    end_time=0
    junctions_marker=0    # To store the line number at which the junctions section starts
    outfalls_marker=0     # To store the line number at which the emitter section starts
    storage_marker=0      # To store the line number at which the pumps section starts
    conduits_marker=0     # to store the line number at which the valves section
    outlets_marker=0      # To store the line number at which the vertices section starts
    xsections_marker=0    # To store the line number of teh emitter exponent option
    curves_marker=0
    coords_marker=0

    # Loops over each line in the input file 
    for line in file:
        if re.search("^END_TIME",line):
            end_time=linecount
        if re.search("^DIMENSIONS",line):
            dimensions=linecount
        # Record the position of the phrase [JUNCTIONS] and add 2 to skip the header line
        if re.search('\[JUNCTIONS\]',line):
            junctions_marker=linecount+3
        # Record the position of the phrase [TANKS] and add 2 to skip the header line
        if re.search('\[OUTFALLS\]',line):
            outfalls_marker=linecount+3
        # Record the position of the phrase [PUMPS] and subtract 1 to add pipes to the end of the pipe section
        if re.search('\[STORAGE\]',line):
            storage_marker=linecount+3
        # Record the position of the phrase [VALVES] and add 2 to skip the header line
        if re.search('\[CONDUITS\]',line):
            conduits_marker=linecount+3
        # Record the position of the phrase [Vertices] and subtract 1 to add Tank cooridnates to the end of the coordinates section
        if re.search('\[OUTLETS\]',line):
            outlets_marker=linecount+3
        # Record the position of the phrase [Vertices] and subtract 1 to add Tank cooridnates to the end of the coordinates section
        if re.search('\[XSECTIONS\]',line):
            xsections_marker=linecount+3
        # Record the position of the phrase [Vertices] and subtract 1 to add Tank cooridnates to the end of the coordinates section
        if re.search('\[CURVES\]',line):
            curves_marker=linecount+3
        # Record the position of the phrase [Vertices] and subtract 1 to add Tank cooridnates to the end of the coordinates section
        if re.search('\[COORDINATES\]',line):
            coords_marker=linecount+3
        # Store all lines in a list
        lines.append(line)
        linecount+=1

    new_file_name=dir+name_only+"_Outlet-Outfall.inp"
    file=open(new_file_name,'w')
    lines[end_time]="END_TIME             "+str(supply_hh)+":"+str(supply_mm)+":00\n"
    lines[dimensions]="DIMENSIONS "+dimensions_line
    lines[coords_marker:coords_marker]=coordinate_section
    lines[curves_marker:curves_marker]=curves_section
    lines[xsections_marker:xsections_marker]=xsections_section
    lines[outlets_marker:outlets_marker]=outlet_section
    lines[conduits_marker:conduits_marker]=conduits_section
    lines[storage_marker:storage_marker]=storage_section
    lines[outfalls_marker:outfalls_marker]=outfall_section
    lines[junctions_marker:junctions_marker]=junctions_section


    # All lines added by this script are missing a new line character at the end, the conditional statements below add the new line character for these lines only and writes all lines to the file
    for line in lines:
        file.write(line+'\n')    
    file.close()

    demands=pd.DataFrame(zip(outlet_ids,desired_demands),columns=["ID","Demand"])
    demands.set_index("ID", inplace=True)
    demands.to_csv(new_file_name[0:-4]+"_Demands.csv")
    return new_file_name


def to_Outlet_Storage(path:str,Hmin:float,Hdes:float,del_x_max:float):
    """
    Converts an EPANET Input file to an EPA-SWMM input file that uses a volume-restricted method (Outlet-Storage)

    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    Hmin (float): Value of the minimum pressure Hmin used for Pressure-Dependent Analysis (PDA)

    Hdes (float): Value of the desired pressure Hmin used for Pressure-Dependent Analysis (PDA)

    del_x_max (float): Maximum pipe length used for discretizing larger pipes. 
    Input arbitrarily high value for no discretization

    Returns: path of produced file. Saves produced file in same directory as input file
    """
    file=path.split("/")[-1]
    name_only=file[0:-4]
    if len(path.split("/"))>1:
        dir=path.rsplit("/",1)[0]+"/"
    else:dir=""    
    print("Selected File: ",name_only)
    pressure_diff=Hdes-Hmin 

    demand_nodes=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations
    elevations=[]         # For storing elevations of demand nodes
    coords=dict()         # For storing coordinates corresponding to each node as a tuple with the id as key
    all_nodes=[]          # For storing list of node ids of all nodes
    all_elevations=[]     # For storing elevations of all nodes

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)

    # Iterates over the junction list in the Network object
    for node in network.junctions():
        all_nodes.append(node[1].name)
        all_elevations.append(node[1].elevation)
        coords[node[1].name]=node[1].coordinates
        # For all nodes that have non-zero demands
        if node[1].base_demand != 0:
            # Record node ID (name), desired demand (base_demand) in CMS, elevations, x and y coordinates
            demand_nodes.append(node[1].name)
            desired_demands.append(node[1].base_demand)
            elevations.append(node[1].elevation)
            

    conduit_ids= []       # To store IDs of the original pipes in the EPANET file
    conduit_from= []      # To store the origin node for each pipe
    conduit_to= []        # To store the destination node for each pipe
    conduit_lengths= []   # To store pipe lengths
    conduit_diameters= [] # To store pipe diameters

    # Loop over each link in the EPANET model
    for link in network.links():

        # Extract and store each of the aforementioned properties
        conduit_ids.append(link[1].name)
        conduit_from.append(link[1].start_node_name)
        conduit_to.append(link[1].end_node_name)
        conduit_lengths.append(link[1].length)
        conduit_diameters.append(link[1].diameter)

    reservoir_ids=[]      # To store the source reservoirs' IDs
    reservoir_heads={}    # To store the total head of each reservoir indexed by ID
    reservoir_coords={}   # To store the coordinates as tuple (x,y) indexed by ID

    # Loops over each reservoir
    for reservoir in network.reservoirs():
        reservoir_ids.append(reservoir[1].name)
        reservoir_heads[reservoir_ids[-1]]=reservoir[1].base_head
        reservoir_coords[reservoir_ids[-1]]=reservoir[1].coordinates
    reservoir_elevations={reservoir:reservoir_heads[reservoir]-30 for reservoir in reservoir_heads}

    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)
    supply_hh=str(supply_duration//60)     # The hour value of the supply duration (quotient of total supply in minutes/ 60)
    supply_mm=str(supply_duration%60)      # The minute value of the supply duration (remainder)

    # Corrects the formatting of the HH:MM by adding a 0 if it is a single digit: if minutes =4 -> 04
    if len(supply_mm)<2:
        supply_mm='0'+supply_mm
    if len(supply_hh)<2:
        supply_hh='0'+supply_hh

    # Maximum length of conduit allowed
    maximum_xdelta=10

    # Dataframe aggregating all node information gathered from the EPANET file
    junctions=pd.DataFrame(zip(all_nodes,all_elevations,coords.values()),columns=["ID","Elevation","Coordinates"])
    # Set the junction ID as the index of the Dataframe
    junctions.set_index("ID",inplace=True)

    # Dataframe aggregating all conduit information gathered from the EPANET file
    conduits=pd.DataFrame(zip(conduit_ids,conduit_from,conduit_to,conduit_lengths,conduit_diameters),columns=["ID","from node","to node","Length","diameter"])
    # Set the conduit ID as the index
    conduits.set_index("ID",inplace=True)

    # Loop over each conduit in the original file
    for conduit in conduits.index:

        length=conduits["Length"][conduit]  #Stores the length of the current conduit for shorthand

        # If the conduit is bigger than the maximum allowable length (delta x), we will break it down into smaller pipes
        if length>maximum_xdelta:
            # Number of smaller pipes is calculated from 
            n_parts=math.ceil(length/maximum_xdelta)
            # Calculate the length of each part 
            part_length=length/n_parts
            # Start node ID (for shorthand)
            start_node=conduits["from node"][conduit]
            # End node ID (for shorthand)
            end_node=conduits["to node"][conduit]
            # If the start node is a reservoir
            if start_node in reservoir_ids:
                # MAke the start elevation the same as the end but add 1 (since reservoirs don't have ground elevation in EPANET)
                start_elevation=junctions.at[end_node,"Elevation"]+1
                reservoir_elevations[start_node]=start_elevation+1
            # Otherwise make the start elevation equal to the elevation of the start node
            else: start_elevation=junctions.at[start_node,"Elevation"]
            
            # If the end node is a reservoir
            if end_node in reservoir_ids:
                # MAke the end elevation the same as the start but subtract 1 (since reservoirs don't have ground elevation in EPANET)
                end_elevation=start_elevation-1
            # Make the end elevation equal to the elevation of the end node
            else: end_elevation=junctions.at[end_node,"Elevation"]
            # Calculate the uniform drop (or rise) in elevation for all the intermediate nodes about to be created when this pipe is broken into several smaller ones
            unit_elev_diff=(end_elevation-start_elevation)/n_parts

            # if the starting node is a reservoir
            if start_node in reservoir_ids:
                # Get coordinates from reservoir data
                start_x=reservoir_coords[start_node][0]
                start_y=reservoir_coords[start_node][1]
            else:
                # Get the coordinates from the junction data
                start_x=junctions.at[start_node,"Coordinates"][0]
                start_y=junctions.at[start_node,"Coordinates"][1]
            
            # If the end node is a reservoir
            if end_node in reservoir_ids:
                # Get the coordinates from the reservoir data
                end_x=reservoir_coords[end_node][0]
                end_y=reservoir_coords[end_node][1]
            else:
                # Get them from the junctions data
                end_x=junctions.at[end_node,"Coordinates"][0]
                end_y=junctions.at[end_node,"Coordinates"][1]
                
            # Calculate the unit difference in x and y coordinates for this pipe and its segments
            unit_x_diff=(end_x-start_x)/n_parts
            unit_y_diff=(end_y-start_y)/n_parts


    # THIS LOOP GENERATES THE SMALLER PIPES TO REPLACE THE ORIGINAL LONG PIPE
            # For each part to be created
            for part in np.arange(1,n_parts+1):

                # CREATING THE LINKS
                # Create the ID for the new smaller pipe as OriginPipeID-PartNumber
                new_id=conduit+"-"+str(part)
                # Set the new pipe's diameter equal to the original one
                conduits.at[new_id,"diameter"]=conduits["diameter"][conduit]
                # Set the start node as OriginStartNode-NewNodeNumber-OriginEndNode  as in the first intermediate nodes between node 13 and 14 will be named 13-1-14
                conduits.at[new_id,"from node"]=start_node+"-"+str(part-1)+"-"+end_node
                # if this is the first part, use the original start node 
                if part==1:
                    conduits.at[new_id,"from node"]=start_node
                # Set the end node as OriginStartNode-NewNodeNumber+1-OriginEndNode  as in the second intermediate nodes between node 13 and 14 will be named 13-2-14
                conduits.at[new_id,"to node"]=start_node+"-"+str(part)+"-"+end_node
                # If this is the last part, use the original end node as the end node
                if part==n_parts:
                    conduits.at[new_id,"to node"]=end_node
                # Set the new pipe's length to the length of each part
                conduits.at[new_id,"Length"]=part_length

                # if this is NOT the last part (as the last pipe segment joins a pre-existing node and does not need a node to be created)
                if part<n_parts:
                    # Create a new node at the end of this pipe segment whose elevation is translated from the start elevation using the unit slope and the part number
                    junctions.at[conduits.at[new_id,"to node"],"Elevation"]=start_elevation+part*unit_elev_diff
                    # Calculate the coordinates for the new node using the unit difference in x and y coordinates
                    junctions.at[conduits.at[new_id,"to node"],"Coordinates"]=(start_x+part*unit_x_diff,start_y+part*unit_y_diff)

            # After writing the new smaller pipes, delete the original pipe (since it is now redundant)
            conduits.drop(conduit,inplace=True)

    MaxDepth=[0]*len(junctions)
    InitDepth=MaxDepth
    SurDepth=[100] * len(junctions)  # High value to prevent surcharging
    Aponded=InitDepth

    # Creates dataframe with each row representing one line from the junctions section
    junctions_section=pd.DataFrame(list(zip(junctions.index,junctions["Elevation"],MaxDepth,InitDepth,SurDepth,Aponded)))
    # Converts the dataframe into a list of lines in the junctions section
    junctions_section=junctions_section.to_string(header=False,index=False,col_space=10).splitlines()
    # adds a new line character to the end of each line in the section
    junctions_section=[line+'\n' for line in junctions_section]

    # Add Outfall to each demand node ID
    outfall_ids=["Outfall_FAKE"]
    # Same as the demand nodes
    outfall_elevations=[min(elevations)]
    # Free outfalls
    outfall_type=["FREE"]
    # Blank Stage Data
    stage_data=["   "]
    # Not gated
    outfall_gated=["NO"]

    # Creates dataframe with each row representing one line from the outfalls section
    outfall_section=pd.DataFrame(zip(outfall_ids,outfall_elevations,outfall_type,stage_data,outfall_gated))
    # Converts the dataframe into a list of lines in the outfalls section
    outfall_section=outfall_section.to_string(header=False,index=False,col_space=10).splitlines()
    # adds a new line character to the end of each line in the section
    outfall_section=[line+'\n' for line in outfall_section]

    tank_height=1

    storage_ids=["StorageforNode"+id for id in demand_nodes]
    storage_areas=[demand*60* supply_duration/tank_height for demand in desired_demands]
    storage_elevations=elevations
    storage_curves=[round(volume*10000) for volume in storage_areas]
    storage_MaxDepth=[max(100,max(reservoir_heads.values()))]*len(storage_ids)
    storage_InitDepth=[0]*len(storage_ids)
    storage_shape=["TABULAR"]*len(storage_ids)
    blanks=['    ']*len(storage_ids)    # for the other curve parameters which are not required in Tabular definition
    storage_SurDepth=[0]*len(storage_ids)
    storage_fevap=[0]*len(storage_ids)

    storage_units=pd.DataFrame(zip(storage_ids,storage_elevations,storage_MaxDepth,storage_InitDepth,storage_shape,storage_curves,blanks,blanks,storage_SurDepth,storage_fevap))

    reservoir_elevations=reservoir_elevations.values()
    MaxDepth=[max(100,max(reservoir_heads.values())+10)]*len(reservoir_ids)
    InitDepth=[head-elevation for head, elevation in zip(reservoir_heads.values(),reservoir_elevations)]
    reservoir_shape=["FUNCTIONAL"]*len(reservoir_ids)
    reservoir_coeff=[0]*len(reservoir_ids)
    reservoir_expon=[0]*len(reservoir_ids)
    reservoir_const=[1000000]*len(reservoir_ids)
    reservoir_SurDepth=reservoir_expon
    reservoir_psi=reservoir_expon

    storage_section=pd.DataFrame(zip(reservoir_ids,reservoir_elevations,MaxDepth,InitDepth,reservoir_shape,reservoir_coeff,reservoir_expon,reservoir_const,reservoir_SurDepth,reservoir_psi))
    storage_section= pd.concat([storage_section,storage_units])
    storage_section=storage_section.to_string(header=False,index=False,col_space=10).splitlines()
    storage_section=[line+'\n' for line in storage_section]

    roughness=[0.011]*len(conduits)
    conduit_zeros=[0]*len(conduits)

    conduits_section=pd.DataFrame(zip(conduits.index,conduits["from node"],conduits["to node"],conduits["Length"],roughness,conduit_zeros,conduit_zeros,conduit_zeros,conduit_zeros))
    conduits_section=conduits_section.to_string(header=False,index=False,col_space=10).splitlines()
    conduits_section=[line+'\n' for line in conduits_section]

    outlet_ids = ["Outlet"+id for id in demand_nodes]
    outlet_from = demand_nodes[:]
    outlet_to = storage_ids [:]
    outlet_offset=[0]*len(outlet_ids)
    outlet_type=["FUNCTIONAL/DEPTH"]*len(outlet_ids)
    outlet_coeff=[demand*1000/np.sqrt(pressure_diff) for demand in desired_demands]  # To generate unique Table IDs for each demand rate (not demand node) i.e., juncitons with the same demand are assigned the same outlet curve
    outlet_expon=["0.5"]*len(outlet_ids)
    outlet_gated=["YES"]*len(outlet_ids)

    outlet_ids.append("Outlet_FAKE")
    outlet_from.append("1")
    outlet_to.append("Outfall_FAKE")
    outlet_offset.append(0)
    outlet_type.append("FUNCTIONAL/DEPTH")
    outlet_coeff.append(0.00001)
    outlet_expon.append(0)
    outlet_gated.append("YES")

    outlets=pd.DataFrame(list(zip(outlet_ids,outlet_from,outlet_to,outlet_offset,outlet_type,outlet_coeff,outlet_expon,outlet_gated)))
    outlet_section=outlets.to_string(header=False,index=False,col_space=10).splitlines()
    outlet_section=[line+'\n' for line in outlet_section]

    shape=["FORCE_MAIN"]*len(conduits.index)
    hwcoeffs=[130]*len(shape)
    geom3=[0]*len(shape)
    geom4=geom3
    nbarrels=[1]*len(shape)

    xsections_section=pd.DataFrame(zip(conduits.index,shape,conduits["diameter"],hwcoeffs,geom3,geom4,nbarrels))
    xsections_section=xsections_section.to_string(header=False,index=False, col_space=10).splitlines()
    xsections_section=[line+'\n' for line in xsections_section]

    table_ids=list(set(storage_curves))   # removes duplicates from list
    curves_name=[]
    curves_type=[]
    curves_x=[]
    curves_y=[]
    for table in table_ids:
        volume=int(table)/10000                # in LPS
        for depth in [0,1,1.0001,100]:
            curves_name.append(table)
            curves_x.append(depth)
            if depth<=1:
                curves_y.append(volume)
            else: curves_y.append(0.000001)
            if depth==0:
                curves_type.append("Storage")
            else: 
                curves_type.append(" ")
        curves_name.append(";")
        curves_type.append(" ")
        curves_x.append(" ")
        curves_y.append(" ")

    curves=pd.DataFrame(list(zip(curves_name,curves_type,curves_x,curves_y)))
    curves_section=curves.to_string(header=False,index=False,col_space=10).splitlines()
    curves_section=[line+'\n' for line in curves_section]

    coords_demand= { node: coords[node] for node in demand_nodes}
    coords_ids=list(junctions.index)+reservoir_ids+storage_ids

    coords_x1=[coord[0] for coord in junctions["Coordinates"]]
    coords_x2=[coord[0] for coord in reservoir_coords.values()]
    coords_x3=[coord[0] +2 for coord in coords_demand.values()]
    coords_x=coords_x1+coords_x2+coords_x3

    coords_y1=[coord[1] for coord in junctions["Coordinates"]]
    coords_y2=[coord[1] for coord in reservoir_coords.values()]
    coords_y3=[coord[1] +2 for coord in coords_demand.values()]
    coords_y=coords_y1+coords_y2+coords_y3

    coordinate_section=pd.DataFrame(zip(coords_ids,coords_x,coords_y))
    coordinate_section=coordinate_section.to_string(header=False,index=False,col_space=10).splitlines()
    coordinate_section=[line+'\n' for line in coordinate_section]

    #Setting View Dimensions
    x_left=min(coords_x)-max(coords_x)/4
    x_right=max(coords_x)+max(coords_x)/4
    y_down=min(coords_y)-max(coords_y)/4
    y_up=max(coords_y)+max(coords_y)/4
    dimensions_line=str(x_left)+" "+str(y_down)+" "+str(x_right)+" "+str(y_up)+"\n"

    # opens .inp file to read
    lines=__swmm_template__()
    linecount=0           # Counter for the number of lines

    # Loops over each line in the input file 
    for line in lines:
        if re.search("^END_TIME",line):
            end_time=linecount
        if re.search("^DIMENSIONS",line):
            dimensions=linecount
        # Record the position of the phrase [JUNCTIONS] and add 3 to skip the header lines
        if re.search('\[JUNCTIONS\]',line):
            junctions_marker=linecount+3
        # Record the position of the phrase [OUTFALLS] and add 3 to skip the header lines
        if re.search('\[OUTFALLS\]',line):
            outfalls_marker=linecount+3
        # Record the position of the phrase [STORAGE] and add 3 to skip the header lines
        if re.search('\[STORAGE\]',line):
            storage_marker=linecount+3
        # Record the position of the phrase [CONDUITS] and add 3 to skip the header lines
        if re.search('\[CONDUITS\]',line):
            conduits_marker=linecount+3
        # Record the position of the phrase [OUTLETS] and add 3 to skip the header lines
        if re.search('\[OUTLETS\]',line):
            outlets_marker=linecount+3
        # Record the position of the phrase [XSECTIONS] and add 3 to skip the header lines
        if re.search('\[XSECTIONS\]',line):
            xsections_marker=linecount+3
        # Record the position of the phrase [CURVES] and add 3 to skip the header lines
        if re.search('\[CURVES\]',line):
            curves_marker=linecount+3
        # Record the position of the phrase [COORDINATES] and add 3 to skip the header lines
        if re.search('\[COORDINATES\]',line):
            coords_marker=linecount+3
        # Store all lines in a list
        linecount+=1


    new_file_name=dir+name_only+"_Outlet-Storage.inp"
    file=open(new_file_name,'w')
    lines[end_time]="END_TIME             "+str(supply_hh)+":"+str(supply_mm)+":00\n"
    lines[dimensions]="DIMENSIONS "+dimensions_line

    lines[coords_marker:coords_marker]=coordinate_section
    lines[curves_marker:curves_marker]=curves_section
    lines[xsections_marker:xsections_marker]=xsections_section
    lines[outlets_marker:outlets_marker]=outlet_section
    lines[conduits_marker:conduits_marker]=conduits_section
    lines[storage_marker:storage_marker]=storage_section
    lines[outfalls_marker:outfalls_marker]=outfall_section
    lines[junctions_marker:junctions_marker]=junctions_section

    # All lines added by this script are missing a new line character at the end, the conditional statements below add the new line character for these lines only and writes all lines to the file
    for line in lines:
        file.write(line+'\n')    
    file.close()
    return new_file_name


def change_duration(path:str,duration_hr:int,duration_min:int):
    """
    Converts an EPANET .inp file from one supply duration to another, scaling the desired demand accordingly

    Parameters
    -----------
    path (str): path to input file. relative or full absolute path

    duration_hr (int): New Supply Duration (HH)

    duration_min (int): New Supply Duration (MM)

    Returns: path to produced file. Saves produced file in same directory
    """

    assert 0<=duration_hr<=24, 'Durations of 24 hours or more are not intermittent and thus not supported'
    assert 0<=duration_min<=59, 'Enter Valid Value for minutes 0-59'

    file=path.split("/")[-1]
    name_only=file[0:-4]
    if len(path.split("/"))>1:
        dir=path.rsplit("/",1)[0]+"/"
    else:dir=""
    print("Selected File: ",name_only)  
    demand_nodes=[]       # For storing list of nodes that have non-zero demands
    desired_demands=[]    # For storing demand rates desired by each node for desired volume calculations
    elevations=[]

    # Creates a network model object using EPANET .inp file
    network=wntr.network.WaterNetworkModel(path)

    # Iterates over the junction list in the Network object
    for node in network.junctions():
        # Record node ID (name), desired demand (base_demand) in CMS, elevations, x and y coordinates
        demand_nodes.append(node[1].name)
        desired_demands.append(node[1].base_demand)
        elevations.append(node[1].elevation)

    # Get the supply duration in minutes (/60) as an integer
    supply_duration=int(network.options.time.duration/60)
    new_duration=duration_hr*60+duration_min
    demand_multiplier=supply_duration/new_duration
    if duration_min <10:
        duration_min="0"+str(duration_min)
    else: duration_min=str(duration_min)

    desired_demands=[demand*demand_multiplier*1000 for demand in desired_demands]
    patterns=["       " for demand in desired_demands]
    semicolons=[";" for demand in desired_demands]
    node_section=pd.DataFrame(list(zip(demand_nodes,elevations,desired_demands,patterns,semicolons)))
    node_section=node_section.to_string(header=False,index=False,col_space=10).splitlines()

    # opens .inp file to read
    file=open(path,'r')
    lines=[]            # list to store all lines in the .inp file
    linecount=0         # Counter for the number of lines
    junctions_marker=0  # To store the line number at which the junctions section starts
    supply_duration_line=0

    # Loops over each line in the input file 
    for line in file:
        # Record the position of the phrase [JUNCTIONS] and add 2 to skip the header line
        if re.search('\[JUNCTIONS\]',line):
            junctions_marker=linecount+2
        if re.search('Duration',line):
            supply_duration_line=linecount
        linecount+=1
        # Store all lines in a list
        lines.append(line)
    file.close()

    # Inserts the created sections in their appropriate location in the list of lines
    lines[supply_duration_line]="Duration      "+str(duration_hr)+":"+duration_min+"\n"
    lines[junctions_marker:junctions_marker+len(node_section)]=node_section

    print(lines[supply_duration_line])
    # Opens a new file in the same directory to write the modified network .inp file in
    new_file_name=dir+name_only+"_"+str(duration_hr)+"hr.inp"
    file=open(new_file_name,'w')
    c=0     #line counter

    # All lines added by this script are missing a new line character at the end, the conditional statements below add the new line character for these lines only and writes all lines to the file
    for line in lines:
        if c>=junctions_marker and c<=junctions_marker+len(node_section)+len(node_section):
            file.write(line+'\n')
        else: file.write(line)    
        c+=1
    file.close()
    return new_file_name


def to_all(dir:str,file:str,Hmin:float,Hdes:float,del_x_max:float):
    '''
    converts a PDA .inp file to all 7 other methods

    Parameters
    -----------
    dir (str): Directory in which origin file is located  

    file (str): Filename with extension of origin file  

    Hmin (float): Value of the minimum pressure Hmin used for Pressure-Dependent Analysis (PDA)

    Hdes (float): Value of the desired pressure Hmin used for Pressure-Dependent Analysis (PDA)

    del_x_max (float): Maximum pipe length used for discretizing larger pipes. 
    Input arbitrarily high value for no discretization

    Returns: list of paths of produced files. Saves produced file sin same directory as input file
    '''


    assert 0<=Hmin<=Hdes, "Hmin must be smaller than Hdes"
    assert del_x_max>0, "Delta x must be a positive number"
    output_paths=[]
    output_paths.append(to_CVRes(dir,file,Hmin,Hdes))
    output_paths.append(to_CVTank(dir,file,Hmin,Hdes))
    output_paths.append(to_FCVEM(dir,file,Hmin,Hdes))
    output_paths.append(to_FCVRes(dir,file,Hmin,Hdes))
    output_paths.append(to_PSVTank(dir,file,Hmin,Hdes))
    output_paths.append(to_Outlet_Outfall(dir,file,Hmin,Hdes,del_x_max))
    output_paths.append(to_Outlet_Storage(dir,file,Hmin,Hdes,del_x_max))

    return output_paths

def __swmm_template__():
    template='''
[TITLE]
;;Project Title/Notes

[OPTIONS]
;;Option             Value
FLOW_UNITS           LPS
INFILTRATION         HORTON
FLOW_ROUTING         DYNWAVE
LINK_OFFSETS         DEPTH
MIN_SLOPE            0
ALLOW_PONDING        NO
SKIP_STEADY_STATE    NO

START_DATE           05/18/2022
START_TIME           00:00:00
REPORT_START_DATE    05/18/2022
REPORT_START_TIME    00:00:00
END_DATE             05/18/2022
END_TIME             04:00:00
SWEEP_START          01/01
SWEEP_END            12/31
DRY_DAYS             0
REPORT_STEP          00:00:10
WET_STEP             00:01:00
DRY_STEP             00:01:00
ROUTING_STEP         0:00:01
RULE_STEP            00:00:00

INERTIAL_DAMPING     PARTIAL
NORMAL_FLOW_LIMITED  BOTH
FORCE_MAIN_EQUATION  H-W
VARIABLE_STEP        0.75
LENGTHENING_STEP     0
MIN_SURFAREA         0.00000001
MAX_TRIALS           20
HEAD_TOLERANCE       0.000005
SYS_FLOW_TOL         5
LAT_FLOW_TOL         5
MINIMUM_STEP         0.1
THREADS              4

[FILES]
;;Interfacing Files


[EVAPORATION]
;;Data Source    Parameters
;;-------------- ----------------
CONSTANT         0.0
DRY_ONLY         NO

[JUNCTIONS]
;;Name           Elevation  MaxDepth   InitDepth  SurDepth   Aponded
;;-------------- ---------- ---------- ---------- ---------- ----------


[OUTFALLS]
;;Name           Elevation  Type       Stage Data       Gated    Route To
;;-------------- ---------- ---------- ---------------- -------- ----------------


[STORAGE]
;;Name           Elev.    MaxDepth   InitDepth  Shape      Curve Name/Params            N/A      Fevap    Psi      Ksat     IMD
;;-------------- -------- ---------- ----------- ---------- ---------------------------- -------- --------          -------- --------


[CONDUITS]
;;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset  InitFlow   MaxFlow
;;-------------- ---------------- ---------------- ---------- ---------- ---------- ---------- ---------- ----------


[OUTLETS]
;;Name           From Node        To Node          Offset     Type            QTable/Qcoeff    Qexpon     Gated
;;-------------- ---------------- ---------------- ---------- --------------- ---------------- ---------- --------


[XSECTIONS]
;;Link           Shape        Geom1            Geom2      Geom3      Geom4      Barrels    Culvert
;;-------------- ------------ ---------------- ---------- ---------- ---------- ---------- ----------


[CURVES]
;;Name           Type       X-Value    Y-Value
;;-------------- ---------- ---------- ----------


[REPORT]
;;Reporting Options
SUBCATCHMENTS ALL
NODES ALL
LINKS ALL

[TAGS]

[MAP]
DIMENSIONS 1649303.155 4942192.850 1656007.105 4948224.150
Units      None

[COORDINATES]
;;Node           X-Coord            Y-Coord
;;-------------- ------------------ ------------------


[VERTICES]
;;Link           X-Coord            Y-Coord
;;-------------- ------------------ ------------------
    '''
    template=template.split('\n')
    return template