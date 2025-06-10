# 🧬 Kinfin UI – Local Setup Guide

This repository provides the frontend interface for **Kinfin**, which allows users to run and visualize biological analyses. This guide outlines how to set up and run Kinfin UI and backend locally, using test data.

---

## 📋 Prerequisites

Ensure the following are installed on your system:

- **Node.js** (v14 or later)
- **npm** (v6 or later)
- **Python** (v3.7 or later)
- **Curl** (to download test data)
- **jq** (for JSON processing)

---

## 🔧 1. Clone the Repository

```bash
git clone https://github.com/genomehubs/kinfin.git
cd kinfin
```

## 📂 2. Download and Extract Test Data

```bash
export WORKDIR=~/tmp/kinfin
mkdir -p $WORKDIR
cd $WORKDIR

curl -L http://molluscdb.cog.sanger.ac.uk/dev/kinfin/api_test_data.tar.gz -o api_test_data.tar.gz
tar -xzf api_test_data.tar.gz
rm api_test_data.tar.gz
```

## 🧪 3. Setup and Start the Backend API

In a new terminal navigate back to the Kinfin root directory and install Python dependencies:

```bash
cd ~/kinfin
pip install -r requirements.txt
```

Start the backend API:

```bash
export KINFIN_PORT=8000
export CLUSTER_FILE_PATH=$WORKDIR/api_test_data/Orthogroups.txt
export SEQUENCE_IDS_FILE_PATH=$WORKDIR/api_test_data/kinfin.SequenceIDs.txt
export TAXON_IDX_MAPPING_FILE_PATH=$WORKDIR/api_test_data/taxon_idx_mapping.json
export RESULTS_BASE_DIR=$WORKDIR/output
export SESSION_INACTIVITY_THRESHOLD=24  # Files retained for 24 hours

./src/main.py serve -p $KINFIN_PORT
```

## ⚙️ 4. Setup the Frontend (Kinfin UI)

Open a new terminal and start the frontend:

```bash
cd src/ui
npm install --legacy-peer-deps
```

Create a .env file based on .env.dist:

```bash
cp .env.dist .env
# Edit the .env file if needed
```

```bash
npm run dev
```

## 📊 6. Access the Dashboard

- Once both frontend and backend are running:
- Open your browser and visit: http://localhost:5173/define-node-labels
- Create a file called node_labels.json and paste the following content into it:
- Use the upload feature to upload node_labels.json.
- Visit http://localhost:5173/6599179a64accf331ffe653db00a0e24/dashboard after 1-2 min to see the results.

```bash
[
  {
    "taxon": "CBRIG",
    "clade": "CBRIG",
    "host": "outgroup"
  },
  {
    "taxon": "DMEDI",
    "clade": "DMEDI",
    "host": "human"
  },
  {
    "taxon": "LSIGM",
    "clade": "n16",
    "host": "other"
  },
  {
    "taxon": "AVITE",
    "clade": "n16",
    "host": "other"
  },
  {
    "taxon": "CELEG",
    "clade": "CELEG",
    "host": "outgroup"
  },
  {
    "taxon": "EELAP",
    "clade": "n16",
    "host": "other"
  },
  {
    "taxon": "OOCHE2",
    "clade": "OOCHE2",
    "host": "other"
  },
  {
    "taxon": "OFLEX",
    "clade": "n11",
    "host": "other"
  },
  {
    "taxon": "LOA2",
    "clade": "n15",
    "host": "human"
  },
  {
    "taxon": "SLABI",
    "clade": "SLABI",
    "host": "other"
  },
  {
    "taxon": "BMALA",
    "clade": "n15",
    "host": "human"
  },
  {
    "taxon": "DIMMI",
    "clade": "n11",
    "host": "other"
  },
  {
    "taxon": "WBANC2",
    "clade": "n15",
    "host": "human"
  },
  {
    "taxon": "TCALL",
    "clade": "TCALL",
    "host": "other"
  },
  {
    "taxon": "OOCHE1",
    "clade": "n11",
    "host": "other"
  },
  {
    "taxon": "BPAHA",
    "clade": "n15",
    "host": "other"
  },
  {
    "taxon": "OVOLV",
    "clade": "n11",
    "host": "human"
  },
  {
    "taxon": "WBANC1",
    "clade": "WBANC1",
    "host": "human"
  },
  {
    "taxon": "LOA1",
    "clade": "LOA1",
    "host": "human"
  }
]

```
