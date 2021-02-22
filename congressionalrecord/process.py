import argparse
import datetime
import json
import logging
import re
from pathlib import Path

from tqdm import tqdm

# Estimated from 2010-2020:
# Of the 100 most commonly appearing "titles" in the data, we collect speeches given by
# members of congress (i.e., that have a bioguide_id). We manually inspect the 50 with 
# the lowest unigram entropy and include those that are strictly procedural and have at
# least 10 associated speeches
PROCEDURAL_TITLES = [
    "APPOINTMENT OF ACTING PRESIDENT PRO TEMPORE",
    "HOUR OF MEETING ON TOMORROW",
    "ADJOURNMENT",
    "PLEDGE OF ALLEGIANCE",
    "THE JOURNAL",
    "EXECUTIVE REPORTS OF COMMITTEES",
    "UNANIMOUS CONSENT AGREEMENT--EXECUTIVE CALENDAR",
    "ADJOURNMENT UNTIL 9:30 A.M. TOMORROW",
    "APPOINTMENT",
    "AUTHORITY FOR COMMITTEES TO MEET",
    "PROGRAM",
    "EXECUTIVE REPORTS OF COMMITTEE",
    "PRIVILEGES OF THE FLOOR",
    "APPOINTMENTS",
    "GENERAL LEAVE",
    "ADJOURNMENT UNTIL 10 A.M. TOMORROW",   
]


MONTH_MAP = {
    datetime.date(2020, i, 1).strftime('%B'): f"{i:02}"
    for i in range(1, 13)
}


def load_json(fpath):
    """
    Load a file from json
    Args:
        fpath (string or pathlib.Path object):
            Path to a json file
    Returns:
        python object parsed from json
    """
    with open(fpath, "r") as infile:
        return json.load(infile)


def filter_terms(date, terms):
    """
    Filter the terms a legislator to a date
    Args:
        date (string in YYYY-MM-DD format):
            Date by which to select the term
        terms (list):
            List of dicts, each with a "start" and "end" key in the same format
    Returns:
        First element of `term` that intersects with `date`
    """
    for term in reversed(terms):
        if term["start"] <= date <= term["end"]: 
            return term

    last_term = terms[-1]
    logging.warning(
        f"Legislator's terms do not overlap with {date} "
        f" using most recent term, ending {last_term['end']}"
    )
    return last_term


def process_legislator_data(raw_data):
    """
    Clean & (partially) flatten the legislator data
    Args:
        raw_data (list of nested dictionaries):
            Legislator data from 

    Returns:
        dict where key is Bioguide ID and values are legislator info
    """
    legislator_data = {}
    for leg in raw_data:
        speaker_id = leg["id"]["bioguide"]

        legislator_data[speaker_id] = {
            "first_name": leg["name"]["first"],
            "last_name": leg["name"]["last"],
            "gender": leg["bio"]["gender"],
            
            "terms": leg["terms"],
        }

    return legislator_data

def process_and_speech_data(
    input_paths,
    legislator_data=None,
    output_fpath=None,
    remove_procedural=False,
    restrict_to_gop_dem=False,
    ):
    """
    Clean and save/return speech data matched with the legislator data
    Args:
        input_paths (list of str or pathlib.Path):
            Paths to json speech data
        legislator_data (dict):
            Dictionary mapping bioguide ids to legislator data
        output_fpath (str or pathlib.Path):
            Where to save jsonlist. If not specified, will return a list of dicts
        remove_procedural (bool):
            Remove procedural speeches, as defined by `PROCEDURAL_TITLES`
        restrict_to_gop_dem (bool):
            Keep only Republicans/Democrats, or those who caucus with them (e.g., Sanders)
    Returns:
        None (if `output_fpath` specified), else a list of dicts
    """
    speeches = [] if output_fpath else None
    for i, path in enumerate(tqdm(input_paths)):
        data = load_json(path)

        if remove_procedural and data["title"] in PROCEDURAL_TITLES:
            continue

        # Collect dates
        date = "{year}-{month}-{day}".format(
            year=data["header"]["year"],
            month=MONTH_MAP[data["header"]["month"]],
            day=f"{int(data['header']['day']):02}",
        )
        assert(len(date) == len("XXXX-XX-XX"))

        # Get speech content
        for speech in data["content"]:
            if (
                speech["kind"] == "speech" and 
                speech["speaker_bioguide"] != "None" and 
                speech["speaker_bioguide"]
            ):
                # clean text, which often begins with the speaker name
                text = speech["text"].replace(speech["speaker"], "").lstrip(". ")
                speaker_id = speech["speaker_bioguide"]
                legislator = legislator_data[speaker_id]
                term = filter_terms(date, legislator["terms"])
                
                # set the party
                party = term.get("party", None)
                if restrict_to_gop_dem and party not in ["Republican", "Democrat"]:
                    party = term.get("caucus", None) # set party to caucus
                    if party not in ["Republican", "Democrat"]: # if not matched, drop
                        continue
                    
                clean_data = {
                    # speech info
                    "id": f"{data['id']}_{speech['itemno']}",
                    "source_file": str(path),
                    "title": data["title"],
                    "date": date,
                    "text": re.sub("\s+", " ", text),
                    
                    "chamber": data["header"]["chamber"],

                    # legislator info
                    "speaker_id": speaker_id,
                    "party": party,
                    "first_name": legislator["first_name"],
                    "last_name": legislator["last_name"],
                    "gender": legislator["gender"],
                    "state": term["state"],
                }

                if output_fpath is not None:
                    with open(out_fpath, mode="w" if i == 0 else "a") as outfile:
                        outfile.write(json.dumps(clean_data)+"\n")
                else:
                    speeches.append(clean_data)
    
    return speeches

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--speech_data_dir",
        default="./data",
        help=(
            "Data directory containing congressional record in json format. "
            "expects to be in same format made by `download.py`, i.e., a subfolders "
            "listed by year"
        )
    )
    parser.add_argument(
        "--legislator_data_fpaths",
        nargs="+",
        default=[
            "data/legislators-current.json",
            "data/legislators-historical.json",
        ],
        help=(
            "Legislator json files (each is a list of dictionaries), go to "
            "https://github.com/unitedstates/congress-legislators to download"
        )
    )
    parser.add_argument("--output_dir", default="output")
    parser.add_argument(
        "--start",
        default=None,
        help="Start date, YYYY-MM-DD format, inclusive"
    )
    parser.add_argument(
        "--end",
        default=None,
        help="End date, YYYY-MM-DD format, inclusive"
    )
    parser.add_argument(
        "--remove_procedural_speeches",
        action="store_true",
        default=False,
        help="Remove (some) procedural speeches"
    )
    parser.add_argument(
        "--restrict_to_gop_dem",
        action="store_true",
        default=False,
        help="Keep only Republicans & Democrats, and those who caucus with them"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    Path(args.output_dir).mkdir(exist_ok=True, parents=True)

    # Flatten & clean legislator data
    raw_legislator_data = []
    for path in args.legislator_data_fpaths:
        raw_legislator_data.extend(load_json(path))
    legislator_data = process_legislator_data(raw_legislator_data)

    # Flatten & clean speech data
    speech_paths = list(Path(args.speech_data_dir).glob("[0-9][0-9][0-9][0-9]/**/*.json"))

    # Filter the dates
    dates = [(p, p.parent.parent.name.replace("CREC-", "")) for p in speech_paths]
    start = args.start or min(d for _, d in dates)
    end = args.end or max(d for _, d in dates)
    speech_paths = [p for p, d in dates if start <= d <= end]

    out_fpath = Path(args.output_dir, f"speeches-{start}-to-{end}.jsonl")

    process_and_speech_data(
        input_paths=speech_paths,
        legislator_data=legislator_data,
        output_fpath=out_fpath,
        remove_procedural=args.remove_procedural_speeches,
        restrict_to_gop_dem=args.restrict_to_gop_dem,
    )
