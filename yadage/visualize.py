import shlex
import pydotplus
import networkx as nx
from networkx.drawing.nx_pydot import write_dot
import logging
import subprocess

log = logging.getLogger(__name__)

def simple_stage_graph(workflow):
    graph = nx.DiGraph()
    for stage in workflow['stages']:
        graph.add_node(stage['name'])
        for x in stage['dependencies']:
            graph.add_edge(x,stage['name'])
    return graph

def write_stage_graph(workdir,workflow):
    graph = simple_stage_graph(workflow)
    write_dot(graph,'{}/adage_stages.dot'.format(workdir))
    subprocess.call(shlex.split('dot -Tpdf {}/yadage_stages.dot'.format(workdir)),
                    stdout = open('{}/yadage_stages.pdf'.format(workdir),'w'))
    
def write_prov_graph(workdir,adagegraph,workflow):
    provgraph = pydotplus.graphviz.Graph()
    
    stagedict = {stage['name']:stage for stage in workflow['stages']}
    for stage in nx.topological_sort(simple_stage_graph(workflow)):

        for x,step in [(step.identifier,step) for step in stagedict[stage]['scheduled_steps']]:

            stagecluster = pydotplus.graphviz.Cluster(graph_name = stage, label = stage)
            provgraph.add_subgraph(stagecluster)

            pars = step.task.attributes.copy()
    
            # print pars
            parstrings =  [': '.join((k,str(pars[k]))) for k in sorted(pars.keys())]
            
            step_report = u'''\
{name}
______
{pars}
'''
    
            rep = step_report.format(name = step.name,
                                     pars = '\n'.join(parstrings))
    
            attr = {'color':'red','label':rep,'shape':'box'}    
            stagecluster.add_node(pydotplus.graphviz.Node(name = x, obj_dict = None, **attr))
    
            #add outputs circles
            for k,v in step.result_of().iteritems():
                for i,y in enumerate(v if type(v)==list else [v]):
                    name = 'output_{}_{}_{}'.format(step.task.name,k,i)
                    
    
                    attr = {'label':'{}_{}: {}'.format(k,i,y),'color':'blue'}
                    stagecluster.add_node(pydotplus.graphviz.Node(name, obj_dict = None, **attr))
    
                    provgraph.add_edge(pydotplus.graphviz.Edge(x,name))
    
            nodeinfo =  step.task
            
            #connect node to outputs
            #if input information is there, add edge to input
            if nodeinfo.inputs:
                for k,inputs_from_node in nodeinfo.inputs.iteritems():
                    for one in inputs_from_node:
                        depname = 'output_{}_{}_{}'.format(k,one[0],one[1])
                        provgraph.add_edge(pydotplus.graphviz.Edge(depname,x))
    
    
            #if not, we'll just add to the dependent node directly
            else:
                for pre in adagegraph.predecessors(x):
                    log.warning('really no inputs to this node but predecessors?: %s',x)
                    provgraph.add_edge(pydotplus.graphviz.Edge(pre,x))
            
                
        
    with open('{}/yadage_workflow_instance.dot'.format(workdir),'w') as dotfile:
        dotfile.write(provgraph.to_string())

    subprocess.call(shlex.split('dot -Tpdf {}/yadage_workflow_instance.dot'.format(workdir)),
                    stdout = open('{}/yadage_workflow_instance.pdf'.format(workdir),'w'))