import kinfin_index_py

INDEX = "../example/index.mmap"
PARTITIONS = [[0, 1]]

collected = []


def cb(batch):
    print("callback received batch:", len(batch))
    for row in batch:
        print(row)
    collected.extend(batch)


if __name__ == "__main__":
    kinfin_index_py.analyse_clusters_memmap(
        INDEX, PARTITIONS, callback=cb, batch_size=4
    )
    print("Total rows:", len(collected))
