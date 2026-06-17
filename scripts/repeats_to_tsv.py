#!/usr/bin/env python3

import sys

import pandas as pd


def run(fn):
    header = []
    rows = []
    with open(fn) as fh:
        for idx, line in enumerate(fh):
            # print(line)
            if not header:
                _ = line.split()
                header = [
                    "score",
                    "div",
                    "del",
                    "ins",
                    "sequence",
                    "qstart",
                    "qend",
                    "qleft",
                    "C",
                    "repeat",
                    "family",
                    "mstart",
                    "mend",
                    "mleft",
                    "ID",
                    "last",
                ]
            else:
                row = line.split()
                rows.append({h: r for h, r in zip(header, row)})
            # if idx == 30:
            #    sys.exit(1)
    pd.DataFrame.from_dict(rows).to_csv(f"{fn}.tsv", sep="\t", index=False)


if __name__ == "__main__":
    run(sys.argv[1])
