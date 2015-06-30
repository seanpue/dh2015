def draw_parser_graph(g):
    num_nodes = len(g.nodes())
    colors = [None]*num_nodes
    labels = {}#[None]*num_nodes
    node_sizes = [None]*num_nodes
    node_shapes = {}#['d']*num_nodes
    len(g.nodes())
    #for n,d in g.nodes(data=True)
    len(colors)

    for n,d in g.nodes(data=True):
        node_shapes[n] = 'd'
        if n==0:
            colors[n] = '#00FF00'
            labels[n] = 'Start'
            node_sizes[n] = 400

        elif d.get('token'):
            colors[n] = '#BA2CCB'
            labels[n] = d['token']
            node_sizes[n] = 600
        else:
 # something wrong here
            colors[n] = '#2CBAFB'
            if not 'found' in d:    
                labels[n]=""#"***********"
            else:# continue
                labels[n] = d['found']
            node_sizes[n] = 300
    import matplotlib.pyplot as plt
    plt.figure(figsize=(15,15))


    nx.draw(g,#node_size=node_sizes,#[G.population[v] for v in H],
            node_color=colors,node_size=node_sizes,node_shape='o',#node_shapes,
            edge_color='#A0A0A0',font_size=10,
            labels=labels)
