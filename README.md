<img src="https://cloud.githubusercontent.com/assets/167909/26763490/8f07758a-494b-11e7-8fb7-83b8153f4691.png" width="128">

## Citing KinFin

> [Laetsch DR and Blaxter ML, 2017. KinFin: Software for Taxon-Aware Analysis of Clustered Protein Sequences. G3: Genes, Genomes, Genetics. Doi:10.1534/g3.117.300233](https://doi.org/10.1534/g3.117.300233)

## Dependencies

- UNIX system

## Quick Start (Recommended with Dev Container)

For the easiest setup with a fully isolated development environment, use our **development container** setup:

1. **Prerequisites:**
   - [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - [VS Code](https://code.visualstudio.com/) with [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

2. **Setup:**

   ```bash
   git clone https://github.com/DRL/kinfin.git
   cd kinfin
   ```

   - Open this folder in VS Code
   - Click "Reopen in Container" when prompted (or use Command Palette: `Dev Containers: Reopen in Container`)
   - VS Code automatically installs all dependencies

3. **Run:**
   ```bash
   python -m src.main          # Backend
   cd src/ui && npm run dev    # Frontend (in another terminal)
   ```

**Benefits:**

- ✅ All dependencies pre-configured (Python 3.11, Node.js 20, system tools)
- ✅ Project databases automatically initialized
- ✅ Isolated from your system Python/Node installations
- ✅ Sandboxed environment when using AI agents

For detailed info (including AI agent safety), see [`.devcontainer/README.md`](.devcontainer/README.md).

## Traditional Installation

Alternatively, install using Conda (manual setup):

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
