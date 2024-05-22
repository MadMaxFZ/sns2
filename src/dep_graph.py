import networx as nx
import pyvis

# Create a networkx graph object
G = nx.DiGraph()

# Add nodes to the graph
for package in project_packages:
    G.add_node(package)

# Add edges to the graph
for package in project_packages:
    for dependency in package.dependencies:
        G.add_edge(package, dependency)

# Create a pyvis network object
network = pyvis.network.Network()

# Add the nodes and edges from the networkx graph object to the pyvis network object
for node in G.nodes():
    network.add_node(node)

for edge in G.edges():
    network.add_edge(edge[0], edge[1])

# Visualize the graph
network.show('dependency_graph.html')