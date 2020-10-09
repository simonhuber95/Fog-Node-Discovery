import geopandas
import matplotlib.pyplot as plt


def visualize_movements(env, map_file, EPSG="EPSG:31468"):
    fig, ax = plt.subplot()
    gdf = geopandas.read_file(map_file)
    gdf = gdf.to_crs("EPSG:31468")
    client_x = []
    client_y = []
    for client in env.clients:
        cl = client["obj"]
        x = cl.phy_x
        y = cl.phy_y
        client_x.append(x)
        client_y.append(y)

    gdf.plot(ax = ax)
    gdf.show()
    #plt.plot(client_x, client_y, ax = ax)
    
