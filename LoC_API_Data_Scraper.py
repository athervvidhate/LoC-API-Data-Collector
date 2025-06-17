import time
import re
import json
from urllib.request import urlopen
import requests
import pandas as pd
import pickle
from requests.exceptions import ChunkedEncodingError, RequestException, HTTPError
import numpy as np
import os

# If running in Colab, you may need to mount Google Drive and set working directory
# from google.colab import drive
# drive.mount('/content/drive/')
# os.chdir("drive/My Drive/Rallies")

def get_ids_custom(url, items=[], params={"fo": "json", "c": 100, "at": "results,pagination"}):
    """
    Retrieves all item IDs from the LOC API, handling pagination.

    Args:
        url (str): The base URL for the API request.
        items (list, optional): A list to append fetched IDs to. Defaults to [].
        params (dict, optional): API request parameters. Defaults to {"fo": "json", "c": 100, "at": "results,pagination"}.

    Returns:
        list: The list 'items' populated with all retrieved IDs.
    """
    r = requests.get(url, params=params)
    r.raise_for_status()
    for result in r.json()['results']:
        items.append(result.get('id'))
    next_page = r.json()['pagination'].get('next')
    count = 0
    while next_page:
        try:
            r = requests.get(next_page, params=params)
            r.raise_for_status()
            for result in r.json()['results']:
                items.append(result.get('id'))
            next_page = r.json()['pagination'].get('next')
            print(f"Fetched {len(items)} items so far...")
            if count % 2 == 0:
                print('Waiting for 5 seconds...')
                time.sleep(5)
            count += 1
        except ChunkedEncodingError:
            print(f"ChunkedEncodingError encountered for {url}. Retrying after 15 seconds...")
            time.sleep(15)
            try:
                call_retry = requests.get(next_page, params=params)
                call_retry.raise_for_status()
                data = call_retry.json()
                text = data.get('full_text')
                items.append(text)
                print(f"Successfully downloaded result {next_page} on retry. Waiting 5 seconds...")
                time.sleep(5)
            except (RequestException, HTTPError, ChunkedEncodingError) as retry_err:
                print(f"Retry failed for {next_page}. Skipping. Error: {retry_err}")
                items.append(np.nan)
                continue
            except Exception as retry_e:
                print(f"Retry failed during processing for {url}. Skipping. Error: {retry_e}")
                items.append(np.nan)
                continue
        except HTTPError as http_err:
            if http_err.response.status_code == 429:
                print(f'Too many requests (429) when accessing {url}. Stopping early.')
                print(f'Current number of requests: {len(items)}.')
                pagination = r.json()['pagination'].get('current')
                print(f'Current pagination: {pagination}')
                break
            else:
                print(f"HTTP error for {next_page}: {http_err}. Skipping.")
                items.append(np.nan)
                continue
    return items

def get_full_text(results, checkpoint_path="loc_full_text.pkl", sleep_time=4, checkpoint_interval=100, checkpoint_time_interval=600, candidate_name=None):
    """
    Fetches full text and specified metadata from a list of LoC URLs, with automatic checkpointing.

    Args:
      results (list): List of URLs to fetch.
      checkpoint_path (str): Path to checkpoint file.
      sleep_time (int): Seconds to wait between successful requests.
      checkpoint_interval (int): Save after this many downloads.
      checkpoint_time_interval (int): Save after this many seconds have elapsed.
      candidate_name (str, optional): Name of the candidate being processed.
    Returns:
      list: A list of lists, where each inner list contains [full_text, library_of_congress_control_number, location_city, location_state].
            None or np.nan will be used for failures or missing data.
    """
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, "rb") as f:
            items = pickle.load(f)
        start_idx = len(items)
        print(f"Resuming from checkpoint: {start_idx}/{len(results)} already done.")
    else:
        items = []
        start_idx = 0
        print("No checkpoint found; starting from scratch.")
    last_save_time = time.time()
    for i in range(start_idx, len(results)):
        url = results[i]
        print(f"[{i+1}/{len(results)}] Downloading {url}")
        full_text = None
        loc_control_number = None
        location_city = None
        location_state = None
        date = None
        try:
            resp = requests.get(url, params={"fo": "json"})
            resp.raise_for_status()
            data = resp.json()
            item_data = data.get("item", {})
            full_text = data.get("full_text", None)
            loc_control_number = item_data.get("library_of_congress_control_number", None)
            city_list = item_data.get("location_city", None)
            if city_list and isinstance(city_list, list):
                location_city = city_list[0]
            state_list = item_data.get("location_state", None)
            if state_list and isinstance(state_list, list):
                location_state = state_list[0]
            date = item_data.get("date", None)
            items.append([candidate_name if candidate_name else None, loc_control_number, date, location_city, location_state, full_text])
        except ChunkedEncodingError:
            print("  ChunkedEncodingError; retrying in 15s…")
            time.sleep(15)
            try:
                resp = requests.get(url, params={"fo": "json"})
                resp.raise_for_status()
                data = resp.json()
                item_data = data.get("item", {})
                full_text = data.get("full_text", None)
                loc_control_number = item_data.get("library_of_congress_control_number", None)
                city_list = item_data.get("location_city", [])
                location_city = city_list[0] if city_list and isinstance(city_list, list) else None
                state_list = item_data.get("location_state", [])
                location_state = state_list[0] if state_list and isinstance(state_list, list) else None
                date = item_data.get("date", None)
                items.append([candidate_name if candidate_name else None, loc_control_number, date, location_city, location_state, full_text])
            except Exception as e:
                print(f"  Retry failed: {e}. Appending np.nan for all fields.")
                items.append([np.nan, np.nan, np.nan, np.nan])
        except HTTPError as http_err:
            if http_err.response.status_code == 429:
                print("  429 Too Many Requests—stopping early.")
                break
            else:
                print(f"  HTTPError ({http_err.response.status_code}); skipping.")
                items.append([np.nan, np.nan, np.nan, np.nan])
        except RequestException as req_err:
            print(f"  RequestException: {req_err}; skipping.")
            items.append([None, None, None, None])
        except Exception as e:
            print(f"  Unexpected error: {e}; skipping.")
            items.append([np.nan, np.nan, np.nan, np.nan])
        print(f"  Done. Sleeping {sleep_time}s…")
        time.sleep(sleep_time)
        now = time.time()
        needs_save = (
            (i + 1) % checkpoint_interval == 0
            or (now - last_save_time) >= checkpoint_time_interval
        )
        if needs_save:
            with open(checkpoint_path, "wb") as f:
                pickle.dump(items, f)
            print(f"  ⇒ Checkpoint saved at index {i+1}.")
            last_save_time = now
    with open(checkpoint_path, "wb") as f:
        pickle.dump(items, f)
    print("All done. Final checkpoint written.")
    return items

# This function is not used in the final code, but is kept for reference
def to_link(row):
    """
    Generates a Chronicling America URL based on a row from regex extracted link DataFrame.

    Args:
        row (pd.Series): A row from prelink DataFrame with '0', '1', '2' as column names.

    Returns:
        str: The Chronicling America URL.
    """
    base_url = 'http://www.loc.gov/resource/'
    sn = row[2]
    date = row[0]
    page = row[1]
    url = f"{base_url}{sn}/{date}/ed-1/"
    if page is not None:
        url += f"?sp={page}"
    return url

def candidate_aggregator(file_name):
    """
    Generates a list of Chronicling America URLs for searching candidate names from an Excel file.

    Args:
      file_name (str): The path to the Excel file containing 'Year' and
                       'Candidate_var1' through 'Candidate_var4' columns.

    Returns:
      list: A list of strings, where each string is a fully constructed URL
            for a Chronicling America search query.
    """
    name_cols = [f'Candidate_var{i}' for i in range(1, 5)]
    df = pd.read_excel(file_name, usecols=['Year'] + name_cols)
    base_url = (
        "https://www.loc.gov/collections/chronicling-america/?dl=page"
        "&start_date={year}-07-01&end_date={year}-11-15"
        "&qs={terms}&ops={ops}&searchType=advanced&fo=json"
    )
    queries = []
    for row in df.itertuples(index=False):
        year = int(row.Year)
        names = [
            str(getattr(row, col)).replace(" ", "+")
            for col in name_cols
            if pd.notnull(getattr(row, col)) and not isinstance(getattr(row, col), int)
        ]
        terms = "+".join(f'"{n}"' for n in names)
        ops = '""' if len(names) == 1 else "OR"
        queries.append(base_url.format(year=year, terms=terms, ops=ops))
    return queries

def create_filename(url_string):
    """
    Extracts start date, end date, and a modified name from a URL string
    and combines them into a filename format 'name_startdate_end_date'.

    Args:
      url_string (str): The url to extract the name, start date, and end date from.

    Returns:
      str: A filename in the format 'name_startdate_end_date'.
    """
    start_date_match = re.search(r"start_date=(\d{4}-\d{2}-\d{2})", url_string)
    end_date_match = re.search(r"end_date=(\d{4}-\d{2}-\d{2})", url_string)
    name_match = re.search(r'qs="([^"]+)"', url_string)
    start_date = start_date_match.group(1) if start_date_match else None
    end_date = end_date_match.group(1) if end_date_match else None
    name = name_match.group(1) if name_match else None
    if name:
        name = name.replace('+', '_')
    if start_date and end_date and name:
        return [f"{name}_{start_date}_{end_date}", name]
    else:
        return "Could not extract all required information."

def flatten_triple_nested_array(triple_nested_array):
    """
    Flattens a triple-nested list into a single-nested list of document information.


    Args:
        triple_nested_array (list): A list of lists, where the innermost lists
                                     contain four elements: full text (str),
                                     document ID (str), city (str), and state (str).

    Returns:
        list: A single-nested list where each sublist represents a document's
              information (full text, id, city, state).
    """
    flattened_data = []
    for candidate_docs in triple_nested_array:
        for doc_info in candidate_docs:
            flattened_data.append(doc_info)
    return flattened_data

def complete_candidates_collector(xlsx):
    """
    Collects and processes Library of Congress data for presidential candidates.
    This function orchestrates the entire data collection pipeline for presidential
    candidates. It starts by generating search URLs from an Excel file, then
    iterates through each candidate to collect document IDs and their full text
    from the Library of Congress. Finally, it flattens the collected data and
    saves it to a CSV file.

    Args:
        xlsx (str): The path to the Excel file containing candidate information
                    (e.g., 'RawData/AmericanStories/PresidentialCandidates_Wikipedia.xlsx').

    Returns:
        None: The function saves the processed data to a CSV file named
                'LOC_Presidential_Candidates_Complete_Data.csv' and does not return
                any value.
    """
    print('Creating all links from inputted file...')
    search_urls = candidate_aggregator(xlsx)
    num_candidates = len(search_urls)
    print(f'Done. Created {num_candidates} links.')
    all_ids = []
    for url in search_urls:
        ids = []
        filename = create_filename(url)
        print(f'Starting ID Collection for Candidate {filename[0]}\n')
        get_ids_custom(url, items=ids)
        texts = get_full_text(ids, checkpoint_path=f'{filename[0]}.pkl', candidate_name=filename[1])
        all_ids.append(texts)
        print(f'\nFinished ID Collection for Candidate {filename[0]}')
    print('All Data Collected. Concatenating all texts into DataFrame...')
    flattened = flatten_triple_nested_array(all_ids)
    df = pd.DataFrame(flattened, columns=['name', 'library_of_congress_control_number', 'date', 'location_city', 'location_state', 'full_text'])
    df.to_csv('LOC_Presidential_Candidates_Complete_Data.csv')
    print("Done. Saved all data to 'LOC_Presidential_Candidates_Complete_Data.csv'")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LoC API Data Scraper for Presidential Candidates")
    parser.add_argument('xlsx', type=str, help='Path to the Excel file with candidate info (e.g., RawData/AmericanStories/PresidentialCandidates_Wikipedia.xlsx)')
    args = parser.parse_args()

    complete_candidates_collector(args.xlsx) 