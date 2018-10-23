# -------------------------------------------------------------
# Name:             ShortestPathRouting.py
# Purpose:          Does the shortest path routing for the one stage FTTB
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
import math


def check_exists(name_in):
    """
    This function check existence of the feature class, which name is specified, and deletes it, if it exists. Some 
    arcpy functions even with the activated overwrite output return errors if the feature class already exists

    :param name_in: check if this file already exists
    :return: 
    """
    if arcpy.Exists(name_in):
        arcpy.Delete_management(name_in)
    return


def check_object_id(layer_in):
    """
    
    :param layer_in:    the layer, where we are not sure how the field is named 
    :return: the name  of the field
    """
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

    return points_id


def post_processing_fiber(sr, routes_all_in, protection_in=False, routes_working_in='#'):
    """
    This function calculates the fiber lengths (as the sum of the individual paths lengths) an the duct as the total 
    length (counting the streect segments only once). Returns fiber and duct lengths in meters.
    
    :param routes_all_in: the routes to get the fiber from, feature class
    :param protection_in: if the protection has to be included, binary 
    :param routes_working_in: the routes to take into account when calculating additional duct for protection, feature class
    
    :return: 
    """

    # Add the path lengths in meters
    arcpy.AddGeometryAttributes_management(routes_all_in, 'LENGTH_GEODESIC', 'METERS')

    field_name = check_object_id(routes_all_in)

    dissolved_name = os.path.join('in_memory', 'dissolved')
    check_exists(dissolved_name)

    # For the LMF we calculate the average lengths in the cluster
    if not protection_in:
        # Dissolve_management (in_features, out_feature_class, {dissolve_field}, {statistics_fields}, {multi_part},
        # {unsplit_lines})
        arcpy.Dissolve_management(routes_all_in, dissolved_name, field_name, statistics_fields="LENGTH_GEO SUM")

        arcpy.AddGeometryAttributes_management(dissolved_name, 'LENGTH_GEODESIC', 'METERS')

        with arcpy.da.SearchCursor(dissolved_name, ['SUM_LENGTH_GEO', 'LENGTH_GEO']) as rows:
            for row in rows:
                fiber = row[0] # fiber length
                duct = row[1]  # duct length

    # For the FF we calculate the individual lengths
    else:
        # Individual fiber lengths
        # Create a dictionary to solve the results
        fiber = {'FF':{'working': {}, 'protection': {}, 'duct': 0}}
        duct = 0

        # Working paths
        arcpy.AddGeometryAttributes_management(routes_working_in, 'LENGTH_GEODESIC', 'METERS')
        with arcpy.da.SearchCursor(routes_working_in, ['Name','LENGTH_GEO']) as cursor:
            for row in cursor:
                name = str(row[0]).split(' ')[1]
                fiber['FF']['working'][name] = row[1]

        # Protection paths
        arcpy.AddGeometryAttributes_management(routes_all_in, 'LENGTH_GEODESIC', 'METERS')
        with arcpy.da.SearchCursor(routes_all_in, ['Name', 'LENGTH_GEO']) as cursor:
            for row in cursor:
                fiber['FF']['protection'][name] = row[1]

        # Total Duct lengths
        duct_list = [routes_all_in, routes_working_in]
        path = arcpy.Describe(routes_all_in).path
        merge_path = os.path.join(path, 'ff_merged')
        check_exists(merge_path)
        arcpy.Merge_management(duct_list, merge_path)

        arcpy.Dissolve_management(merge_path, dissolved_name, field_name, statistics_fields="LENGTH_GEO SUM")

        arcpy.AddGeometryAttributes_management(dissolved_name, 'LENGTH_GEODESIC', 'METERS')

        with arcpy.da.SearchCursor(dissolved_name, ['LENGTH_GEO']) as rows:
            for row in rows:
                fiber['FF']['duct'] =  row[0] # duct length

    return fiber, duct


def route_fiber(nd_in, incidents_in, facilities_in, name_in, output_dir_in, protection_in=False, pro_in=False):
    """
    This function routes the working and if requested the protection fiber. It returns the respective paths to the 
    created feature classes (lines).
    
    :param nd_in: network dataset on which the shortest path routing is done, network dataset
    :param incidents_in: the demands, feature class
    :param facilities_in: the ps or co location, feature class
    :param name_in: the name that is used to store the output, string
    :param output_dir_in: the directory to store the results, path
    :param protection_in: if the protection has to be included, binary 
    :param pro_in: if the script is executed in arcgis pro, binary 
    
    :return: 
    """

    arcpy.CheckOutExtension('Network')
    # Set local variables
    layer_name = "ClosestFacility"
    impedance = "Length"

    # First route the working paths, shortes paths
    # MakeClosestFacilityLayer_na (in_network_dataset, out_network_analysis_layer, impedance_attribute,
    # {travel_from_to}, {default_cutoff}, {default_number_facilities_to_find}, {accumulate_attribute_name},
    # {UTurn_policy}, {restriction_attribute_name}, {hierarchy}, {hierarchy_settings}, {output_path_shape},
    # {time_of_day}, {time_of_day_usage})
    #
    # http://desktop.arcgis.com/en/arcmap/10.3/tools/network-analyst-toolbox/make-closest-facility-layer.htm
    result_object = arcpy.na.MakeClosestFacilityLayer(nd_in, layer_name, impedance, 'TRAVEL_TO', default_cutoff=None,
                                                      default_number_facilities_to_find=1,
                                                      output_path_shape='TRUE_LINES_WITH_MEASURES')

    # Get the layer object from the result object. The Closest facility layer can
    # now be referenced using the layer object.
    layer_object = result_object.getOutput(0)

    # Get the names of all the sublayers within the Closest facility layer.
    sublayer_names = arcpy.na.GetNAClassNames(layer_object)

    # Stores the layer names that we will use later
    incidents_layer_name = sublayer_names["Incidents"]  # as origins
    facilities_layer_name = sublayer_names["Facilities"]  # as destinations
    lines_layer_name = sublayer_names["CFRoutes"]  # as lines

    arcpy.na.AddLocations(layer_object, incidents_layer_name, incidents_in)
    arcpy.na.AddLocations(layer_object, facilities_layer_name, facilities_in)

    # Solve the Closest facility  layer
    arcpy.na.Solve(layer_object)

    # # Save the solved Closest facility layer as a layer file on disk
    # output_layer_file = os.path.join(output_dir_in, layer_name)
    # arcpy.MakeFeatureLayer_management(layer_object, output_layer_file)

    # Get the Lines Sublayer (all the distances)
    if pro_in:
        lines_sublayer = layer_object.listLayers(lines_layer_name)[0]
    elif not pro_in:
        lines_sublayer = arcpy.mapping.ListLayers(layer_object, lines_layer_name)[0]

    # Save results
    layer_out_path = os.path.join(output_dir_in, name_in)
    arcpy.management.CopyFeatures(lines_sublayer, layer_out_path)

    protection_out_path = "#"

    # If requested route the protection paths
    if protection_in:
        # For all the routed apths the disjoint path has to be found
        n_paths = int(arcpy.GetCount_management(incidents_in).getOutput(0))

        field_objects = arcpy.ListFields(layer_out_path)
        fields = [field.name for field in field_objects if field.type != 'Geometry']

        if 'Total_Length' in fields:
            field_len = 'Total_Length'
        elif 'Shape_Length' in fields:
            field_len = 'Shape_Length'

        # Iterate through all the facility-demand pairs and their respective routes
        cursor_r = arcpy.da.SearchCursor(layer_out_path, ['SHAPE@', field_len])
        cursor_n = arcpy.da.SearchCursor(incidents_in, 'SHAPE@')

        protection_out_path = os.path.join(output_dir_in,'{0}_protection'.format(name_in))
        check_exists(protection_out_path)
        arcpy.CreateFeatureclass_management(output_dir_in,'{0}_protection'.format(name_in), template=layer_out_path)

        for i in range(n_paths):
            path = cursor_r.next()
            node = cursor_n.next()
            if not path[1] == 0:
                tmp = protection_routing(nd_in, facilities_in, node[0], path[0], pro_in)
                # Add the protection route to the output feature class
                arcpy.Append_management(tmp, protection_out_path, schema_type="NO_TEST")

    return layer_out_path, protection_out_path


def protection_routing(nd_in, start_in, end_in, route_in, pro_in):
    """
    This function finds a disjoint path between given start-end node pars to the given existing working path. 
    The general procedure is the same as for the fiber routing but with additional constraint (line barrier) and thus 
    restricted on one node pair (facility-demand).
    
    :param nd_in: network dataset on which the shortest path routing is done, network dataset
    :param start_in: starting node, feature class
    :param end_in: end node, feature class
    :param route_in: working path, feature class
    :param pro_in: if the script is executed in arcgis pro, binary
    
    :return: the resulting line layer -> path
    """
    # Set local variables
    layer_name = "ClosestFacility"
    impedance = "Length"

    # MakeClosestFacilityLayer_na (in_network_dataset, out_network_analysis_layer, impedance_attribute,
    # {travel_from_to}, {default_cutoff}, {default_number_facilities_to_find}, {accumulate_attribute_name},
    # {UTurn_policy}, {restriction_attribute_name}, {hierarchy}, {hierarchy_settings}, {output_path_shape},
    # {time_of_day}, {time_of_day_usage})
    #
    # http://desktop.arcgis.com/en/arcmap/10.3/tools/network-analyst-toolbox/make-closest-facility-layer.htm
    result_object = arcpy.na.MakeClosestFacilityLayer(nd_in, layer_name, impedance, 'TRAVEL_TO', default_cutoff=None,
                                                      default_number_facilities_to_find=1,
                                                      output_path_shape='TRUE_LINES_WITH_MEASURES')

    # Get the layer object from the result object. The Closest facility layer can
    # now be referenced using the layer object.
    layer_object = result_object.getOutput(0)

    # Get the names of all the sublayers within the Closest facility layer.
    sublayer_names = arcpy.na.GetNAClassNames(layer_object)

    # Stores the layer names that we will use later
    incidents_layer_name = sublayer_names["Incidents"]  # as origins
    facilities_layer_name = sublayer_names["Facilities"]  # as destinations
    lines_layer_name = sublayer_names["CFRoutes"]  # as lines

    arcpy.na.AddLocations(layer_object, incidents_layer_name, end_in)
    arcpy.na.AddLocations(layer_object, facilities_layer_name, start_in)

    # Cost attribute for disjoint paths
    sc_tmp1 = 200

    # Add the cost upscaled working path to the restrictions as the scaled cost
    mapping = "Name Name #;Attr_Length # " + str(sc_tmp1) + "; BarrierType # 1"
    arcpy.na.AddLocations(layer_object, "Line Barriers", route_in, mapping, search_tolerance="5 Meters")

    # Solve the Closest facility  layer
    arcpy.na.Solve(layer_object)

    # # Save the solved Closest facility layer as a layer file on disk
    # output_layer_file = os.path.join(output_dir_in, layer_name)
    # arcpy.MakeFeatureLayer_management(layer_object, output_layer_file)

    # Get the Lines Sublayer (all the distances)
    if pro_in:
        lines_sublayer = layer_object.listLayers(lines_layer_name)[0]
    elif not pro_in:
        lines_sublayer = arcpy.mapping.ListLayers(layer_object, lines_layer_name)[0]

    return lines_sublayer


def main(nd_in, n_clusters_in, co_in, output_dir_in, facilities_in, sr_in, protection_in=False, pro_in=False):
    """
    This function routes the fiber in the city grid in a single stage. If specified it also provides the link disjoint 
    protection of all the fiber. It returns a list with last mile and feeder fiber lengths and ducts in meters. For the 
    protection the additional duct for the protection is included and additional fiber. 
     
    :param nd_in: network dataset on which the shortest path routing is done, network dataset
    :param n_clusters_in: the number of PS that were placed at the clustering stage, int
    :param co_in: central office location (predefined), feature class
    :param output_dir_in: the directory to store the results, path
    :param facilities_in: the PSs locations (cluster heads), feature class
    :param sr_in: user splitting ratio at the clustering , int
    :param protection_in: if the protection has to be included, binary 
    :param pro_in: if the script is executed in arcgis pro, binary
    
    :return: planning_results = [lmf, lm_duct, ff, f_duct] or 
    [lmf, lm_duct, ff, f_duct, lmf_protection, lm_duct_protection-lm_duct, ff_protection, f_duct_protection-f_duct]
    """
    routes_all_list = []
    routes_all_list_protection = []

    lmf_dict = {'LMF':{}}

    # LMF
    # Route fiber for all the clusters
    for i in range(int(n_clusters_in)):
        cluster = os.path.join(output_dir_in, 'Cluster_{0}_sr{1}'.format(i, sr_in))
        n_members = int(arcpy.GetCount_management(cluster).getOutput(0))
        cluster_head = os.path.join(output_dir_in, 'Cluster_head_{0}_sr{1}'.format(i, sr_in))

        with arcpy.da.SearchCursor(cluster_head, 'Name') as cursor:
            for row in cursor:
                head_name = str(row[0]).split(' ')[1]

        name_out = 'SP_LMF_{0}_sr{1}'.format(i, sr_in)
        check_exists(os.path.join(output_dir_in, name_out))

        # Working  paths, i.e., shortest paths
        route, route_protection = route_fiber(nd_in, cluster, cluster_head, name_out, output_dir_in,
                                              protection_in, pro_in)
        routes_all_list.append(route)

        # Protection paths, i.e., disjoint with working
        if protection_in:
            routes_all_list_protection.append(route_protection)

        lmf, lm_duct = post_processing_fiber(sr_in, route)

        lmf_dict['LMF'][head_name] = {'average fiber': float(lmf)/float(n_members), 'average duct': float(lm_duct)/float(n_members)}

    #arcpy.AddMessage(lmf_dict)

    # FF
    # Route fiber from the CO to the cluster heads
    cluster = os.path.join(output_dir_in, 'Cluster_heads_sr{0}'.format(sr_in))
    name_out = 'SP_FF_sr{0}'.format(sr_in)
    check_exists(os.path.join(output_dir_in, name_out))
    ff_routes, ff_routes_protection = route_fiber(nd_in, cluster, co_in, name_out, output_dir_in, True, pro_in)
    # Get the fiber and duct lengths
    # Working paths
    ff_dict = post_processing_fiber(sr_in, ff_routes_protection, True, ff_routes)[0]

    #arcpy.AddMessage(ff_dict)

    return lmf_dict, ff_dict


if __name__ == '__main__':
    nd = r'D:\GISworkspace\Test_for_Scripting.gdb\NewYork_nodes\New_York_JOCN_125_ND'
    co = r'D:\GISworkspace\Test_for_Scripting.gdb\NewYork_nodes\CO_to_streets'
    demands_in = r'D:\GISworkspace\Test_for_Scripting.gdb\NewYork_nodes\bs_to_street_125_to_streets'

    output_dir = r'D:\GISworkspace\Test_for_Scripting.gdb\NewYork_nodes'
    facilities = 'Intersections'
    sr = 32
    protection = True
    pro = False

    arcpy.MakeTableView_management(demands_in, "myTableView")
    n_nodes = int(arcpy.GetCount_management("myTableView").getOutput(0))
    n_clusters = int(math.ceil(float(n_nodes) / float(sr)))

    main(nd, n_clusters, co, output_dir, facilities, sr, protection, pro)