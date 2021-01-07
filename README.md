# Master Thesis — Simon Huber

## Identifying nearest nodes in distributed Fog Platforms with mobile clients

This repository is an implementation of a simulation to gain insights into the nearest node discovery in a distributed Fog Platform.
It supports several scenarios. The scenarios used in the Master Thesis are:

### Default Scenario:

- Simulation Area is a sub-area of Berlin
- Fog Nodes are scattered over the area, placement is partially derived from the location of cell towers
- Clients move within the boundaries of the simulation are and stop if they step out of bounds

### All Berlin Scenario:

- Simulation Area is whole Berlin
- Fog Nodes are scattered over the area, placement is partially derived from the location of cell towers
- Clients move within Berlin, no bounds for the clients are set

### Germany Scenario:

- Simulation Area is whole Germany
- Fog Nodes are placed in every major city of Germany (see main.py line 48 for more information)
- Clients move within Berlin, no bounds for the clients are set

---

## How to use the simulation:

Step 1: Install the Dependencies from environment.yml with Anaconda:

```
conda env create -f environment.yml
```

Step 2: Activate Anaconda environment:

```
conda activate fog-node-discovery
```

Step 3: Set the parameters in config.yml

Simulation:

- **runtime**: The runtime of the simulation in seconds
- **area**: x and y translation in meter of selected area. Results in an area of x\*y km^2
- **area_selection**: Selection Method of the area, either _random_, _center_, or _all_. _all_ will not account for the defined area but take the whole area
- **verbose**: Verbosity of the simulation. Either _True_ or _False_.
- **scenario**: Scenario used for the simulation, either _berlin_ or _germany_. Standard scenario uses _berlin_ combined with area selection _random_ or _center_
- **discovery_protocol**: Defines the discovery protocol used for the simulation. Either _baseline_, _vivaldi_, _meridian_, _random_

Clients:

- **path**: Path to the reduced Open Berlin Scenario. Usually _data/reduced_berlin_v5.4-10pct.plans.xml_
- **max_clients**: Maximum amount of clients used for the simulation. _None_ if no max clients, else any positive integer
- **client_ratio**: How many clients are put in the simulation compared to the amount of slots of the Fog Platform. Should be a float between _0_ and _1_. Upper limit is still defined by max_clients if set to an integer
- **latency_threshold**: The latency threshold in seconds. Usually a float like _0.005_
- **roundtrip_threshold**: The roundtrip threshold in seconds. Usually a float like _0.010_
- **timeout_threshold**: The timeout threshold in seconds. Usually a float like _0.100_

Fog Nodes:

- **path**: Path to the cell tower locations. Usually _data/cell_towers/cell_towers.shp_
- **min_nodes**: Minumum amount of Fog Nodes for the simulation. Resamples the simulation area until enough nodes are found. _None_ if no min nodes, else integer usually _1_
- **max_nodes**: Minumum amount of Fog Nodes for the simulation. _None_ if no max nodes, else integer
- **slot_scaler**: Scales the amount of slots of the Fog Nodes. Non-negative integer, usually _1_
- **unlimited_bandwidth**: Whether or not the bandwidth of the Fog Nodes is unlimited. Overrides the amount of slots with float('inf) if True. Either _True_ or _False_

Boundaries:

- **x_min**: Lower x boundary coordinates in Gaus-Krüger 4 for the Berlin area. Usually _4573063.1296_
- **x_max**: Upper x boundary coordinates in Gaus-Krüger 4 for the Berlin area. Usually _4620052.7497_
- **y_min**: Lower y boundary coordinates in Gaus-Krüger 4 for the Berlin area. Usually _5800675.0537_
- **y_max:** Upper y boundary coordinates in Gaus-Krüger 4 for the Berlin area. Usually _5839575.7712_

Step 4: Run the simulation

```
python main.py
```

Measurements are saved ./measurements/ folder
