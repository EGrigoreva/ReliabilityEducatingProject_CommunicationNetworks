# -------------------------------------------------------------
# Name:             optimize_ilp.py
# Purpose:          Optimization formulations for Gurobi
# Author:           Petra Stojsavljevic
# Created:          12/10/2018
# Copyright:        (c) Chair of Communication Networks, Department of Electrical and Computer Engineering,
#                   Technical University of Munich
# ArcGIS Version:   10.3.1
# Python Version:   2.7
# -------------------------------------------------------------


from gurobipy import *
import networkx as nx
import arcpy


# Optimize resilience
def optimize_unprotected_path(G, D, R):
    model = Model("Unprotected paths")

    # Identify the source and the destination of the demand
    t = {}
    RL = list(enumerate(R))

    for r, (src, dst) in RL:
        for n in G.nodes():
            if n == src:
                t[r, n] = -1
            elif n == dst:
                t[r, n] = 1
            else:
                t[r, n] = 0


    # Transform undirected edges to directed arcs
    d = {}
    arcs = []

    for i, j in G.edges():
        d[i,j] = D[i,j]
        d[j,i] = D[j,i]
        arcs.append((i,j))
        arcs.append((j,i))

    # Binary variables indicate if arc (i,j) belongs to the path of demand r
    u= {}
    for r in RL:
        for i,j in arcs:
            u[r[0],i,j] = model.addVar(obj=0, vtype="B", name="u[%s,%s,%s]" %(r,i,j))
    model.update()

    # Optimization goal is to minimize the length of the paths
    model.setObjective(quicksum(u[r[0],i,j] * d[i,j] for r in RL for i,j in arcs), GRB.MINIMIZE)

    # Flow conservation constraint
    for r in RL:
        for m in G.nodes():
            model.addConstr(quicksum(u[r[0],i,j] for i,j in arcs if j==m) - quicksum(u[r[0],i,j] for i,j in arcs if i==m), "=", t[r[0],m])

    # Start optimization
    model.params.outputflag = 0
    model.optimize()

    # If optimal solution is found get the results
    if model.status != GRB.Status.OPTIMAL:
        arcpy.AddMessage('The model cannot be solved.')
        distance = 0
        path = 0
    else:
        su = model.getAttr('x', u)

        # The result is given as set of paths for every demand
        distance = {}
        path = {}
        for r in RL:
            p = []
            dp = 0
            for i,j in arcs:
                if su[r[0],i,j]>0:
                    p.append((i,j))
                    dp += d[i,j]

            distance[r[1]] = dp
            path[r[1]] = p
    return distance, path


# MILP formulation for link disjoint paths
def optimize_link_disjoint(G, D, R):
    model = Model("Link disjoint paths")

    # Identify the source and the destination of the demand
    t = {}
    RL = list(enumerate(R))

    for r, (src, dst) in RL:
        for n in G.nodes():
            if n == src:
                t[r, n] = -1
            elif n == dst:
                t[r, n] = 1
            else:
                t[r, n] = 0

    # Transform undirected edges to directed arcs
    d = {}
    arcs = []
    for i, j in G.edges():
        d[i,j] = D[i,j]
        d[j,i] = D[j,i]
        arcs.append((i,j))
        arcs.append((j,i))

    # # Binary variables indicate if arc (i,j) belongs to the working and backup paths of demand r
    u, v = {}, {}
    for r in RL:
        for i,j in arcs:
            u[r[0],i,j] = model.addVar(vtype="B", name="u[%s,%s,%s]" %(r,i,j))
            v[r[0],i,j] = model.addVar(vtype="B", name="v[%s,%s,%s]" %(r,i,j))
    model.update()

    # Optimization goal
    model.setObjective(quicksum((u[r[0],i,j] + v[r[0],i,j])*d[i,j] for r in RL for i,j in arcs), GRB.MINIMIZE)

    # Constraint: Link paths have to be link disjoint
    for r in RL:
        for i,j in arcs:
            model.addConstr(u[r[0],i,j] + v[r[0],i,j], "<=", 1, name="Link disjoint paths")

    # Flow conservation constraint
    for r in RL:
        for m in G.nodes():
            model.addConstr(quicksum(u[r[0],i,j] for i,j in arcs if j==m) - quicksum(u[r[0],i,j] for i,j in arcs if i==m), "=", t[r[0],m])
            model.addConstr(quicksum(v[r[0],i,j] for i,j in arcs if j==m) - quicksum(v[r[0],i,j] for i,j in arcs if i==m), "=", t[r[0],m])

    # Start optimization
    model.params.outputflag = 0
    model.optimize()

    # If optimal solution is found get the results
    if model.status != GRB.Status.OPTIMAL:
        if model.status == 3:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        elif model.status == 4:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible or unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        if model.status == 5:
            arcpy.AddMessage('Optimal solution is not found! The model is unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

    else:
        su = model.getAttr('x', u)
        sv = model.getAttr('x', v)

        # The result is given as set of working and protection paths for every demand
        distance1, distance2 = {}, {}
        path1, path2 = {}, {}

        for r in RL:
            d1 = 0
            d2 = 0
            p1 = []
            p2 = []
            for i, j in arcs:
                if su[r[0], i, j] > 0:
                    p1.append((i, j))
                    d1 += d[i, j]
                if sv[r[0], i, j] > 0:
                    p2.append((i, j))
                    d2 += d[i, j]

                    # Select the shorter path as working path and longer as backup path
            if d1 <= d2:
                distance1[r[1]] = d1
                distance2[r[1]] = d2
                path1[r[1]] = p1
                path2[r[1]] = p2
            else:
                distance1[r[1]] = d2
                distance2[r[1]] = d1
                path1[r[1]] = p2
                path2[r[1]] = p1

    return distance1, distance2, path1, path2


# MILP formulation for link disjoint paths with capacity constraint
def optimize_link_disjoint_cap(G, D, R):
    model = Model("Link disjoint paths with capacity constraint")

    # Identify the source and the destination of the demand
    t = {}
    RL = list(enumerate(R))

    for r, (src, dst) in RL:
        for n in G.nodes():
            if n==src:
                t[r,n] = -1
            elif n==dst:
                t[r,n] = 1
            else:
                t[r,n] = 0

    # Transform undirected edges to directed arcs
    d = {}
    c = {}
    arcs = []
    C = nx.get_edge_attributes(G, "capacity")

    for i, j in G.edges():
        d[i,j] = D[i,j]
        d[j,i] = D[j,i]
        c[i,j] = C[i,j]
        c[j,i] = C[i,j]
        arcs.append((i,j))
        arcs.append((j,i))

    # Binary variables indicate if arc (i,j) belongs to the working and backup paths of demand r
    u, v = {}, {}
    for r in RL:
        for i,j in arcs:
            u[r[0],i,j] = model.addVar(vtype="B", name="u[%s,%s,%s]" %(r[0],i,j))
            v[r[0],i,j] = model.addVar(vtype="B", name="v[%s,%s,%s]" %(r[0],i,j))
    model.update()

    # Optimization goal
    model.setObjective(quicksum((u[r[0],i,j] + v[r[0],i,j])*d[i,j] for r in RL for i,j in arcs), GRB.MINIMIZE)

    # Constraint: Link paths have to be link disjoint
    for r in RL:
        for i, j in arcs:
            model.addConstr(u[r[0],i,j] + v[r[0],i,j], "<=", 1, name="Link disjoint paths")

    # Flow conservation constraint
    for r in RL:
        for m in G.nodes():
            model.addConstr(quicksum(u[r[0],i,j] for i,j in arcs if j==m) - quicksum(u[r[0],i,j] for i,j in arcs if i==m), "=", t[r[0],m])
            model.addConstr(quicksum(v[r[0],i,j] for i,j in arcs if j==m) - quicksum(v[r[0],i,j] for i,j in arcs if i==m), "=", t[r[0],m])

    # Capacity constraint
    for i, j in arcs:
        model.addConstr(quicksum(R[RL[r[0]][1]]*(u[r[0],i,j] + v[r[0],i,j]) for r in RL), '<', c[i,j])

    # Start optimization
    model.params.outputflag = 0
    model.optimize()

    # If optimal solution is found get the results
    if model.status != GRB.Status.OPTIMAL:
        if model.status == 3:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        elif model.status == 4:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible or unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        if model.status == 5:
            arcpy.AddMessage('Optimal solution is not found! The model is unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

    else:
        su = model.getAttr('x', u)
        sv = model.getAttr('x', v)

        # The result is given as set of working and protection paths for every demand
        distance1, distance2 = {}, {}
        path1, path2 = {}, {}

        for r in RL:
            d1 = 0
            d2 = 0
            p1 = []
            p2 = []
            for i, j in arcs:
                if su[r[0], i, j] > 0:
                    p1.append((i, j))
                    d1 += d[i, j]
                if sv[r[0], i, j] > 0:
                    p2.append((i, j))
                    d2 += d[i, j]

                    # Select the shorter path as working path and longer as backup path
            if d1 <= d2:
                distance1[r[1]] = d1
                distance2[r[1]] = d2
                path1[r[1]] = p1
                path2[r[1]] = p2
            else:
                distance1[r[1]] = d2
                distance2[r[1]] = d1
                path1[r[1]] = p2
                path2[r[1]] = p1

    return distance1, distance2, path1, path2


# MILP formulation for node disjoint paths with capacity constraint
def optimize_node_disjoint_cap(G, D, R):
    model = Model("Node disjoint paths with capacity constraint")

    # Identify the source and the destination of the demand
    t = {}
    RL = list(enumerate(R))

    for r, (src, dst) in RL:
        for n in G.nodes():
            if n==src:
                t[r,n] = -1
            elif n==dst:
                t[r,n] = 1
            else:
                t[r,n] = 0

        print RL[r][1]
        print R[RL[r][1]]

    # Transform undirected edges to directed arcs
    d = {}
    c = {}
    arcs = []
    C = nx.get_edge_attributes(G, "capacity")

    for i, j in G.edges():
        d[i,j] = D[i,j]
        d[j,i] = D[j,i]
        c[i,j] = C[i,j]
        c[j,i] = C[i,j]
        arcs.append((i,j))
        arcs.append((j,i))

    # Binary variables indicate if arc (i,j) belongs to the working and backup paths of demand r
    u, v = {}, {}
    for r in RL:
        for i,j in arcs:
            u[r[0],i,j] = model.addVar(vtype="B", name="u[%s,%s,%s]" %(r[0],i,j))
            v[r[0],i,j] = model.addVar(vtype="B", name="v[%s,%s,%s]" %(r[0],i,j))

    # Binary variables indicate if node n belongs to the working and backup paths of demand r
    h, k = {}, {}
    for r in RL:
        for n in G.nodes():
            h[r[0],n] = model.addVar(vtype="B", name="u[%s,%s]" %(r[0],n))
            k[r[0],n] = model.addVar(vtype="B", name="v[%s,%s]" %(r[0],n))
    model.update()

    # Optimization goal
    model.setObjective(quicksum((u[r[0],i,j] + v[r[0],i,j])*d[i,j] for r in RL for i,j in arcs), GRB.MINIMIZE)

    # Flow conservation constraint
    for r in RL:
        for m in G.nodes():
            model.addConstr(
                quicksum(u[r[0], i, j] for i, j in arcs if j == m) - quicksum(u[r[0], i, j] for i, j in arcs if i == m),
                "=", t[r[0], m])
            model.addConstr(
                quicksum(v[r[0], i, j] for i, j in arcs if j == m) - quicksum(v[r[0], i, j] for i, j in arcs if i == m),
                "=", t[r[0], m])

            # Capacity constraint
            for i, j in arcs:
                model.addConstr(quicksum(R[RL[r[0]][1]]*(u[r[0],i,j] + v[r[0],i,j]) for r in RL), '<', c[i,j])

    # Constraint: if the link is chosen, both of the nodes have to be indicated as chosen
    for r in RL:
        for n in G.nodes():
            model.addConstr(h[r[0], n] - quicksum(u[r[0],n,j] for i,j in arcs if i == n), "=>", 0)
            model.addConstr(k[r[0], n] - quicksum(v[r[0],n,j] for i,j in arcs if i == n), "=>", 0)

    # Constraint: Link paths have to be node disjoint
    for r in RL:
        for n in G.nodes():
            # except source and destination
            if n != r[1][1] and n != r[1][0]:
                model.addConstr(h[r[0], n] + k[r[0], n], "<=", 1, name="Node disjoint paths")


    # Start optimization
    model.params.outputflag = 0
    model.optimize()

    # If optimal solution is found get the results
    if model.status != GRB.Status.OPTIMAL:
        if model.status == 3:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        elif model.status == 4:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible or unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        if model.status == 5:
            arcpy.AddMessage('Optimal solution is not found! The model is unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

    else:
        su = model.getAttr('x', u)
        sv = model.getAttr('x', v)

        # The result is given as set of working and protection paths for every demand
        distance1, distance2 = {}, {}
        path1, path2 = {}, {}

        for r in RL:
            d1 = 0
            d2 = 0
            p1 = []
            p2 = []
            for i, j in arcs:
                if su[r[0], i, j] > 0:
                    p1.append((i, j))
                    d1 += d[i, j]
                if sv[r[0], i, j] > 0:
                    p2.append((i, j))
                    d2 += d[i, j]

                    # Select the shorter path as working path and longer as backup path
            if d1 <= d2:
                distance1[r[1]] = d1
                distance2[r[1]] = d2
                path1[r[1]] = p1
                path2[r[1]] = p2
            else:
                distance1[r[1]] = d2
                distance2[r[1]] = d1
                path1[r[1]] = p2
                path2[r[1]] = p1

    return distance1, distance2, path1, path2


# MILP formulation for link disjoint paths with capacity constraint and link SRGs
def optimize_link_disjoint_cap_srg_links(G, D, R, srg_links):
    model = Model("Link disjoint paths with capacity constraint and link SRGs")

    # Identify the source and the destination of the demand
    t = {}
    RL = list(enumerate(R))

    for r, (src, dst) in RL:
        for n in G.nodes():
            if n == src:
                t[r, n] = -1
            elif n == dst:
                t[r, n] = 1
            else:
                t[r, n] = 0

        print RL[r][1]
        print R[RL[r][1]]

    # Transform undirected edges to directed arcs
    d = {}
    c = {}
    arcs = []
    C = nx.get_edge_attributes(G, "capacity")

    for i, j in G.edges():
        d[i, j] = D[i, j]
        d[j, i] = D[j, i]
        c[i, j] = C[i, j]
        c[j, i] = C[i, j]
        arcs.append((i, j))
        arcs.append((j, i))

    # Binary variables indicate if arc (i,j) belongs to the working and backup paths of demand r
    u, v = {}, {}
    for r in RL:
        for i,j in arcs:
            u[r[0],i,j] = model.addVar(vtype="B", name="u[%s,%s,%s]" %(r[0],i,j))
            v[r[0],i,j] = model.addVar(vtype="B", name="v[%s,%s,%s]" %(r[0],i,j))
    model.update()

    # Optimization goal
    model.setObjective(quicksum((u[r[0],i,j] + v[r[0],i,j])*d[i,j] for r in RL for i,j in arcs), GRB.MINIMIZE)

    # Constraint: Link paths have to be link disjoint
    for r in RL:
        for i, j in arcs:
            model.addConstr(u[r[0],i,j] + v[r[0],i,j], "<=", 1, name="Link disjoint paths")

    # SRG constraint
    for r in RL:
        for key,value in srg_links.items():
            model.addConstr(u[r[0], value[0][0], value[0][1]] + v[r[0], value[1][0], value[1][1]], "<=", 1, name="SRG links first direction")
            model.addConstr(u[r[0], value[0][0], value[0][1]] + v[r[0], value[1][1], value[1][0]], "<=", 1,
                            name="SRG links first direction")

            model.addConstr(u[r[0], value[0][1], value[0][0]] + v[r[0], value[1][0], value[1][1]], "<=", 1, name="SRG links second direction")
            model.addConstr(u[r[0], value[0][1], value[0][0]] + v[r[0], value[1][1], value[1][0]], "<=", 1,
                            name="SRG links second direction")

            model.addConstr(u[r[0], value[1][0], value[1][1]] + v[r[0], value[0][0], value[0][1]], "<=", 1, name="SRG links first direction")
            model.addConstr(u[r[0], value[1][0], value[1][1]] + v[r[0], value[0][1], value[0][0]], "<=", 1,
                            name="SRG links first direction")
            model.addConstr(u[r[0], value[1][1], value[1][0]] + v[r[0], value[0][1], value[0][0]], "<=", 1, name="SRG links second direction")
            model.addConstr(u[r[0], value[1][1], value[1][0]] + v[r[0], value[0][0], value[0][1]], "<=", 1,
                        name="SRG links second direction")


    # Flow conservation constraint
    for r in RL:
        for m in G.nodes():
            model.addConstr(quicksum(u[r[0],i,j] for i,j in arcs if j==m) - quicksum(u[r[0],i,j] for i,j in arcs if i==m), "=", t[r[0],m])
            model.addConstr(quicksum(v[r[0],i,j] for i,j in arcs if j==m) - quicksum(v[r[0],i,j] for i,j in arcs if i==m), "=", t[r[0],m])

    # Capacity constraint
    for i, j in arcs:
        model.addConstr(quicksum(R[RL[r[0]][1]]*(u[r[0],i,j] + v[r[0],i,j]) for r in RL), '<', c[i,j])

    # Start optimization
    model.params.outputflag = 0
    model.optimize()

    # If optimal solution is found get the results
    if model.status != GRB.Status.OPTIMAL:
        if model.status == 3:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        elif model.status == 4:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible or unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        if model.status == 5:
            arcpy.AddMessage('Optimal solution is not found! The model is unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

    else:
        su = model.getAttr('x', u)
        sv = model.getAttr('x', v)

        # The result is given as set of working and protection paths for every demand
        distance1, distance2 = {}, {}
        path1, path2 = {}, {}

        for r in RL:
            d1 = 0
            d2 = 0
            p1 = []
            p2 = []
            for i, j in arcs:
                if su[r[0], i, j] > 0:
                    p1.append((i, j))
                    d1 += d[i, j]
                if sv[r[0], i, j] > 0:
                    p2.append((i, j))
                    d2 += d[i, j]

                    # Select the shorter path as working path and longer as backup path
            if d1 <= d2:
                distance1[r[1]] = d1
                distance2[r[1]] = d2
                path1[r[1]] = p1
                path2[r[1]] = p2
            else:
                distance1[r[1]] = d2
                distance2[r[1]] = d1
                path1[r[1]] = p2
                path2[r[1]] = p1

    return distance1, distance2, path1, path2


# MILP formulation for node disjoint paths with capacity constraint and Node SRGs
def optimize_node_disjoint_cap_srg_nodes(G, D, R, srg_node):
    model = Model("Node disjoint paths with capacity constraint")

    # Identify the source and the destination of the demand
    t = {}
    RL = list(enumerate(R))

    for r, (src, dst) in RL:
        for n in G.nodes():
            if n == src:
                t[r, n] = -1
            elif n == dst:
                t[r, n] = 1
            else:
                t[r, n] = 0

        print RL[r][1]
        print R[RL[r][1]]

    # Transform undirected edges to directed arcs
    d = {}
    c = {}
    arcs = []
    C = nx.get_edge_attributes(G, "capacity")

    arcpy.AddMessage(C)

    for i, j in G.edges():
        d[i, j] = D[i, j]
        d[j, i] = D[j, i]
        c[i, j] = C[i, j]
        c[j, i] = C[i, j]
        arcs.append((i, j))
        arcs.append((j, i))

    # Binary variables indicate if arc (i,j) belongs to the working and backup paths of demand r
    u, v = {}, {}
    for r in RL:
        for i,j in arcs:
            u[r[0],i,j] = model.addVar(vtype="B", name="u[%s,%s,%s]" %(r[0],i,j))
            v[r[0],i,j] = model.addVar(vtype="B", name="v[%s,%s,%s]" %(r[0],i,j))

    # Binary variables indicate if node n belongs to the working and backup paths of demand r
    h, k = {}, {}
    for r in RL:
        for n in G.nodes():
            h[r[0],n] = model.addVar(vtype="B", name="u[%s,%s]" %(r[0],n))
            k[r[0],n] = model.addVar(vtype="B", name="v[%s,%s]" %(r[0],n))
    model.update()

    # Optimization goal
    model.setObjective(quicksum((u[r[0],i,j] + v[r[0],i,j])*d[i,j] for r in RL for i,j in arcs), GRB.MINIMIZE)

    # Flow conservation constraint
    for r in RL:
        for m in G.nodes():
            model.addConstr(
                quicksum(u[r[0], i, j] for i, j in arcs if j == m) - quicksum(u[r[0], i, j] for i, j in arcs if i == m),
                "=", t[r[0], m])
            model.addConstr(
                quicksum(v[r[0], i, j] for i, j in arcs if j == m) - quicksum(v[r[0], i, j] for i, j in arcs if i == m),
                "=", t[r[0], m])

            # Capacity constraint
            for i, j in arcs:
                model.addConstr(quicksum(R[RL[r[0]][1]]*(u[r[0],i,j] + v[r[0],i,j]) for r in RL), '<', c[i,j])

    # Constraint: if the link is chosen, both of the nodes have to be indicated as chosen
    for r in RL:
        for n in G.nodes():
            model.addConstr(h[r[0], n] - quicksum(u[r[0],n,j] for i,j in arcs if i == n), "=>", 0)
            model.addConstr(k[r[0], n] - quicksum(v[r[0],n,j] for i,j in arcs if i == n), "=>", 0)

    # Constraint: Link paths have to be node disjoint
    for r in RL:
        for n in G.nodes():
            # except source and destination
            if n != r[1][1] and n != r[1][0]:
                model.addConstr(h[r[0], n] + k[r[0], n], "<=", 1, name="Node disjoint paths")

    # SRG constraint
    for r in RL:
        for key, value in srg_node.items():
            if value[0] != r[1][1] and value[1] != r[1][0]:
                model.addConstr(h[r[0], value[0]] + k[r[0], value[1]], "<=", 1, name="Node srg 1")
                model.addConstr(h[r[0], value[1]] + k[r[0], value[0]], "<=", 1, name="Node srg 2")


    # Start optimization
    model.params.outputflag = 0
    model.optimize()

    # If optimal solution is found get the results
    if model.status != GRB.Status.OPTIMAL:
        if model.status == 3:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        elif model.status == 4:
            arcpy.AddMessage('Optimal solution is not found! The model is infeasible or unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

        if model.status == 5:
            arcpy.AddMessage('Optimal solution is not found! The model is unbounded.')
            distance1 = 0
            distance2 = 0
            path1 = 0
            path2 = 0

    else:
        su = model.getAttr('x', u)
        sv = model.getAttr('x', v)

        # The result is given as set of working and protection paths for every demand
        distance1, distance2 = {}, {}
        path1, path2 = {}, {}

        for r in RL:
            d1 = 0
            d2 = 0
            p1 = []
            p2 = []
            for i, j in arcs:
                if su[r[0], i, j] > 0:
                    p1.append((i, j))
                    d1 += d[i, j]
                if sv[r[0], i, j] > 0:
                    p2.append((i, j))
                    d2 += d[i, j]

                    # Select the shorter path as working path and longer as backup path
            if d1 <= d2:
                distance1[r[1]] = d1
                distance2[r[1]] = d2
                path1[r[1]] = p1
                path2[r[1]] = p2
            else:
                distance1[r[1]] = d2
                distance2[r[1]] = d1
                path1[r[1]] = p2
                path2[r[1]] = p1

    return distance1, distance2, path1, path2
