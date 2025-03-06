# curl examples

A set of example commands to get started with the KinFin API

## Fetch the test data

```bash
export WORKDIR=~/tmp/kinfin
mkdir -p $WORKDIR
cd $WORKDIR
curl -L http://molluscdb.cog.sanger.ac.uk/dev/kinfin/api_test_data.tar.gz > api_test_data.tar.gz
tar xf api_test_data.tar.gz && rm api_test_data.tar.gz
```

## Set some variables

```bash
export KINFIN_PORT=4322
export CLUSTER_FILE_PATH=$WORKDIR/api_test_data/Orthogroups.txt
export SEQUENCE_IDS_FILE_PATH=$WORKDIR/api_test_data/kinfin.SequenceIDs.txt
export TAXON_IDX_MAPPING_FILE_PATH=$WORKDIR/api_test_data/taxon_idx_mapping.json
export RESULTS_BASE_DIR=$WORKDIR/output
export SESSION_INACTIVITY_THRESHOLD=24
```

## Clone the KinFin repo

```bash
git clone https://github.com/genomehubs/kinfin
pip install -r requirements.txt
```

## Start the API
```
./src/main.py serve -p $KINFIN_PORT
```


## Use the API

```bash
export KINFIN_PORT=4322
export KINFIN_HOST="http://127.0.0.1:$KINFIN_PORT"
export SESSION_ID="6599179a64accf331ffe653db00a0e24"
```

### 1. Initialize the Analysis Process

The `/init` endpoint calls the main analysis function to run KinFin and generate a set of output files to be explored via the remaining endpoints.

```bash
curl -X POST "$KINFIN_HOST/kinfin/init" \
-H "Content-Type: application/json" \
-d '{"config": [{"taxon": "CBRIG", "clade": "CBRIG", "host": "outgroup"}, {"taxon": "DMEDI", "clade": "DMEDI", "host": "human"}, {"taxon": "LSIGM", "clade": "n16", "host": "other"}, {"taxon": "AVITE", "clade": "n16", "host": "other"}, {"taxon": "CELEG", "clade": "CELEG", "host": "outgroup"}, {"taxon": "EELAP", "clade": "n16", "host": "other"}, {"taxon": "OOCHE2", "clade": "OOCHE2", "host": "other"}, {"taxon": "OFLEX", "clade": "n11", "host": "other"}, {"taxon": "LOA2", "clade": "n15", "host": "human"}, {"taxon": "SLABI", "clade": "SLABI", "host": "other"}, {"taxon": "BMALA", "clade": "n15", "host": "human"}, {"taxon": "DIMMI", "clade": "n11", "host": "other"}, {"taxon": "WBANC2", "clade": "n15", "host": "human"}, {"taxon": "TCALL", "clade": "TCALL", "host": "other"}, {"taxon": "OOCHE1", "clade": "n11", "host": "other"}, {"taxon": "BPAHA", "clade": "n15", "host": "other"}, {"taxon": "OVOLV", "clade": "n11", "host": "human"}, {"taxon": "WBANC1", "clade": "WBANC1", "host": "human"}, {"taxon": "LOA1", "clade": "LOA1", "host": "human"}]}' | jq
```

The remaining API endpoints require a `session_id` parameter so they can be associated with the results of an analysis. This parameter is set based on the input data to avoid unecessary duplication if multiple users request the same data, which is particularly liekly in the context of user-facing example analyses. As such the parameter value is deterministic based on the input and should match the `SESSION_ID` variable set earlier. To confirm this, check `data.session_id` in the output of the above command.

### 2. Get Run Status

The `/status` endpoint returns the current status of a session. While the analysis is running it will include `data.is_complete: false`. Upon completion this value will be set to `true`.

```bash
curl -X GET "$KINFIN_HOST/kinfin/status" \
-H "x-session-id: $SESSION_ID" | jq
```

### 3. Get Run Summary

The `run-summary` endpoint returns a high-level summary of the session run, including numbers of clusters, proteins and proteomes and lists of proteomes that have been included or excluded relative to the full clustering dataset.

```bash
curl -X GET "$KINFIN_HOST/kinfin/run-summary" \
-H "x-session-id: $SESSION_ID" | jq
```

### 4. Get Available Attributes and Taxon Sets

The `/available-attributes-taxonsets` endpoint returns lists of available attributes and taxon sets in a session. These lists are determined by the input data so will be specific to the current session.

```bash
curl -X GET "$KINFIN_HOST/kinfin/available-attributes-taxonsets" \
-H "x-session-id: $SESSION_ID" | jq
```

### 5. Get Counts by Taxon

The `counts-by-taxon` endpoint returns counts for each orthogroup of the number of proteins in that cluster from each taxon.

```bash
curl -X GET "$KINFIN_HOST/kinfin/counts-by-taxon" \
-H "x-session-id: $SESSION_ID" | jq
```

### 6. Get Cluster Summary

The `cluster-summary/{attribute}` endpoint returns a summary of `attribute` statistics for each cluster.

```bash
curl -X GET "$KINFIN_HOST/kinfin/cluster-summary/host" \
-H "x-session-id: $SESSION_ID" | jq
```

### 7. Get Attribute Summary

The `attribute-summary/{attribute}` endpoint returns a summary including singleton, specific, shared and absent protein/cluster counts for each taxon_set defined for the given `attribute`

```bash
curl -X GET "$KINFIN_HOST/kinfin/attribute-summary/host" \
-H "x-session-id: $SESSION_ID" | jq
```

### 8. Get Cluster Metrics

The `/cluster-metrics/{attribute}/{taxon_set}` endpoint returns a set of metrics for the given `attribute` and `taxon_set` in each cluster

```bash
curl -X GET "$KINFIN_HOST/kinfin/cluster-metrics/host/human" \
-H "x-session-id: $SESSION_ID" | jq
```

### 9. Get Pairwise Analysis

The `/pairwise-analysis/{attribute}` endpoint returns a pairwise analysis for protein counts between pairs of taxon sets in each cluster for a given `attribute`

```bash
curl -X GET "$KINFIN_HOST/kinfin/pairwise-analysis/clade" \
-H "x-session-id: $SESSION_ID" | jq
```

### 10. Get Plot

The `/plot/{plot-type}` endpoint returns a png plot for the requested `plot-type`.

```bash
curl -X GET "$KINFIN_HOST/kinfin/plot/cluster-size-distribution" \
-H "x-session-id: $SESSION_ID" -o "cluster_size_distribution.png"
```
