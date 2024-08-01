import os
from typing import Dict, List, Optional, Set, Tuple, Union


class ServeArgs:
    def __init__(self, port: int = 8000):
        self.port = port


class InputData:
    def __init__(
        self,
        nodesdb_f: str,
        pfam_mapping_f: str,
        ipr_mapping_f: str,
        go_mapping_f: str,
        cluster_file: str,
        config_f: str,
        sequence_ids_file: str,
        species_ids_file: Optional[str] = None,
        functional_annotation_f: Optional[str] = None,
        fasta_dir: Optional[str] = None,
        tree_file: Optional[str] = None,
        output_path: Optional[str] = None,
        infer_singletons: Optional[bool] = False,
        plot_tree: bool = False,
        min_proteomes: int = 2,
        test: str = "mannwhitneyu",
        taxranks: List[str] = ["phylum", "order", "genus"],
        repetitions: int = 30,
        fuzzy_count: int = 1,
        fuzzy_fraction: float = 0.75,
        fuzzy_range: Set[int] = {x for x in range(20 + 1) if x != 1},
        fontsize: int = 18,
        plotsize: Tuple[float, float] = (24, 12),
        plot_format: str = "pdf",
        taxon_idx_mapping_file: Optional[str] = None,
    ):
        if output_path:
            if not os.path.isabs(output_path):
                output_path = os.path.abspath(output_path)
        else:
            output_path = os.path.join(os.getcwd(), "kinfin_results")

        self.cluster_f = cluster_file
        self.config_f = config_f
        self.sequence_ids_f = sequence_ids_file
        self.species_ids_f = species_ids_file
        self.tree_f = tree_file
        self.functional_annotation_f = functional_annotation_f
        if config_f.endswith(".json"):
            if not taxon_idx_mapping_file:
                raise ValueError("[ERROR] - taxon_idx_mapping not present")
        self.taxon_idx_mapping_file = taxon_idx_mapping_file
        self.nodesdb_f = nodesdb_f
        self.pfam_mapping_f = pfam_mapping_f
        self.ipr_mapping_f = ipr_mapping_f
        self.go_mapping_f = go_mapping_f

        self.test = test
        self.plot_tree = plot_tree
        self.fasta_dir = fasta_dir
        self.output_path = output_path
        self.infer_singletons = infer_singletons
        self.fuzzy_count = fuzzy_count
        self.fuzzy_fraction = fuzzy_fraction
        self.fuzzy_range = fuzzy_range
        self.repetitions = repetitions
        self.min_proteomes = min_proteomes
        self.plot_format = plot_format
        self.fontsize = fontsize
        self.taxranks = taxranks
        self.plotsize = plotsize

        self.pfam_mapping = True
        self.ipr_mapping = True
