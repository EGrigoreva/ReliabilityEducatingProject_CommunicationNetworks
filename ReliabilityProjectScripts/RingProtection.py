# -------------------------------------------------------------
# Name:             RingProtection.py
# Purpose:          Investigates access network protection options: link disjoint and ring
# Author:           Elena Grigoreva, e.v.grigoryeva@gmail.com (Technical University of Munich)
# About author:     https://egrigoreva.github.io/
# Created:          12/10/2018
# Copyright:        (c) Chair of Communication Networks, Department of Electrical and Computer Engineering,
#                   Technical University of Munich
# ArcGIS Version:   10.3.1
# Python Version:   2.7
# -------------------------------------------------------------

import arcpy
import os

# TODO update ring protection to be disjoint


def processing(lines):
    length = 0
    arcpy.AddGeometryAttributes_management(lines, 'LENGTH_GEODESIC', 'METERS')

    with arcpy.da.SearchCursor(lines, 'LENGTH_GEO') as rows:
        for row in rows:
            length += row[0]
    return length


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


def get_ids(layer_in):
    """
    This function reads the name of the identifying field in a feature class. 
    :param layer_in: any feature class 
    :return: ids - the list of the ids, points_id - the name of the identifier field 
    """

    ids = []

    # Get fields of points
    field_objects = arcpy.ListFields(layer_in)
    fields = [field.name for field in field_objects if field.type != 'Geometry']

    # Get the nodes ids
    if "OID" in fields:
        points_id = 'OID'

    elif "OBJECTID" in fields:
        points_id = 'OBJECTID'

    elif "ObjectID" in fields:
        points_id = "ObjectID"

    with arcpy.da.SearchCursor(layer_in, points_id) as cursor:
        for row in cursor:
            ids.append(row[0])

    return ids, points_id


def post_processing_fiber(stops_in):

    # Create a dictionary to solve the results
    fiber = {'working': {}, 'protection': {}}

    # Get the number of stops
    n_stops = int(arcpy.GetCount_management(stops_in).getOutput(0))
    # arcpy.AddMessage('n_stops = {0}'.format(n_stops))

    # Get the total ring length
    clause = 'Sequence = {0}'.format(n_stops)
    arcpy.SelectLayerByAttribute_management(stops_in, selection_type='NEW_SELECTION', where_clause=clause)

    with arcpy.da.SearchCursor(stops_in, 'Cumul_Length') as cursor:
        for row in cursor:
            total_length = row[0]

    # arcpy.AddMessage('Total ring length = {0}'.format(total_length))

    # Iterate through the stops in the order starting from 2 (field - sequence)
    for i in range(2, n_stops):
        clause = 'Sequence = {0}'.format(i)
        arcpy.SelectLayerByAttribute_management(stops_in, selection_type='NEW_SELECTION', where_clause=clause)

        with arcpy.da.SearchCursor(stops_in, ['Cumul_Length', 'Name']) as cursor:
            for row in cursor:
                fiber_1 = row[0]
                name = str(row[1]).split(' ')[1]

        fiber_2 = total_length - fiber_1

        if fiber_1 >= fiber_2:
            fiber['working'].update({name:{'fiber': fiber_2}})
            fiber['protection'].update({name:{'fiber': fiber_1}})
        else:
            fiber['working'].update({name:{'fiber': fiber_1}})
            fiber['protection'].update({name:{'fiber': fiber_2}})

        fiber['duct'] = total_length

    # Calculate the working path (shorter) and the protection path (longer) fiber lengths. Fiber and duct
    # lengths in this case are the same
    return fiber


def route(nds, ring_name, stop1, stop2, mapping_disjoint, constraints, j):
    """
    This function finds the SP between the two points and takes into account the constrains provided.
    
    :param nds: network dataset, nds path
    :param ring_name: the name for the route layer, string
    :param stop1: point 1, selection on the point layer
    :param stop2: point 2, selection on the point layer
    :param mapping_disjoint: disjointness constraint, expression
    :param constraints: the routes already in the path, list of line features 
    :param j: counter, int
    :return: returns the path to the calculated route
    """

    name_merged = 'merged__f' + str(j)
    merge_f = os.path.join('in_memory', name_merged)

    name_tmp = 'tmp_' + str(j)
    path_tmp = os.path.join('in_memory', name_tmp)

    layer_object = arcpy.na.MakeRouteLayer(nds, ring_name, impedance_attribute='Length',
                                           output_path_shape='TRUE_LINES_WITH_MEASURES',
                                           ordering_type='PRESERVE_BOTH').getOutput(0)

    na_classes = arcpy.na.GetNAClassNames(layer_object)

    arcpy.na.AddLocations(layer_object, na_classes["Stops"], stop1)
    arcpy.na.AddLocations(layer_object, na_classes["Stops"], stop2)

    if len(constraints) == 1:
        arcpy.na.AddLocations(layer_object, "Line Barriers", constraints[0], mapping_disjoint,
                              search_tolerance="5 Meters")
    elif len(constraints) > 1:
        arcpy.Merge_management(constraints, merge_f)
        arcpy.na.AddLocations(layer_object, "Line Barriers", merge_f, mapping_disjoint,
                              search_tolerance="5 Meters")

    arcpy.na.Solve(layer_object)

    tmp = arcpy.MakeFeatureLayer_management(arcpy.mapping.ListLayers(layer_object, na_classes["Routes"])[0],
                                            name_tmp)

    arcpy.management.CopyFeatures(tmp, path_tmp)

    return path_tmp


def ring_route(nds, ring_name, stops, output_dir, co, cost_reduction='#'):
    """
    Calculates the protection route. Returns duct and fiber length in m. 
    
    :param nds: network dataset, nds path
    :param ring_name: the name for the route layer, string
    :param stops: all the nodes in the ring, point feature 
    :param output_dir: path to store the results, typically feature dataset path
    :param co: central office, point feature
    :param cost_reduction: not used
    :return: {'ff_ring_duct': duct, 'ff_ring_fiber': fiber}
    """
    arcpy.CheckOutExtension("Network")

    # Create points layer
    layer_path = os.path.join('in_memory', 'stops')
    stops_layer = arcpy.MakeFeatureLayer_management(stops, layer_path)

    # Create points layer for selecting the nearest
    layer_path = os.path.join('in_memory', 'stops_selection')
    stops_layer_selection = arcpy.MakeFeatureLayer_management(stops, layer_path)

    # Create CO layer
    co_layer_path = os.path.join('in_memory', 'co')
    co_layer = arcpy.MakeFeatureLayer_management(co, co_layer_path)

    # # Cost attribute for disjoint paths
    # sc_disjoint = 20000
    # mapping_disjoint = "Name Name #;Attr_Length # " + str(sc_disjoint) + "; BarrierType # 1"
    #
    # cycle = int(arcpy.GetCount_management(stops).getOutput(0))
    #
    # ids_list, id_field = get_ids(stops_layer)

    # # Nearest neighbor heuristics
    # ####################################################################################################################
    # # Start with CO, find nearest neighbor
    # arcpy.Near_analysis(co_layer, stops_layer, method='GEODESIC')
    #
    # # Get the closest id
    # with arcpy.da.SearchCursor(co_layer, 'NEAR_FID') as cursor:
    #     for row in cursor:
    #         stop_id = row[0]
    #
    # # Select the closest node
    # clause = '"{0}" = {1}'.format(id_field, stop_id)
    # arcpy.SelectLayerByAttribute_management(stops_layer, 'NEW_SELECTION', clause)
    #
    # # Compute the route
    # constraints = []
    # co_path = route(nds, ring_name, co_layer, stops_layer, mapping_disjoint, constraints, 0)
    # # Add to constraints
    # constraints.append(co_path)
    #
    # # Iterate through the nodes
    # sort_out_ids = []
    # for j in range(1, cycle):
    #     # Store the previous
    #     prev = stop_id
    #     # Outsort the previous
    #     sort_out_ids.append(prev)
    #     # Get the next node but not going back
    #
    #     clause = ''
    #     for i in range(len(sort_out_ids)):
    #         if i == 0 or i == len(sort_out_ids):
    #             clause += '"{0}" = {1}'.format(id_field, sort_out_ids[i])
    #         else:
    #             clause += ' OR "{0}" = {1}'.format(id_field, sort_out_ids[i])
    #
    #     arcpy.SelectLayerByAttribute_management(stops_layer_selection, 'NEW_SELECTION', clause)
    #     arcpy.SelectLayerByAttribute_management(stops_layer_selection, 'SWITCH_SELECTION')
    #
    #     arcpy.Near_analysis(stops_layer, stops_layer_selection, method='GEODESIC')
    #
    #     with arcpy.da.SearchCursor(stops_layer, 'NEAR_FID') as cursor:
    #         for row in cursor:
    #             stop_id = row[0]
    #
    #     clause = '"{0}" = {1}'.format(id_field, stop_id)
    #     arcpy.SelectLayerByAttribute_management(stops_layer, 'NEW_SELECTION', clause)
    #
    #     clause = '"{0}" = {1}'.format(id_field, prev)
    #     arcpy.SelectLayerByAttribute_management(stops_layer_selection, 'NEW_SELECTION', clause)
    #
    #     path_tmp = route(nds, ring_name, stops_layer_selection, stops_layer, mapping_disjoint, constraints, j)
    #
    #     constraints.append(path_tmp)
    #
    #     arcpy.SelectLayerByAttribute_management(stops_layer_selection, 'CLEAR_SELECTION')
    #
    # # The last node has to be connected to the CO
    # clause = '"{0}" = {1}'.format(id_field, stop_id)
    # arcpy.SelectLayerByAttribute_management(stops_layer, 'NEW_SELECTION', clause)
    #
    # co_path = route(nds, ring_name, co_layer, stops_layer, mapping_disjoint, constraints, cycle+1)
    # # Add to constraints
    # constraints.append(co_path)

    layer_object = arcpy.na.MakeRouteLayer(nds, ring_name, impedance_attribute='Length',
                                           find_best_order='FIND_BEST_ORDER',
                                           output_path_shape='TRUE_LINES_WITH_MEASURES',
                                           ordering_type='PRESERVE_BOTH').getOutput(0)

    na_classes = arcpy.na.GetNAClassNames(layer_object)

    arcpy.na.AddLocations(layer_object, na_classes["Stops"], co_layer)
    arcpy.na.AddLocations(layer_object, na_classes["Stops"], stops_layer)
    arcpy.na.AddLocations(layer_object, na_classes["Stops"], co_layer)

    arcpy.na.Solve(layer_object)

    tmp = arcpy.MakeFeatureLayer_management(arcpy.mapping.ListLayers(layer_object, na_classes["Routes"])[0],
                                            'ring')

    route_out_name = os.path.join(output_dir, '{0}_ring'.format(ring_name))
    check_exists(route_out_name)
    arcpy.CopyFeatures_management(tmp, route_out_name)

    fiber = post_processing_fiber(arcpy.mapping.ListLayers(layer_object, na_classes["Stops"])[0])

    return fiber


def main(nds, ring_name, stops, output_dir, co):
    ring_lengths = ring_route(nds, ring_name, stops, output_dir, co)
    return ring_lengths


if __name__ == '__main__':
    nds_in = r'D:\GISworkspace\4_Teaching\Reliability_project\AccessTopologies.gdb\Ottobrun\Ottobrun_ND'
    ring_name_in = 'test'
    stops_in = r'D:\GISworkspace\4_Teaching\Reliability_project\AccessTopologies.gdb\Ottobrun\Demands_test'
    output_dir_in = r'D:\GISworkspace\4_Teaching\Reliability_project\AccessTopologies.gdb\Ottobrun'
    co_in = r'D:\GISworkspace\4_Teaching\Reliability_project\AccessTopologies.gdb\Ottobrun\Ottobrun_CO'

    main(nds_in, ring_name_in, stops_in, output_dir_in, co_in)