
import json
import ntpath

from modeci_mdf.standard_functions import mdf_functions, create_python_expression, _add_mdf_function
from typing import List, Tuple, Dict, Optional, Set, Any, Union
from modeci_mdf.utils import load_mdf, print_summary
from modeci_mdf.mdf import *
from modeci_mdf.full_translator import *
from modeci_mdf.execution_engine import EvaluableGraph

import argparse
import sys

def main():

    parser = argparse.ArgumentParser(description=' Running the translator to stateful parameters')
    parser.add_argument('--dt', default=5e-05, type=float,  help='time increment')
    parser.add_argument('--run', default=False, type=bool,  help='Run the graph')



    args = parser.parse_args()
    print(args)
    file_path = 'States.json'
    data = convert_states_to_stateful_parameters(file_path, args.dt)
    # print(data)
    with open('Translated_'+ file_path, 'w') as fp:
        json.dump(data, fp,  indent=4)


    if args.run:

        f = open(file_path)
        data = json.load(f)
        filtered_list = ['parameters','functions', 'states','output_ports','input_ports']
        all_nodes = []
        def nodeExtractor(nested_dictionary: Dict[str, Any] = None):
            """Extracts all the node objects in the graph
            Args:
                nested_dictionary: input data
            Returns:
                Dictionary of node objects
            """
            for k, v in nested_dictionary.items():
                if isinstance(v, dict) and k in 'nodes':
                    all_nodes.append(v.keys())
                elif isinstance(v, dict):
                    nodeExtractor(v)
        nodeExtractor(data)
        nodes_dict = dict.fromkeys(all_nodes[0])
        

        for key in list(nodes_dict.keys()):
            nodes_dict[key] = {}

        def parameterExtractor(nested_dictionary: Dict[str, Any] = None):
            """ Extracts Parameters, states, functions, input and output ports at each node object
            Args:
                nested_dictionary: Input Data
            Returns:
                stores states, parameters, functions, input and output ports
            """
            for k, v in nested_dictionary.items():
                if isinstance(v, dict) and k in list(nodes_dict.keys()):
                    for kk, vv in v.items():
                        if isinstance(vv, dict) and kk in filtered_list:
                            nodes_dict[k][kk] = vv
                if isinstance(v, dict):
                    parameterExtractor(v)
        parameterExtractor(data)
        arg_dict = {}
        def get_arguments(d:Dict[str, Any] = None):
            """ Extracts all parameters including stateful,dt for each node object
            Args:
                d: Node level dictionary with filtered keys
            Returns:
                all parameters for each node object
            """
            for key in d.keys():
                vi = []
                flag = 0
                if 'parameters' in d[key].keys():
                    vi += list(d[key]['parameters'].keys())
                if 'states' in d[key].keys():
                    vi += list(d[key]['states'].keys())
                if 'states' in d[key].keys():
                    for state in d[key]['states'].keys():
                        if 'time_derivative' in d[key]['states'][state].keys():
                            flag = 1
                        if flag == 1 and 'dt' not in vi :
                            vi.append('dt')

                arg_dict[key] = vi
        get_arguments(nodes_dict)

        time_derivative_dict = {}
        def get_time_derivative(d: Dict[str, Any] = None):
            """get time_derivative expression for each state variable
            Args:
                d: Node level dictionary with filtered keys
            Returns:
                store time_derivative expression for each state variable
            """
            for key in d.keys():
                vi = []
                li = []
                temp_dic = {}
                if 'states' in d[key].keys():
                    for state in d[key]['states'].keys():
                        li.append(state)
                        if 'time_derivative' in d[key]['states'][state].keys():
                            vi.append(d[key]['states'][state]['time_derivative'])
                        else:
                            vi.append(None)
                for i in range(len(vi)):
                    temp_dic[li[i]] = vi[i]
                time_derivative_dict[key] = temp_dic
        get_time_derivative(nodes_dict)

        for node, states in time_derivative_dict.items():
            for state in states.keys():
                if time_derivative_dict[node][state] is not None:
                    _add_mdf_function("evaluate_{}_{}_next_value".format(node, state),
                                      description="computing the next value of stateful parameter {}".format(state),
                                      arguments=arg_dict[node], expression_string=str(state) + "+" "(dt*" + str(
                            time_derivative_dict[node][state]) + ")", )
                else:
                    print(
                        'No need to create MDF function for node %s, state %s since there is no expression for time derivative!' % (
                        node, state))

        verbose = True
                
            
        mod_graph = load_mdf('Translated_%s'% file_path).graphs[0]
        eg = EvaluableGraph(mod_graph, verbose)
        
        mod_graph_old = load_mdf(file_path).graphs[0]
        eg_old = EvaluableGraph(mod_graph_old, verbose)
        

        duration= 2
        t = 0
        recorded = {}
        times = []
        s = []
        s_old=[]
        while t<=duration:

           
            print("======   Evaluating at t = %s  ======"%(t))
            
            if t == 0:
                eg_old.evaluate() # replace with initialize?
            else:
                eg_old.evaluate(time_increment=args.dt)

            # levels.append(eg.enodes['sine_node'].evaluable_stateful_parameters['level'].curr_value) 
            # t+=args.dt
        
            eg.evaluate()
            
            # print("time first>>>",type(t))
            t = eg.enodes['sine_node'].evaluable_stateful_parameters['time'].curr_value
            times.append(eg.enodes['sine_node'].evaluable_stateful_parameters['time'].curr_value)

            # times.append(t)            
            s_old.append(eg_old.enodes['sine_node'].evaluable_outputs['out_port'].curr_value)
            
            s.append(eg.enodes['sine_node'].evaluable_outputs['out_port'].curr_value)
            
            
        print(s_old[:10], s[:10])
        import matplotlib.pyplot as plt
        plt.plot(times,s)
        

        plt.show()
        plt.savefig('translated_levelrate_sineplot.jpg')



if __name__ == "__main__":
    main()

