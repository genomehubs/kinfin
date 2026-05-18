#!/usr/bin/env python3

import argparse

import hvplot.pandas
import pandas as pd

hvplot.extension("bokeh")


def validate_args():
    parser = argparse.ArgumentParser(description="Plotting script.")
    parser.add_argument(
        "-i",
        required=True,
        type=str,
        help="Input file.",
    )
    return parser.parse_args()


def parse_df(infile):
    df = pd.read_csv(infile, sep="\t")
    df["size"] = df.drop(["#ID"], axis=1).sum(axis=1)
    return df


def get_data(df):
    data = df["size"].value_counts().sort_index()
    return data


def plot_data(data, fn="test.png"):
    data.index.names = ["Cluster size"]
    p = data.hvplot.scatter(
        x="Cluster size", y="count", c="black", logy=True, logx=True
    )
    hvplot.save(p, fn)
    print(f"[+] Generated {fn}")
    hvplot.show(p)


def main():
    args = validate_args()
    df = parse_df(args.i)
    data = get_data(df)
    plot_data(data)


if __name__ == "__main__":
    main()
