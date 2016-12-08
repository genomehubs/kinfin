#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
usage: kinfin-d.py      -g <FILE> -c <FILE> -s <FILE> [-t <FILE>] [-o <PREFIX>]
                        [--infer_singletons]
                        [-p <FILE>] [-a <DIR>]
                        [--functional_annotation <FILE>]
                        [--nodesdb <FILE>] [--taxranks <STRING>]
                        [-f <FLOAT>] [-n <INT>] [--min <INT>] [--max <INT>]
                        [-r <INT>] [--min_proteomes <INT>]
                        [--fontsize <INT>] [--plotsize INT,INT]
                        [--plotfmt <PLOTFORMAT>]
                        [-h|--help]

    Options:
        -h --help                               show this

        Input files
            -g, --cluster_file <FILE>           OrthologousGroups.txt produced by OrthoFinder
            -c, --attribute_file <FILE>         SpeciesClassification file
            -s, --sequence_ids_file <FILE>      SequenceIDs.txt used in OrthoFinder

            -p, --species_ids_file <FILE>       SpeciesIDs.txt used in OrthoFinder
            --functional_annotation <FILE>      Mapping of ProteinIDs to GO/IPRS/SignalP/Pfam/... (can be generated through 'iprs_to_table.py')
            -a, --fasta_dir <DIR>               Directory of FASTA files
            --nodesdb <FILE>                    nodesdb file (sames as blobtools nodesDB file)
            -t, --tree_file <FILE>              Tree file (on which ALOs are defined)
        General options
            -o, --outprefix <STR>               Output prefix
            --infer_singletons                  Absence of proteins in clustering is interpreted as singleton
            --min_proteomes <INT>               Minimum number of proteomes for an ALO to be used in computations [default: 2]
            --taxranks <STRING>                 Taxranks to be inferred from TaxID [default: kingdom,phylum,class,superfamily]
        "Fuzzy"-Orthology-groups
            -f, --fuzzyness <FLOAT>             "Fuzzyness"-factor F [default: 0.75]
            -n, --target_count <INT>            Protein count by proteome in (100*F)%% of cluster [default: 1]
            --min <INT>                         Min count of proteins by proteome in (100*(1-F))%% of cluster [default: 0]
            --max <INT>                         Max count of proteins by proteome in (100*(1-F))%% of cluster [default: 100]

        Plotting
            -r, --repetitions <INT>             Number of repetitions for rarefaction curves [default: 30]
            --fontsize <INT>                    Fontsize for plots [default: 18]
            --plotsize <INT,INT>                Size (WIDTH,HEIGHT) for plots [default: 24,12]
            --plotfmt <STR>                     Plot formats [default: png]

"""


########################################################################
# Imports
########################################################################

from __future__ import division
import sys
from os.path import isfile, join, exists
from os import getcwd, mkdir
import shutil
import random
import time
from decimal import Decimal

from collections import Counter, defaultdict
from math import sqrt, log

import_errors = []
try:
    from docopt import docopt
except ImportError:
    import_errors.append("[ERROR] : Module \'Docopt\' was not found. Please install \'Docopt\' using \'pip install docopt\'")
try:
    import matplotlib as mat
    mat.use("agg")
except ImportError:
    import_errors.append("[ERROR] : Module \'Matplotlib\' was not found. Please install \'Matplotlob\' using \'pip install matplotlib\'")
try:
    import scipy
except ImportError:
    import_errors.append("[ERROR] : Module \'SciPy\' was not found. Please install \'SciPy\' using \'pip install scipy\'")
#try:
#    import seaborn as sns
#except ImportError:
#    import_errors.append("[ERROR] : Module \'Seaborn\' was not found. Please install \'Seaborn\' using \'pip install seaborn\'")
#try:
#    import powerlaw
#except ImportError:
#    import_errors.append("[ERROR] : Module \'powerlaw\'' was not found. Please install \'powerlaw\' using \'pip install powerlaw\'")
if import_errors:
    sys.exit("\n".join(import_errors))

import numpy as np
from matplotlib.ticker import FormatStrFormatter
import matplotlib.pyplot as plt
import seaborn as sns
plt.style.use('ggplot')
sns.set_context("talk")
sns.set(style="whitegrid")
sns.set_color_codes("pastel")
mat.rc('ytick', labelsize=20)
mat.rc('xtick', labelsize=20)
axis_font = {'size':'20'}
mat.rcParams.update({'font.size': 22})

########################################################################
# General functions
########################################################################

def check_file(infile):
    if infile:
        if not isfile(infile):
            sys.exit("[ERROR] - %s does not exist." % (infile))

def get_attribute_cluster_type(singleton, implicit_protein_ids_by_proteome_id_by_level):
    if singleton:
        return 'singleton'
    else:
        if len(implicit_protein_ids_by_proteome_id_by_level) > 1:
            return 'shared'
        else:
            return 'specific'

def get_ALO_cluster_cardinality(ALO_proteome_counts_in_cluster):
    if len(ALO_proteome_counts_in_cluster) > 2:
        ALO_proteome_counts_in_cluster_length = len(ALO_proteome_counts_in_cluster)
        if all(count == 1 for count in ALO_proteome_counts_in_cluster):
            return 'true'
        else:
            ALO_proteome_counts_in_cluster_at_fuzzycount_count = len([ALO_proteome_counts for ALO_proteome_counts in ALO_proteome_counts_in_cluster if ALO_proteome_counts == inputObj.fuzzy_count])
            ALO_proteome_counts_in_cluster_in_fuzzyrange_count = len([ALO_proteome_counts for ALO_proteome_counts in ALO_proteome_counts_in_cluster if ALO_proteome_counts in inputObj.fuzzy_range])
            fuzzy_fraction = ALO_proteome_counts_in_cluster_at_fuzzycount_count/ALO_proteome_counts_in_cluster_length
            if fuzzy_fraction >= inputObj.fuzzy_fraction:
                if ALO_proteome_counts_in_cluster_at_fuzzycount_count + ALO_proteome_counts_in_cluster_in_fuzzyrange_count == ALO_proteome_counts_in_cluster_length:
                    return 'fuzzy'
    return None

def mannwhitneyu(count_1, count_2):
    pvalue, log2_mean, mean_count_1, mean_count_2 = None, None, None, None
    implicit_count_1 = [count for count in count_1 if count > 0]
    implicit_count_2 = [count for count in count_2 if count > 0]
    if len(implicit_count_1) >= inputObj.min_proteomes and len(implicit_count_2) >= inputObj.min_proteomes:
        try:
            pvalue = scipy.stats.mannwhitneyu(implicit_count_1, implicit_count_2, alternative="two-sided")[1]
        except:
            pvalue = 1.0
        mean_count_1 = mean(implicit_count_1)
        mean_count_2 = mean(implicit_count_2)
        log2_mean = log((mean(implicit_count_1)/mean(implicit_count_2)), 2)
    return pvalue, log2_mean, mean_count_1, mean_count_2

def get_lineage(taxid, nodesdb):
    lineage = {taxrank : 'undef' for taxrank in inputObj.taxranks}
    parent = ''
    node = taxid
    while parent != "1":
        taxrank = nodesdb[node]['rank']
        name = nodesdb[node]['name']
        parent = nodesdb[node]['parent']
        if taxrank in inputObj.taxranks:
            lineage[taxrank] = name
        node = parent
    return lineage

def parse_nodesdb(nodesdb_f):
    nodesdb = {}
    nodesdb_count = 0
    nodes_count = 0
    for line in read_file(nodesdb_f):
        if line.startswith("#"):
            nodesdb_count = int(line.lstrip("# nodes_count = ").rstrip("\n"))
        else:
            nodes_count += 1
            node, rank, name, parent = line.rstrip("\n").split("\t")
            nodesdb[node] = {'rank' : rank, 'name' : name, 'parent' : parent}
            if nodesdb_count:
                progress(nodes_count, 1000, nodesdb_count)
    return nodesdb

def parse_tree(tree_f, outgroups):
    check_file(tree_f)
    print "[STATUS] - Parsing Tree file : %s ..." % (tree_f)
    tree_ete = ete3.Tree(tree_f)
    if len(outgroups) > 1:
        print "[STATUS] - Setting LCA of %s as outgroup : ..." % (",".join(outgroups))
        outgroup_node = tree_ete.get_common_ancestor(outgroups)
        tree_ete.set_outgroup(outgroup_node)
    else:
        print "[STATUS] - Setting %s as outgroup : ..." % (",".join(outgroups))
        tree_ete.set_outgroup(outgroups[0])
    print tree_ete
    node_idx_by_proteome_ids = {}
    for idx, node in enumerate(tree_ete.traverse("levelorder")):
        proteome_ids = frozenset([leaf.name for leaf in node])
        if not node.name:
            node.add_features(name=idx, nodetype="node", idx="node%s" % (idx), proteome_ids=proteome_ids, counts={'specific' : 0, 'shared' : 0, "absent" : 0, "singleton" : 0})
        else:
            node.add_features(nodetype="tip", idx="node%s" % (idx), proteome_ids=proteome_ids, counts={'specific' : 0, 'shared' : 0, "absent" : 0, "singleton" : 0})
        node_idx_by_proteome_ids[proteome_ids] = node.name
    return tree_ete, node_idx_by_proteome_ids

def readFastaLen(infile):
    with open(infile) as fh:
        header, seqs = '', []
        for l in fh:
            if l[0] == '>':
                if header:
                    yield header, len(''.join(seqs))
                header, seqs = l[1:-1].split()[0], [] # Header is split at first whitespace
            else:
                seqs.append(l[:-1])
        yield header, len(''.join(seqs))

def median(lst):
    list_sorted = sorted(lst)
    list_length = len(lst)
    index = (list_length - 1) // 2
    if list_length % 2:
        return list_sorted[index]/1.0
    else:
        return (list_sorted[index] + list_sorted[index + 1])/2.0

def mean(lst):
    if lst:
        return float(sum(lst)) / len(lst)
    else:
        return 0.0

def sd(lst, population=True):
    n = len(lst)
    differences = [x_ - mean(lst) for x_ in lst]
    sq_differences = [d ** 2 for d in differences]
    ssd = sum(sq_differences)
    if population is True:
        variance = ssd / n
    else:
        variance = ssd / (n - 1)
    sd_result = sqrt(variance)
    return sd_result

def progress(iteration, steps, max_value):
    if int(iteration) == int(max_value):
        sys.stdout.write('\r')
        print "[PROGRESS] \t- %d%%" % (100)
    elif int(iteration) % int(steps+1) == 0:
        sys.stdout.write('\r')
        print "[PROGRESS] \t- %d%%" % (float(int(iteration)/int(max_value))*100),
        sys.stdout.flush()
    else:
        pass

def read_file(infile):
    if not infile or not exists(infile):
        sys.exit("[ERROR] - File '%s' does not exist." % (infile))
    with open(infile) as fh:
        for line in fh:
            yield line.rstrip("\n")

########################################################################
# CLASS : DataFactory
########################################################################

class DataFactory():
    def __init__(self):
        self.dirs = None

    ###############################
    ### build_AloCollection
    ###############################
    def build_AloCollection(self):
        attribute_f = inputObj.attribute_f
        nodesdb_f = inputObj.nodesdb_f
        tree_f = inputObj.tree_f
        proteomes, proteome_id_by_species_id, attributes, level_by_attribute_by_proteome_id = self.parse_attributes(attribute_f)
        # Add taxonomy if needed
        if 'taxid' in set(attributes):
            print "[STATUS] - Attribute 'taxid' found, inferring taxonomic ranks from nodesDB..."
            attributes, level_by_attribute_by_proteome_id = self.add_taxid_attributes(nodesdb_f, attributes, level_by_attribute_by_proteome_id)
        # Add ALOs from tree if provided
        tree_ete = None
        node_idx_by_proteome_ids = None
        if tree_f:
            outgroups = []
            if not "OUT" in attributes:
                sys.exit("[ERROR] - Please specify one of more outgroup taxa in the attribute file.")
            outgroups = [proteome_id for proteome_id in proteomes if level_by_attribute_by_proteome_id[proteome_id]["OUT"] == "1"]
            tree_ete, node_idx_by_proteome_ids = parse_tree(tree_f, outgroups)
        print "[STATUS] - Building AloCollection ..."
        return AloCollection(proteomes, proteome_id_by_species_id, attributes, level_by_attribute_by_proteome_id, tree_ete, node_idx_by_proteome_ids)

    ###############################
    ### build_AloCollection  parse_attributes
    ###############################

    def parse_attributes(self, attribute_f):
        print "[STATUS] - Parsing SpeciesClassification file: %s ..." % (attribute_f)
        attributes = []
        level_by_attribute_by_proteome_id = {}
        proteomes = set()
        proteome_id_by_species_id = {}
        for line in read_file(attribute_f):
            if line.startswith("#"):
                attributes = [x.strip() for x in line.lstrip("#").split(",")]
                if not 'IDX' == attributes[0] or not 'PROTEOME' == attributes[1]:
                    sys.exit("[ERROR] - First/second element have to be IDX/PROTEOME.\n\t%s" % (attributes))
            elif line.strip():
                temp = line.split(",")
                if not len(temp) == len(attributes):
                    sys.exit("[ERROR] - number of columns in line differs from header\n\t%s\n\t%s" % (attributes, temp))
                if temp[1] in proteomes:
                    sys.exit("[ERROR] - 'proteome' should be unique. %s was encountered multiple times" % (temp[0]))
                species_id = temp[0]
                proteome_id = temp[1]
                proteomes.add(proteome_id)
                proteome_id_by_species_id[species_id] = proteome_id
                level_by_attribute_by_proteome_id[proteome_id] = {x : '' for x in attributes}
                for idx, level in enumerate(temp):
                    attribute = attributes[idx]
                    level_by_attribute_by_proteome_id[proteome_id][attribute] = level
                level_by_attribute_by_proteome_id[proteome_id]['global'] = 'True'
            else:
                pass
        attributes.insert(0, "global") # append to front
        return proteomes, proteome_id_by_species_id, attributes, level_by_attribute_by_proteome_id

    ###############################
    ### build_AloCollection  add_taxid_attributes
    ###############################

    def add_taxid_attributes(self, nodesdb_f, attributes, level_by_attribute_by_proteome_id):
        if nodesdb_f:
            check_file(nodesdb_f)
        else:
            sys.exit("[ERROR] - Please provide a nodesDB file or remove the 'taxid' attribute")
        print "[STATUS] - Parsing nodesDB %s" % (nodesdb_f)
        NODESDB = parse_nodesdb(nodesdb_f)
        for proteome_id in level_by_attribute_by_proteome_id:
            taxid = level_by_attribute_by_proteome_id[proteome_id]['taxid']
            lineage = get_lineage(taxid, NODESDB)
            # add lineage attribute/levels
            for taxrank in inputObj.taxranks:
                level_by_attribute_by_proteome_id[proteome_id][taxrank] = lineage[taxrank].replace(" ", "_")
            # remove taxid-levels
            del level_by_attribute_by_proteome_id[proteome_id]['taxid']
        # remove taxid-attribute
        attributes.remove('taxid')
        # add taxranks to rank
        for taxrank in inputObj.taxranks:
            attributes.append(taxrank)
        self.nodesdb_file = nodesdb_f
        return attributes, level_by_attribute_by_proteome_id

    ###############################
    ### setup_dirs
    ###############################

    def setup_dirs(self, inputObj):
        outprefix = inputObj.outprefix
        self.dirs = {}
        if outprefix:
            result_path = join(getcwd(), "%s.kinfin_results" % (outprefix))
        else:
            result_path = join(getcwd(), "kinfin_results")
        self.dirs['main'] = result_path
        print "[STATUS] - Output directories in \n\t%s" % (result_path)
        if exists(result_path):
            print "[STATUS] - Directory exists. Deleting directory ..."
            shutil.rmtree(result_path)
        print "[STATUS] - Creating directories ..."
        mkdir(result_path)
        for attribute in aloCollection.attributes:
            attribute_path = join(result_path, attribute)
            self.dirs[attribute] = attribute_path
            if not exists(attribute_path):
                print "\t%s" % (attribute_path)
                mkdir(attribute_path)
        if aloCollection.tree_ete:
            tree_path = join(result_path, "tree")
            node_chart_path = join(tree_path, "charts")
            node_header_path = join(tree_path, "headers")
            self.dirs["tree"] = tree_path
            self.dirs["tree_charts"] = node_chart_path
            self.dirs["tree_headers"] = node_header_path
            if not exists(tree_path):
                print "\t%s" % (tree_path)
                mkdir(tree_path)
                print "\t%s" % (node_chart_path)
                mkdir(node_chart_path)
                print "\t%s" % (node_header_path)
                mkdir(node_header_path)

    ###############################
    ### build_ProteinCollection
    ###############################

    def build_ProteinCollection(self, inputObj):
        # PARSE PROTEINS
        proteinObjs = []
        sequence_ids_f = inputObj.sequence_ids_f
        print "[STATUS] - Parsing sequence IDs: %s ..." % sequence_ids_f
        for line in read_file(sequence_ids_f):
            temp = line.split(": ")
            sequence_id = temp[0]
            protein_id = temp[1].split(" ")[0]
            species_id = sequence_id.split("_")[0]
            proteome_id = aloCollection.proteome_id_by_species_id.get(species_id, None)
            if proteome_id:
                proteinObj = ProteinObj(protein_id, proteome_id, species_id, sequence_id)
                proteinObjs.append(proteinObj)
        proteinCollection = ProteinCollection(proteinObjs)
        print "[STATUS]\t - Proteins found = %s" % (proteinCollection.protein_count)

        # PARSE FASTA DIR
        fasta_dir = inputObj.fasta_dir
        species_ids_f = inputObj.species_ids_f
        if fasta_dir:
            print "[STATUS] - Parsing FASTAs ..."
            fasta_file_by_species_id = self.parse_species_ids(species_ids_f)
            fasta_len_by_protein_id = self.parse_fasta_dir(fasta_dir, fasta_file_by_species_id)
            print "[STATUS] - Adding FASTAs to ProteinCollection ..."
            parse_steps = proteinCollection.protein_count/100
            for idx, proteinObj in enumerate(proteinCollection.proteinObjs):
                proteinObj.add_length(fasta_len_by_protein_id[proteinObj.protein_id])
                progress(idx+1, parse_steps, proteinCollection.protein_count)
            aloCollection.fastas_parsed = True
            proteinCollection.fastas_parsed = True
        else:
            print "[STATUS] - No Fasta-Dir given, no AA-span information will be reported ..."

        # PARSE DOMAINS
        functional_annotation_f = inputObj.functional_annotation_f
        if functional_annotation_f:
            # PARSE DOMAINS
            print "[STATUS] - Parsing %s ... this may take a while" % (functional_annotation_f)
            for line in read_file(functional_annotation_f):
                temp = line.split("\t")
                if temp[0].startswith("#"):
                    proteinCollection.domain_sources = temp[1:]
                else:
                    if not proteinCollection.domain_sources:
                        sys.exit("[ERROR] - %s does not seem to have a header." % (functional_annotation_f))
                    domain_protein_id = temp.pop(0)
                    go_terms = []
                    domain_counter_by_domain_source = {}
                    for idx, field in enumerate(temp):
                        if not field == "None":
                            domain_source = proteinCollection.domain_sources[idx]
                            domain_string = field.split(";")
                            if domain_source == "GO":
                                for go_term in domain_string:
                                    go_terms.append(go_term)
                            else:
                                domain_counts_by_domain_id = {}
                                for domain_id_count in domain_string:
                                    domain_id, domain_count = domain_id_count.split(":")
                                    domain_counts_by_domain_id[domain_id] = int(domain_count)
                                domain_counter = Counter(domain_counts_by_domain_id)
                                domain_counter_by_domain_source[domain_source] = domain_counter
                    proteinCollection.add_annotation_to_proteinObj(domain_protein_id, domain_counter_by_domain_source, go_terms)
            proteinCollection.functional_annotation_parsed = True
        return proteinCollection

    ###############################
    ### build_ProteinCollection : parse_species_ids
    ###############################

    def parse_species_ids(self, species_ids_f):
        fasta_by_ortho_id = {}
        for line in read_file(species_ids_f):
            idx, fasta = line.split(": ")
            fasta_by_ortho_id[idx] = fasta
        self.species_ids_file = species_ids_f
        return fasta_by_ortho_id

    ###############################
    ### build_ProteinCollection : parse_fasta_dir
    ###############################

    def parse_fasta_dir(self, fasta_dir, fasta_file_by_species_id):
        fasta_len_by_protein_id = {}
        for species_id, fasta_f in fasta_file_by_species_id.items():
            fasta_path = join(fasta_dir, fasta_f)
            if not isfile(fasta_path):
                sys.exit("[ERROR] - %s does not exist." % (fasta_path))
            print "[STATUS]\t - Parsing FASTA %s" % (fasta_path)
            for header, length in readFastaLen(fasta_path):
                fasta_len_by_protein_id[header] = length
        self.fasta_dir = fasta_dir
        return fasta_len_by_protein_id

    ###############################
    ### build_ClusterCollection
    ###############################

    def build_ClusterCollection(self, inputObj):
        cluster_f = inputObj.cluster_f
        print "[STATUS] - Parsing %s ... this may take a while" % (cluster_f)
        clusterObjs = []
        with open(cluster_f) as fh:
            for line in fh:
                temp = line.rstrip("\n").split(" ")
                cluster_id, protein_string = temp[0].replace(":", ""), temp[1:]
                clusterObj = ClusterObj(cluster_id, protein_string)
                for protein_id in protein_string:
                    proteinObj = proteinCollection.proteinObjs_by_protein_id[protein_id]
                    proteinObj.clustered = True
                clusterObjs.append(clusterObj)
        inferred_singletons_count = 0
        if inputObj.infer_singletons:
            print "[STATUS] - Inferring singletons ..."
            singleton_idx = 0
            for proteinObj in proteinCollection.proteinObjs:
                if proteinObj.clustered == False:
                    cluster_id = "singleton_%s" % singleton_idx
                    clusterObj = ClusterObj(cluster_id, [proteinObj.protein_id])
                    clusterObjs.append(clusterObj)
                    singleton_idx += 1
            inferred_singletons_count = singleton_idx
        return ClusterCollection(clusterObjs, inferred_singletons_count, proteinCollection.functional_annotation_parsed, proteinCollection.fastas_parsed, proteinCollection.domain_sources)

    ###############################
    ### write_output
    ###############################

    def write_output(self):
        self.plot_cluster_sizes()
        self.write_cluster_metrics()

    ###############################
    ### write_output : write_ALO_stats
    ###############################

    def plot_cluster_sizes(self):
        cluster_protein_count = []
        for clusterObj in clusterCollection.clusterObjs:
            cluster_protein_count.append(clusterObj.protein_count)
        cluster_protein_counter = Counter(cluster_protein_count)
        count_plot_f = join(self.dirs['main'], "cluster_sizes.%s" % (inputObj.plot_format))
        f, ax = plt.subplots(figsize=inputObj.plot_size)
        x_values = []
        y_values = []
        for value, count in cluster_protein_counter.items():
            x_values.append(value)
            y_values.append(count)
        x_array = np.array(x_values)
        y_array = np.array(y_values)
        #fit = powerlaw.Fit(np.array(cluster_protein_count)+1,xmin=1,discrete=True)
        #fit.power_law.plot_pdf(color= 'b',linestyle='--',label='fit ccdf')
        #fit.plot_pdf( color= 'b')
        ax.scatter(x_array, y_array, marker='o', alpha=0.8, s=100)
        ax.set_xlabel('Cluster size', fontsize=inputObj.plot_font_size)
        ax.set_ylabel('Count', fontsize=inputObj.plot_font_size)
        ax.set_yscale('log')
        ax.set_xscale('log')
        plt.margins(0.8)
        plt.gca().set_ylim(bottom=0.8)
        plt.gca().set_xlim(left=0.8)
        ax.xaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        f.tight_layout()
        ax.grid(True, linewidth=0.5, which="minor", color="lightgrey")
        ax.grid(True, linewidth=1, which="major", color="lightgrey")
        print "[STATUS] - Plotting %s" % (count_plot_f)
        f.savefig(count_plot_f, format=inputObj.plot_format)
        plt.close()

    def get_header_line(self, filetype, attribute):
        if filetype == "attribute_metrics":
            attribute_metrics_header = []
            attribute_metrics_header.append("#attribute")
            attribute_metrics_header.append("level")
            attribute_metrics_header.append("cluster_total_count")
            attribute_metrics_header.append("protein_total_count")
            attribute_metrics_header.append("protein_total_span")
            attribute_metrics_header.append("singleton_cluster_count")
            attribute_metrics_header.append("singleton_protein_count")
            attribute_metrics_header.append("singleton_protein_span")
            attribute_metrics_header.append("specific_cluster_count")
            attribute_metrics_header.append("specific_protein_count")
            attribute_metrics_header.append("specific_protein_span")
            attribute_metrics_header.append("shared_cluster_count")
            attribute_metrics_header.append("shared_protein_count")
            attribute_metrics_header.append("shared_protein_span")
            attribute_metrics_header.append("specific_cluster_true_1to1_count")
            attribute_metrics_header.append("specific_cluster_fuzzy_count")
            attribute_metrics_header.append("shared_cluster_true_1to1_count")
            attribute_metrics_header.append("shared_cluster_fuzzy_count")
            attribute_metrics_header.append("absent_cluster_total_count")
            attribute_metrics_header.append("absent_cluster_singleton_count")
            attribute_metrics_header.append("absent_cluster_specific_count")
            attribute_metrics_header.append("absent_cluster_shared_count")
            attribute_metrics_header.append("members_count")
            attribute_metrics_header.append("members")
            return "\t".join(attribute_metrics_header)
        elif filetype == "cluster_metrics_ALO":
            cluster_metrics_ALO_header = []
            cluster_metrics_ALO_header.append("#cluster_id")
            cluster_metrics_ALO_header.append("cluster_status")
            cluster_metrics_ALO_header.append("cluster_type")
            cluster_metrics_ALO_header.append("cluster_protein_count")
            cluster_metrics_ALO_header.append("cluster_proteome_count")
            cluster_metrics_ALO_header.append("ALO_protein_count")
            cluster_metrics_ALO_header.append("ALO_mean_count")
            cluster_metrics_ALO_header.append("non_ALO_mean_count")
            cluster_metrics_ALO_header.append("representation")
            cluster_metrics_ALO_header.append("log2_mean(ALO/others)")
            cluster_metrics_ALO_header.append("mwu_pvalue(ALO vs. others)")
            cluster_metrics_ALO_header.append("ALO_proteome_coverage")
            cluster_metrics_ALO_header.append("ALO_proteomes_present_count")
            cluster_metrics_ALO_header.append("ALO_proteomes_present")
            cluster_metrics_ALO_header.append("go_terms")
            for domain_source in clusterCollection.domain_sources:
                cluster_metrics_ALO_header.append(domain_source)
            return "\t".join(cluster_metrics_ALO_header)
        elif filetype == "cluster_metrics":
            cluster_metrics_header = []
            cluster_metrics_header.append("#cluster_id")
            cluster_metrics_header.append("cluster_protein_count")
            cluster_metrics_header.append("protein_median_count")
            cluster_metrics_header.append("proteome_count")
            cluster_metrics_header.append("attribute")
            cluster_metrics_header.append("attribute_cluster_type")
            cluster_metrics_header.append("protein_span_mean")
            cluster_metrics_header.append("protein_span_sd")
            cluster_metrics_header += ["%s_count" % level for level in aloCollection.ALO_by_level_by_attribute[attribute]]
            if not attribute == "PROTEOME":
                cluster_metrics_header += ["%s_median" % level for level in aloCollection.ALO_by_level_by_attribute[attribute]]
                cluster_metrics_header += ["%s_cov" % level for level in aloCollection.ALO_by_level_by_attribute[attribute]]
            return "\t".join(cluster_metrics_header)
        elif filetype == "cluster_metrics_domains":
            cluster_metrics_domains_header = []
            cluster_metrics_domains_header.append("#cluster_id")
            cluster_metrics_domains_header.append("cluster_protein_count")
            cluster_metrics_domains_header.append("proteome_count")
            cluster_metrics_domains_header.append("protein_span_mean")
            cluster_metrics_domains_header.append("protein_span_sd")
            cluster_metrics_domains_header.append("fraction_secreted")
            cluster_metrics_domains_header.append("go_terms")
            for domain_source in clusterCollection.domain_sources:
                cluster_metrics_domains_header.append(domain_source)
                cluster_metrics_domains_header.append("%s_entropy" % (domain_source))
            return "\t".join(cluster_metrics_domains_header)
        elif filetype == "cafe":
            cafe_header = []
            cafe_header.append("Description")
            cafe_header.append("ID")
            for level in aloCollection.ALO_by_level_by_attribute['PROTEOME']:
                cafe_header.append(level)
            return "\t".join(cafe_header)
        elif filetype == "pairwise_representation_test":
            pairwise_representation_test_header = []
            pairwise_representation_test_header.append("#cluster_id")
            pairwise_representation_test_header.append("level_1")
            pairwise_representation_test_header.append("level_1_mean")
            pairwise_representation_test_header.append("level_2")
            pairwise_representation_test_header.append("level_2_mean")
            pairwise_representation_test_header.append("log2_mean(level_1/level_2)")
            pairwise_representation_test_header.append("mwu_pvalue(level_1 vs. level2)")
            pairwise_representation_test_header.append("go_terms")
            for domain_source in clusterCollection.domain_sources:
                pairwise_representation_test_header.append(domain_source)
            return "\t".join(pairwise_representation_test_header)
        else:
            sys.exit("[ERROR] %s is not a valid header 'filetype'" % (filetype))

    def get_attribute_metrics(self, ALO):
        attribute_metrics = []
        attribute_metrics.append(ALO.attribute)
        attribute_metrics.append(ALO.level)
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_status_by_cluster_type('present', 'total'))
        attribute_metrics.append(ALO.get_protein_count_by_cluster_type('total'))
        attribute_metrics.append(ALO.get_protein_span_by_cluster_type('total'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_status_by_cluster_type('present', 'singleton'))
        attribute_metrics.append(ALO.get_protein_count_by_cluster_type('singleton'))
        attribute_metrics.append(ALO.get_protein_span_by_cluster_type('singleton'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_status_by_cluster_type('present', 'specific'))
        attribute_metrics.append(ALO.get_protein_count_by_cluster_type('specific'))
        attribute_metrics.append(ALO.get_protein_span_by_cluster_type('specific'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_status_by_cluster_type('present', 'shared'))
        attribute_metrics.append(ALO.get_protein_count_by_cluster_type('shared'))
        attribute_metrics.append(ALO.get_protein_span_by_cluster_type('shared'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_cardinality_by_cluster_type('specific', 'true'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_cardinality_by_cluster_type('specific', 'fuzzy'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_cardinality_by_cluster_type('shared', 'true'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_cardinality_by_cluster_type('shared', 'fuzzy'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_status_by_cluster_type('absent', 'total'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_status_by_cluster_type('absent', 'singleton'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_status_by_cluster_type('absent', 'specific'))
        attribute_metrics.append(ALO.get_cluster_count_by_cluster_status_by_cluster_type('absent', 'shared'))
        attribute_metrics.append(ALO.proteome_count)
        attribute_metrics.append(ALO.get_proteomes())
        return "\t".join([str(field) for field in attribute_metrics])

    def write_cluster_metrics(self):
        cafe_f = join(self.dirs['main'], "clusters.cafe.txt")
        cafe_output = []
        cafe_output.append(self.get_header_line('cafe', "PROTEOME"))

        cluster_metrics_domains_f = join(self.dirs['main'], "cluster_metrics_domains.txt")
        cluster_metrics_domains_output = []
        cluster_metrics_domains_output.append(self.get_header_line('cluster_metrics_domains', "PROTEOME"))

        for attribute in aloCollection.attributes:

            attribute_metrics_f = join(self.dirs[attribute], "%s.attribute_metrics.txt" % (attribute))
            attribute_metrics_output = []
            attribute_metrics_output.append(self.get_header_line('attribute_metrics', attribute))

            pairwise_representation_test_f = join(self.dirs[attribute], "%s.pairwise_representation_test.txt" % (attribute))
            pairwise_representation_test_output = []
            pairwise_representation_test_output.append(self.get_header_line('pairwise_representation_test', attribute))

            pairwise_representation_test_by_pair_by_attribute = {}

            ###########################
            # cluster_metrics
            ###########################

            cluster_metrics_f = join(self.dirs[attribute], "%s.cluster_metrics.txt" % (attribute))
            cluster_metrics_output = []
            cluster_metrics_output.append(self.get_header_line('cluster_metrics', attribute))

            levels = sorted([x for x in aloCollection.ALO_by_level_by_attribute[attribute]])
            levels_seen = set()

            for level in levels:
                ALO = aloCollection.ALO_by_level_by_attribute[attribute][level]

                ###########################
                # attribute_metrics
                ###########################

                attribute_metrics_output.append(self.get_attribute_metrics(ALO))

                ###########################
                # cluster_metrics_ALO : setup
                ###########################

                cluster_metrics_ALO_f = join(self.dirs[attribute], "%s.cluster_metrics_ALO.%s.txt" % (attribute, level))
                cluster_metrics_ALO_output = []
                cluster_metrics_ALO_output.append(self.get_header_line('cluster_metrics_ALO', attribute))
                background_representation_test_by_pair_by_attribute = {}

                for clusterObj in clusterCollection.clusterObjs:

                    ###########################
                    # cluster_metrics (only done once for each attribute)
                    ###########################

                    if not levels_seen:
                        cluster_metrics_line = []
                        cluster_metrics_line.append(clusterObj.cluster_id)
                        cluster_metrics_line.append(clusterObj.protein_count)
                        cluster_metrics_line.append(clusterObj.protein_median)
                        cluster_metrics_line.append(clusterObj.proteome_count)
                        cluster_metrics_line.append(attribute)
                        cluster_metrics_line.append(clusterObj.cluster_type_by_attribute[attribute])
                        if clusterCollection.fastas_parsed:
                            cluster_metrics_line.append(clusterObj.protein_length_stats['mean'])
                            cluster_metrics_line.append(clusterObj.protein_length_stats['sd'])
                        else:
                            cluster_metrics_line.append("N/A")
                            cluster_metrics_line.append("N/A")
                        for _level in levels:
                            cluster_metrics_line.append(sum(clusterObj.protein_counts_of_proteomes_by_level_by_attribute[attribute][_level]))
                        if not attribute == "PROTEOME":
                            for _level in levels:
                                cluster_metrics_line.append(median(clusterObj.protein_counts_of_proteomes_by_level_by_attribute[attribute][_level]))
                            for _level in levels:
                                cluster_metrics_line.append("{0:.2f}".format(clusterObj.proteome_coverage_by_level_by_attribute[attribute][_level]))
                        cluster_metrics_output.append("\t".join([str(field) for field in cluster_metrics_line]))

                    ###########################
                    # cafe (only done for attribute "PROTEOME")
                    ###########################

                    if not levels_seen and attribute == "PROTEOME":
                        cafe_line = []
                        cafe_line.append("None")
                        cafe_line.append(str(clusterObj.cluster_id))
                        for _level in levels:
                            cafe_line.append(sum(clusterObj.protein_counts_of_proteomes_by_level_by_attribute[attribute][_level]))
                        cafe_output.append("\t".join([str(field) for field in cafe_line]))

                    ###########################
                    # cluster_metrics_domains (only done for attribute "PROTEOME")
                    ###########################

                    if not levels_seen and attribute == "PROTEOME":
                        if clusterCollection.functional_annotation_parsed:
                            cluster_metrics_domains_line = []
                            cluster_metrics_domains_line.append(clusterObj.cluster_id)
                            cluster_metrics_domains_line.append(clusterObj.protein_count)
                            cluster_metrics_domains_line.append(clusterObj.proteome_count)
                            if clusterCollection.fastas_parsed:
                                cluster_metrics_domains_line.append(clusterObj.protein_length_stats['mean'])
                                cluster_metrics_domains_line.append(clusterObj.protein_length_stats['sd'])
                            else:
                                cluster_metrics_domains_line.append("N/A")
                                cluster_metrics_domains_line.append("N/A")
                            if "SignalP_EUK" in clusterCollection.domain_sources:
                                cluster_metrics_domains_line.append("{0:.2f}".format(clusterObj.secreted_cluster_coverage))
                            else:
                                cluster_metrics_domains_line.append("N/A")
                            if clusterObj.go_terms:
                                cluster_metrics_domains_line.append(";".join(sorted(list(clusterObj.go_terms))))
                            else:
                                cluster_metrics_domains_line.append("N/A")
                            for domain_source in clusterCollection.domain_sources:
                                if domain_source in clusterObj.domain_counter_by_domain_source:
                                    cluster_metrics_domains_line.append(";".join(["%s:%s" % (domain, count) for domain, count in clusterObj.domain_counter_by_domain_source[domain_source].most_common()]))
                                    cluster_metrics_domains_line.append("{0:.3f}".format(clusterObj.domain_entropy_by_domain_source[domain_source]))
                                else:
                                    cluster_metrics_domains_line.append("N/A")
                                    cluster_metrics_domains_line.append("N/A")
                            cluster_metrics_domains_output.append("\t".join([str(field) for field in cluster_metrics_domains_line]))

                    ###########################
                    # cluster_metrics_ALO : populate
                    ###########################

                    cluster_metrics_ALO_line = []
                    cluster_metrics_ALO_line.append(clusterObj.cluster_id)
                    cluster_metrics_ALO_line.append(ALO.cluster_status_by_cluster_id[clusterObj.cluster_id])
                    cluster_metrics_ALO_line.append(ALO.cluster_type_by_cluster_id[clusterObj.cluster_id])
                    cluster_metrics_ALO_line.append(clusterObj.protein_count)
                    cluster_metrics_ALO_line.append(clusterObj.proteome_count)
                    cluster_metrics_ALO_line.append(sum(clusterObj.protein_counts_of_proteomes_by_level_by_attribute[attribute][level]))
                    if ALO.cluster_mean_ALO_count_by_cluster_id[clusterObj.cluster_id]:
                        cluster_metrics_ALO_line.append(ALO.cluster_mean_ALO_count_by_cluster_id[clusterObj.cluster_id])
                    else:
                        cluster_metrics_ALO_line.append("N/A")
                    if ALO.cluster_mean_non_ALO_count_by_cluster_id[clusterObj.cluster_id]:
                        cluster_metrics_ALO_line.append(ALO.cluster_mean_non_ALO_count_by_cluster_id[clusterObj.cluster_id])
                    else:
                        cluster_metrics_ALO_line.append("N/A")
                    if ALO.cluster_type_by_cluster_id[clusterObj.cluster_id] == 'shared':
                        if ALO.cluster_mwu_log2_mean_by_cluster_id[clusterObj.cluster_id]:
                            background_pair = (level, "background")
                            if not attribute in background_representation_test_by_pair_by_attribute:
                                background_representation_test_by_pair_by_attribute[attribute] = {}
                            if not background_pair in background_representation_test_by_pair_by_attribute[attribute]:
                                background_representation_test_by_pair_by_attribute[attribute][background_pair] = []
                            background_representation_test = []
                            background_representation_test.append(clusterObj.cluster_id)
                            background_representation_test.append(level)
                            background_representation_test.append("background")
                            background_representation_test.append(ALO.cluster_mean_ALO_count_by_cluster_id[clusterObj.cluster_id])
                            background_representation_test.append(ALO.cluster_mean_non_ALO_count_by_cluster_id[clusterObj.cluster_id])
                            background_representation_test.append(ALO.cluster_mwu_log2_mean_by_cluster_id[clusterObj.cluster_id])
                            background_representation_test.append(ALO.cluster_mwu_pvalue_by_cluster_id[clusterObj.cluster_id])
                            background_representation_test_by_pair_by_attribute[attribute][background_pair].append(background_representation_test)

                            if ALO.cluster_mwu_log2_mean_by_cluster_id[clusterObj.cluster_id] > 0:
                                cluster_metrics_ALO_line.append("enriched")
                            elif ALO.cluster_mwu_log2_mean_by_cluster_id[clusterObj.cluster_id] < 0:
                                cluster_metrics_ALO_line.append("depleted")
                            else:
                                cluster_metrics_ALO_line.append("equal")
                            cluster_metrics_ALO_line.append(ALO.cluster_mwu_log2_mean_by_cluster_id[clusterObj.cluster_id])
                            cluster_metrics_ALO_line.append(ALO.cluster_mwu_pvalue_by_cluster_id[clusterObj.cluster_id])
                        else:
                            cluster_metrics_ALO_line.append("N/A")
                            cluster_metrics_ALO_line.append("N/A")
                            cluster_metrics_ALO_line.append("N/A")
                    else:
                        cluster_metrics_ALO_line.append("N/A")
                        cluster_metrics_ALO_line.append("N/A")
                        cluster_metrics_ALO_line.append("N/A")
                    cluster_metrics_ALO_line.append("{0:.2f}".format(clusterObj.proteome_coverage_by_level_by_attribute[attribute][level]))
                    ALO_proteomes_present = []
                    if ALO.cluster_status_by_cluster_id[clusterObj.cluster_id] == 'present':
                        ALO_proteomes_present = clusterObj.proteome_ids.intersection(ALO.proteomes)
                    cluster_metrics_ALO_line.append(len(ALO_proteomes_present))
                    if ALO_proteomes_present:
                        cluster_metrics_ALO_line.append(",".join(sorted(list(ALO_proteomes_present))))
                    else:
                        cluster_metrics_ALO_line.append("N/A")
                    if clusterObj.go_terms:
                        cluster_metrics_ALO_line.append(";".join(sorted(list(clusterObj.go_terms))))
                    else:
                        cluster_metrics_ALO_line.append("N/A")
                    for domain_source in clusterCollection.domain_sources:
                        if domain_source in clusterObj.domain_counter_by_domain_source:
                            cluster_metrics_ALO_line.append(";".join(["%s:%s" % (domain, count) for domain, count in clusterObj.domain_counter_by_domain_source[domain_source].most_common()]))
                        else:
                            cluster_metrics_ALO_line.append("N/A")
                    cluster_metrics_ALO_output.append("\t".join([str(field) for field in cluster_metrics_ALO_line]))

                    if len(levels) > 1 and len(ALO_proteomes_present) >= inputObj.min_proteomes:
                        for result in self.pairwise_representation_test(clusterObj, attribute, level, levels_seen, levels):
                            # [clusterObj.cluster_id, level, other_level, mean_level, mean_other_level, log2fc_mean, pvalue]
                            if not attribute in pairwise_representation_test_by_pair_by_attribute:
                                pairwise_representation_test_by_pair_by_attribute[attribute] = {}
                            pair = (result[1], result[2])
                            if not pair in pairwise_representation_test_by_pair_by_attribute[attribute]:
                                pairwise_representation_test_by_pair_by_attribute[attribute][pair] = []
                            pairwise_representation_test_by_pair_by_attribute[attribute][pair].append(result)

                            pairwise_representation_test_line = []
                            pairwise_representation_test_line.append(result[0])
                            pairwise_representation_test_line.append(result[1])
                            pairwise_representation_test_line.append(result[3])
                            pairwise_representation_test_line.append(result[2])
                            pairwise_representation_test_line.append(result[4])
                            pairwise_representation_test_line.append(result[5])
                            pairwise_representation_test_line.append(result[6])
                            if clusterObj.go_terms:
                                pairwise_representation_test_line.append(";".join(sorted(list(clusterObj.go_terms))))
                            else:
                                pairwise_representation_test_line.append("N/A")
                            for domain_source in clusterCollection.domain_sources:
                                if domain_source in clusterObj.domain_counter_by_domain_source:
                                    pairwise_representation_test_line.append(";".join(["%s:%s" % (domain, count) for domain, count in clusterObj.domain_counter_by_domain_source[domain_source].most_common()]))
                                else:
                                    pairwise_representation_test_line.append("N/A")
                            pairwise_representation_test_output.append("\t".join([str(field) for field in pairwise_representation_test_line]))

                levels_seen.add(level)
                # END of cluster loop

                if len(cafe_output) > 1:
                    with open(cafe_f, 'w') as cafe_fh:
                        print "[STATUS] - Writing %s" % (cafe_f)
                        cafe_fh.write("\n".join(cafe_output) + "\n")
                    cafe_output = []
                if len(cluster_metrics_output) > 1:
                    with open(cluster_metrics_f, 'w') as cluster_metrics_fh:
                        print "[STATUS] - Writing %s" % (cluster_metrics_f)
                        cluster_metrics_fh.write("\n".join(cluster_metrics_output) + "\n")
                    cluster_metrics_output = []
                if len(cluster_metrics_domains_output) > 1:
                    with open(cluster_metrics_domains_f, 'w') as cluster_metrics_domains_fh:
                        print "[STATUS] - Writing %s" % (cluster_metrics_domains_f)
                        cluster_metrics_domains_fh.write("\n".join(cluster_metrics_domains_output) + "\n")
                    cluster_metrics_domains_output = []
                if len(cluster_metrics_ALO_output) > 1:
                    with open(cluster_metrics_ALO_f, 'w') as cluster_metrics_ALO_fh:
                        print "[STATUS] - Writing %s" % (cluster_metrics_ALO_f)
                        cluster_metrics_ALO_fh.write("\n".join(cluster_metrics_ALO_output) + "\n")
                    cluster_metrics_ALO_output = []
                if background_representation_test_by_pair_by_attribute:
                    self.plot_count_comparisons_vulcano(background_representation_test_by_pair_by_attribute)


            if len(attribute_metrics_output) > 1:
                with open(attribute_metrics_f, 'w') as attribute_metrics_fh:
                    print "[STATUS] - Writing %s" % (attribute_metrics_f)
                    attribute_metrics_fh.write("\n".join(attribute_metrics_output) + "\n")
            if len(pairwise_representation_test_output) > 1:
                with open(pairwise_representation_test_f, 'w') as pairwise_representation_test_fh:
                    print "[STATUS] - Writing %s" % (pairwise_representation_test_f)
                    pairwise_representation_test_fh.write("\n".join(pairwise_representation_test_output) + "\n")
            if pairwise_representation_test_by_pair_by_attribute:
                self.plot_count_comparisons_vulcano(pairwise_representation_test_by_pair_by_attribute)

    def plot_count_comparisons_vulcano(self, pairwise_representation_test_by_pair_by_attribute):
        # [clusterObj.cluster_id, level, other_level, mean_level, mean_other_level, log2fc_mean, pvalue]
        for attribute in pairwise_representation_test_by_pair_by_attribute:
            for pair in pairwise_representation_test_by_pair_by_attribute[attribute]:
                pair_list = list(pair)
                x_label = pair_list[0]
                y_label = pair_list[1]
                pair_data = pairwise_representation_test_by_pair_by_attribute[attribute][pair]
                pair_data_count = len(pair_data)
                p_values = []
                log2fc_values = []
                for data in pair_data:
                    log2fc_values.append(data[5])
                    p_values.append(data[6])
                if p_values:
                    pairwise_representation_test_f = join(self.dirs[attribute], "%s.pairwise_representation_test.%s.%s" % (attribute, "_".join(pair_list), inputObj.plot_format))
                    f, ax = plt.subplots(figsize=inputObj.plot_size)
                    p_array = np.array(p_values)
                    log2fc_array = np.array(log2fc_values)
                    ax.scatter(log2fc_array, p_array, alpha=0.8, edgecolors='none',s=25 , c='grey')

                    ooFive = 0.05
                    ooOne = 0.01
                    ooFive_corrected = 0.05/pair_data_count
                    ooOne_corrected = 0.01/pair_data_count

                    ax.axhline(y=ooFive, linewidth=2, color='orange', linestyle="--")
                    ooFive_artist = plt.Line2D((0,1),(0,0), color='orange', linestyle='--')
                    ax.axhline(y=ooOne, linewidth=2, color='red', linestyle="--")
                    ooOne_artist = plt.Line2D((0,1),(0,0), color='red', linestyle='--')
                    ax.axhline(y=ooFive_corrected, linewidth=2, color='grey', linestyle="--")
                    ooFive_corrected_artist = plt.Line2D((0,1),(0,0), color='grey', linestyle='--')
                    ax.axhline(y=ooOne_corrected, linewidth=2, color='black', linestyle="--")
                    ooOne_corrected_artist = plt.Line2D((0,1),(0,0), color='black', linestyle='--')

                    #Create legend from custom artist/label lists
                    ax.legend([ooFive_artist, ooOne_artist, ooFive_corrected_artist, ooOne_corrected_artist], \
                        [ooFive, ooOne, "%s (0.05 corrected)" % '%.2E' % Decimal(ooFive_corrected), "%s (0.01 corrected)" % '%.2E' % Decimal(ooOne_corrected)], \
                        fontsize=inputObj.plot_font_size, frameon=True)
                    if abs(np.min(log2fc_array)) < abs(np.max(log2fc_array)):
                        x_min = 0.0-abs(np.max(log2fc_array))
                        x_max = 0.0+abs(np.max(log2fc_array))
                        ax.set_xlim(x_min-1, x_max+1)
                    else:
                        x_min = 0.0-abs(np.min(log2fc_array))
                        x_max = 0.0+abs(np.min(log2fc_array))
                        ax.set_xlim(x_min-1, x_max+1)
                    ax.grid(True, linewidth=0.5, which="minor", color="lightgrey")
                    ax.grid(True, linewidth=1, which="major", color="lightgrey")
                    ax.set_ylim(np.min(p_array)*0.1, 1.1)
                    ax.set_xlabel("log2(mean(%s)/mean(%s))" % (x_label, y_label), fontsize=inputObj.plot_font_size)
                    ax.set_ylabel("p-value", fontsize=inputObj.plot_font_size)
                    plt.gca().invert_yaxis()
                    ax.set_yscale('log')
                    print "[STATUS] - Plotting %s" % (pairwise_representation_test_f)
                    f.savefig(pairwise_representation_test_f, format=inputObj.plot_format)
                    plt.close()

    def pairwise_representation_test(self, clusterObj, attribute, level, levels_seen, levels):
        for other_level in set(levels).difference(levels_seen):
            if not other_level == level:
                other_ALO = aloCollection.ALO_by_level_by_attribute[attribute][other_level]
                if len(clusterObj.proteome_ids.intersection(other_ALO.proteomes)) >= 2:
                    protein_counts_level = [count for count in clusterObj.protein_counts_of_proteomes_by_level_by_attribute[attribute][level] if count > 0]
                    protein_counts_other_level = [count for count in clusterObj.protein_counts_of_proteomes_by_level_by_attribute[attribute][other_level] if count > 0]
                    if protein_counts_level and protein_counts_other_level:
                        pvalue = None
                        try:
                            pvalue = scipy.stats.mannwhitneyu(protein_counts_level, protein_counts_other_level, alternative="two-sided")[1]
                        except:
                            pvalue = 1.0
                        mean_level = mean(protein_counts_level)
                        mean_other_level = mean(protein_counts_other_level)
                        log2fc_mean = log((mean_level/mean_other_level), 2)
                        yield [clusterObj.cluster_id, level, other_level, mean_level, mean_other_level, log2fc_mean, pvalue]

########################################################################
# CLASS : AloCollection
########################################################################

class AloCollection():
    def __init__(self, proteomes, proteome_id_by_species_id, attributes, level_by_attribute_by_proteome_id, tree_ete, node_idx_by_proteome_ids):
        self.attributes_verbose = attributes
        self.attributes = [attribute for attribute in attributes if attribute not in inputObj.ATTRIBUTE_RESERVED] # list of attributes
        self.proteome_id_by_species_id = proteome_id_by_species_id
        self.tree_ete = tree_ete

        self.node_idx_by_proteome_ids = node_idx_by_proteome_ids
        self.level_by_attribute_by_proteome_id = level_by_attribute_by_proteome_id
        self.proteome_ids_by_level_by_attribute = self.compute_proteomes_by_level_by_attribute()

        self.counts_of_all_proteome_subsets = {}
        self.cluster_ids_of_all_proteome_subsets = {}

        self.ALO_by_level_by_attribute = self.create_ALOs()

        self.fastas_parsed = False
        self.rarefaction_by_samplesize_by_level_by_attribute = {}

    ###############################
    ### create_ALOs
    ###############################

    def create_ALOs(self):
        ALO_by_level_by_attribute = {attribute: {} for attribute in self.attributes}
        for attribute in self.proteome_ids_by_level_by_attribute:
            for level in self.proteome_ids_by_level_by_attribute[attribute]:
                proteome_ids = self.proteome_ids_by_level_by_attribute[attribute][level]
                ALO = AttributeLevelObj(attribute, level, proteome_ids)
                if not level in ALO_by_level_by_attribute[attribute]:
                    ALO_by_level_by_attribute[attribute][level] = {}
                ALO_by_level_by_attribute[attribute][level] = ALO
        return ALO_by_level_by_attribute

    ###############################
    ### compute_proteomes_by_level_by_attribute
    ###############################

    def compute_proteomes_by_level_by_attribute(self):
        proteomes_by_level_by_attribute = {attribute : {} for attribute in self.attributes}
        for proteome_id in self.level_by_attribute_by_proteome_id:
            for attribute in self.attributes:
                level = self.level_by_attribute_by_proteome_id[proteome_id][attribute]
                if not level in proteomes_by_level_by_attribute[attribute]:
                    proteomes_by_level_by_attribute[attribute][level] = set()
                proteomes_by_level_by_attribute[attribute][level].add(proteome_id)
        return proteomes_by_level_by_attribute
    ###############################
    ### compute_levels_by_attribute
    ###############################

    def compute_levels_by_attribute(self):
        levels_by_attribute = {attribute : set() for attribute in self.attributes}
        for proteome in self.level_by_attribute_by_proteome_id:
            for attribute in self.attributes:
                level = self.level_by_attribute_by_proteome_id[proteome][attribute]
                levels_by_attribute[attribute].add(level)
        return levels_by_attribute

    def analyse_domains(self):
        if proteinCollection.functional_annotation_parsed:
            for attribute in self.ALO_by_level_by_attribute:
                for level in self.ALO_by_level_by_attribute[attribute]:
                    ALO = self.ALO_by_level_by_attribute[attribute][level]
                    ALO.analyse_domains()
    ###############################
    ### analyse_clusters
    ###############################

    def analyse_clusters(self):
        if clusterCollection.inferred_singletons_count:
            print "[STATUS]\t - Clusters found = %s (of which %s were inferred singletons)" % (clusterCollection.cluster_count, clusterCollection.inferred_singletons_count)
        else:
            print "[STATUS]\t - Clusters found = %s" % (clusterCollection.cluster_count)
        parse_steps = clusterCollection.cluster_count/100
        print "[STATUS] - Analysing clusters ..."
        analyse_clusters_start = time.time()
        for idx, clusterObj in enumerate(clusterCollection.clusterObjs):
            self.analyse_cluster(clusterObj)
            progress(idx+1, parse_steps, clusterCollection.cluster_count)
        analyse_clusters_end = time.time()
        analyse_clusters_elapsed = analyse_clusters_end - analyse_clusters_start
        print "[STATUS] - Took %ss to analyse clusters" % (analyse_clusters_elapsed)

 ###############################
    ### analyse_clusters : analyse_cluster
    ###############################

    def analyse_cluster(self, clusterObj):
        '''This function selects the ALOs to which the cluster has to be added'''
        # avoiding dots
        protein_get_by_proteome_id = clusterObj.protein_ids_by_proteome_id.get

        implicit_protein_ids_by_proteome_id_by_level_by_attribute = {}
        cluster_type_by_attribute = {}
        protein_counts_of_proteomes_by_level_by_attribute = {}
        proteome_coverage_by_level_by_attribute = {}
        if self.tree_ete:
            proteomes_to_index = {node.proteome_ids : node.idx for node in self.tree_ete.traverse("levelorder")}
            counts_by_proteome_subset_by_node_name = {}
            for node in self.tree_ete.traverse("levelorder"):
                proteome_ids = node.proteome_ids
                intersection = clusterObj.proteome_ids.intersection(proteome_ids)
                difference = clusterObj.proteome_ids.difference(proteome_ids)
                if len(intersection) == 0:
                    node.counts['absent'] +=1
                    #print clusterObj.cluster_id, ":", clusterObj.proteome_ids, "absent", proteome_ids
                else:
                    if clusterObj.singleton == True:
                        node.counts['singleton'] +=1
                        #print clusterObj.cluster_id, ":", clusterObj.proteome_ids, "singleton", proteome_ids
                    elif len(difference) > 0:
                        node.counts['shared'] +=1
                        #print clusterObj.cluster_id, ":", clusterObj.proteome_ids, "shared", proteome_ids
                    elif len(difference) == 0:
                        node.counts['specific'] +=1
                        #print clusterObj.cluster_id, ":", clusterObj.proteome_ids, "specific", proteome_ids
                    else:
                        sys.exit("[ERROR] Something unexpected happened...")

        if not clusterObj.singleton:
            #if not clusterObj.proteome_ids in self.counts_of_all_proteome_subsets:
            #    self.counts_of_all_proteome_subsets[clusterObj.proteome_ids] = 0
            #self.counts_of_all_proteome_subsets[clusterObj.proteome_ids] += 1
            if not clusterObj.proteome_ids in self.cluster_ids_of_all_proteome_subsets:
                self.cluster_ids_of_all_proteome_subsets[clusterObj.proteome_ids] = []
            self.cluster_ids_of_all_proteome_subsets[clusterObj.proteome_ids].append(clusterObj.cluster_id)

        for attribute in self.attributes:
            protein_counts_of_proteomes_by_level_by_attribute[attribute] = {}
            proteome_coverage_by_level_by_attribute[attribute] = {}
            implicit_protein_ids_by_proteome_id_by_level_by_attribute[attribute] = {}
            protein_ids_by_level = {}
            protein_length_stats_by_level = {}
            explicit_protein_count_by_proteome_id_by_level = {}

            for level in self.ALO_by_level_by_attribute[attribute]:
                protein_ids_by_proteome_id = {}
                protein_count_by_proteome_id = {}
                protein_ids_by_level[level] = []
                for proteome_id in self.ALO_by_level_by_attribute[attribute][level].proteomes_list:
                    protein_ids = protein_get_by_proteome_id(proteome_id, [])
                    protein_ids_by_level[level] += protein_ids
                    protein_count_by_proteome_id[proteome_id] = len(protein_ids)
                    if not protein_count_by_proteome_id[proteome_id] == 0:
                        protein_ids_by_proteome_id[proteome_id] = protein_ids
                if protein_ids_by_proteome_id:
                    implicit_protein_ids_by_proteome_id_by_level_by_attribute[attribute][level] = protein_ids_by_proteome_id
                explicit_protein_count_by_proteome_id_by_level[level] = protein_count_by_proteome_id
                protein_length_stats_by_level[level] = proteinCollection.get_protein_length_stats(protein_ids_by_level[level])
                protein_counts_of_proteomes_by_level_by_attribute[attribute][level] = [protein_count for proteome_id, protein_count in protein_count_by_proteome_id.items()]
            cluster_type_by_attribute[attribute] = get_attribute_cluster_type(clusterObj.singleton, implicit_protein_ids_by_proteome_id_by_level_by_attribute[attribute])

            for level in self.ALO_by_level_by_attribute[attribute]:
                ALO = self.ALO_by_level_by_attribute[attribute][level]
                proteome_coverage_by_level_by_attribute[attribute][level] = len(implicit_protein_ids_by_proteome_id_by_level_by_attribute[attribute].get(level, []))/ALO.proteome_count
                ALO_cluster_status = None
                ALO_cluster_cardinality = None
                mwu_pvalue = None
                mwu_log2_mean = None
                mean_ALO_count = None
                mean_non_ALO_count = None
                if not level in implicit_protein_ids_by_proteome_id_by_level_by_attribute[attribute]:
                    ALO_cluster_status = 'absent'
                else:
                    ALO_cluster_status = 'present'
                    if not cluster_type_by_attribute[attribute] == 'singleton':
                        ALO_proteome_counts_in_cluster = [count for proteome_id, count in explicit_protein_count_by_proteome_id_by_level[level].items()]
                        ALO_cluster_cardinality = get_ALO_cluster_cardinality(ALO_proteome_counts_in_cluster)
                        if cluster_type_by_attribute[attribute] == 'shared':
                            non_ALO_levels = [non_ALO_level for non_ALO_level in explicit_protein_count_by_proteome_id_by_level if not non_ALO_level == level]
                            non_ALO_proteome_counts_in_cluster = []
                            for non_ALO_level in non_ALO_levels:
                                for proteome_id in explicit_protein_count_by_proteome_id_by_level[non_ALO_level]:
                                    non_ALO_proteome_counts_in_cluster.append(explicit_protein_count_by_proteome_id_by_level[non_ALO_level][proteome_id])
                            mwu_pvalue, mwu_log2_mean, mean_ALO_count, mean_non_ALO_count = mannwhitneyu(ALO_proteome_counts_in_cluster, non_ALO_proteome_counts_in_cluster)

                ALO.add_clusterObj(\
                    clusterObj, \
                    cluster_type_by_attribute[attribute], \
                    ALO_cluster_status, \
                    ALO_cluster_cardinality, \
                    protein_ids_by_level[level], \
                    protein_length_stats_by_level[level], \
                    mwu_pvalue, \
                    mwu_log2_mean, \
                    mean_ALO_count, \
                    mean_non_ALO_count \
                    )
        clusterObj.protein_counts_of_proteomes_by_level_by_attribute = protein_counts_of_proteomes_by_level_by_attribute
        clusterObj.protein_median = median([count for count in protein_counts_of_proteomes_by_level_by_attribute['global']['True'] if not count == 0])
        clusterObj.proteome_coverage_by_level_by_attribute = proteome_coverage_by_level_by_attribute
        clusterObj.implicit_protein_ids_by_proteome_id_by_level_by_attribute = implicit_protein_ids_by_proteome_id_by_level_by_attribute
        clusterObj.cluster_type_by_attribute = cluster_type_by_attribute

    def analyse_tree(self):

        if self.tree_ete:
            print "[STATUS] - Preparing data for tree ... "
            proteome_ids_by_node_id = {node.proteome_ids : node.idx for node in self.tree_ete.traverse("levelorder")}
            cluster_ids_by_proteome_ids_by_node_name = {}
            synapomorphic_clusters_by_node_id = {}
            for node in self.tree_ete.traverse("levelorder"):
                print "# ",node.name
                proteome_ids = node.proteome_ids
                print "\tcontains :", proteome_ids
                if not node.is_leaf():
                    children_proteome_ids = [child_node.proteome_ids for child_node in node.get_children()]
                    child_nodes_covered = []
                    print "\tchildren : ", children_proteome_ids
                    for proteome_set, cluster_ids in self.cluster_ids_of_all_proteome_subsets.items():
                        print proteome_set, len(cluster_ids)
                        if len(proteome_set) > 1:
                            if not proteome_ids.isdisjoint(proteome_set):
                                for child_proteome_ids in children_proteome_ids:
                                    if child_proteome_ids.isdisjoint(proteome_set):
                                        child_nodes_covered.append(False)
                                    else:
                                        child_nodes_covered.append(True)
                                print child_nodes_covered
                                if all(child_nodes_covered):
                                    print "### COVERED ###"




                           #    for child_proteome_ids in children_proteome_ids:

                           #if not proteome_subset.difference(proteome_ids):
                           #    overlapping_children = 0
                           #    for child_proteome_ids in children_proteome_ids:
                           #        if child_proteome_ids.intersection(proteome_subset):
                           #            overlapping_children += 1
                           #    if overlapping_children >1:
                           #        subsets_of_proteome_ids.append(proteome_subset)


                    #subsets_of_proteome_ids = self.generate_subsets_to_query_for_node(proteome_ids, children_nodes)
                    #print "\t SUBSETS : ", subsets_of_proteome_ids
                    #for subset_of_proteome_ids in subsets_of_proteome_ids:
                    #    counts_by_proteome_subset_by_node_name[node.name][subset_of_proteome_ids] = self.counts_of_all_proteome_subsets.get(subset_of_proteome_ids, 0)
                #counts_by_cluster_type_by_node_name[node.name] = node.counts
            #node_label_by_proteome_subset = self.generate_node_labels(counts_by_proteome_subset_by_node_name)
            sys.exit("STOP")
            #node_stats_by_node_id = self.generate_counts(counts_by_cluster_type_by_node_name, counts_by_proteome_subset_by_node_name, node_label_by_proteome_subset)
            node_stats_by_node_id = self.generate_counts(counts_by_proteome_subset_by_node_name, node_label_by_proteome_subset)
            header_f_by_node_name = self.generate_header_for_node(node_stats_by_node_id)
            charts_f_by_node_name = self.generate_chart_for_node(node_stats_by_node_id)
            if inputObj.render_tree:
                self.plot_tree(header_f_by_node_name, charts_f_by_node_name)
        #if self.tree_ete:
        #    print "[STATUS] - Preparing data for tree ... "
        #    #proteomes_to_index = {node.proteome_ids : node.idx for node in self.tree_ete.traverse("levelorder")}
        #    proteome_ids_by_node_id = {node.proteome_ids : node.idx for node in self.tree_ete.traverse("levelorder")}
        #    counts_by_proteome_subset_by_node_name = {}
        #    #counts_by_cluster_type_by_node_name = {}
        #    for node in self.tree_ete.traverse("levelorder"):
        #        print "# ",node.name
        #        if not node.name in counts_by_proteome_subset_by_node_name:
        #            "[seen first time]"
        #            counts_by_proteome_subset_by_node_name[node.name] = {}
        #        proteome_ids = node.proteome_ids
        #        print "\tcontains :", proteome_ids
        #        if not node.is_leaf():
        #            print "\t [not a leaf]"
        #            children_nodes = node.get_children()
        #            print "\t CHILDREN : ", children_nodes
        #            subsets_of_proteome_ids = self.generate_subsets_to_query_for_node(proteome_ids, children_nodes)
        #            print "\t SUBSETS : ", subsets_of_proteome_ids
        #            for subset_of_proteome_ids in subsets_of_proteome_ids:
        #                counts_by_proteome_subset_by_node_name[node.name][subset_of_proteome_ids] = self.counts_of_all_proteome_subsets.get(subset_of_proteome_ids, 0)
        #        #counts_by_cluster_type_by_node_name[node.name] = node.counts
        #    node_label_by_proteome_subset = self.generate_node_labels(counts_by_proteome_subset_by_node_name)
        #    sys.exit("STOP")
        #    #node_stats_by_node_id = self.generate_counts(counts_by_cluster_type_by_node_name, counts_by_proteome_subset_by_node_name, node_label_by_proteome_subset)
        #    node_stats_by_node_id = self.generate_counts(counts_by_proteome_subset_by_node_name, node_label_by_proteome_subset)
        #    header_f_by_node_name = self.generate_header_for_node(node_stats_by_node_id)
        #    charts_f_by_node_name = self.generate_chart_for_node(node_stats_by_node_id)
        #    if inputObj.render_tree:
        #        self.plot_tree(header_f_by_node_name, charts_f_by_node_name)

    def plot_tree(self, header_f_by_node_name, charts_f_by_node_name):
        tree_f = join(dataFactory.dirs['tree'], "tree.%s" % ('pdf')) # must be PDF! (otherwise it breaks)
        style = ete3.NodeStyle()
        style["vt_line_width"] = 5
        style["hz_line_width"] = 5
        style["fgcolor"] = "darkgrey"
        for node in self.tree_ete.traverse("levelorder"):
            node.set_style(style)
            node_header_face = ete3.faces.ImgFace(header_f_by_node_name[node.name]) # must be PNG! (ETE can't do PDF Faces)
            node.add_face(node_header_face, column=0, position="branch-top")
            if node.name in charts_f_by_node_name:
                node_chart_face = ete3.faces.ImgFace(charts_f_by_node_name[node.name]) # must be PNG! (ETE can't do PDF Faces)
                node.add_face(node_chart_face, column=0, position="branch-bottom")
            node_name_face = ete3.TextFace(node.name, fsize=64)
            node.img_style["size"] = 10
            node.img_style["shape"] = "sphere"
            node.img_style["fgcolor"] = "black"
            if not node.is_leaf():
                node.add_face(node_name_face, column=0, position="branch-right")
            node.add_face(node_name_face, column=0, position="aligned")
        ts = ete3.TreeStyle()
        ts.draw_guiding_lines=True
        ts.show_scale=False
        ts.show_leaf_name=False
        ts.allow_face_overlap=True
        ts.guiding_lines_color="lightgrey"
        print "[STATUS] - Writing tree %s ... " % (tree_f)
        self.tree_ete.render(tree_f, dpi=600, h=1189, units="mm", tree_style = ts)

    def generate_node_labels(self, counts_by_proteome_subset_by_node_name):
        node_label_by_proteome_subset = {}
        for node_name in counts_by_proteome_subset_by_node_name:
            #print node_name
            for proteome_subset in counts_by_proteome_subset_by_node_name[node_name]:
                #print "\t", proteome_subset
                for proteome_ids, node_label in sorted(self.node_idx_by_proteome_ids.items(), key=lambda x: x[1]):
                    #print "\t", proteome_ids, node_label
                    if proteome_ids.issubset(proteome_subset):
                        if len(proteome_ids) >= 2:
                            if not proteome_subset in node_label_by_proteome_subset:
                                node_label_by_proteome_subset[proteome_subset] = list(proteome_subset.difference(proteome_ids))
                                node_label_by_proteome_subset[proteome_subset].append("n"+str(node_label))
                        else:
                            if not proteome_subset in node_label_by_proteome_subset:
                                node_label_by_proteome_subset[proteome_subset] = list(proteome_subset)
        return node_label_by_proteome_subset

    def generate_header_for_node(self, node_stats_by_node_id):
        node_header_f_by_node_name = {}
        print "[STATUS] - Generating headers for nodes in tree ... "
        left, width = .25, .5
        bottom, height = .25, .5
        right = left + width
        top = bottom + height
        for node_name in node_stats_by_node_id:
            data = []
            data.append(("Apomorphies (size=1)", "{:,}".format(node_stats_by_node_id[node_name]['apomorphies_singletons'])))
            data.append(("Apomorphies (size>1)", "{:,}".format(node_stats_by_node_id[node_name]['apomorphies_non_singletons'])))
            data.append(("Synapomorphies (all)", "{:,}".format(node_stats_by_node_id[node_name]['synapomorphies_all'])))
            data.append(("Synapomorphies (cov=100%)", "{:,}".format(node_stats_by_node_id[node_name]['synapomorphies_present_in_all'])))
            data.append(("Synapomorphies (cov<100%)", "{:,}".format(node_stats_by_node_id[node_name]['synapomorphies_with_stochastic_absence'])))

            node_header_f = join(dataFactory.dirs['tree_headers'], "node_%s.header.pdf" % (node_name))
            col_labels = ('Type','Count')
            nrows, ncols = len(data)-1, len(col_labels)
            hcell, wcell = 0.3, 1.
            hpad, wpad = 0, 0
            fig, ax = plt.subplots(figsize=(2, 0.5))
            table= ax.table(cellText=data,
                    colLabels=col_labels,
                    #loc='bottom',fontsize=64, colLoc='center',rowLoc='right', edges='')
                    loc='bottom',fontsize=24, colLoc='center',rowLoc='right', edges='')
            #table.set_fontsize(48)
            table.set_fontsize(24)
            #table.scale(ncols, nrows)
            table.scale(2, 1)
            for key, cell in table.get_celld().items():
                row, col = key
                cell._text.set_color('grey')
                if row > 0:
                    cell.set_edgecolor("darkgrey")
                    cell.visible_edges = "T"
                else:
                    cell.set_edgecolor("darkgrey")
                    cell.visible_edges = "B"
                if row == len(data)-2:
                    cell.set_edgecolor("darkgrey")
                    cell.visible_edges = "T"
            #fig.suptitle('n%s' % node_name, color="darkgrey")
            ax.axis('tight')
            ax.axis("off")
            #fig.savefig(node_header_f, bbox_inches='tight', format=inputObj.plot_format)
            print "[STATUS]\t- Plotting %s" % (node_header_f)
            fig.savefig(node_header_f, pad=0, bbox_inches='tight', format='png')
            plt.close()
            node_header_f_by_node_name[node_name] = node_header_f
        return node_header_f_by_node_name

    #def generate_counts(self, counts_by_cluster_type_by_node_name, counts_by_proteome_subset_by_node_name, node_label_by_proteome_subset):
    def generate_counts(self, counts_by_proteome_subset_by_node_name, node_label_by_proteome_subset):
        node_stats_by_node_id = {}
        node_stats_f = join(dataFactory.dirs['tree'], "tree.node_stats.txt")
        node_stats = []
        node_stats.append("\t".join([\
            'nodeID', \
            'taxon_specific_apomorphies (singletons)', \
            'taxon_specific_apomorphies (non-singletons)', \
            'node_specific_synapomorphies', \
            'node_specific_synapomorphies (all taxa)', \
            'node_specific_synapomorphies (stochastic absence)', \
            'proteome_count' \
            ]))

        node_clusters_f = join(dataFactory.dirs['tree'], "tree.node_clusters.txt")
        node_clusters = []
        node_clusters.append("\t".join([ \
            'clusterID', \
            'nodeID', \
            'synapomorphy', \
            "fraction", \
            "children", \
            "proteomes_present" \
            ]))

        print self.tree_ete.get_ascii(attributes=["name"], show_internal=True)
        for node_name in counts_by_proteome_subset_by_node_name:
            proteome_ids_by_label = {}
            label = ''
            if str(node_name).isdigit():
                label = "n%s" % (node_name)
            else:
                label = "%s" % (node_name)

            apomorphies_non_singletons = sum([leaf.counts['specific'] for leaf in self.tree_ete.search_nodes(name=node_name)[0]])
            apomorphies_singletons = sum([leaf.counts['singleton'] for leaf in self.tree_ete.search_nodes(name=node_name)[0]])
            node_proteome_count = len(self.tree_ete.search_nodes(name=node_name)[0].get_leaves())
            node_proteomes_by_child_node = {}
            for child_node in self.tree_ete.search_nodes(name=node_name)[0].children:
                node_proteomes_by_child_node[child_node] = set([leaf.name for leaf in child_node])
            synapomorphies_present_in_all = 0
            synapomorphies_with_stochastic_absence = 0
            synapomorphies_coverage = []
            for proteome_subset, count in sorted(counts_by_proteome_subset_by_node_name[node_name].items(), key=lambda x: x[1], reverse=True):
                if count:
                    proteome_ids_by_label[label] = "+".join(sorted(list(node_label_by_proteome_subset[proteome_subset])))
                    child_node_proteome_count_present = []
                    child_node_proteome_count_total = []
                    child_node_proteome_count_string = []
                    for child_node in node_proteomes_by_child_node:
                        count_present = len(proteome_subset.intersection(node_proteomes_by_child_node[child_node]))
                        count_total = len(node_proteomes_by_child_node[child_node])
                        child_node_proteome_count_present.append(count_present)
                        child_node_proteome_count_total.append(count_total)
                        if str(child_node.name).isdigit():
                            child_node_proteome_count_string.append("n%s=(%s/%s)" % (child_node.name, count_present, count_total))
                        else:
                            child_node_proteome_count_string.append("%s=(%s/%s)" % (child_node.name, count_present, count_total))
                    child_node_proteome_fraction = sum(child_node_proteome_count_present)/sum(child_node_proteome_count_total)
                    synapomorphies_coverage.append(child_node_proteome_fraction)

                    if label == proteome_ids_by_label[label]:
                        # synapomorphy-all
                        synapomorphies_present_in_all = count
                        for cluster_id in self.cluster_ids_of_all_proteome_subsets.get(proteome_subset, []):
                            node_clusters.append("\t".join([ \
                                cluster_id, \
                                label, \
                                'synapomorphy-all', \
                                '{0:.3}'.format(child_node_proteome_fraction), \
                                ";".join(child_node_proteome_count_string), \
                                ",".join(list(sorted(proteome_subset))) \
                                ]))
                    else:
                        # synapomorphy-stochastic
                        synapomorphies_with_stochastic_absence += count
                        for cluster_id in self.cluster_ids_of_all_proteome_subsets.get(proteome_subset, []):
                            node_clusters.append("\t".join([ \
                                cluster_id, \
                                label, \
                                'synapomorphy-stochastic-absent', \
                                '{0:.3}'.format(child_node_proteome_fraction), \
                                ";".join(child_node_proteome_count_string), \
                                ",".join(list(sorted(proteome_subset))) \
                                ]))
            node_stats_by_node_id[node_name] = {}
            node_stats_by_node_id[node_name]['apomorphies_singletons'] = apomorphies_singletons
            node_stats_by_node_id[node_name]['apomorphies_non_singletons'] = apomorphies_non_singletons
            node_stats_by_node_id[node_name]['synapomorphies_all'] = synapomorphies_present_in_all + synapomorphies_with_stochastic_absence
            node_stats_by_node_id[node_name]['synapomorphies_present_in_all'] = synapomorphies_present_in_all
            node_stats_by_node_id[node_name]['synapomorphies_with_stochastic_absence'] = synapomorphies_with_stochastic_absence
            node_stats_by_node_id[node_name]['synapomorphies_coverage'] = synapomorphies_coverage

            node_stats_line = []
            node_stats_line.append(label)
            node_stats_line.append(str(apomorphies_singletons))
            node_stats_line.append(str(apomorphies_non_singletons))
            node_stats_line.append(str(synapomorphies_present_in_all + synapomorphies_with_stochastic_absence))
            node_stats_line.append(str(synapomorphies_present_in_all))
            node_stats_line.append(str(synapomorphies_with_stochastic_absence))
            node_stats_line.append(str(node_proteome_count))
            node_stats.append("\t".join(node_stats_line))
        print "[STATUS] - Writing %s ... " % node_stats_f
        with open(node_stats_f, 'w') as node_stats_fh:
            node_stats_fh.write("\n".join(node_stats) + "\n")
        print "[STATUS] - Writing %s ... " % node_clusters_f
        with open(node_clusters_f, 'w') as node_clusters_fh:
            node_clusters_fh.write("\n".join(node_clusters) + "\n")
        return node_stats_by_node_id

    def generate_chart_for_node(self, node_stats_by_node_id):
        node_chart_f_by_node_name = {}
        print "[STATUS] - Generating charts for nodes in tree ... "
        for node_name in node_stats_by_node_id:
            values = sorted(node_stats_by_node_id[node_name]['synapomorphies_coverage'])
            if values:
                chart_f = join(dataFactory.dirs['tree_charts'], "node_%s.barchart.pdf" % (node_name))
                f, ax = plt.subplots(figsize=(3.0, 3.0))
                x_values = np.array(values)
                ax.hist(x_values, histtype='stepfilled', align='mid', bins=np.arange(0.0, 1.0 + 0.1, 0.1))
                ax.set_xlim(-0.1, 1.1)
                for tick in ax.xaxis.get_major_ticks():
                    tick.label.set_fontsize(inputObj.plot_font_size-2)
                    tick.label.set_rotation('vertical')
                for tick in ax.yaxis.get_major_ticks():
                    tick.label.set_fontsize(inputObj.plot_font_size-2)
                ax.set_frame_on(False)
                ax.xaxis.grid(True, linewidth=1, which="major", color="lightgrey")
                ax.yaxis.grid(True, linewidth=1, which="major", color="lightgrey")
                f.suptitle("Synapomorphies", y=1.1)
                ax.set_ylabel("Count", fontsize=inputObj.plot_font_size)
                ax.set_xlabel("Proteome coverage", fontsize=inputObj.plot_font_size)
                print "[STATUS]\t- Plotting %s" % (chart_f)
                f.savefig(chart_f,  bbox_inches='tight', format='png')
                plt.close()
                node_chart_f_by_node_name[node_name] = chart_f
        return node_chart_f_by_node_name

    #def generate_subsets_to_query_for_node(self, proteome_ids, children_nodes):
    #    subsets_of_proteome_ids = []
    #    subsets_of_proteome_ids.append(proteome_ids)
    #    children_proteome_ids = [child_node.proteome_ids for child_node in children_nodes]
    #    for proteome_subset, count in sorted(self.counts_of_all_proteome_subsets.items(), key=lambda x: x[1], reverse=True):
    #        if len(proteome_subset) > 1:
    #            if not proteome_subset.difference(proteome_ids):
    #                overlapping_children = 0
    #                for child_proteome_ids in children_proteome_ids:
    #                    if child_proteome_ids.intersection(proteome_subset):
    #                        overlapping_children += 1
    #                if overlapping_children >1:
    #                    subsets_of_proteome_ids.append(proteome_subset)
    #    return subsets_of_proteome_ids

    def compute_rarefaction_data(self):
        rarefaction_by_samplesize_by_level_by_attribute = {}
        print "[STATUS] - Generating rarefaction data ..."
        for attribute in self.attributes:
            for level in self.proteome_ids_by_level_by_attribute[attribute]:
                proteome_ids = self.proteome_ids_by_level_by_attribute[attribute][level]
                if not len(proteome_ids) == 1:
                    ALO = self.ALO_by_level_by_attribute[attribute][level]
                    if not attribute in rarefaction_by_samplesize_by_level_by_attribute:
                        rarefaction_by_samplesize_by_level_by_attribute[attribute] = {}
                    if not level in rarefaction_by_samplesize_by_level_by_attribute[attribute]:
                        rarefaction_by_samplesize_by_level_by_attribute[attribute][level] = {}
                    for repetition in xrange(0, inputObj.repetitions):
                        seen_cluster_ids = set()
                        random_list_of_proteome_ids = [x for x in ALO.proteomes]
                        random.shuffle(random_list_of_proteome_ids)
                        for idx, proteome_id in enumerate(random_list_of_proteome_ids):
                            proteome_ALO = self.ALO_by_level_by_attribute['PROTEOME'][proteome_id]
                            seen_cluster_ids.update(proteome_ALO.cluster_ids_by_cluster_type_by_cluster_status['present']['specific'])
                            seen_cluster_ids.update(proteome_ALO.cluster_ids_by_cluster_type_by_cluster_status['present']['shared'])
                            sample_size = idx + 1
                            if not sample_size in rarefaction_by_samplesize_by_level_by_attribute[attribute][level]:
                                rarefaction_by_samplesize_by_level_by_attribute[attribute][level][sample_size] = []
                            rarefaction_by_samplesize_by_level_by_attribute[attribute][level][sample_size].append(len(seen_cluster_ids))

        for attribute in rarefaction_by_samplesize_by_level_by_attribute:
            rarefaction_plot_f = join(dataFactory.dirs[attribute], "%s.rarefaction.%s" % (attribute, inputObj.plot_format))
            rarefaction_by_samplesize_by_level = rarefaction_by_samplesize_by_level_by_attribute[attribute]
            f, ax = plt.subplots(figsize=inputObj.plot_size)
            max_number_of_samples = 0
            for idx, level in enumerate(rarefaction_by_samplesize_by_level):
                number_of_samples = len(rarefaction_by_samplesize_by_level[level])
                if number_of_samples > max_number_of_samples:
                    max_number_of_samples = number_of_samples
                colour = plt.cm.Paired(idx/len(rarefaction_by_samplesize_by_level))
                x_values = []
                y_mins = []
                y_maxs = []
                median_y_values = []
                median_x_values = []
                for x, y_reps in rarefaction_by_samplesize_by_level[level].items():
                    x_values.append(x)
                    y_mins.append(min(y_reps))
                    y_maxs.append(max(y_reps))
                    median_y_values.append(median(y_reps))
                    median_x_values.append(x)
                x_array = np.array(x_values)
                y_mins_array = np.array(y_mins)
                y_maxs_array = np.array(y_maxs)
                ax.plot(median_x_values, median_y_values, '-', color=colour, label=level)
                ax.fill_between(x_array, y_mins_array, y_maxs_array, color=colour, alpha=0.5)
            ax.set_xlim([0, max_number_of_samples + 1])
            ax.set_ylabel("Count of non-singleton clusters", fontsize=inputObj.plot_font_size)
            ax.set_xlabel("Sampled proteomes", fontsize=inputObj.plot_font_size)
            ax.legend(ncol=1, numpoints=1, loc="lower right", frameon=True, fontsize=inputObj.plot_font_size)
            print "[STATUS]\t- Plotting %s" % (rarefaction_plot_f)
            f.savefig(rarefaction_plot_f, format=inputObj.plot_format)
            plt.close()

########################################################################
# CLASS : AttributeLevelObj
########################################################################

class AttributeLevelObj():
    '''
    Definitions:
        'shared' : shared between one ALO and others
        'singleton' : cardinality of 1 ('specific', but separate)
        'specific' : only present within one ALO
    '''
    def __init__(self, attribute, level, proteomes):
        self.attribute = attribute # string
        self.level = level # string
        self.proteomes_list = list(proteomes) #
        self.proteomes = set(proteomes) # frozenset(), used for checking whether cluster and ALO intersect
        self.proteome_count = len(proteomes) # int

        self.cluster_ids_by_cluster_type_by_cluster_status = {'present' : {'singleton' : [], 'specific' : [], 'shared' : []},
                                                              'absent' : {'singleton' : [], 'specific' : [], 'shared' : []}}  # sums up to cluster_count
        self.protein_ids_by_cluster_type = {'singleton' : [], 'specific' : [], 'shared' : []} # list of lists
        self.protein_span_by_cluster_type = {'singleton' : [], 'specific' : [], 'shared' : []}
        self.clusters_by_cluster_cardinality_by_cluster_type = {'shared' : {'true' : [], 'fuzzy' : []}, 'specific' : {'true' : [], 'fuzzy' : []}}

        self.cluster_status_by_cluster_id = {}
        self.cluster_type_by_cluster_id = {}

        self.cluster_mwu_pvalue_by_cluster_id = {}
        self.cluster_mwu_log2_mean_by_cluster_id = {}
        self.cluster_mean_ALO_count_by_cluster_id = {}
        self.cluster_mean_non_ALO_count_by_cluster_id = {}

        self.domain_counter_by_domain_source_by_cluster_type = None
        self.protein_with_domain_count_by_domain_source_by_cluster_type = None

        self.protein_length_stats_by_cluster_id = {}
        self.protein_count_by_cluster_id = {}

        self.rarefaction_data = {} # repetition : number of clusters

    ###############################
    ### add_clusterObj
    ###############################

    def analyse_domains(self):
        print "[STATUS] - Analysing domains (this may take a while) ... "
        domain_counter_by_domain_source_by_cluster_type = {'singleton' : {}, 'specific' : {}, 'shared' : {}}
        protein_with_domain_count_by_domain_source_by_cluster_type = {'singleton' : {}, 'specific' : {}, 'shared' : {}}
        get_proteinObj_by_protein_id = proteinCollection.proteinObjs_by_protein_id.get
        for cluster_type in self.protein_ids_by_cluster_type:
            for domain_source in proteinCollection.domain_sources:
                if not domain_source in domain_counter_by_domain_source_by_cluster_type[cluster_type]:
                    domain_counter_by_domain_source_by_cluster_type[cluster_type][domain_source] = Counter()
                    protein_with_domain_count_by_domain_source_by_cluster_type[cluster_type][domain_source] = 0
                for protein_id in self.protein_ids_by_cluster_type[cluster_type]:
                    proteinObj = get_proteinObj_by_protein_id(protein_id)
                    if domain_source in proteinObj.domain_counter_by_domain_source:
                        domain_counter = proteinObj.domain_counter_by_domain_source[domain_source]
                        if domain_counter:
                            domain_counter_by_domain_source_by_cluster_type[cluster_type][domain_source] += domain_counter
                            protein_with_domain_count_by_domain_source_by_cluster_type[cluster_type][domain_source] += 1
                    if proteinObj.go_terms:
                        domain_counter = Counter(list(proteinObj.go_terms))
                        domain_counter_by_domain_source_by_cluster_type[cluster_type]["GO"] += domain_counter
                        protein_with_domain_count_by_domain_source_by_cluster_type[cluster_type]["GO"] += 1

        domain_counter_by_domain_source_by_cluster_type['total'] = {}
        protein_with_domain_count_by_domain_source_by_cluster_type['total'] = {}
        for domain_source in proteinCollection.domain_sources:
            domain_counter_by_domain_source_by_cluster_type['total'][domain_source] = Counter()
            protein_with_domain_count_by_domain_source_by_cluster_type['total'][domain_source] = 0

        for cluster_type in domain_counter_by_domain_source_by_cluster_type:
            for domain_source in proteinCollection.domain_sources:
                domain_counter_by_domain_source_by_cluster_type['total'][domain_source] += domain_counter_by_domain_source_by_cluster_type[cluster_type][domain_source]
                protein_with_domain_count_by_domain_source_by_cluster_type['total'][domain_source] += protein_with_domain_count_by_domain_source_by_cluster_type[cluster_type][domain_source]
        self.domain_counter_by_domain_source_by_cluster_type = domain_counter_by_domain_source_by_cluster_type
        self.protein_with_domain_count_by_domain_source_by_cluster_type = protein_with_domain_count_by_domain_source_by_cluster_type
        #print self.level
        #for cluster_type in self.domain_counter_by_domain_source_by_cluster_type:
        #    print cluster_type
        #    print self.domain_counter_by_domain_source_by_cluster_type[cluster_type]
        #    print self.protein_with_domain_count_by_domain_source_by_cluster_type[cluster_type]

    def add_clusterObj(self, clusterObj, attribute_cluster_type, ALO_cluster_status, ALO_cluster_cardinality, ALO_protein_ids_in_cluster, ALO_protein_length_stats, mwu_pvalue, mwu_log2_mean, mean_ALO_count, mean_non_ALO_count):
        self.cluster_ids_by_cluster_type_by_cluster_status[ALO_cluster_status][attribute_cluster_type].append(clusterObj.cluster_id)
        self.cluster_status_by_cluster_id[clusterObj.cluster_id] = ALO_cluster_status
        self.cluster_type_by_cluster_id[clusterObj.cluster_id] = attribute_cluster_type
        self.protein_length_stats_by_cluster_id[clusterObj.cluster_id] = ALO_protein_length_stats

        self.protein_count_by_cluster_id[clusterObj.cluster_id] = len(ALO_protein_ids_in_cluster)
        if ALO_cluster_status == 'present':
            for ALO_protein_id in ALO_protein_ids_in_cluster:
                self.protein_ids_by_cluster_type[attribute_cluster_type].append(ALO_protein_id)
            self.protein_span_by_cluster_type[attribute_cluster_type].append(ALO_protein_length_stats['sum'])
            if not attribute_cluster_type == 'singleton':
                if ALO_cluster_cardinality:
                    self.clusters_by_cluster_cardinality_by_cluster_type[attribute_cluster_type][ALO_cluster_cardinality].append(clusterObj.cluster_id)

        self.cluster_mwu_pvalue_by_cluster_id[clusterObj.cluster_id] = mwu_pvalue
        self.cluster_mwu_log2_mean_by_cluster_id[clusterObj.cluster_id] = mwu_log2_mean
        self.cluster_mean_ALO_count_by_cluster_id[clusterObj.cluster_id] = mean_ALO_count
        self.cluster_mean_non_ALO_count_by_cluster_id[clusterObj.cluster_id] = mean_non_ALO_count

    ###############################
    ### get_protein_count_by_cluster_type
    ###############################

    def get_protein_count_by_cluster_type(self, cluster_type):
        if cluster_type == 'total':
            return sum([len(protein_ids) for cluster_type, protein_ids in self.protein_ids_by_cluster_type.items()])
        else:
            return len(self.protein_ids_by_cluster_type[cluster_type])

    ###############################
    ### get_protein_span_by_cluster_type
    ###############################

    def get_protein_span_by_cluster_type(self, cluster_type):
        span = 0
        if cluster_type == 'total':
            span = sum([sum(protein_ids) for cluster_type, protein_ids in self.protein_span_by_cluster_type.items()])
        else:
            span = sum(self.protein_span_by_cluster_type[cluster_type])
        return span

    ###############################
    ### get_cluster_count_by_cluster_status_by_cluster_type
    ###############################

    def get_cluster_count_by_cluster_status_by_cluster_type(self, cluster_status, cluster_type):
        if cluster_type == 'total':
            return sum([len(cluster_ids) for cluster_type, cluster_ids in self.cluster_ids_by_cluster_type_by_cluster_status[cluster_status].items()])
        else:
            return len(self.cluster_ids_by_cluster_type_by_cluster_status[cluster_status][cluster_type])

    def get_cluster_count_by_cluster_cardinality_by_cluster_type(self, cluster_type, cluster_cardinality):
        return len(self.clusters_by_cluster_cardinality_by_cluster_type[cluster_type][cluster_cardinality])

    def get_proteomes(self):
        return ", ".join(sorted([str(proteome_id) for proteome_id in self.proteomes]))

########################################################################
# CLASS : ProteinCollection
########################################################################

class ProteinCollection():
    def __init__(self, proteinObjs):
        self.proteinObjs = proteinObjs
        self.proteinObjs_by_protein_id = {proteinObj.protein_id : proteinObj for proteinObj in proteinObjs}
        self.protein_count = len(proteinObjs)
        self.domain_sources = []
        self.fastas_parsed = False
        self.functional_annotation_parsed = False

    ###############################
    ### add_domainObjs_to_proteinObjs
    ###############################

    def add_annotation_to_proteinObj(self, domain_protein_id, domain_counter_by_domain_source, go_terms):
        proteinObj = self.proteinObjs_by_protein_id.get(domain_protein_id, None)
        if not proteinObj:
            sys.exit("[ERROR] : Protein-ID %s is part of functional annotation but is not part of any proteome" % (domainObj.domain_protein_id))
        proteinObj.domain_counter_by_domain_source = domain_counter_by_domain_source
        signalp_notm = proteinObj.domain_counter_by_domain_source.get("SignalP_EUK", None)
        if signalp_notm and "SignalP-noTM" in signalp_notm:
            proteinObj.secreted = True
        proteinObj.go_terms = go_terms

    def get_protein_length_stats(self, protein_ids):
        protein_length_stats = {'sum' : 0, 'mean' : 0.0, 'median' : 0, 'sd': 0.0}
        if protein_ids and self.fastas_parsed:
            protein_lengths = [self.proteinObjs_by_protein_id[protein_id].length for protein_id in protein_ids]
            protein_length_stats['sum'] = sum(protein_lengths)
            protein_length_stats['mean'] = mean(protein_lengths)
            protein_length_stats['median'] = median(protein_lengths)
            protein_length_stats['sd'] = sd(protein_lengths)
        return protein_length_stats
########################################################################
# CLASS : ProteinObj
########################################################################

class ProteinObj():
    def __init__(self, protein_id, proteome_id, species_id, sequence_id):
        self.protein_id = protein_id
        self.proteome_id = proteome_id
        self.species_id = species_id
        self.sequence_id = sequence_id
        self.length = None
        self.clustered = False

        self.secreted = False

        self.domain_counter_by_domain_source = {}
        self.go_terms = []


    ###############################
    ### add_length
    ###############################

    def add_length(self, length):
        self.length = length

    ###############################
    ### get_domain_list
    ###############################

    def get_domain_list(self):
        return sorted(self.domain_list, key=lambda x: x.domain_start, reverse=False)


    ###############################
    ### compute_domain_count_by_domain_id_by_domain_source
    ###############################

    def compute_domain_count_by_domain_id_by_domain_source(self):
        if self.domain_list:
            domain_ids_by_domain_source = {domainObj.domain_source : [] for domainObj in self.domain_list}
            for domainObj in self.domain_list:
                domain_ids_by_domain_source[domainObj.domain_source].append(domainObj.domain_id)
            self.domain_count_by_domain_id_by_domain_source = {domain_source : Counter(domain_ids_by_domain_source[domain_source]) for domain_source in domain_ids_by_domain_source}
        else:
            self.domain_count_by_domain_id_by_domain_source = Counter()

########################################################################
# CLASS : ClusterCollection
########################################################################

class ClusterCollection():
    def __init__(self, clusterObjs, inferred_singletons_count, functional_annotation_parsed, fastas_parsed, domain_sources):
        self.clusterObjs = clusterObjs
        self.cluster_count = len(clusterObjs)
        self.inferred_singletons_count = inferred_singletons_count
        self.functional_annotation_parsed = functional_annotation_parsed
        self.fastas_parsed = fastas_parsed
        self.domain_sources = [domain_source for domain_source in domain_sources if not domain_source == "GO"]
########################################################################
# CLASS : ClusterObj
########################################################################

class ClusterObj():
    def __init__(self, cluster_id, protein_ids):
        self.cluster_id = cluster_id
        self.protein_ids = set(protein_ids)
        self.protein_count = len(protein_ids)
        self.proteomes_by_protein_id = {protein_id : proteinCollection.proteinObjs_by_protein_id[protein_id].proteome_id for protein_id in protein_ids}
        self.proteome_ids_list = self.proteomes_by_protein_id.values()
        self.protein_count_by_proteome_id = Counter(self.proteome_ids_list)
        self.proteome_ids = frozenset(self.proteome_ids_list)
        self.proteome_count = len(self.proteome_ids)
        self.singleton = False if self.protein_count > 1 else True
        self.apomorphy = False if self.proteome_count > 1 else True
        self.protein_ids_by_proteome_id = self.compute_protein_ids_by_proteome()

        # DOMAINS
        self.go_terms = self.compute_go_terms()
        self.domain_counter_by_domain_source = self.compute_domain_counter_by_domain_source()
        self.secreted_cluster_coverage = self.compute_secreted_cluster_coverage()
        self.domain_entropy_by_domain_source = self.compute_domain_entropy_by_domain_source()
        self.protein_length_stats = self.compute_protein_length_stats()

        self.implicit_protein_ids_by_proteome_id_by_level_by_attribute = None
        self.proteome_ids_by_level_by_attribute = None # used for checking status
        self.proteome_coverage_by_level_by_attribute = None
        self.protein_counts_of_proteomes_by_level_by_attribute = None # non-zero-counts
        self.protein_median = None
        self.cluster_type_by_attribute = None

    ###############################
    ### compute_protein_ids_by_proteome
    ###############################

    def compute_protein_ids_by_proteome(self):
        protein_ids_by_proteome_id = defaultdict(set)
        for protein_id, proteome_id in self.proteomes_by_protein_id.items():
            protein_ids_by_proteome_id[proteome_id].add(protein_id)
        return protein_ids_by_proteome_id

    def compute_secreted_cluster_coverage(self):
        secreted = 0
        for protein_id in self.protein_ids:
            if proteinCollection.proteinObjs_by_protein_id[protein_id].secreted:
                secreted += 1
        return secreted/self.protein_count

    def compute_protein_length_stats(self):
        protein_lengths = [proteinCollection.proteinObjs_by_protein_id[protein_id].length for protein_id in self.protein_ids]
        if all(protein_lengths):
            protein_length_stats = {}
            protein_length_stats['mean'] = mean(protein_lengths)
            protein_length_stats['median'] = median(protein_lengths)
            protein_length_stats['sd'] = sd(protein_lengths)
            return protein_length_stats

    def compute_domain_counter_by_domain_source(self):
        cluster_domain_counter_by_domain_source = {}
        for protein_id in self.protein_ids:
            protein_domain_counter_by_domain_source = proteinCollection.proteinObjs_by_protein_id[protein_id].domain_counter_by_domain_source
            if protein_domain_counter_by_domain_source:
                for domain_source, protein_domain_counter in protein_domain_counter_by_domain_source.items():
                    if not domain_source in cluster_domain_counter_by_domain_source:
                        cluster_domain_counter_by_domain_source[domain_source] = Counter()
                    cluster_domain_counter_by_domain_source[domain_source] += protein_domain_counter
        return cluster_domain_counter_by_domain_source

    def compute_domain_entropy_by_domain_source(self):
        domain_entropy_by_domain_source = {}
        for domain_source, domain_counter in self.domain_counter_by_domain_source.items():
            total_count = len([domain for domain in domain_counter.elements()])
            domain_entropy = -sum([i/total_count * log(i/total_count, 2) for i in domain_counter.values()])
            if str(domain_entropy) == "-0.0":
                domain_entropy_by_domain_source[domain_source] = 0.0
            else:
                domain_entropy_by_domain_source[domain_source] = domain_entropy
        return domain_entropy_by_domain_source

    def compute_go_terms(self):
        go_terms = set()
        for protein_id in self.protein_ids:
            if proteinCollection.proteinObjs_by_protein_id[protein_id].go_terms:
                for go_term in proteinCollection.proteinObjs_by_protein_id[protein_id].go_terms:
                    go_terms.add(go_term)
        return go_terms


class InputObj():
    def __init__(self, args):
        # reserved attributes
        self.ATTRIBUTE_RESERVED = ['IDX', 'OUT', "TAXID"]
        # input files
        self.cluster_f = args['--cluster_file']
        self.attribute_f = args['--attribute_file']
        self.sequence_ids_f = args['--sequence_ids_file']
        self.species_ids_f = args['--species_ids_file']
        self.tree_f = args['--tree_file']
        self.render_tree = True
        self.nodesdb_f = args['--nodesdb']
        self.functional_annotation_f = args['--functional_annotation']
        self.check_input_files()
        #self.check_that_ete_can_plot()
        # FASTA files
        self.fasta_dir = args['--fasta_dir']
        self.check_if_fasta_dir_and_species_ids_f()
        # outprefix
        self.outprefix = args['--outprefix']
        # proteins
        self.infer_singletons = args['--infer_singletons']
        # values: fuzzyness
        self.fuzzy_count = None
        self.check_fuzzy_count(args['--target_count'])
        self.fuzzy_fraction = None
        self.check_fuzzy_fraction(args['--fuzzyness'])
        self.fuzzy_min = None
        self.fuzzy_max = None
        self.check_fuzzy_min_max(args['--min'], args['--max'])
        self.fuzzy_range = set([x for x in xrange(self.fuzzy_min, self.fuzzy_max+1) if not x == self.fuzzy_count])
        # values: rarefaction
        self.repetitions = int(args['--repetitions']) + 1
        self.check_repetitions()
        self.min_proteomes = int(args['--min_proteomes'])
        self.check_min_proteomes()
        # values: plots
        self.plot_format = args['--plotfmt']
        self.check_plot_format()
        self.plot_size = tuple(int(x) for x in args['--plotsize'].split(","))
        self.plot_font_size = int(args['--fontsize'])
        # taxrank
        self.taxranks = [taxrank.replace(" ","") for taxrank in args['--taxranks'].split(",")]
        self.check_taxranks()

    def check_plot_format(self):
        SUPPORTED_PLOT_FORMATS = set(['png', 'pdf', 'svg'])
        if self.plot_format not in SUPPORTED_PLOT_FORMATS:
            sys.exit("[ERROR] : Plot format %s not part of supported plot formats (%s)" % (self.plot_format, SUPPORTED_PLOT_FORMATS))

    def check_repetitions(self):
        if not self.repetitions > 0:
            sys.exit("[ERROR] : Please specify a positive integer for the number of repetitions for the rarefaction curves")

    def check_min_proteomes(self):
        if not self.min_proteomes > 0:
            sys.exit("[ERROR] : Please specify a positive integer for the minimum number of proteomes to consider for computations")

    def check_taxranks(self):
        SUPPORTED_TAXRANKS = set(['superkingdom', 'kingdom', 'phylum', 'class', 'order', 'superfamily', 'family', 'subfamily', 'genus', 'species'])
        unsupported_taxranks = []
        for taxrank in self.taxranks:
            if not taxrank in SUPPORTED_TAXRANKS:
                unsupported_taxranks.append(taxrank)
        if unsupported_taxranks:
            sys.exit("[ERROR] : Taxrank(s) %s not part of supported Taxranks (%s)" % (",".join(sorted(unsupported_taxranks)), ",".join(sorted(SUPPORTED_TAXRANKS))))

    def check_if_fasta_dir_and_species_ids_f(self):
        if self.fasta_dir:
            if not self.species_ids_f:
                sys.exit("[ERROR] : You have provided a FASTA-dir using '--fasta-dir'. Please provide a Species-ID file using ('--species_ids_file').")

    def check_input_files(self):
        check_file(self.sequence_ids_f)
        check_file(self.species_ids_f)
        check_file(self.attribute_f)
        check_file(self.functional_annotation_f)
        check_file(self.sequence_ids_f)
        check_file(self.tree_f)
        check_file(self.nodesdb_f)

    def check_that_ete_can_plot(self):
        if self.tree_f:
            try:
                import ete3
            except ImportError:
                sys.exit("[ERROR] : Module \'ete3\' was not found. Please install \'ete3\' using \'pip install ete3\'\n/tPlotting of trees requires additional dependencies:\n\t- PyQt4\n\t")
            try:
                import PyQt4
            except ImportError:
                sys.exit("[ERROR] : PyQt4 is not installed. Please install PyQt4")
            from ete3 import Tree
            t = Tree( "((a,b),c);" )
            try:
                test_tree_f = join(getcwd(), "%s.this_is_a_test_tree.pdf" % (outprefix))
                t.render("test_tree_f.pdf", w=40, units="mm")
                print "[STATUS] : ETE can connect to X server (X11). Tree will be rendered."
            except:
                print "[WARN] : ETE cannot connect to X server (X11). No tree will be rendered."
                self.render_tree = False

    def check_fuzzy_count(self, target_count):
        if int(target_count) > 0:
            self.fuzzy_count = int(target_count)
        else:
            sys.exit("[ERROR] : --target_count %s must be greater than 0" % (target_count))

    def check_fuzzy_fraction(self, fuzzyness):
        if 0 <= float(fuzzyness) <= 1:
            self.fuzzy_fraction = float(fuzzyness)
        else:
            sys.exit("[ERROR] : --fuzzyness %s is not between 0.0 and 1.0" (fuzzyness))

    def check_fuzzy_min_max(self, fuzzy_min, fuzzy_max):
        if int(fuzzy_min) <= int(fuzzy_max):
            self.fuzzy_min = int(args['--min'])
            self.fuzzy_max = int(args['--max'])
        else:
            sys.exit("[ERROR] : --min %s is greater than --max %s" (fuzzy_min, fuzzy_max))

if __name__ == "__main__":
    __version__ = 0.1
    args = docopt(__doc__)
    # Sanitise input
    inputObj = InputObj(args)
    if inputObj.tree_f:
        try:
            import ete3
        except:
            sys.exit("[ERROR] : Module \'ete3\' was not found. Please install \'ete3\' using \'pip install ete3\'")

    # Input sane ... now we start
    print "[STATUS] - Starting analysis ..."
    overall_start = time.time()
    # Initialise
    aloCollection = None
    proteinCollection = None
    domainCollection = None
    clusterCollection = None
    # Build dataFactory
    dataFactory = DataFactory()
    # Build Collections
    aloCollection = dataFactory.build_AloCollection()
    proteinCollection = dataFactory.build_ProteinCollection(inputObj)
    clusterCollection = dataFactory.build_ClusterCollection(inputObj)
    dataFactory.setup_dirs(inputObj)
    aloCollection.analyse_clusters()
    # aloCollection.analyse_domains() # takes prohibitely long, implement faster!
    aloCollection.analyse_tree()
    sys.exit("STOP.")
    aloCollection.compute_rarefaction_data()
    dataFactory.write_output()

    overall_end = time.time()
    overall_elapsed = overall_end - overall_start
    print "[STATUS] - Took %ss to run kinfin." % (overall_elapsed)
    ###
    del aloCollection
    del proteinCollection
    del domainCollection
    del clusterCollection
    ###
    '''
    Pending
        1. generate output for some overall metrics:
            - singletons with domains
            - specific clusters with domains
        2. annotate legend with boniferroni corrected p-values
        3. Make Vulcanos's after attribute-output is completed
        4. Make separate output file for 1-to-1's

        for each set of proteomes theit cluster ids
        for each subnode
            intersectiom
            if true append to list
        if all in list true synapomorphy

    '''
