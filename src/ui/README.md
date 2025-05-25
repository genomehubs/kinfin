# Kinfin UI

This repository provides the frontend interface for Kinfin, which can be used to run and visualize analyses. Below are the instructions to run Kinfin locally, set up the environment, and execute the necessary requests.

## Prerequisites

- **Node.js** (v14 or later)
- **npm** (v6 or later)
- **Curl** (to execute API requests)
- **jq** (for JSON processing)

## Setup Instructions

**Clone the repository:**

Clone the `kinfin_ui` repository from GitHub:

```bash
git clone https://github.com/heisdinesh/kinfin_ui.git
```

```bash
cd kinfin_ui
```

```
npm i --legacy-peer-deps
```

## Run Kinfin locally:

You can now run Kinfin locally. Refer to the official documentation for more details on how to run Kinfin:

[Kinfin Getting Started](https://github.com/genomehubs/kinfin/blob/master/docs/getting-started.md)

## Execute the Request

Once you have Kinfin running locally, you'll need to execute a `POST` request to initialize the system with a hardcoded configuration.

### Curl Command:

Execute the following `curl` command to initialize Kinfin:

````curl -X POST "$KINFIN_HOST/kinfin/init"
-H "Content-Type: application/json"
-d '{ "config": [ {"taxon": "CBRIG", "clade": "CBRIG", "host": "outgroup"}, {"taxon": "DMEDI", "clade": "DMEDI", "host": "human"}, {"taxon": "LSIGM", "clade": "n16", "host": "other"}, {"taxon": "AVITE", "clade": "n16", "host": "other"}, {"taxon": "CELEG", "clade": "CELEG", "host": "outgroup"}, {"taxon": "EELAP", "clade": "n16", "host": "other"}, {"taxon": "OOCHE2", "clade": "OOCHE2", "host": "other"}, {"taxon": "OFLEX", "clade": "n11", "host": "other"}, {"taxon": "LOA2", "clade": "n15", "host": "human"}, {"taxon": "SLABI", "clade": "SLABI", "host": "other"}, {"taxon": "BMALA", "clade": "n15", "host": "human"}, {"taxon": "DIMMI", "clade": "n11", "host": "other"}, {"taxon": "WBANC2", "clade": "n15", "host": "human"}, {"taxon": "TCALL", "clade": "TCALL", "host": "other"}, {"taxon": "OOCHE1", "clade": "n11", "host": "other"}, {"taxon": "BPAHA", "clade": "n15", "host": "other"}, {"taxon": "OVOLV", "clade": "n11", "host": "human"}, {"taxon": "WBANC1", "clade": "WBANC1", "host": "human"}, {"taxon": "LOA1", "clade": "LOA1", "host": "human"} ] }' | jq```
````

## Viewing the Dashboard

After executing the request:

1. Open the UI.
2. Click on the **Dashboard** button.
3. You should now see the Kinfin analysis.

## Notes

- Currently, the configuration is hardcoded.
- In the next few days, the configuration will be made fully dynamic.

---

This document provides a step-by-step guide to running Kinfin UI and initializing the analysis. Future updates will include dynamic configurations.
