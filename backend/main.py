# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import uuid
from datetime import datetime, timedelta, timezone # Added timezone
from bson import ObjectId
from typing import List, Any, Dict, Tuple
import io
import base64
from email.mime.text import MIMEText
from pydantic import EmailStr, ValidationError # Import ValidationError for explicit catch

# --- Google API Imports ---
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- EARLY PANDAS IMPORT ---
try:
    from excel_exporter import export_to_excel
    print("DEBUG: Successfully imported excel_exporter (pandas) early.")
except Exception as e:
    print(f"DEBUG: FAILED to import excel_exporter (pandas) early: {e}")

# --- Application Specific Imports ---
from jd_parser import parse_jd_file
from resume_parser import parse_resumes
from match_engine import match_resumes_to_jd

# Import from database.py
from database import (
    db_manager,
    JobDescriptionDB,
    ResumeDB,
    MatchResultDB,
    ScheduledInterviewDB, 
    logger
)

STATIC_DIR = "static"

app = FastAPI(
    title="HisbandHR.ai Backend",
    description="API for Resume-JD Matching and Google Services Integration",
    version="1.7.1" 
)

# --- Google API Configuration ---
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' 
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.file'
]
# --- End Google API Configuration ---


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

app.mount(f"/{STATIC_DIR}", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup_db_client():
    await db_manager.connect_to_database()
    if db_manager.db is None:
        logger.critical("CRITICAL: Database connection failed on startup. Application may not function correctly.")
    else:
        logger.info("Database client started and connection appears successful.")

@app.on_event("shutdown")
async def shutdown_db_client():
    await db_manager.close_database_connection()

# --- Google API Helper Functions ---
def get_user_credentials():
    if os.path.exists('token.json'):
        return Credentials.from_authorized_user_file('token.json', SCOPES)
    return None

async def _get_or_create_folder_id(service, folder_name: str) -> str:
    # This function seems unused in the current context, but keeping it for completeness
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and 'root' in parents and trashed = false"
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    
    if response.get('files'):
        return response.get('files')[0].get('id')
    else:
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
# --- End Google API Helper Functions ---


# --- Google OAuth 2.0 Flow Endpoints ---
@app.get("/authorize")
async def authorize():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = 'http://localhost:8000/callback' 
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent', 
        include_granted_scopes='true'
    )
    return RedirectResponse(authorization_url)

@app.get("/callback")
async def callback(request: Request):
    state = request.query_params.get('state')
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = 'http://localhost:8000/callback'
    
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)

    creds = flow.credentials
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    # Redirect to the frontend app's main page or a specific success page
    return RedirectResponse(url="http://localhost:5173/app?auth=success") 


# --- Google API Action Endpoints ---
@app.post("/api/schedule-interview", summary="Schedules an interview on Google Calendar and stores it")
async def schedule_interview(
    candidate_name: str = Form(...),
    candidate_email: EmailStr = Form(...), # FastAPI/Pydantic validates this Form input to be EmailStr compatible string
    interviewer_emails_str: str = Form(..., alias="interviewer_emails"), 
    start_time_str: str = Form(..., alias="start_time"), 
    duration_minutes: int = Form(...) 
):
    creds = get_user_credentials()
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest())
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                logger.info("Google credentials refreshed.")
            except Exception as refresh_err:
                logger.error(f"Error refreshing Google credentials: {refresh_err}")
                auth_url_for_user = "http://localhost:8000/authorize"
                raise HTTPException(status_code=401, detail=f"Failed to refresh credentials. Please re-authorize via {auth_url_for_user}")
        else:
            logger.warning("Authentication required for scheduling.")
            auth_url_for_user = "http://localhost:8000/authorize"
            raise HTTPException(status_code=401, detail=f"User not authenticated. Please authorize via {auth_url_for_user}")

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Split and strip interviewer emails. Pydantic will validate them when creating ScheduledInterviewDB.
        interviewer_email_list_strings: List[str] = [
            email.strip() for email in interviewer_emails_str.split(',') if email.strip()
        ]
        if not interviewer_email_list_strings:
            raise HTTPException(status_code=422, detail="At least one interviewer email is required.")

        try:
            # Ensure start_time_str is parsed correctly. Google API expects ISO format.
            # Frontend sends datetime-local input which is usually `YYYY-MM-DDTHH:MM`.
            # This is compatible with fromisoformat if it has no Z or offset.
            start_datetime_obj_naive = datetime.fromisoformat(start_time_str)
            # IMPORTANT: Assume frontend sends local time. Convert to UTC for Google Calendar.
            # For simplicity, let's assume the server's local timezone is what the user meant.
            # A more robust solution would involve getting timezone from frontend or user profile.
            start_datetime_obj_local = start_datetime_obj_naive.astimezone() # Convert to server's local timezone
            start_datetime_obj_utc = start_datetime_obj_local.astimezone(timezone.utc) # Convert to UTC
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid start_time format. Expected YYYY-MM-DDTHH:MM.")

        end_datetime_obj_utc = start_datetime_obj_utc + timedelta(minutes=duration_minutes)

        # For Google API, emails must be strings. candidate_email is already a validated string.
        google_api_attendees = [{'email': str(candidate_email)}] # Convert EmailStr to str
        google_api_attendees.extend([{'email': email} for email in interviewer_email_list_strings])

        event_body_for_google = {
            'summary': f'Interview: {candidate_name}',
            'description': f'Interview with {candidate_name}. Scheduled via HisbandHR.ai.',
            'start': {'dateTime': start_datetime_obj_utc.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end_datetime_obj_utc.isoformat(), 'timeZone': 'UTC'},
            'attendees': google_api_attendees,
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            },
            'reminders': {'useDefault': True},
        }
        
        created_event = service.events().insert(
            calendarId='primary', 
            body=event_body_for_google, 
            sendUpdates='all', 
            conferenceDataVersion=1
        ).execute()

        meet_link = created_event.get('hangoutLink')
        calendar_link = created_event.get('htmlLink')
        logger.info(f"Successfully created event with Meet link: {meet_link}")
        
        # Store in MongoDB. Pydantic will validate here.
        scheduled_interview_doc_data = {
            "candidate_name": candidate_name,
            "candidate_email": str(candidate_email), # Store as string
            "interviewer_emails": interviewer_email_list_strings, # List of strings
            "start_time": start_datetime_obj_utc, # Store as UTC datetime
            "end_time": end_datetime_obj_utc,     # Store as UTC datetime
            "duration_minutes": duration_minutes,
            "google_meet_link": meet_link,
            "google_calendar_link": calendar_link
        }
        # Pydantic model instantiation will validate the data
        scheduled_interview_doc = ScheduledInterviewDB(**scheduled_interview_doc_data)
        
        scheduled_interviews_collection = db_manager.get_collection("scheduled_interviews")
        if scheduled_interviews_collection is None:
            logger.error("scheduled_interviews collection not available.")
            raise HTTPException(status_code=500, detail="Interview scheduled in Google but failed to save to local DB.")
        
        await scheduled_interviews_collection.insert_one(scheduled_interview_doc.model_dump(by_alias=True, exclude_none=True))
        logger.info(f"Scheduled interview for {candidate_name} saved to DB.")

        return {"status": "success", "event_link": calendar_link, "meet_link": meet_link}

    except ValidationError as e: 
        logger.error(f"Pydantic validation error during scheduling: {e.errors()}", exc_info=False)
        error_details = []
        for error_item in e.errors():
            field = " -> ".join(str(loc) for loc in error_item['loc']) if error_item['loc'] else "general"
            msg = error_item['msg']
            error_details.append(f"Field '{field}': {msg}")
        raise HTTPException(status_code=422, detail=f"Invalid input: {'; '.join(error_details)}")
    except HTTPException as http_exc:
        raise http_exc 
    except Exception as e:
        logger.error(f"Unexpected error creating calendar event or saving to DB: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create calendar event or save to DB: {str(e)}")


@app.get("/api/upcoming-interviews", response_model=List[ScheduledInterviewDB], summary="Get all upcoming scheduled interviews")
async def get_upcoming_interviews():
    if db_manager.db is None:
        raise HTTPException(status_code=503, detail="Database service unavailable.")
    
    scheduled_interviews_collection = db_manager.get_collection("scheduled_interviews")
    if scheduled_interviews_collection is None:
        raise HTTPException(status_code=503, detail="Scheduled interviews collection unavailable.")
    
    now_utc = datetime.now(timezone.utc)
    
    interviews_cursor = scheduled_interviews_collection.find(
        {"start_time": {"$gte": now_utc}} 
    ).sort("start_time", 1).limit(100) 
    
    interviews_list = await interviews_cursor.to_list(length=100)
    return interviews_list


# --- Your Existing HisbandHR.ai Endpoints ---
@app.post("/api/match", summary="Process JD and Resumes for Advanced Semantic Matching")
async def process_files_for_matching(
    jd_file_upload: UploadFile = File(..., alias="jd"),
    resume_file_uploads: List[UploadFile] = File(..., alias="resumes")
):
    logger.info(f"Received JD: {jd_file_upload.filename}, Resumes count: {len(resume_file_uploads)}")
    
    if db_manager.db is None:
        logger.error("Database is not connected. Cannot process request.")
        raise HTTPException(status_code=503, detail="Database service unavailable. Please try again later.")

    session_id = str(uuid.uuid4()) 

    jds_collection = db_manager.get_collection("job_descriptions")
    resumes_collection = db_manager.get_collection("resumes")
    matches_collection = db_manager.get_collection("match_results")

    if jds_collection is None or resumes_collection is None or matches_collection is None:
        logger.error("One or more MongoDB collections are not available (returned None).")
        raise HTTPException(status_code=503, detail="Database collections unavailable.")

    try:
        parsed_jd_text, jd_categorized_keywords, jd_sections_text, jd_embeddings = await parse_jd_file(jd_file_upload)
        
        if not parsed_jd_text: 
            logger.error(f"Failed to parse Job Description content: {jd_file_upload.filename}")
            raise HTTPException(status_code=422, detail=f"Failed to parse Job Description: {jd_file_upload.filename}. It might be empty, corrupted, or an unsupported format.")

        flat_jd_keywords_for_db = []
        if jd_categorized_keywords:
            flat_jd_keywords_for_db.extend(jd_categorized_keywords.get("essential", []))
            flat_jd_keywords_for_db.extend(jd_categorized_keywords.get("desirable", []))
            flat_jd_keywords_for_db.extend(jd_categorized_keywords.get("general", []))
            flat_jd_keywords_for_db = sorted(list(set(flat_jd_keywords_for_db)), key=len, reverse=True)


        jd_doc_data = JobDescriptionDB(
            filename=jd_file_upload.filename,
            parsed_text=parsed_jd_text,
            keywords=flat_jd_keywords_for_db,
        )
        dict_to_insert_jd = jd_doc_data.model_dump(by_alias=True, exclude_none=True)
        result_jd = await jds_collection.insert_one(dict_to_insert_jd)
        jd_db_id = result_jd.inserted_id
        logger.info(f"Saved JD '{jd_file_upload.filename}' to DB with ID: {jd_db_id}")

        parsed_resumes_full_data = await parse_resumes(resume_file_uploads)
        if not parsed_resumes_full_data:
             logger.warning("No resumes were successfully parsed from the uploaded files.")
             return {"results": [], "excelUrl": None, "message": "No resume content could be processed."}

        resumes_for_matching_engine = []
        for resume_item_data in parsed_resumes_full_data:
            resume_doc_data = ResumeDB(
                jd_id=jd_db_id, 
                session_id=session_id,
                filename=resume_item_data["filename"],
                parsed_text=resume_item_data["parsed_text"],
            )
            dict_to_insert_resume = resume_doc_data.model_dump(by_alias=True, exclude_none=True)
            result_resume = await resumes_collection.insert_one(dict_to_insert_resume)
            
            resumes_for_matching_engine.append({
                "filename": resume_item_data["filename"],
                "parsed_text": resume_item_data["parsed_text"],
                "embedding": resume_item_data.get("embedding"), 
                "skills": resume_item_data.get("skills", []),   
                "db_id": result_resume.inserted_id             
            })
            logger.info(f"Saved resume '{resume_item_data['filename']}' to DB with ID: {result_resume.inserted_id}")

        match_results_from_engine = match_resumes_to_jd(
            parsed_jd_text,        
            jd_categorized_keywords, 
            jd_sections_text,      
            jd_embeddings,         
            resumes_for_matching_engine 
        )

        final_match_results_for_response = []
        for match_item_from_engine in match_results_from_engine:
            resume_db_id_for_match = None
            for r_data in resumes_for_matching_engine:
                if r_data["filename"] == match_item_from_engine.get("original_filename"): 
                    resume_db_id_for_match = r_data["db_id"]
                    break
            
            if resume_db_id_for_match is None:
                logger.warning(f"Could not find DB ID for matched resume: {match_item_from_engine.get('original_filename')}. Skipping DB save for this specific match result, but including in response.")
                final_match_results_for_response.append(match_item_from_engine) 
                continue

            match_doc_data = MatchResultDB(
                resume_id=resume_db_id_for_match, 
                jd_id=jd_db_id, 
                session_id=session_id,
                candidate_name=match_item_from_engine.get("name", "Unknown Candidate"),
                jd_fit_score=match_item_from_engine.get("jdFit", 0),
                interview_score=match_item_from_engine.get("interviewScore", 0.0),
                red_flags=match_item_from_engine.get("redFlags", []),
                experience_summary=match_item_from_engine.get("experienceSummary", "N/A"),
            )
            dict_to_insert_match = match_doc_data.model_dump(by_alias=True, exclude_none=True)
            result_match = await matches_collection.insert_one(dict_to_insert_match)
            logger.info(f"Saved match result for '{match_item_from_engine.get('name')}' to DB with ID: {result_match.inserted_id}")
            
            response_item = {**match_item_from_engine}
            response_item["match_db_id"] = str(result_match.inserted_id) 
            response_item["resume_db_id"] = str(resume_db_id_for_match)
            response_item["jd_db_id"] = str(jd_db_id)
            # Add candidate email and phone to response if extracted by match_engine
            response_item["email"] = match_item_from_engine.get("email") 
            response_item["phone"] = match_item_from_engine.get("phone")
            final_match_results_for_response.append(response_item)

        excel_url = export_to_excel(final_match_results_for_response)
        
        return {
            "results": final_match_results_for_response,
            "excelUrl": excel_url,
            "message": f"Successfully processed and matched {len(final_match_results_for_response)} candidates." if final_match_results_for_response else "No candidates were matched or processed successfully."
        }

    except HTTPException as http_exc: 
        logger.error(f"HTTP Exception in /api/match: {http_exc.detail}", exc_info=True)
        raise http_exc
    except Exception as e: 
        logger.exception(f"An unexpected error occurred in /api/match: {e}") 
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred. Please check logs. Error: {str(e)}")


@app.get("/", include_in_schema=False) 
async def root_redirect():
    # Redirect to the frontend's main application page
    return RedirectResponse(url="http://localhost:5173/app")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Uvicorn server for HisbandHR.ai Backend v{app.version}...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)