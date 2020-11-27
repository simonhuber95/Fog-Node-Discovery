import geopandas
import matplotlib.pyplot as plt
import numpy as np
# use ggplot style for more sophisticated visuals
plt.style.use('ggplot')


def visualize_movements(env, map_file=None, EPSG="EPSG:31468"):
    plt.ion()
    fig, ax = plt.subplots()
    client_x, client_y = [], []
    client_sc = ax.scatter(client_x, client_y)
    node_x, node_y = [], []
    node_sc = ax.scatter(node_x, node_y)
    (x_lower, x_upper, y_lower, y_upper) = env.boundaries
    plt.xlim(x_lower, x_upper)
    plt.ylim(y_lower, y_upper)
    plt.draw()

    while True:

        client_x = [client["obj"].get_coordinates()[0]
                    for client in env.clients]
        client_y = [client["obj"].get_coordinates()[1]
                    for client in env.clients]
        node_x = [node["obj"].get_coordinates()[0]
                  for node in env.nodes]
        node_y = [node["obj"].get_coordinates()[1]
                  for node in env.nodes]

        client_sc.set_offsets(np.c_[client_x, client_y])
        node_sc.set_offsets(np.c_[node_x, node_y])
        fig.canvas.draw_idle()
        ax.set_title(env.now)
        plt.pause(0.001)
        yield env.timeout(5)


def visualize_vivaldi(env, EPSG="EPSG:31468"):

    plt.ion()
    fig, ax = plt.subplots()
    node_x, node_y = [], []
    node_sc = ax.scatter(node_x, node_y)
    # client_x, client_y = [], []
    # client_sc = ax.scatter(client_x, client_y)
    plt.xlim(-1, 1)
    plt.ylim(-1, 1)
    plt.draw()
    while True:

        node_x = [node["obj"].vivaldiposition.getLocation()[0]
                  for node in env.nodes]
        node_y = [node["obj"].vivaldiposition.getLocation()[1]
                  for node in env.nodes]
        # client_x = [client["obj"].vivaldiposition.getLocation()[0]
        #             for client in env.clients]
        # client_y = [client["obj"].vivaldiposition.getLocation()[1]
        #             for client in env.clients]

        node_sc.set_offsets(np.c_[node_x, node_y])
        # client_sc.set_offsets(np.c_[client_x, client_y])
        fig.canvas.draw_idle()
        plt.pause(0.001)
        yield env.timeout(5)


def visualize_client_performance(env, runtime):
    plt.ion()
    hl, = plt.plot([], [])
    # client_x, client_y = [], []
    # client_sc = ax.scatter(client_x, client_y)
    plt.xlim(0, runtime)
    plt.ylim(0, 0.02)
    plt.draw()
    while True:
        performance_i = [
            client["obj"].out_performance for client in env.clients]
        hl.set_xdata(np.append(hl.get_xdata(), env.now))
        hl.set_ydata(np.append(hl.get_ydata(), np.mean(performance_i)))

        plt.draw()
        plt.pause(0.001)
        yield env.timeout(1)


def visualize_node_performance(env, runtime):
    plt.ion()
    hl, = plt.plot([], [])
    plt.xlim(0, runtime)
    plt.ylim(0, 0.05)
    plt.draw()
    while True:
        performance_i = [
            node["obj"].connect_performance for node in env.nodes]
        hl.set_xdata(np.append(hl.get_xdata(), env.now))
        hl.set_ydata(np.append(hl.get_ydata(), np.nanmean(performance_i)))

        plt.draw()
        plt.pause(0.001)
        yield env.timeout(1)

    