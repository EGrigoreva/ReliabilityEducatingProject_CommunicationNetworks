# Communications Network Reliability Educational Project



This is an *educational* project enabling the students in-depth understanding of the communication network reliability concepts. It supports the [Communication Network Reliability course](https://www.lkn.ei.tum.de/en/teaching/lectures/communication-network-reliability/) offered by the Chair of Communication Networks in the Technical University of Munich. The project solves the network planning problems and provides the necessary data for the results analysis. The students are expected to write a post-processing script that evaluates graph properties, their connection to the network parameters as connection availability. 



The main goal of the project is to let students analyze the network planning options from technical and economical points of view, based on the typical network planning project outcome. This is puts the student into prospective of the Network Operator that has to make some decisions based on the available information.



There are two parts of the project: core and access networks. The core network protection is optimal, i.e., formulated and solved as a set of optimization problems.  Access network protection relies on [heuristics](https://mediatum.ub.tum.de/doc/1403207/36324.pdf). In the access case only the feeder fiber is protected. All the implementation has been finalized in the ArcGIS and Gurobi Python scripts, so that the students can concentrate on the analysis part.



## Requirements


This project relies on the following software:
	
1. [**ArcGIS Desctop**](http://desktop.arcgis.com/en/), i.e., ArcMap 10.3.1
	
2. [**Gurobi**](https://www.gurobi.com/) 7.0.2 for win32 (for ArcMap 10.3.1)

ArcGIS requires a payed license, Gurobi has a free scientific license.

Installation guidlines are in the file HowTos.pdf




## Description


The students get a ready for work package with all the needed input data as core network topologies and access network topologies.



**Core network** topologies are imported from [SNDlib](http://sndlib.zib.de). They are real examples of the existing core topologies that are imported to ArcGIS and visualized there. For every original core network topology there is a slightly changed one by deleting or adding some links. There are four demands distributions.



There are five protection options:

- Unprotected (for comparison)

- Link disjoint protection, no capacity constraint

- Link disjoint protection with capacity constrant

- Node disjoint protection with capacity constrant

- Link disjoint protection with capacity constrant and link Shared Risk Groups (SRGs)

- Node disjoint protection with capacity constrant and node Shared Risk Groups (SRGs)



Each option features more optimization constraints. The link, i.e., arc, capacity is an input from the user.
One can try finding the minimum cpapacity, where the optimization is still feasible. 



The results are stored in the specified folders, i.e., in .pkl files. The files store the graph properties, lengths in meters and the optimization results. 



The **Access Networks** are the Fiber-To-The-Building one stage Gigabit Passive Optical Networks (GPON) architectures planned based on the geographical data from [Open Street Maps](https://www.openstreetmap.org). The OSM data has been prepared for the planning process. For the residential users scenario, only the Feeder Fiber is protected. The scenario can be extended with the point-to-point Base Station connections and their protection. 



The analysis can be as follows:

- Influence of the splitting ratio of the Power Splitter. The proposed options are 16, 32, 64, based on the state-of-the-art implementations.

- Disjoint shortest path protection vs. ring protection

.

The results include the details on the fiber lengths.




## Data 


- **HowTos.pdf**: is a full description of the installation process and common problems. It explains how to link the arcpy distribution and Gurobi for optimization. It also includes most common issues with the installation. 

- **ProjectHints&Tricks.pdf**: describes little things that make the project much easier to work with, especially with no familiarity with ArcMap.

- **quick_demo.wmv**: a demo video of the core part tool.

- **AccessTopologies.gdb.zip**: a .zip of the ArcMap database with the access topologies. The format of the database is custom and is seen by other applications as a folder with encrypted files. Shall be unzipped but never changed outside the ArcGIS environment. 

- **CoreTopologies.gdb.zip**: a .zip of the ArcMap database, where the planning results will be stored. The results are overwritten in the next run. The format of the database is custom and is seen by other applications as a folder with encrypted files. Shall be unzipped but never changed outside the ArcGIS environment. 

- **AccessNetwork.mxd**: ArcMap project file that stores the pointers to the data, used for visualization. 

- **CoreNetwork.mxd**: ArcMap project file that stores the pointers to the data, used for visualization. 
- **CoreNetworkTopologies**: the folder with the saved examples of the core topologies (can be extended).

- **ReliabilityProjectScripts**: the relevant scripts for the tool. Without this folder the toolbox will not work.

- **ReliabilityProject.tbx**: ArcMap toolbox, the actual tool to work with.



## Python scripts


In general, there is no need to go into the code. The toolbox is fully functional and there is no Python knowledge required. However, the code can be easily extended. 



Core network:

- **CoreNetworkProtection&#46;py**: the main script file that does the transfer the core network to the ArcMap, to Gurobi, does optimization and passes the results back to ArcMap for visualization.

- **PrepareLines&#46;py**: prepares the street segments for the graph analysis by adding origin and destination node.

- **optimize_ilp.py**: optimization formulations for Gurobi.

- **srgs_dumping.py**: formatting for the SRGs.



Access network:

- **AccessNetworkProtection&#46;py**: does the main access planning and processing. Requires Network Analyst license, or in general advanced ArcGIS license. 

- **RingProtection&#46;py**: uses ArcMap Travelling Salesman problem formulation for the ring protection. Requires Network Analyst license, or in general advanced ArcGIS license. 

- **ShortestPathRouting&#46;py**: does what it says with pre-implemented ArcGIS tools.

- **ClusteringLocationAllocation&#46;py**: does what it says with pre-implemented ArcGIS tools.




## Contributors

The ArcGIS part was prepared by Elena Grigoreva, e.v.grigoryeva@gmail.com, the ILPs are prepared by Petra Stojsavljevic, Chair of Communication Networks, TUM Department of Electrical and Computer Engineering, Technical University of Munich. 
