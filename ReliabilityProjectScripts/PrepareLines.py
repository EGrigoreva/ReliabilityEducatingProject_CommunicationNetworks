# -------------------------------------------------------------
# Name:             PrepareLines.py
# Purpose:          It labels the lines in arcgis feature class with the origin and destination nodes
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


def add_fields(points_in, lines_in, output_fds_in):

    # Create a point layer
    points_layer = arcpy.MakeFeatureLayer_management(points_in, 'points_layer')

    # Get the spatial reference (as in the points)
    descript = arcpy.Describe(points_in)
    spatial_ref_in = descript.spatialReference

    # Create a lines layer
    lines_layer = arcpy.MakeFeatureLayer_management(lines_in, 'lines_layer')

    # Add the Origin and Destination fields
    arcpy.AddField_management(lines_layer, 'OriginID', 'TEXT')
    arcpy.AddField_management(lines_layer, 'DestinationID', 'TEXT')

    # Create a featureclass to store the resulting links
    links_out_name = 'links_out'
    all_links_in = arcpy.CreateFeatureclass_management('in_memory', links_out_name, 'POLYLINE',
                                                       spatial_reference=spatial_ref_in)

    # Add the Origin and Destination fields
    arcpy.AddField_management(all_links_in, 'OriginID', 'TEXT')
    arcpy.AddField_management(all_links_in, 'DestinationID', 'TEXT')

    # Go through the edges OBJECT IDs and select them by one

    # Get the number of lines
    arcpy.MakeTableView_management(lines_in, "myTableView")
    n_lines = int(arcpy.GetCount_management("myTableView").getOutput(0))

    # Get fields of lines
    lines_field_objects = arcpy.ListFields(lines_layer)
    lines_fields = [field.name for field in lines_field_objects if field.type != 'Geometry']

    # Get fields of points
    points_field_objects = arcpy.ListFields(points_layer)
    points_fields = [field.name for field in points_field_objects if field.type != 'Geometry']

    for i in range(1, n_lines+1):
        if "OID" in lines_fields:
            # Define the SQL expression for the points with the IDs with the range
            clause_in = '"OID" = {0}'.format(i)

        elif "OBJECTID" in lines_fields:
            # Define the SQL expression for the points with the IDs with the range
            clause_in = '"OBJECTID" = {0}'.format(i)

        arcpy.SelectLayerByAttribute_management(lines_layer, 'NEW_SELECTION', clause_in)

        # Select from the points the intersecting ones
        arcpy.SelectLayerByLocation_management(points_layer, overlap_type='INTERSECT', select_features=lines_layer,
                                               selection_type='NEW_SELECTION')
        ids_tmp = []
        with arcpy.da.SearchCursor(points_layer, 'NAME') as cursor:
            for row in cursor:
                ids_tmp.append(row[0])

        if len(ids_tmp) == 2:
            # Write to the new fields the Nodes IDs with search cursor
            with arcpy.da.UpdateCursor(lines_layer, ["OriginID", 'DestinationID']) as cursor:
                for row in cursor:
                    row[0] = ids_tmp[0]
                    row[1] = ids_tmp[1]
                    cursor.updateRow(row)

    # Add the links lengths in meters
    arcpy.AddGeometryAttributes_management(lines_in, 'LENGTH_GEODESIC', 'METERS')
    arcpy.Delete_management(lines_layer)

    return


def main(nodes, edges, name_input):

    # Get the output dir
    descript = arcpy.Describe(nodes)
    path_full = descript.catalogPath
    output_dir = os.path.split(path_full)[0]
    arcpy.env.workspace = output_dir

    arcpy.AddMessage('Output location is {0}'.format(output_dir))

    name_edges = os.path.join(output_dir, 'Roads_input')

    if arcpy.Exists(name_edges):
        arcpy.Delete_management(name_edges)

    arcpy.management.CopyFeatures(edges, name_edges)

    name_out = os.path.join(output_dir, name_input)

    if arcpy.Exists(name_out):
        arcpy.Delete_management(name_out)

    add_fields(nodes, name_edges, output_dir)

    arcpy.Delete_management(name_edges)

    return


if __name__ == '__main__':
    nodes_in = arcpy.GetParameterAsText(0)
    edges_in = arcpy.GetParameterAsText(1)
    name_input_in = arcpy.GetParameterAsText(2)

    main(nodes_in, edges_in, name_input_in)