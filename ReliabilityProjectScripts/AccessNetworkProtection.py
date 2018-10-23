# -------------------------------------------------------------
# Name:             AccessNetworkProtection.py
# Purpose:          Allows running the scripts with ArcGIS GUI
# Author:           Elena Grigoreva, e.v.grigoryeva@gmail.com (Technical University of Munich)
# About author:     https://egrigoreva.github.io/
# Created:          12/10/2018
# Copyright:        (c) Chair of Communication Networks, Department of Electrical and Computer Engineering,
#                   Technical University of Munich
# ArcGIS Version:   10.3.1
# Python Version:   2.7
# -------------------------------------------------------------

import arcpy
import math
import pickle
import os

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Network")


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


def main(sr, buildings, intersections, co, results_path, input_gdb, network_name):

    pro = False

    spatial_reference = arcpy.SpatialReference(4326)

    fd_name = network_name+'_results_sr{0}'.format(sr)
    fd_path = os.path.join(input_gdb, fd_name)
    check_exists(fd_path)
    arcpy.CreateFeatureDataset_management(input_gdb, fd_name, spatial_reference)

    fd_path_nd = os.path.join(input_gdb, network_name)
    network_nd = os.path.join(fd_path_nd, network_name+'_ND')

    lengths_out = {}

    import ClusteringLocationAllocation as clst
    import ShortestPathRouting as spr

    ####################################################################################################################
    # Clustering: location-allocation
    facilities = 'Intersections'
    output_name_fttb = 'sr{0}'.format(sr)

    arcpy.AddMessage('Clustering nodes with the SR = {0}'.format(sr))
    # (network_nd, demands, intersections, facilities, sr, output_fds, output_name, pro, default_cutoff)
    n_clusters, facilities_ids = clst.main(network_nd, buildings, intersections, facilities, sr, fd_path, output_name_fttb, pro, '#')

    ####################################################################################################################
    # Shortest Path routing

    arcpy.AddMessage('Routing fiber with Dijkstra: Shortest Path with protection only for the FF')

    # (nd_in, n_clusters_in, co_in, output_dir_in, facilities_in, sr_in, protection_in=False, pro_in=False)
    lengths_out['SP'] = spr.main(network_nd, n_clusters, co, fd_path, facilities, sr)

    ####################################################################################################################
    # RING Feeder

    import RingProtection as rp

    arcpy.AddMessage('Ring protection for the FF')

    stops = os.path.join(fd_path,'Cluster_heads_sr{0}'.format(sr_in))
    lengths_out['Ring'] = rp.main(network_nd, 'FF_ring_sr{0}'.format(sr), stops, fd_path, co)

    #arcpy.AddMessage(lengths_out)

    output_file = os.path.join(results_path, 'access_planning_results_{0}_sr{1}.pkl'.format(network_name, sr))
    with open(output_file, 'wb') as f:
        pickle.dump(lengths_out, f)

    return


if __name__ == '__main__':

    run_from_arcgis = True

    if run_from_arcgis:
            network_name_user_in = arcpy.GetParameter(0)

            buildings_in = arcpy.GetParameter(1)
            intersections_in = arcpy.GetParameter(2)

            srs = arcpy.GetParameter(3)

            co_in = arcpy.GetParameter(4)

            path_home_in = str(arcpy.GetParameter(5).value)
            input_gdb_in = os.path.join(path_home_in, 'AccessTopologies.gdb')

            output_path_in = str(arcpy.GetParameter(6).value)

            ############################################################################################################
            # Network name
            if network_name_user_in == 'Dense Urban: New York':
                network_name_in = 'NewYork'

            elif network_name_user_in == 'Dense Urban: Paris':
                network_name_in = 'Paris'

            elif network_name_user_in == 'Urban: Chicago':
                network_name_in = 'Chicago'

            elif network_name_user_in == 'Urban: Munich':
                network_name_in = 'Munich'

            elif network_name_user_in == 'Sub-Urban: Ottobrun':
                network_name_in = 'Ottobrun'

            elif network_name_user_in == 'Sub-Urban: Novgorod':
                network_name_in = 'Novgorod'

            elif network_name_user_in == 'Rural: Miesbach':
                network_name_in = 'Miesbach'


    else:
        sr_in = [4, 8]
        buildings_in = r'D:\GISworkspace\4_Teaching\Reliability_project\AccessTopologies.gdb\Ottobrun\Demands_test'
        intersections_in = r'D:\GISworkspace\4_Teaching\Reliability_project\AccessTopologies.gdb\Ottobrun\Ottobrun_ND_Junctions'
        co_in = r'D:\GISworkspace\4_Teaching\Reliability_project\AccessTopologies.gdb\Ottobrun\Ottobrun_CO'
        output_path_in = r'D:\GISworkspace\4_Teaching\Reliability_project'
        input_gdb_in = r'D:\GISworkspace\4_Teaching\Reliability_project\AccessTopologies.gdb'
        network_name_in = 'Ottobrun'

    for sr_fl in srs:
        sr_in = int(sr_fl)
        main(int(sr_in), buildings_in, intersections_in, co_in, output_path_in, input_gdb_in, network_name_in)
