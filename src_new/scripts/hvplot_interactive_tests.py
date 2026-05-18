#!/usr/bin/env python3

import argparse

import hvplot.pandas
import pandas as pd
import panel as pn

hvplot.extension("bokeh")
pn.extension()


def validate_args():
    parser = argparse.ArgumentParser(description="Plotting script.")
    parser.add_argument(
        "-i",
        required=True,
        type=str,
        help="Input file.",
    )
    return parser.parse_args()


def parse_data(infile):
    df = pd.read_csv(infile, sep="\t")
    df["size"] = df.drop(["#ID"], axis=1).sum(axis=1)
    return df


def get_data(df):
    data = df["size"].value_counts().sort_index().reset_index()
    return data


# def plot_data(data, min_count, fn="test.png"):
#    data.index.names = ["Cluster size"]
#    data = data[data >= min_count.value]
#    p = data.hvplot.scatter(
#        x="Cluster size", y="count", c="black", logy=True, logx=True
#    )
#    # hvplot.show(p)
#    return p
#    # hvplot.save(p, fn)
#    # print(f"[+] Generated {fn}")


def main():
    args = validate_args()
    df = parse_data(args.i)
    data = get_data(df)
    print(data)
    hvexplorer = data.hvplot.explorer()
    hvexplorer.show()
    # hvplot.save(plot, "test.html", resources=INLINE)


if __name__ == "__main__":
    main()
