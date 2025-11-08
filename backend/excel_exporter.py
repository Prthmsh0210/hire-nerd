import pandas as pd
from typing import List, Dict, Any
import os
from datetime import datetime

from database import logger

REPORTS_DIR_BASE = "static" # Excel files will be served from /static/reports/
REPORTS_SUBDIR = "reports"
FULL_REPORTS_DIR = os.path.join(REPORTS_DIR_BASE, REPORTS_SUBDIR)

os.makedirs(FULL_REPORTS_DIR, exist_ok=True) # Ensure directory exists

def export_to_excel(match_results: List[Dict[str, Any]]) -> str:
    """
    Exports the matching results to an Excel file.
    Returns the web-accessible path to the file.
    """
    if not match_results:
        logger.warning("No match results to export to Excel.")
        return ""

    try:
        # Prepare data for DataFrame
        export_data = []
        for res in match_results:
            export_data.append({
                "Candidate Name": res.get("name", "N/A"),
                "JD Fit (%)": res.get("jdFit", 0),
                "Interview Score (X/5)": res.get("interviewScore", 0),
                "Red Flags": ", ".join(res.get("redFlags", []) if res.get("redFlags") else ["None"]),
                "Experience Summary": res.get("experienceSummary", "N/A"),
                "Original Filename": res.get("original_filename", "N/A")
            })

        df = pd.DataFrame(export_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"MatchedCandidates_{timestamp}.xlsx"
        excel_filepath_system = os.path.join(FULL_REPORTS_DIR, excel_filename)
        
        # Use openpyxl engine for .xlsx format
        df.to_excel(excel_filepath_system, index=False, engine='openpyxl')
        
        logger.info(f"Successfully exported results to {excel_filepath_system}")
        
        # Return web-accessible path
        excel_url_path = f"/{REPORTS_DIR_BASE}/{REPORTS_SUBDIR}/{excel_filename}"
        return excel_url_path

    except Exception as e:
        logger.error(f"Error exporting to Excel: {e}")
        return ""