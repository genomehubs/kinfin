<img src="https://cloud.githubusercontent.com/assets/167909/26763490/8f07758a-494b-11e7-8fb7-83b8153f4691.png" width="128">

## Citing KinFin

> [Laetsch DR and Blaxter ML, 2017. KinFin: Software for Taxon-Aware Analysis of Clustered Protein Sequences. G3: Genes, Genomes, Genetics. Doi:10.1534/g3.117.300233](https://doi.org/10.1534/g3.117.300233)

## Dependencies

- UNIX system

## Installation

- Create [Conda](https://conda.io/en/latest/miniconda.html) environment

```
$ conda create -n kinfin -c conda-forge docopt==0.6.2 scipy==0.19.0 matplotlib networkx==1.11 ete3
$ conda activate kinfin
```

- Clone github repo

```
$ git clone https://github.com/DRL/kinfin.git
```

- Run install script for fetching databases

```
$ cd kinfin
$ ./install
```

- Test kinfin

```
$ ./test
```

## Usage

    $ ./kinfin -h

## Documentation

[kinfin.readme.io](https://kinfin.readme.io)

## AI usage declaration

This repository tracks AI usage per user for transparency. Tracking began in November 2026; figures before that date are estimates based on previous usage and proportional development effort.

<!-- AI_PER_USER_METRICS_START -->

### Contributor Development Breakdown

| Developer | Pure Human | Autocomplete | Co-Piloted | Agentic | Last Active Tool |
| :-------- | :--------: | :----------: | :--------: | :-----: | :--------------- |

<!-- AI_PER_USER_METRICS_END -->

### Declaring AI usage in a pull request

1. Run the setup script once per clone. It installs a pre-push hook that reads the declaration file:

```
bash scripts/setup-ai-logs.sh
```

2. Create a `.ai-state.json` file in the repository root describing AI usage for the current PR. AI agents working in this repository should create it too:

```
{
  "autonomy_level": "agentic",
  "phases": ["core_logic", "testing"],
  "tools": ["Claude Code"]
}
```

The file is git-ignored and is not committed. Update its fields for each PR:

- `autonomy_level`: one of `none`, `autocomplete`, `co-piloted`, or `agentic`.
- `phases`: any of `planning`, `core_logic`, `testing` that apply.
- `tools`: names of the AI tools used, e.g. `Claude Code`, `Cursor`.

### No AI usage

If `.ai-state.json` is absent, AI usage is assumed to be none. To declare this explicitly, use:

```
{
  "autonomy_level": "none",
  "phases": [],
  "tools": []
}
```
