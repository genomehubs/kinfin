# kinfin_index - Usage

Quick usage notes for the Rust CLIs and the Python API provided by the kinfin_index crate.

## Rust CLIs

- Build the binaries in the crate folder:

```bash
cd kinfin_index
cargo build --bins --release
```

- Example commands (run from repo root):

```bash
# create indexes (bincode + memmap)
cargo run --bin indexer -- --example example --out example/index

# analyse (bincode in-memory). `--partition` accepts comma-separated species indices or species names.
# Examples: `--partition 0,1` or `--partition Homo_sapiens,Mus_musculus`
cargo run --bin analyse_cli -- --index example/index.bincode --partition 0,1

# analyse (memmap, disk-backed streaming). `--partition` accepts indices or names (see above).
cargo run --bin analyse_memmap_cli -- --index example/index.mmap --partition 0,1

# inspect memmap file
cargo run --bin mmap_inspect -- --index example/index.mmap
```

Notes:

- `indexer` generates `index.bincode` and `index.mmap` in the output path.
- `analyse_memmap_cli` streams batch results and is suitable for large indexes that don't fit in RAM.

## Python API

The Python extension (built with PyO3/maturin) exposes two primary helpers:

- `analyse_clusters_memmap(index_path, partitions, callback=None, batch_size=256)`
  - Computes cluster statistics from a memmap-backed index and optionally calls a Python `callback` with each batch (a Python list of dicts).
  - `partitions` should be a list of lists of species indices (e.g. `[[0,1],[2,3]]`).

- `MemmapBatchIter(index_path, partitions, batch_size=256)`
  - A Python iterator which yields batches as a dict-of-lists. Each yielded dict contains the following keys:
    - `cluster_idx`, `group_count`, `other_count` (integers)
    - `group_mean`, `other_mean`, `group_sd`, `other_sd`, `group_median`, `other_median` (floats; missing values are `nan`)
  - This iterator computes batches without holding the Python GIL and returns one dict per batch (reduces per-row Python allocations).

Example (using the iterator):

```python
from kinfin_index_py import MemmapBatchIter

it = MemmapBatchIter('example/index.mmap', [[0,1]], batch_size=128)
for batch in it:
    # batch is a dict of lists; e.g. batch['cluster_idx'] is a list of cluster indices
    print(len(batch['cluster_idx']))
```

Building the Python extension (example):

```bash
# in the crate root
maturin develop --release
# then in Python
python -c "import kinfin_index_py; print(dir(kinfin_index_py))"
```

## Further work

- We plan to add full zero-copy numpy-backed batches (via pyo3-numpy) if you need absolutely zero-copy buffers exposed to NumPy.
- See `tests/memmap_roundtrip.rs` for a unit test that validates memmap write->read roundtrip.
  kinfin_index — index builder for kinfin

This crate builds a compact `bincode`-serialized index from KinFin-style input files.

Usage (from repository root):

```bash
# build
cd kinfin_index
cargo build --release

# run against example/ and emit example/index.bincode
cargo run --bin indexer -- --input ../example --output ../example/index.bincode --include-names
```

Output:

- `index.bincode` — binary bincode-serialized `Index` struct
- `index.meta.json` — small JSON summary with counts

This is a developer-friendly prototype. For production scale we'll add a flat memmap layout and per-cluster sparse aggregates.

## Python bindings (PyO3) and usage

This crate exposes a minimal PyO3 module `kinfin_index_py` with a streaming API `analyse_clusters`.

Build and install into your active Python environment (recommended: use `maturin`):

```bash
# install maturin if needed
pip install maturin

# from kinfin_index/ directory
maturin develop --release
```

After installing, use the Python API:

```python
from kinfin_index_py import analyse_clusters

def cb(batch):
	for row in batch:
		print(row)

# partitions is a list of partitions; each partition is a list of species indices
partitions = [[0,1], [2,3]]
analyse_clusters('example/index.bincode', partitions, callback=cb, batch_size=256)
```

If you prefer not to use Python bindings yet, use the included CLI to test analysis:

```bash
cargo run --bin analyse_cli -- --index ../example/index.bincode --partition 0,1
```

Next steps: implement memmap flat layout, per-cluster sparse aggregates and an LRU cache for partition results.
