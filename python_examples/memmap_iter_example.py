#!/usr/bin/env python3
"""Example: iterate batches from MemmapBatchIter and print summaries."""
import math

from kinfin_index_py import MemmapBatchIter


def main():
    idx = "example/index.mmap"
    partitions = [[0, 1]]  # example: treat species 0 and 1 as the group

    it = MemmapBatchIter(idx, partitions, batch_size=4)
    total_batches = 0
    total_clusters = 0

    for batch in it:
        # batch is a dict-of-lists
        cidx = batch["cluster_idx"]
        gcount = batch["group_count"]
        ocount = batch["other_count"]
        gmean = batch.get("group_mean", [math.nan] * len(cidx))
        omean = batch.get("other_mean", [math.nan] * len(cidx))

        print(f"Batch {total_batches}: {len(cidx)} clusters")
        for ci, g, o, gm, om in zip(cidx, gcount, ocount, gmean, omean):
            gm_str = f"{gm:.2f}" if not math.isnan(gm) else "NA"
            om_str = f"{om:.2f}" if not math.isnan(om) else "NA"
            print(
                f"  cluster {ci}: group={g} other={o} mean_group={gm_str} mean_other={om_str}"
            )
            total_clusters += 1

        total_batches += 1

    print(f"Done: {total_batches} batches, {total_clusters} clusters total")


if __name__ == "__main__":
    main()
