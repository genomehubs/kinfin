import pathlib

ARGS_SUPPORTED_PLOT_FORMATS = ["png", "jpeg", "pdf"]
ARGS_SUPPORTED_OUTPUT_FORMATS = ["tsv", "parquet", "feather"]
ARGS_SUPPORTED_OUTPUT_FORMATS_CONFIG = ["csv", "json"]
ARGS_TAXONOMY_RANKS_DEFAULT = ["phylum", "order", "genus"]
ARGS_TAXONOMY_RANKS_SUPPORTED = [
    "species",
    "genus",
    "family",
    "order",
    "class",
    "phylum",
    "kingdom",
    "realm",
]

CWD = pathlib.Path.cwd().absolute()

TMP_PATHS_FILE = pathlib.Path(".kinfin.pickle")

BASE_DIR = pathlib.Path(__file__).absolute().parent.parent

CONFIG_DIR = BASE_DIR / "config"

DATA_DIR = BASE_DIR / "data"

LOG_DIR = BASE_DIR / "logs"
LOG_CONFIG = CONFIG_DIR / "logging.json"

STD_FORMAT = "parquet"
PLOT_FORMAT = "png"
ELEMENTS_FN = f"orthogroups.elements.{STD_FORMAT}"
ELEMENTS_ORPHAN_FN = f"orthogroups.elements.orphans.{STD_FORMAT}"
ELEMENTS_ORPHAN_SUMMARY_FN = f"orthogroups.elements.orphans.table.{STD_FORMAT}"
ORTHOGROUPS_FN = f"orthogroups.{STD_FORMAT}"
COUNTS_FN = f"orthogroups.counts.{STD_FORMAT}"
COUNTS_NAN_FN = f"orthogroups.counts.nan.{STD_FORMAT}"
EC_TALLY_FN = f"orthogroups.EC.tally.{STD_FORMAT}"
SC_TALLY_FN = f"orthogroups.SC.tally.{STD_FORMAT}"
ANNOTATION_FN = f"orthogroups.interpro.{STD_FORMAT}"
INTERPRO_FN = f"interpro.{STD_FORMAT}"
ANNOTATION_FN = f"interpro_annotation.{STD_FORMAT}"
ANNOTATION_DENOMINATOR_FN = f"interpro_annotation_denominator.{STD_FORMAT}"
SIGNATURES_FN = f"interpro_signatures.{STD_FORMAT}"
SIGNATURES_SUMMARY_FN = f"interpro_signatures.summary.{STD_FORMAT}"
ENTROPY_FN = "orthogroups.interpro.entropy"

SUPPORTED_FASTA_EXTENSIONS = [".faa", ".fa", ".fas"]
SUPPORTED_INTERPRO_EXTENSIONS = [".tsv"]

CONFIG_MIN_SAMPLE_IDS = 2  # at least one group in comparisons needs to be of length 2

PROGRESS_NCOLS = 0
PROGRESS_DESC_PARTITIONING = f"[{'PARTITIONING'.center(23, '.')}]"
PROGRESS_DESC_ORTHOGROUPS_PARSE = f"[{'ORTHOGROUPS'.center(23, '.')}]"
PROGRESS_DESC_FASTA = f"[{'FASTAS'.center(23, '.')}]"
PROGRESS_DESC_ORTHOGROUPS_ADD_SAMPLE = f"[{'SAMPLEIDS'.center(23, '.')}]"
PROGRESS_DESC_INTERPRO = f"[{'INTERPRO PARSING'.center(23, '.')}]"
PROGRESS_DESC_SIGNATURES = f"[{'SIGNATURES 1/2'.center(23, '.')}]"
PROGRESS_DESC_SIGNATURES_COUNTING = f"[{'SIGNATURES 2/2'.center(23, '.')}]"
PROGRESS_DESC_ANNOTATION_TASK_PREP = f"[{'CHUNKING ANNOTATION'.center(23, '.')}]"
PROGRESS_DESC_ANNOTATION_TASK_RUN = f"[{'ANALYSING ANNOTATION'.center(23, '.')}]"
PROGRESS_DESC_CHUNKS = f"[{'INTERPRO CHUNKS'.center(23, '.')}]"
PROGRESS_DESC_PARTITIONING = f"[{'PARTITIONING'.center(23, '.')}]"
PROGRESS_DESC_TREE = f"[{'TREE'.center(23, '.')}]"

INTERPRO_TSV_COLUMNS = [
    "element_id",
    "sequence_md5",
    "sequence_length",
    "analysis",
    "signature_id",
    "signature_desc",
    "signature_start",
    "signature_stop",
    "signature_score",
    "signature_status",
    "date",
    "interpro_id",
    "interpro_desc",
    "go_annotation",
    "pathway_annotations",
]
INTERPRO_TSV_COLUMNS_VALID = [
    "element_id",
    "analysis",
    "signature_id",
    "signature_desc",
    "interpro_id",
    "interpro_desc",
    "go_annotation",
]
ANNOTATION_INDEX = [
    "orthogroup_id",
    "analysis",
    "signature_id",
    "signature_desc",
    "interpro_id",
    "interpro_desc",
    "go_annotation",
    "sample_id",
]
SIGNATURE_COLUMNS = [
    "signature_id",
    "analysis",
    "signature_desc",
    "interpro_id",
    "interpro_desc",
    "go_annotation",
]
ANNOTATION_COLUMNS = [
    "orthogroup_id",
    "signature_id",
    "analysis",
    "sample_id",
]

TAXDUMP_FN = DATA_DIR / "taxdump.tar.gz"
TAXDUMP_URL = "https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz"
TAXDUMP_URL_NEW = (
    "https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/new_taxdump.tar.gz"
)
TAXONOMY_USER_URL = "https://www.ncbi.nlm.nih.gov/taxonomy"
TAXONOMY_FN = DATA_DIR / "taxonomy.parquet"
TAXONOMY_VERSION = 1.0
TAXONOMY_RANKS = [
    "species",
    "genus",
    "family",
    "order",
    "class",
    "phylum",
    "kingdom",
    "realm",
    "toplevel",
]

REMAINDER_LABEL = "remainder"

TAXIDS_TOPLEVEL = {
    # see https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi
    "2157",  # "Archaea", [domain]
    "2",  # "Bacteria", [domain]
    "2759",  # "Eukaryota", [domain]
    "10239",  # "Viruses", [acellular root]
    "28384",  # "other sequences", [no rank]
    "12908",  # "unclassified sequences", [no rank]
}

TREE_NODES_MAX_FOR_LOG = 100

CONFIG_KEYWORD_MISSING = "NA"  # change to "None"
