[![Build Status](https://travis-ci.org/unitedstates/congressional-record.png)](https://travis-ci.org/unitedstates/congressional-record)

# congressional-record

This tool converts HTML files containing the text of the Congressional Record into structured text data. It is particularly useful for identifying speeches by members of Congress.

From the repository root, type ``python -m congressionalrecord.cli -h`` for instructions.

* It outputs JSON
* Instances of speech are tagged with the speaker's bioguideid wherever possible
* Instances of speech are recorded as "turns," such that each subsequent instance of speech by a Member counts as a new "turn." 

This software is released as-is under the BSD3 License, with no warranty of any kind.

# Installation

In Python 3 using `conda` for e.g.:

```
git clone https://github.com/unitedstates/congressional-record.git
cd congressional-record
conda create -n congressional python=3.8
conda activate congressional
pip install -e .
```

# Download data

Use `python -m congressionalrecord.download -h` to see usage instructions

# Processing data into a jsonlist 

After having downloaded the data *in the json format* as above, you can combine it
with legislator information to create a list of json objects. Requires you to download
legislator information, both [historical](https://theunitedstates.io/congress-legislators/legislators-historical.json) and [current](https://theunitedstates.io/congress-legislators/legislators-current.json). Place them in the same directory.

See `python congressionalrecord/process -h`

# Recommended citation:

Judd, Nicholas, Dan Drinkard, Jeremy Carbaugh, and Lindsay Young. *congressional-record: A parser for the Congressional Record.* Chicago, IL: 2017.
