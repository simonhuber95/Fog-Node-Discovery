import geopandas
import matplotlib.pyplot as plt
import numpy as np
# use ggplot style for more sophisticated visuals
plt.style.use('ggplot')


def visualize_movements(env, map_file=None, EPSG="EPSG:31468"):
    img = plt.imread("Maps_Background.png")
    plt.ion()
    fig, ax = plt.subplots()
    client_x, client_y = [], []
    client_sc = ax.scatter(client_x, client_y)
    node_x, node_y = [], []
    node_sc = ax.scatter(node_x, node_y)
    (x_lower, x_upper, y_lower, y_upper) = env.boundaries
    # ax.imshow(img)
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
        ax.imshow(img, extent = [x_lower, x_upper, y_lower, y_upper])
        plt.pause(0.001)
        yield env.timeout(5)

def full_nodes_over_time(env, runtime):
    plt.ion()
    hl, = plt.plot([], [])
    # client_x, client_y = [], []
    # client_sc = ax.scatter(client_x, client_y)
    plt.xlim(0, runtime)
    plt.ylim(0, 30)
    plt.draw()
    while True:

        performance_i = sum((1 for node in env.nodes if node["obj"].slots == len(node["obj"].clients)))
        
        hl.set_xdata(np.append(hl.get_xdata(), env.now))
        hl.set_ydata(np.append(hl.get_ydata(), np.mean(performance_i)))

        plt.draw()
        plt.pause(0.001)
        yield env.timeout(1)
        
def unique_discovery_over_time(env, runtime):
    plt.ion()
    hl, = plt.plot([], [])
    # client_x, client_y = [], []
    # client_sc = ax.scatter(client_x, client_y)
    plt.xlim(0, 60)
    plt.ylim(0, 30)
    plt.draw()
    while True:
        discoveries = []
        for node in env.nodes:
            discovery = [message.body for message in node.get('obj').out_msg_history if message.msg_type == 2 and message.timestamp > env.now-1]
            discoveries = discoveries + list(set(discovery) - set(discoveries))
        performance_i = len(set(discoveries))
        hl.set_xdata(np.append(hl.get_xdata(), env.now))
        hl.set_ydata(np.append(hl.get_ydata(), performance_i))

        plt.draw()
        plt.pause(0.001)
        yield env.timeout(1)


def visualize_reconnections_over_time(env, runtime):
    plt.ion()
    hl, = plt.plot([], [])
    # client_x, client_y = [], []
    # client_sc = ax.scatter(client_x, client_y)
    plt.xlim(0, runtime)
    plt.ylim(0, 500)
    plt.draw()
    while True:
        performance_i = 0
        for client in env.clients:
            if client["obj"].out_msg_history and len(client["obj"].out_msg_history)>5:
                performance_i += sum((1 for message in client["obj"].out_msg_history[-5:] if message.msg_type == 2 and message.timestamp > env.now - 1))
                # performance_i = [msg for msg in client["obj"].out_msg_history[-5] if message.msg_type == 2 and message.timestamp > self.env.now - 1]
                # performance_i += len(performance_i)
        hl.set_xdata(np.append(hl.get_xdata(), env.now))
        hl.set_ydata(np.append(hl.get_ydata(), performance_i))

        plt.draw()
        plt.pause(0.001)
        yield env.timeout(1)

def visualize_latency_over_time(env, runtime):
    plt.ion()
    hl, = plt.plot([], [])
    # client_x, client_y = [], []
    # client_sc = ax.scatter(client_x, client_y)
    plt.xlim(0, runtime)
    plt.ylim(0, 7)
    plt.draw()
    while True:
        performance_i = [client["obj"].out_msg_history[-1].latency*1000 for client in env.clients if client["obj"].out_msg_history]
        
        hl.set_xdata(np.append(hl.get_xdata(), env.now))
        hl.set_ydata(np.append(hl.get_ydata(), np.mean(performance_i)))

        plt.draw()
        plt.pause(0.001)
        yield env.timeout(1)
    
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

    