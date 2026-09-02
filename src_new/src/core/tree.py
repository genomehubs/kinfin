import logging
import sys
import time

import core.log
import definitions
import ete4
import tqdm

import core.utils

logger = logging.getLogger(__name__)


def get_tree(
    fn,
    sample_ids=[],
    outgroup=[],
):
    """
    # [done]
    - technically only checks for outgroups. A tree with additional tips should work.
    """
    if fn is None:
        logger.info("no tree provided")
        tree = None
    else:
        tree = ete4.Tree(str(fn))
        if outgroup:
            logger.info(
                f"setting the following sample ID(s) as outgroup(s): {','.join(outgroup)}"
            )
            try:
                tree.set_outgroup(tree.common_ancestor(outgroup))
            except KeyError as exc:
                logger.error(
                    f"setting outgroup to {outgroup} failed - {exc} not in tree"
                )
                sys.exit(1)
        else:
            logger.warning(
                "no outgroup provided. No outgroup will be set. Verify tree topology"
            )
        zeros = len(str(len(list(tree.traverse()))))
        idx = 0
        sample_ids_found = []
        for node in tree.traverse("levelorder"):  # rename nodes
            if not node.name:
                node.add_prop("name", f"{str(idx).zfill(zeros)}")
                idx += 1
            else:
                sample_ids_found.append(node.name)
        logger.info(f"tree has {core.utils.format_number(len(sample_ids_found))} taxa")
        sample_ids_missing = set(sample_ids) - set(sample_ids_found)
        if sample_ids_missing:
            logger.error(
                f"{core.utils.format_number(len(sample_ids_missing))} sample IDs not in tree: {' '.join(sample_ids_missing)}"
            )
            sys.exit(1)
        sample_ids_surplus = set(sample_ids_found) - set(sample_ids)
        if sample_ids_surplus:
            logger.warning(f"tree has additional taxa: {' '.join(sample_ids_surplus)}")
        tree.write(
            outfile=core.utils.format_fn(
                fn=("tree.with_node_names.nwk"),
                prefix=core.utils.get_dir("TREE"),
            ),
            props=None,
            parser=1,
        )
        tree_strings = tree.to_str(compact=True, props=["name"]).split("\n")
        if len(tree[str(0).zfill(zeros)]) <= definitions.TREE_NODES_MAX_FOR_LOG:
            logger.debug("[Tree]")
            for tree_string in tree_strings:
                logger.debug(tree_string)
        core.utils.dump(
            tree_strings,
            fn=core.utils.format_fn(
                fn=("tree.with_node_names.txt"),
                prefix=core.utils.get_dir("TREE"),
            ),
        )
    return tree


def process_tree(
    tree_fn="",
    outgroup=[],
    sample_ids=[],
    output_fmt="tsv",
):
    """
    # [done]
    - agnostic about additional leafs
    - OG_AT: ApomorphyType
    - OG_OT: OrthogroupType
    - OG_NP: NodeProportion (based only on leaf_names in df_counts)
    - EC: ElementCount
    """
    t_0 = time.monotonic()
    logger.info(f"processing tree in {tree_fn}")
    tree = get_tree(
        fn=tree_fn,
        sample_ids=sample_ids,
        outgroup=outgroup,
    )

    def place_orthogroup(row):
        row_dict = row.to_dict()
        TNs = [k for k, v in row_dict.items() if v > 0]
        EC = sum(row_dict.values())
        node = tree.common_ancestor(TNs)
        node_id = node.get_prop("name")
        OG_AT = "synapomorphy" if len(TNs) > 1 else "autapomorphy"
        OG_OT = "specific" if EC > 1 else "singleton"
        OG_NP = len(TNs) / len(
            [leaf_name for leaf_name in node.leaf_names() if leaf_name in row_dict]
        )
        return (
            node_id,
            OG_AT,
            OG_OT,
            OG_NP,
            EC,
        )

    logger.info(
        f"placing orthogroups along {core.utils.format_number(len(list(tree.root.edges())))} branches on tree (this might take a moment)"
    )
    tqdm.tqdm.pandas(
        desc=definitions.PROGRESS_DESC_TREE,
        ncols=definitions.PROGRESS_NCOLS,
    )
    df_counts = core.utils.get_counts_df()
    df_nodes = df_counts.progress_apply(
        place_orthogroup,
        axis=1,
        result_type="expand",
    )
    df_nodes.columns = ["node_id", "OG_AT", "OT", "OG_NP", "EC"]
    OG_AT = df_nodes["OG_AT"].value_counts()
    logger.info(
        f"{core.utils.format_number(OG_AT.get('synapomorphy', 0))} synapomorphic orthogroups"
    )
    logger.info(
        f"{core.utils.format_number(OG_AT.get('autapomorphy', 0))} autapomorphic orthogroups"
    )
    df_nodes = df_nodes.reset_index()
    core.utils.dump(
        core.utils.downcast(
            df_nodes,
            categorical=[
                "node_id",
                "OG_AT",
                "OT",
            ],
        ),
        fn=core.utils.format_fn(
            fn=f"tree.node_metrics.{output_fmt}",
            prefix=core.utils.get_dir("TREE"),
        ),
        index=False,
    )
    df_nodes["OG_NT"] = "partial"
    df_nodes["OG_NT"] = df_nodes["OG_NT"].mask(df_nodes["OG_NP"] == 1, "complete")
    df_summary = df_nodes.groupby(
        [
            "node_id",
            "OG_AT",
            "OT",
            "OG_NT",
        ],
        as_index=False,
    ).agg(OC=("orthogroup_id", "count"))
    core.utils.dump(
        core.utils.downcast(
            df_summary,
            categorical=[
                "node_id",
                "OG_AT",
                "OT",
                "OG_NT",
            ],
        ),
        fn=core.utils.format_fn(
            fn=f"tree.summary.{output_fmt}",
            prefix=core.utils.get_dir("TREE"),
        ),
        index=False,
    )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )


if __name__ == "__main__":
    pass
