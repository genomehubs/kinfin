import glob
import time

"""
[ToDo]
= parse fastas
"""


def iter_seq_length(fn):
    with open(fn) as fh:
        header, seqs = "", []
        for line in fh:
            if line[0] == ">":
                if header:
                    header = (
                        header.replace(":", "_")
                        .replace(",", "_")
                        .replace("(", "_")
                        .replace(")", "_")
                    )  # orthofinder replaces chars
                    yield header, len("".join(seqs))
                header, seqs = (
                    line[1:-1].split()[0],
                    [],
                )  # Header is split at first whitespace
            else:
                seqs.append(line[:-1])
        header = (
            header.replace(":", "_")
            .replace(",", "_")
            .replace("(", "_")
            .replace(")", "_")
        )  # orthofinder replaces chars
        yield header, len("".join(seqs))


def get_lengths(path):
    t_0 = time.monotonic()
    data = {}
    for fn in glob.glob(f"{path}/*faa"):
        for header, length in iter_seq_length(fn):
            data[header] = length
    print(f"[get_df_lengths] elapsed: {time.monotonic() - t_0}")
    return data
