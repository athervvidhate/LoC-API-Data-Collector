# Library of Congress API Data Collector

A Python toolkit and Jupyter notebook for collecting, processing, and exporting historical U.S. presidential campaign data from the Library of Congress (LoC) Chronicling America API.

---

## Features
- **Automated Data Collection:** Fetches campaign-related newspaper articles for U.S. presidential candidates using the LoC API.
- **Checkpointing:** Supports resuming long downloads to avoid data loss.
- **Flexible Input:** Reads candidate and year data from Excel files.
- **Rich Output:** Exports results as a CSV with candidate, date, location, and full text fields.
- **Jupyter Notebook:** Interactive exploration and demonstration of the data pipeline.

---

## Requirements
- Python 3.8+
- pandas
- numpy
- requests
- openpyxl (for Excel support)
- pickle (standard library)

Install dependencies:
```bash
pip install pandas numpy requests openpyxl
```

---

## File Descriptions
- `aggregator.py` — Main script for batch data collection and export.
- `aggregator.ipynb` — Jupyter notebook for interactive use and demonstration.
- `PresidentialCandidates_Wikipedia.xlsx` — Example input file listing candidates and years.
- `LOC_Presidential_Candidates_Complete_Data.csv` — Output file (created after running the script).

---

## Usage

### 1. Prepare Input
Edit or create an Excel file (e.g., `PresidentialCandidates_Wikipedia.xlsx`) with columns:
- `Year`
- `Candidate_var1`, `Candidate_var2`, `Candidate_var3`, `Candidate_var4`

Each row should represent a presidential election year and up to four candidate name variants.

### 2. Run the Script
```bash
python aggregator.py PresidentialCandidates_Wikipedia.xlsx
```
- The script will fetch data for each candidate and save the results to `LOC_Presidential_Candidates_Complete_Data.csv`.
- Checkpoint files (`*.pkl`) are created to allow resuming if interrupted.
- Optionally, you can delete the checkpoint folder after successful data collection by using the `--delete-pkl` flag:
  ```bash
  python aggregator.py PresidentialCandidates_Wikipedia.xlsx --delete-pkl
  ```

### 3. Use the Notebook
Open `aggregator.ipynb` in Jupyter or Colab for step-by-step data collection, exploration, and visualization.

---

## Output
The main output is a CSV file with columns:
- `name`: Candidate name
- `library_of_congress_control_number`: LoC document ID
- `date`: Document/publication date
- `location_city`: City of publication
- `location_state`: State of publication
- `page_number`: Page number of the document
- `full_text`: OCR'd newspaper text

---

## FAQ

**Q: What does this project do?**
A: It automates the retrieval of historical newspaper articles about U.S. presidential campaigns from the Library of Congress, based on candidate names and years you provide.

**Q: What input format is required?**
A: An Excel file with columns for `Year` and up to four candidate name variants per row. See the provided `PresidentialCandidates_Wikipedia.xlsx` for an example.

**Q: How do I resume a stopped or interrupted run?**
A: The script automatically saves progress in checkpoint files (`*.pkl`). If you rerun the script, it will resume from the last checkpoint.

**Q: What if I get HTTP 429 (Too Many Requests) errors?**
A: The script will pause and retry, but if the error persists, it will stop early. You can rerun the script later to continue.

**Q: Can I use this in Google Colab?**
A: Yes! The notebook includes commented code for mounting Google Drive and changing directories. Uncomment and adjust as needed.

**Q: Where is the data saved?**
A: The final CSV is saved in the current working directory as `LOC_Presidential_Candidates_Complete_Data.csv`. Checkpoints are saved as `*.pkl` files.

**Q: How do I add more candidates or years?**
A: Add rows to your Excel file with the desired years and candidate names, then rerun the script.

**Q: How do I add more columns/variables to the final output CSV?**
A: To add additional columns, you need to modify the `get_full_text` function in `aggregator.py`. This function extracts data from the API response. Here's how you can do it:

1. **Identify the JSON Response Structure:**
   The API returns a JSON object with various fields. You can explore the full JSON response by visiting any Chronicling America Document JSON API URL (e.g., [https://www.loc.gov/resource/sn83030007/1788-10-13/ed-1/?sp=2&q=George+Washington&fo=json](https://www.loc.gov/resource/sn83030007/1788-10-13/ed-1/?sp=2&q=George+Washington&fo=json)) to see all available fields.

2. **Modify the `get_full_text` Function:**
   In `aggregator.py`, locate the `get_full_text` function. You will see a section where the JSON response is processed. For example, to add a new field, you can extract it from the JSON response like this:

   ```python
   # Example: Extracting a new field from the JSON response
   new_field = data.get("new_field_name", None)
   ```

   Replace `"new_field_name"` with the actual field name from the JSON response.

3. **Update the DataFrame Creation:**
   After extracting the new field, you need to include it in the list of items that are appended to the `items` list. For example:

   ```python
   items.append([candidate_name if candidate_name else None, loc_control_number, date, location_city, location_state, page_number, new_field, full_text])
   ```

4. **Update the DataFrame Columns:**
   Finally, when creating the DataFrame in the `complete_candidates_collector` function, add the new column name to the `columns` list:

   ```python
   df = pd.DataFrame(flattened, columns=['name', 'library_of_congress_control_number', 'date', 'location_city', 'location_state', 'page_number', 'new_field', 'full_text'])
   ```

Make sure to test the changes to ensure the new fields are correctly extracted and included in the final output.

---

## License
This project is for academic and research use. Please cite appropriately if used in publications.