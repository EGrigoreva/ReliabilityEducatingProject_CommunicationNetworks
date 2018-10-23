# -------------------------------------------------------------
# Name:             CoreNetworkProtection.py
# Purpose:          Connect optimization problem and real geographical data
# Author:           Elena Grigoreva, e.v.grigoryeva@gmail.com (Technical University of Munich)
# About author:     https://egrigoreva.github.io/
# Created:          12/10/2018
# Copyright:        (c) Chair of Communication Networks, Department of Electrical and Computer Engineering,
#                   Technical University of Munich
# ArcGIS Version:   10.3.1
# Python Version:   2.7
# -------------------------------------------------------------

import sys
sys.path.insert(0, r"C:\Python27\ArcGIS10.3\Lib\site-packages")
import arcpy
from optimize_ilp import *
import pickle
import os

arcpy.env.overwriteOutput = True


# Read network
def read_network(name, path='#'):
    if path == '#':
        topo = name + '.graphml'
    else:
        name_full = name + '.graphml'
        topo = os.path.join(path, name_full)

    g = nx.read_graphml(topo)
    return g


# Read demands
def read_demand(name, path = '#'):
    if path == '#':
        filename = name + '.txt'
    else:
        filename = os.path.join(path, name + '.txt')

    fp = open(filename)
    lines = fp.readlines()
    # Read demands from file in the format
    # "source" "destination" "capacity"
    R = {}
    for line in lines:
        src, dst, cap = line.split()
        R[(src, dst)] = int(cap)

    fp.close()
    return R


def graph_properties(G):
    graph_properties_dic = {'#nodes': nx.number_of_nodes(G), '#edges': nx.number_of_edges(G), 'diameter': nx.diameter(G)}

    node_degree_all = nx.degree(G)
    graph_properties_dic['average_node_degree'] = float(sum(node_degree_all.values())) / float(len(node_degree_all))

    edge_lengths_all = nx.get_edge_attributes(G, "weight")
    graph_properties_dic['average_edge_length'] = float(sum(edge_lengths_all.values())) / float(len(edge_lengths_all))
    graph_properties_dic['maximum_edge_length'] = max(edge_lengths_all.values())

    return graph_properties_dic


####################################################################################################################
def topology_from_graph(g, spatial_reference, fd_path, name):
    # Input topology nodes
    node_values = []
    for n in g.nodes(data=True):
        node_values.append((n[0], (n[1]['Longitude'], n[1]['Latitude'])))

    nodes_name = 'nodes_{0}'.format(name)
    nodes_path = os.path.join(fd_path, nodes_name)
    check_exists(nodes_path)
    arcpy.CreateFeatureclass_management(fd_path, nodes_name, 'POINT', spatial_reference=spatial_reference)
    arcpy.AddField_management(nodes_path, 'NAME', 'string')

    with arcpy.da.InsertCursor(nodes_path, ['NAME', 'SHAPE@XY']) as n_cursor:
        for node in node_values:
            n_cursor.insertRow(node)

    arcpy.AddGeometryAttributes_management(nodes_path, 'POINT_X_Y_Z_M')
    # Create a point layer
    nodes_layer_name = os.path.join('in_memory', nodes_name)
    nodes_layer = arcpy.MakeFeatureLayer_management(nodes_path, nodes_layer_name)
    features_lines = []

    # Input topology links
    for e in g.edges(data=True):
        clause = "NAME='{0}' OR NAME='{1}'".format(str(e[0]), str(e[1]))
        arcpy.SelectLayerByAttribute_management(nodes_layer, 'NEW_SELECTION', clause)

        # Create an array of points
        array_tmp = arcpy.Array()
        node = arcpy.Point()
        with arcpy.da.SearchCursor(nodes_layer, ['SHAPE@X', 'SHAPE@Y']) as cursor:
            for row in cursor:
                # list_tmp.append(arcpy.Point(row[0], row[1]))
                node.X = row[0]
                node.Y = row[1]
                array_tmp.append(node)
        tmp = arcpy.Polyline(array_tmp, spatial_reference)
        features_lines.append(tmp)

    lines_name = 'lines_{0}'.format(name)
    lines_path = os.path.join(fd_path, lines_name)
    check_exists(lines_path)
    arcpy.CopyFeatures_management(features_lines, lines_path)

    return nodes_path, lines_path


####################################################################################################################
def edges_distance(g, nodes_path, lines_path, fds_path):
    distance_dict = {}

    import PrepareLines as pl

    pl.add_fields(nodes_path, lines_path, fds_path)

    with arcpy.da.SearchCursor(lines_path, ["OriginID", 'DestinationID', 'LENGTH_GEO']) as rows:
        for row in rows:
            g[row[0]][row[1]]["weight"] = round(row[2], 2)
            distance_dict[(row[0], row[1])] = round(row[2], 2)
            distance_dict[(row[1], row[0])] = round(row[2], 2)
    return distance_dict


####################################################################################################################
def edges_capacity_uniform(g, link_path, distance_dict_in, capacity_in):

    lines_layer = arcpy.MakeFeatureLayer_management(link_path, 'lines_layer')
    arcpy.AddField_management(lines_layer, 'Capacity', 'FLOAT')

    with arcpy.da.UpdateCursor(link_path, 'Capacity') as cursor:
        for row in cursor:
            row[0] = capacity_in
            cursor.updateRow(row)

    for key in distance_dict_in:
        g[key[0]][key[1]]["capacity"] = capacity_in

    return


####################################################################################################################
def add_demands_to_map(demands, node_path, demands_name, network_name, fd_path):
    nodes_layer_name = os.path.join('in_memory', 'nodes')
    nodes_layer = arcpy.MakeFeatureLayer_management(node_path, nodes_layer_name)

    for d in demands:
        clause = "NAME='{0}' OR NAME='{1}'".format(str(d[0]), str(d[1]))
        arcpy.SelectLayerByAttribute_management(nodes_layer, 'NEW_SELECTION', clause)

        demand_out_name = '{0}_{1}_{2}{3}'.format(demands_name, network_name, str(d[0]), str(d[1]))
        demand_out_path = os.path.join(fd_path, demand_out_name)
        check_exists(demand_out_path)
        arcpy.CopyFeatures_management(nodes_layer, demand_out_path)

    arcpy.Delete_management('in_memory')

    return


####################################################################################################################
def add_paths_to_map(link_path, name, path, path_out):

    lines_layer_name = os.path.join('in_memory', 'lines')
    check_exists(lines_layer_name)
    lines_layer = arcpy.MakeFeatureLayer_management(link_path, lines_layer_name)

    for p in path:
        path_out_name = '{0}_{1}{2}'.format(name, str(p[0]), str(p[1]))
        arcpy.AddMessage(path_out_name)
        path_out_path = os.path.join(path_out, path_out_name)
        check_exists(path_out_path)

        arcpy.SelectLayerByAttribute_management(lines_layer, 'CLEAR_SELECTION')
        k = 0
        for l in path[p]:

            clause = "OriginID ='{0}' AND DestinationID ='{1}'".format(str(l[0]), str(l[1]))
            arcpy.AddMessage(clause)
            arcpy.SelectLayerByAttribute_management(lines_layer, 'ADD_TO_SELECTION', clause)
            select_count = int(arcpy.GetCount_management(lines_layer).getOutput(0))

            if select_count == k:
                clause = "OriginID ='{0}' AND DestinationID ='{1}'".format(str(l[1]), str(l[0]))
                arcpy.SelectLayerByAttribute_management(lines_layer, 'ADD_TO_SELECTION', clause)

            k += 1

        arcpy.CopyFeatures_management(lines_layer, path_out_path)
        arcpy.Delete_management('in_memory')
    return


####################################################################################################################
def check_exists(name):
    """
    This function check existence of the feature class, which name is specified, and deletes it, if it exists. Some 
    arcpy functions even with the activated overwrite output return errors if the feature class already exists

    :param name: check if this file already exists
    :return: 
    """
    if arcpy.Exists(name):
        arcpy.Delete_management(name)
    return


####################################################################################################################
def main(problems, database_path, path_demands, path_results, core_network_name, demands_name, capacity_uniform,
         srg_links, srg_nodes):
    """
    
    :param problems: python dictionary, keys are the ype of problem and the boolean saying if the problem has to be 
                     evaluated
                    {'Unprotected': False, 'Link_Disjoint': False, 
                    'Capacity': False, 'Node_Disjoint': False, 'SRG_Links': True, 'SRG_Nodes': False }
    :param database_path: a string with the full input database path, 
                          'D:\GISworkspace\4_Teaching\Reliability_project\ReliabilityProject.gdb'
    :param path_demands:  a string with the full path, where the demands are stored
    :param path_results:  a string with the path, where the .pkl results will be stored
    :param core_network_name: string name of the input topology
    :param demands_name: string with the name of the demands
    :param capacity_uniform: int, with the uniform capacity for each arc of the graph
    :param srg_links: string, name of the file where the .pkl is stored
    :param srg_nodes: string, name of the file where the .pkl is stored
    
    :return: graph properties; working and protection paths in .pkl files
    """

    # TODO Stop overwriting the files
    # TODO Change the capacity constraint: now its on one arc
    # TODO Add contraint for both arcs for link disjointness

    arcpy.AddMessage('Importing underlying core network topology: {0}.'.format(core_network_name))

    ####################################################################################################################
    # Import topology
    ####################################################################################################################
    spatial_reference = arcpy.SpatialReference(4326)
    g = read_network(core_network_name, path_demands)

    # name = arcpy.ValidateFieldName(core_network_name)
    fd_path = os.path.join(database_path, core_network_name)
    check_exists(fd_path)
    arcpy.CreateFeatureDataset_management(database_path, core_network_name, spatial_reference)

    node_path, link_path = topology_from_graph(g, spatial_reference, fd_path, core_network_name)

    distance_dict = edges_distance(g, node_path, link_path, fd_path)
    # arcpy.AddMessage(distance_dict)

    edges_capacity_uniform(g, link_path, distance_dict, capacity_uniform)

    output_file_dist = os.path.join(path_results, 'graph_distances_{0}.pkl'.format(core_network_name))

    with open(output_file_dist, 'wb') as f_d:
        pickle.dump(distance_dict, f_d)

    # with open(output_file_dist, 'rb') as f_d:
    #     test = pickle.load(f_d)
    #     arcpy.AddMessage(test)

    # Input demands
    demands = read_demand(demands_name, path_demands)
    add_demands_to_map(demands, node_path, demands_name, core_network_name, fd_path)

    arcpy.AddMessage('Importing demands: {0}.'.format(demands_name))
    arcpy.AddMessage(demands)

    ####################################################################################################################
    # Core network analysis
    ####################################################################################################################

    ####################################################################################################################
    # Graph analysis
    graph_properties_out = graph_properties(g)

    output_file_graph = os.path.join(path_results, 'graph_properties_{0}.pkl'.format(core_network_name))

    with open(output_file_graph, 'wb') as f_g:
        pickle.dump(graph_properties_out, f_g)

    ####################################################################################################################
    # Optimization

    if problems['Unprotected']:
        arcpy.AddMessage('~~~~ Unprotected paths ~~~~')
        distance, path = optimize_unprotected_path(g, distance_dict, demands)

        if distance != 0:
            path_name = 'Path_{0}_{1}_{2}'.format(demands_name, core_network_name, 'unprotected')
            add_paths_to_map(link_path, path_name, path, fd_path)

            result_unprotected = {'working_paths': path, 'working_distance': distance, 'demands': demands}

            arcpy.AddMessage('Working paths:')
            arcpy.AddMessage(path)
            arcpy.AddMessage('Working path lengths:')
            arcpy.AddMessage(distance)

            output_file = os.path.join(path_results, 'graph_properties_{0}_{1}_Unprotected.pkl'.format(core_network_name, demands_name))
            with open(output_file, 'wb') as f_u:
                pickle.dump(result_unprotected, f_u)

    if problems['Link_Disjoint']:
        arcpy.AddMessage('~~~~ Link disjoint paths ~~~~')
        distance1, distance2, path1, path2 = optimize_link_disjoint(g, distance_dict, demands)
        arcpy.AddMessage(distance1)
        arcpy.AddMessage(distance2)
        if distance1 != 0:
            working_path_name = 'WorkingPath_{0}_{1}_{2}'.format(demands_name, core_network_name, 'LinkDisjoint')
            add_paths_to_map(link_path, working_path_name, path1, fd_path)
            protection_path_name = 'ProtectionPath_{0}_{1}_{2}'.format(demands_name, core_network_name, 'LinkDisjoint')
            add_paths_to_map(link_path, protection_path_name, path2, fd_path)

            result_link_disjoint = {'working_paths': path1, 'working_distance': distance1, 'protection_path': path2,
                                    'protection_distance': distance2, 'demands': demands}

            arcpy.AddMessage('Working paths:')
            arcpy.AddMessage(path1)
            arcpy.AddMessage('Working path lengths:')
            arcpy.AddMessage(distance1)
            arcpy.AddMessage('Protection paths:')
            arcpy.AddMessage(path2)
            arcpy.AddMessage('Protection path lengths:')
            arcpy.AddMessage(distance2)

            output_file = os.path.join(path_results,
                                             'graph_properties_{0}_{1}_Link_Disjoint.pkl'.format(core_network_name,
                                                                                                 demands_name))
            with open(output_file, 'wb') as f_ld:
                pickle.dump(result_link_disjoint, f_ld)

    if problems['Capacity']:
        # Capacity constraint
        arcpy.AddMessage('~~~~ Link disjoint paths with capacity constraint ~~~~')
        distance1, distance2, path1, path2 = optimize_link_disjoint_cap(g, distance_dict, demands)

        if distance1 != 0:
            working_path_name = 'WorkingPath_{0}_{1}_{2}_cap'.format(demands_name, core_network_name, 'LinkDisjoint')
            add_paths_to_map(link_path, working_path_name, path1, fd_path)
            protection_path_name = 'ProtectionPath_{0}_{1}_{2}_cap'.format(demands_name, core_network_name, 'LinkDisjoint')
            add_paths_to_map(link_path, protection_path_name, path2, fd_path)

            result_link_capacity = {'working_paths': path1, 'working_distance': distance1, 'protection_path': path2,
                                    'protection_distance': distance2}

            arcpy.AddMessage('Working paths:')
            arcpy.AddMessage(path1)
            arcpy.AddMessage('Working path lengths:')
            arcpy.AddMessage(distance1)
            arcpy.AddMessage('Protection paths:')
            arcpy.AddMessage(path2)
            arcpy.AddMessage('Protection path lengths:')
            arcpy.AddMessage(distance2)

            output_file = os.path.join(path_results,
                                             'graph_properties_{0}_{1}_Link_Disjoint_Capacity.pkl'.format(core_network_name,
                                                                                                          demands_name))
            with open(output_file, 'wb') as f_cap:
                pickle.dump(result_link_capacity, f_cap)

    if problems['Node_Disjoint']:
        # Node disjoint
        arcpy.AddMessage('~~~~ Node disjoint paths with capacity constraint ~~~~')
        distance1, distance2, path1, path2 = optimize_node_disjoint_cap(g, distance_dict, demands)

        if distance1 != 0:
            working_path_name = 'WorkingPath_{0}_{1}_{2}_cap'.format(demands_name, core_network_name, 'NodeDisjoint')
            add_paths_to_map(link_path, working_path_name, path1, fd_path)
            protection_path_name = 'ProtectionPath_{0}_{1}_{2}_cap'.format(demands_name, core_network_name, 'NodeDisjoint')
            add_paths_to_map(link_path, protection_path_name, path2, fd_path)

            result_node_disjoint = {'working_paths': path1, 'working_distance': distance1, 'protection_path': path2,
                                    'protection_distance': distance2}

            arcpy.AddMessage('Working paths:')
            arcpy.AddMessage(path1)
            arcpy.AddMessage('Working path lengths:')
            arcpy.AddMessage(distance1)
            arcpy.AddMessage('Protection paths:')
            arcpy.AddMessage(path2)
            arcpy.AddMessage('Protection path lengths:')
            arcpy.AddMessage(distance2)

            output_file = os.path.join(path_results,
                                             'graph_properties_{0}_{1}_Node_Disjoint.pkl'.format(core_network_name,
                                                                                                 demands_name))
            with open(output_file, 'wb') as f_nd:
                pickle.dump(result_node_disjoint, f_nd)

    if problems['SRG_Links']:
        # SRGs links
        arcpy.AddMessage('~~~~ Link disjoint paths with capacity constraint and link SRGs~~~~')
        srg_links_path = os.path.join(path_demands, srg_links)

        if os.path.isfile(srg_links_path):
            with open(srg_links_path, 'rb') as f_srgs:
                srg_links = pickle.load(f_srgs)

            distance1, distance2, path1, path2 = optimize_link_disjoint_cap_srg_links(g, distance_dict, demands, srg_links)

            if distance1 != 0:
                working_path_name = 'WorkingPath_{0}_{1}_{2}_cap'.format(demands_name, core_network_name, 'SRG_links')
                add_paths_to_map(link_path, working_path_name, path1, fd_path)
                protection_path_name = 'ProtectionPath_{0}_{1}_{2}_cap'.format(demands_name, core_network_name, 'SRG_links')
                add_paths_to_map(link_path, protection_path_name, path2, fd_path)

                result_link_srg = {'working_paths': path1, 'working_distance': distance1, 'protection_path': path2,
                                   'protection_distance': distance2}

                arcpy.AddMessage('Working paths:')
                arcpy.AddMessage(path1)
                arcpy.AddMessage('Working path lengths:')
                arcpy.AddMessage(distance1)
                arcpy.AddMessage('Protection paths:')
                arcpy.AddMessage(path2)
                arcpy.AddMessage('Protection path lengths:')
                arcpy.AddMessage(distance2)

                output_file = os.path.join(path_results,
                                                 'graph_properties_{0}_{1}_SRG_Links.pkl'.format(core_network_name,
                                                                                                     demands_name))
                with open(output_file, 'wb') as f_lsrg:
                    pickle.dump(result_link_srg, f_lsrg)
        else:
            arcpy.AddMessage('The SRG links problem cannot be solved as there are no SRGs defined for this topology.')

    if problems['SRG_Nodes']:
        # SRGs nodes
        arcpy.AddMessage('~~~~ Node disjoint paths with capacity constraint and node SRGs~~~~')

        srg_nodes_path = os.path.join(path_demands, srg_nodes)

        if os.path.isfile(srg_nodes_path):
            with open(srg_nodes_path, 'rb') as f_srgs:
                srg_nodes = pickle.load(f_srgs)

            distance1, distance2, path1, path2 = optimize_node_disjoint_cap_srg_nodes(g, distance_dict, demands, srg_nodes)

            if distance1 != 0:
                working_path_name = 'WorkingPath_{0}_{1}_{2}_cap'.format(demands_name, core_network_name, 'SRG_nodes')
                add_paths_to_map(link_path, working_path_name, path1, fd_path)
                protection_path_name = 'ProtectionPath_{0}_{1}_{2}_cap'.format(demands_name, core_network_name, 'SRG_nodes')
                add_paths_to_map(link_path, protection_path_name, path2, fd_path)

                result_node_srg = {'working_paths': path1, 'working_distance': distance1, 'protection_path': path2,
                                   'protection_distance': distance2}

                arcpy.AddMessage('Working paths:')
                arcpy.AddMessage(path1)
                arcpy.AddMessage('Working path lengths:')
                arcpy.AddMessage(distance1)
                arcpy.AddMessage('Protection paths:')
                arcpy.AddMessage(path2)
                arcpy.AddMessage('Protection path lengths:')
                arcpy.AddMessage(distance2)

                output_file = os.path.join(path_results,
                                                 'graph_properties_{0}_{1}_SRG_Nodes.pkl'.format(core_network_name,
                                                                                                 demands_name))
                with open(output_file, 'wb') as f_nsrg:
                    pickle.dump(result_node_srg, f_nsrg)

        else:
            arcpy.AddMessage('The SRG links problem cannot be solved as there are no SRGs defined for this topology.')

    return


if __name__ == '__main__':

    # For the input parameters: True - input from the user through ArcGIS GUI
    # False - input from the code directly
    run_from_arcgis = True

    if run_from_arcgis:
            problems_user_in = arcpy.GetParameter(0)

            core_network_user_in = arcpy.GetParameter(1)

            demands_user_in = arcpy.GetParameter(2)
            capacity_uniform_in = int(arcpy.GetParameter(3))

            path_home_in = str(arcpy.GetParameter(4).value)
            database_path_in = os.path.join(path_home_in, 'ReliabilityProject.gdb')

            path_demands_in = str(arcpy.GetParameter(5).value)
            path_results_in = str(arcpy.GetParameter(6).value)

            ############################################################################################################
            # Network name
            # Europe
            if core_network_user_in == 'EU-cost266':
                core_network_in = 'cost266'
                demands_in = 'demand_eu_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            elif core_network_user_in == 'EU-cost266-reduced':
                core_network_in = 'cost266_reduced'
                demands_in = 'demand_eu_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            elif core_network_user_in == 'EU-nobel-eu':
                core_network_in = 'nobel_eu'
                demands_in = 'demand_eu_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            elif core_network_user_in == 'EU-nobel-eu-increased':
                core_network_in = 'nobel_eu_increased'
                demands_in = 'demand_eu_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            # Germany
            elif core_network_user_in == 'Ger-germany50':
                core_network_in = 'germany50'
                demands_in = 'demand_ger_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            elif core_network_user_in == 'Ger-germany50-reduced':
                core_network_in = 'germany50_reduced'
                demands_in = 'demand_ger_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            elif core_network_user_in == 'Ger-nobel-ger':
                core_network_in = 'nobel_ger'
                demands_in = 'demand_ger_' + demands_user_in
                srg_links_in = 'srg_links_nobel.pkl'
                srg_nodes_in = 'srg_nodes_nobel.pkl'

            elif core_network_user_in == 'Ger-nobel-ger-increased':
                core_network_in = 'nobel_ger_increased'
                demands_in = 'demand_ger_' + demands_user_in
                srg_links_in = 'srg_links_nobel.pkl'
                srg_nodes_in = 'srg_nodes_nobel.pkl'

            # USA
            elif core_network_user_in == 'USA-janos-us':
                core_network_in = 'janos_us'
                demands_in = 'demand_us_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            elif core_network_user_in == 'USA-janos-us-reduced':
                core_network_in = 'janos_us_reduced'
                demands_in = 'demand_us_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            elif core_network_user_in == 'USA-nobel-us':
                core_network_in = 'nobel_us'
                demands_in = 'demand_us_' + demands_user_in
                srg_links_in = 'srg_links_nobel.pkl'
                srg_nodes_in = 'srg_nodes_nobel.pkl'

            elif core_network_user_in == 'USA-nobel-us-reduced':
                core_network_in = 'nobel_us_reduced'
                demands_in = 'demand_us_' + demands_user_in
                srg_links_in = 'srg_links_nobel.pkl'
                srg_nodes_in = 'srg_nodes_nobel.pkl'

            elif core_network_user_in == 'Poland':
                core_network_in = 'polska'
                demands_in = 'demand_polska_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            elif core_network_user_in == 'Poland-increased':
                core_network_in = 'polska_increased'
                demands_in = 'demand_polska_' + demands_user_in
                srg_links_in = 'srg_links.pkl'
                srg_nodes_in = 'srg_nodes.pkl'

            ############################################################################################################
            # Problems to solve + (possibly) SRGs
            problems_in = {'Unprotected': False, 'Link_Disjoint': False, 'Capacity': False, 'Node_Disjoint': False,
                           'SRG_Links': False, 'SRG_Nodes': False}

            for problem in problems_user_in:
                if 'Unprotected' == problem:
                    problems_in['Unprotected'] = True

                if 'Link disjoint protection' == problem:
                    problems_in['Link_Disjoint'] = True

                if 'Link disjoint protection with capacity constraint' == problem:
                    problems_in['Capacity'] = True

                if 'Node disjoint protection with capacity constraint' == problem:
                    problems_in['Node_Disjoint'] = True

                if 'Link disjoint protection with capacity constraint and link SRGs' == problem:
                    problems_in['SRG_Links'] = True

                if 'Node disjoint protection with capacity constraint and node SRGs' == problem:
                    problems_in['SRG_Nodes'] = True

            arcpy.AddMessage(problems_in)

    else:
        problems_in = {'Unprotected': False, 'Link_Disjoint': False, 'Capacity': False, 'Node_Disjoint': False, 'SRG_Links': True, 'SRG_Nodes': False }

        database_path_in = r'D:\GISworkspace\4_Teaching\Reliability_project\ReliabilityProject.gdb'
        path_results_in = r'D:\GISworkspace\4_Teaching\Reliability_project'
        path_demands_in = r'D:\GISworkspace\4_Teaching\Reliability_project\CoreNetworkTopologies\ProblemSetGer'
        core_network_in = 'nobel_ger'

        demands_in = 'demand_ger_uniform'
        capacity_uniform_in = 5
        srg_links_in = {1: [('Munich', 'Berlin'), ('Hamburg', 'Amsterdam')], 2: [('Dublin', 'Glasgow'), ('London', 'Amsterdam')], 3:
                      [('Budapest', 'Belgrade'), ('Vienna', 'Zagreb')]}
        srg_nodes_in = {1: ['Munich', 'Amsterdam'], 2: ['Glasgow', 'London'], 3: ['Budapest', 'Zagreb']}

    main(problems_in, database_path_in, path_demands_in, path_results_in, core_network_in, demands_in, capacity_uniform_in, srg_links_in, srg_nodes_in)


