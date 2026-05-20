### git
$ git clone https://github.com/genomehubs/kinfin.git
$ cd genomehubs-kinfin/
$ git checkout new_cli
$ cd genomehubs-kinfin/src_new

### create pyenv (or uv)
$ pyenv virtualenv kinfin

### install dependencies
$ pip install -r genomehubs-kinfin/src_new/requirements.txt

### edit config file 
# missing value = NA

### analysis
### adjust paths to your setup
$ python genomehubs-kinfin/src_new/src/main.py analysis -g orthogroups.txt -c config.csv -f fastas/ -d psyche_output -X -r family -p 10 -N -v

### convert (feather to tsv)
$ python genomehubs-kinfin/src_new/src/main.py convert -t FILE.feather -F tsv