# -------------------------------------------------------------
# Name:             srgs_dumping.py
# Purpose:          Formats the SRG dicts for the appropriate input
# Author:           Elena Grigoreva, e.v.grigoryeva@gmail.com (Technical University of Munich)
# About author:     https://egrigoreva.github.io/
# Created:          12/10/2018
# Copyright:        (c) Chair of Communication Networks, Department of Electrical and Computer Engineering,
#                   Technical University of Munich
# ArcGIS Version:   10.3.1
# Python Version:   2.7
# -------------------------------------------------------------

import pickle
import os


def main(path_out, srg_nodes, srg_links):

    ###################################################################################################################
    # SRG links
    output_srg_link = os.path.join(path_out, 'srg_links_nobel.pkl')

    with open(output_srg_link, 'wb') as f_srgl:
        pickle.dump(srg_links, f_srgl)

    with open(output_srg_link, 'rb') as f_d:
        test = pickle.load(f_d)
        print(test)

    ###################################################################################################################
    # SRG nodes
    output_srg_node = os.path.join(path_out, 'srg_nodes_nobel.pkl')

    with open(output_srg_node, 'wb') as f_srgn:
        pickle.dump(srg_nodes, f_srgn)

    with open(output_srg_node, 'rb') as f_d:
        test = pickle.load(f_d)
        print(test)

    return

if __name__ == '__main__':
    # srg_links_in = {1: [('Munich', 'Berlin'), ('Hamburg', 'Amsterdam')],
    #                 2: [('Dublin', 'Glasgow'), ('London', 'Amsterdam')],
    #                 3:[('Budapest', 'Belgrade'), ('Vienna', 'Zagreb')]}
    #
    # srg_nodes_in = {1: ['Munich', 'Amsterdam'], 2: ['Glasgow', 'London'], 3: ['Budapest', 'Zagreb']}
    #
    # path_out_in = r'C:\Users\ga36bat\ownCloud\Reliability_project\CoreNetworkTopologies\ProblemSetEU'

    # path_out_in = r'D:\GISworkspace\4_Teaching\Reliability_project\CoreNetworkTopologies\ProblemSetGER'
    # srg_nodes_in = {1: ['Bremen', 'Hannover', 'Hamburg'], 2: ['Berlin', 'Leipzig'], 3: ['Karlsruhe', 'Stuttgart']}
    # srg_links_in = {1: [('Bremen', 'Hannover'), ('Hannover', 'Hamburg')],
    #                 2: [('Berlin', 'Leipzig'), ('Berlin', 'Greifswald')],
    #                 3:[('Karlsruhe', 'Stuttgart'), ('Karlsruhe', 'Mannheim')]}


    path_out_in = r'D:\GISworkspace\4_Teaching\Reliability_project\CoreNetworkTopologies\ProblemSetGER'
    srg_nodes_in = {1: ['Bremen', 'Hannover', 'Hamburg'], 2: ['Berlin', 'Leipzig'], 3: ['Karlsruhe', 'Stuttgart']}
    srg_links_in = {1: [('Bremen', 'Hannover'), ('Hannover', 'Hamburg')], #
                    2: [('Karlsruhe', 'Stuttgart'), ('Stuttgart', 'Nuernberg')]} #


    # path_out_in = r'D:\GISworkspace\4_Teaching\Reliability_project\CoreNetworkTopologies\ProblemSetUS'
    # srg_nodes_in = {1: ['Nashville', 'Charlotte'], 2: ['Denver', 'ElPaso'], 3: ['LosAngeles', 'SanFrancisco', 'LasVegas']}
    # srg_links_in = {1: [('Indianapolis', 'Nashville'), ('Indianapolis', 'StLouis')],
    #                 2: [('Dallas', 'Nashville'), ('NewOrleans', 'Houston')]}

    # path_out_in = r'D:\GISworkspace\4_Teaching\Reliability_project\CoreNetworkTopologies\ProblemSetUS'
    # srg_nodes_in = {1: ['Princeton', 'Pittsburgh', 'Washington'],
    #                 2: ['Boulder', 'Lincoln'],
    #                 3: ['SanFrancisco', 'San-Diego', 'SaltLakeCity']}
    # srg_links_in = {1: [('Pittsburgh', 'Urbana-Champaign'), ('Pittsburgh', 'Atlanta'), ('Washington', 'Ithaca')],
    #                 2: [('Boulder', 'Lincoln'), ('SaltLakeCity', 'Ann-Arbor')]}

    # path_out_in = r'D:\GISworkspace\4_Teaching\Reliability_project\CoreNetworkTopologies\ProblemSetPoland'
    # srg_nodes_in = {1: ['Kolobrzeg', 'Bydgoszcz'], 2: ['Wroclaw', 'Lodz']}
    # srg_links_in = {1: [('Szczecin', 'Poznan'), ('Bydgoszcz', 'Poznan')],
    #                 2: [('Bialystok', 'Warsaw'), ('Krakow', 'Warsaw')]}

    main(path_out_in, srg_nodes_in, srg_links_in)