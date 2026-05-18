# 0. install requirement (i cleaned them up)
```
pip install -r requirements.txt
```

# 1. uncompress tgz's in test

# 2. run examples

```
KINFIN="/Users/dom/git/genomehubs-kinfin/src_new"

# leps
OUTDIR="/Users/dom/data/leps"
python $KINFIN/src/main.py analysis -g $KINFIN/test/leps.orthogroups.txt  -c $KINFIN/test/leps.config.csv -p 10 -v -I -N -P -d $OUTDIR

# nems
OUTDIR="/Users/dom/data/nems"
python $KINFIN/src/main.py analysis -g $KINFIN/test/nematodes.orthogroups.txt  -c $KINFIN/test/nematodes.config.csv -i $KINFIN/test/nematodes.interproscan.tsv -f $KINFIN/test/nematodes_fastas -t $KINFIN/test/nematodes.tree.nwk -o CELEG CBRIG -p 10 -v -N -d $OUTDIR
```