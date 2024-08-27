### 1. Initialize the Analysis Process

```bash
curl -X POST "http://127.0.0.1:8000/kinfin/init" \
-H "Content-Type: application/json" \
-d '{"config": [{ "taxon": "BGLAB", "label1": "red" },{ "taxon": "CVIRG", "label1": "red" },{ "taxon": "DPOLY", "label1": "red" },{ "taxon": "GAEGI", "label1": "red" },{ "taxon": "LJAPO", "label1": "red" },{ "taxon": "LSAXA", "label1": "red" },{ "taxon": "MANGU", "label1": "red" },{ "taxon": "MAREN", "label1": "red" },{ "taxon": "MGIGA", "label1": "red" },{ "taxon": "MMERC", "label1": "red" },{ "taxon": "MTROS", "label1": "blue" },{ "taxon": "OBIMA", "label1": "blue" },{ "taxon": "OEDUL", "label1": "blue" },{ "taxon": "OSINE", "label1": "blue" },{ "taxon": "OVULG", "label1": "blue" },{ "taxon": "PCANA", "label1": "blue" },{ "taxon": "PMAXI", "label1": "blue" },{ "taxon": "PVULG", "label1": "blue" },{ "taxon": "TGRAN", "label1": "blue" }]}' | jq
```

### 2. Get Run Status

```bash
curl -X GET "http://127.0.0.1:8000/kinfin/status" \
-H "x-session-id: <session_id>" | jq
```

### 3. Get Run Summary

```bash
curl -X GET "http://127.0.0.1:8000/kinfin/run-summary" \
-H "x-session-id: <session_id>" | jq
```

### 4. Get Available Attributes and Taxon Sets

```bash
curl -X GET "http://127.0.0.1:8000/kinfin/available-attributes-taxonsets" \
-H "x-session-id: <session_id>" | jq
```

### 5. Get Counts by Taxon

```bash
curl -X GET "http://127.0.0.1:8000/kinfin/counts-by-taxon" \
-H "x-session-id: <session_id>" | jq
```

### 6. Get Cluster Summary

```bash
curl -X GET "http://127.0.0.1:8000/kinfin/cluster-summary/label1" \
-H "x-session-id: <session_id>" | jq
```

### 7. Get Attribute Summary

```bash
curl -X GET "http://127.0.0.1:8000/kinfin/attribute-summary/label1" \
-H "x-session-id: <session_id>" | jq
```

### 8. Get Cluster Metrics

```bash
curl -X GET "http://127.0.0.1:8000/kinfin/cluster-metrics/label1/red" \
-H "x-session-id: <session_id>" | jq
```

### 9. Get Pairwise Analysis

```bash
curl -X GET "http://127.0.0.1:8000/kinfin/pairwise-analysis/label1" \
-H "x-session-id: <session_id>" | jq
```

### 10. Get Plot

```bash
curl -X GET "http://127.0.0.1:8000/kinfin/plot/<plot_type>" \
-H "x-session-id: <session_id>" -o "<filename>.png"
```
