#!/usr/bin/env python3
import collections
import datetime
import hashlib
import logging
import sys
import tarfile

import pandas as pd
import prettytable
import requests

import core.utils
import definitions

# [CONSTANTS]

TAXDUMP_FN = definitions.TAXDUMP_FN
TAXDUMP_URL_NEW = definitions.TAXDUMP_URL_NEW
TAXDUMP_URL = definitions.TAXDUMP_URL

TAXONOMY_VERSION = definitions.TAXONOMY_VERSION
TAXONOMY_RANKS = definitions.TAXONOMY_RANKS
TAXONOMY_FN = definitions.TAXONOMY_FN

TAXIDS_TOPLEVEL = definitions.TAXIDS_TOPLEVEL

logger = logging.getLogger(__name__)


def is_taxdump_current(taxdump_fn=TAXDUMP_FN, taxdump_new=True):
    taxdump_url = TAXDUMP_URL_NEW if taxdump_new else TAXDUMP_URL
    try:
        md5_local = hashlib.md5(open(taxdump_fn, "rb").read()).hexdigest()
        md5_remote = requests.get(taxdump_url + ".md5").text.split()[0]
        return md5_local == md5_remote
    except FileNotFoundError:
        return False


def download_taxdump(taxdump_fn=TAXDUMP_FN, taxdump_new=True):
    taxdump_url = TAXDUMP_URL_NEW if taxdump_new else TAXDUMP_URL
    logger.info(f"downloading {taxdump_url} ...")
    success = core.utils.download(taxdump_url, TAXDUMP_FN)
    if not success:
        logger.error("download failed")
        sys.exit()
    return True


def get_taxdump(taxdump_fn=TAXDUMP_FN):
    if is_taxdump_current:
        if taxdump_fn.exists():
            if not is_taxdump_current(taxdump_fn=taxdump_fn):
                return download_taxdump()
            return True
    else:
        return download_taxdump()


def get_ncbi_taxdump_node_data(tar):
    node_data = {}
    for line in tar.extractfile("nodes.dmp"):
        fields = str(line.decode()).split("|")
        node = fields[0].strip()
        parent = fields[1].strip()
        rank = fields[2].strip()
        node_data[node] = [parent, rank]
    logger.info(f"NCBI TaxDump 'nodes.dmp': {len(node_data):,} record(s)")
    return node_data


def get_ncbi_taxdump_name_data(tar):
    name_data = {}
    for line in tar.extractfile("names.dmp"):
        fields = str(line.decode()).split("|")
        node = fields[0].strip()
        name = fields[1].strip()
        name_type = fields[3].strip()
        if name_type == "scientific name":
            name_data[node] = name
    logger.info(f"NCBI TaxDump 'names.dmp': {len(name_data):,} record(s)")
    return name_data


def create_taxonomy_df(taxdump_fn=TAXDUMP_FN):
    logger.info(f"parsing NCBI TaxDump from '{taxdump_fn}'")
    tar = tarfile.open(taxdump_fn, "r")
    node_data = get_ncbi_taxdump_node_data(tar)
    name_data = get_ncbi_taxdump_name_data(tar)
    if len(node_data) == len(name_data):
        taxonomy_rows = []
        for node, name in name_data.items():
            parent = node_data[node][0]
            rank = node_data[node][1]
            taxonomy_rows.append((node, name, rank, parent))
        taxonomy_df = pd.DataFrame.from_records(
            taxonomy_rows, columns=["node", "name", "rank", "parent"]
        )
        taxonomy_df.attrs["version"] = TAXONOMY_VERSION
        taxonomy_df.attrs["records"] = len(taxonomy_df.index)
        taxonomy_df.attrs["created"] = datetime.datetime.now().strftime(
            "%Y/%m/%d %H:%M:%s"
        )
        core.utils.dump(taxonomy_df, TAXONOMY_FN)
        return True
    else:
        logger.error(
            "Number of records in 'names.dmp' and 'nodes.dmp' differ. Files might be truncated ..."
        )
        return False


def coerce_lineage(full_lineage, taxonomic_ranks=TAXONOMY_RANKS):
    lineage = {}
    for rank in taxonomic_ranks:
        lineage[rank] = full_lineage.get(rank, "undef")
    higher_rank_name = ""
    for rank, name in reversed(lineage.items()):
        if name == "undef":
            if higher_rank_name:
                lineage[rank] = f"{higher_rank_name}-undef"
        else:
            higher_rank_name = name
    return lineage


def load_taxonomy_df(update_taxdump=False, update_taxonomy=False, index="node"):
    if update_taxonomy or TAXONOMY_FN.exists() is False:
        if update_taxdump or TAXDUMP_FN.exists() is False:
            success = download_taxdump()
            if not success:
                logger.error("unable to to download taxdump")
        success = create_taxonomy_df()
        if not success:
            logger.error("unable to to create taxonomy")
    try:
        taxonomy_df = core.utils.load(TAXONOMY_FN).set_index(index)
    except Exception:
        logger.exception("unable to load taxonomy")
    return taxonomy_df


def get_lineage(taxid, taxonomy_df, taxonomic_ranks=TAXONOMY_RANKS):
    lineage = {}
    while 1:
        try:
            name, rank, parent = taxonomy_df.loc[taxid].to_list()
        except KeyError:
            break
        if taxid in TAXIDS_TOPLEVEL:
            lineage["toplevel"] = name
            break
        lineage[rank] = name
        taxid = parent
    if taxonomic_ranks:
        lineage = coerce_lineage(lineage, taxonomic_ranks)
    return lineage


def get_taxid(name, taxonomy_df):
    name = name.replace("_", " ")
    if name in taxonomy_df.index:
        taxid, _, __ = taxonomy_df.loc[name].to_list()
        logger.info(f"'{name}' found")
    else:
        try:
            # hyphenize last space
            space_idxs = [idx for idx, letter in enumerate(name) if letter == " "]
            if len(space_idxs) > 1:
                idx1, idx2 = space_idxs[-1], space_idxs[-1] + 1
                name_new = name[:idx1] + "-" + name[idx2:]
                logger.warning(f"'{name}' not found. Trying '{name_new}'")
                name = name_new
                taxid, _, __ = taxonomy_df.loc[name].to_list()
                logger.info(f"'{name}' found")
            else:
                raise KeyError
        except KeyError:
            logger.warning(
                f"'{name}' not found. Set to '{definitions.CONFIG_KEYWORD_MISSING}'"
            )
            taxid = "NA"
    return {"taxid": taxid}


def tally_ranks(self):
    counter = collections.Counter()
    total = 0
    for taxid in self.db:
        if self.db[taxid][1] == "species":
            total += 1
            lineage = self.get_lineage(taxid)
            # if "phylum" not in lineage:
            #     print(lineage)
            for rank in lineage.keys():
                counter[rank] += 1
    table = prettytable.PrettyTable()
    table.field_names = [
        "Taxonomic Rank",
        "Species w/ rank (%)",
        "Species w/ rank (#)",
    ]
    for rank, count in counter.most_common():
        table.add_row([rank, f"{count / total:.2%}", f"{count:,}"])
    table.align["Species w/ rank (%)"] = "r"
    table.align["Species w/ rank (#)"] = "r"
    print(table)
    """
        +------------------+---------------------+---------------------+
        |  Taxonomic Rank  | Species w/ rank (%) | Species w/ rank (#) |
        +------------------+---------------------+---------------------+
        |     species      |             100.00% |           2,198,349 |
        |     toplevel     |             100.00% |           2,198,349 |
        |      phylum      |              94.33% |           2,073,659 |
        |      class       |              93.19% |           2,048,611 |
        |     kingdom      |              92.90% |           2,042,260 |
        |      order       |              90.81% |           1,996,321 |
        |      family      |              85.52% |           1,879,978 |
        |     no rank      |              73.85% |           1,623,554 |
        |      clade       |              73.52% |           1,616,235 |
        |      genus       |              72.17% |           1,586,561 |
        |    subphylum     |              61.95% |           1,361,841 |
        |     subclass     |              52.68% |           1,158,170 |
        |     suborder     |              40.01% |             879,669 |
        |   superfamily    |              36.63% |             805,307 |
        |    infraclass    |              36.46% |             801,493 |
        |      cohort      |              34.74% |             763,708 |
        |    subfamily     |              29.73% |             653,480 |
        |    infraorder    |              28.16% |             619,011 |
        |    superorder    |              14.09% |             309,785 |
        |      tribe       |              13.92% |             305,941 |
        |    subkingdom    |               7.74% |             170,107 |
        |    superclass    |               6.44% |             141,468 |
        |    parvorder     |               4.18% |              91,824 |
        |      realm       |               3.08% |              67,655 |
        |     subtribe     |               2.28% |              50,221 |
        |     subgenus     |               1.05% |              23,058 |
        |    subcohort     |               0.81% |              17,916 |
        |  species group   |               0.39% |               8,643 |
        |     section      |               0.30% |               6,652 |
        | species subgroup |               0.04% |                 811 |
        |    subsection    |               0.03% |                 607 |
        |      series      |               0.01% |                 198 |
        |   superphylum    |               0.01% |                 148 |
        +------------------+---------------------+---------------------+
        """
