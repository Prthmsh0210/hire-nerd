# resume_parser.py
import tempfile
import os
import shutil
from typing import List, Dict, Any
from fastapi import UploadFile
import asyncio
import re

# --- New Imports for Text Extraction ---
import docx # For .docx files (from python-docx)
import PyPDF2 # For .pdf files
# --- End New Imports ---

from database import logger
# Ensure correct imports from jd_parser for shared resources
from jd_parser import clean_extracted_text, sentence_model, nlp, COMMON_TECH_DOMAINS, JD_RESUME_STOPWORDS # Assuming _extract_text_from_file will be here or imported

# --- DUPLICATED HELPER FUNCTION (Ideally move to a shared utils.py) ---
async def _extract_text_from_file(filepath: str, original_filename: str) -> str:
    """Helper function to extract text based on file extension."""
    _, file_extension = os.path.splitext(original_filename)
    file_extension = file_extension.lower()
    raw_text = ""

    try:
        logger.info(f"Attempting to extract text from: {original_filename} (extension: {file_extension})")
        if file_extension == ".pdf":
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f, strict=False) # MODIFIED: Added strict=False
                if reader.is_encrypted:
                    try:
                        reader.decrypt('') # Try with empty password
                        logger.info(f"Decrypted PDF: {original_filename}")
                    except Exception as decrypt_err:
                        logger.warning(f"Could not decrypt PDF {original_filename}: {decrypt_err}. Text extraction may fail or be incomplete.")

                text_parts = []
                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as page_err:
                        logger.warning(f"Error extracting text from page {i+1} of {original_filename}: {page_err}")
                raw_text = "\n".join(text_parts)
                if not raw_text.strip() and len(reader.pages) > 0:
                    logger.warning(f"PyPDF2 extracted no text from {original_filename}, though it has pages. PDF might be image-based or have complex encoding.")

        elif file_extension == ".docx":
            doc_obj = docx.Document(filepath) # Renamed to doc_obj to avoid conflict with spacy's doc
            raw_text = "\n".join([para.text for para in doc_obj.paragraphs])
        elif file_extension == ".txt":
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                raw_text = f.read()
        elif file_extension == ".doc":
            logger.warning(f".doc format ({original_filename}) has limited support. Trying basic text decode. For best results, convert to .docx or .pdf.")
            try:
                with open(filepath, 'rb') as f_doc:
                    content_bytes = f_doc.read()
                raw_text = content_bytes.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                with open(filepath, 'rb') as f_doc_latin:
                    content_bytes = f_doc_latin.read()
                raw_text = content_bytes.decode('latin-1', errors='replace')
        else:
            logger.warning(f"Unsupported file extension '{file_extension}' for {original_filename}. Attempting to read as plain text.")
            try:
                with open(filepath, 'rb') as f_unknown:
                    content_bytes = f_unknown.read()
                raw_text = content_bytes.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                 with open(filepath, 'rb') as f_unknown_latin:
                    content_bytes = f_unknown_latin.read()
                 raw_text = content_bytes.decode('latin-1', errors='replace')

        logger.info(f"Successfully extracted raw text (length: {len(raw_text)}) from {original_filename}")
        return raw_text.strip()

    except Exception as e:
        logger.error(f"Error during text extraction for {original_filename} (path: {filepath}): {e}", exc_info=True)
        try:
            logger.info(f"Fallback extraction attempt for {original_filename}")
            with open(filepath, 'rb') as f_fallback:
                content_bytes = f_fallback.read()
            return content_bytes.decode('utf-8', errors='replace').strip()
        except Exception as e_fallback:
            logger.error(f"Final fallback text extraction also failed for {original_filename}: {e_fallback}")
            return ""
# --- END DUPLICATED HELPER FUNCTION ---


async def parse_resume_file(resume_file: UploadFile) -> Dict[str, Any]:
    parsed_info: Dict[str, Any] = {
        "filename": resume_file.filename, "parsed_text": "",
        "raw_content": "", "embedding": None, "skills": []
    }
    temp_file_path = None

    try:
        suffix = os.path.splitext(resume_file.filename)[1] if resume_file.filename else '.tmp'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(resume_file.file, tmp)
            temp_file_path = tmp.name

        # --- MODIFIED: Use new text extraction helper ---
        raw_parsed_text = await _extract_text_from_file(temp_file_path, resume_file.filename)
        # --- END MODIFICATION ---

        parsed_text = clean_extracted_text(raw_parsed_text)
        if not parsed_text.strip():
            logger.warning(f"No text could be extracted or cleaned from resume: {resume_file.filename}")
            # Return early if no text
            return parsed_info # Will have empty parsed_text, skills, etc.

        parsed_info["parsed_text"] = parsed_text
        parsed_info["raw_content"] = raw_parsed_text # Store the version before heavy cleaning

        # Log the quality of text extracted by new logic
        logger.debug(f"Resume '{resume_file.filename}' - Cleaned Parsed Text (first 300 chars): {parsed_text[:300]}")

        if parsed_text and sentence_model:
            try:
                # Limit length of text for embedding to avoid excessive processing time/memory
                max_embed_len_resume = 10000 
                text_to_embed_resume = parsed_text[:max_embed_len_resume]
                parsed_info["embedding"] = sentence_model.encode(text_to_embed_resume)
                logger.debug(f"Embedded resume '{resume_file.filename}' (text length: {len(text_to_embed_resume)})")
            except Exception as emb_ex:
                 logger.error(f"Error embedding resume {resume_file.filename}: {emb_ex}")

        if parsed_text and nlp:
            max_len = nlp.max_length
            doc_text_for_nlp = parsed_text[:max_len] # Use potentially long text for NLP
            doc = nlp(doc_text_for_nlp) # spaCy doc object

            potential_skills = set()

            for chunk in doc.noun_chunks:
                chunk_text = chunk.text.lower().strip()
                if 2 < len(chunk_text) < 50 and not chunk_text.isnumeric() and \
                   not all(t.is_stop or t.is_punct or t.is_space for t in chunk):
                    cleaned_chunk = re.sub(r"^(?:proficiency|experience|knowledge|expertise)\s+(?:in|of|with|on|using)\s+", "", chunk_text)
                    cleaned_chunk = re.sub(r"\s+(?:tools|technologies|platforms|systems|frameworks|libraries)$", "", cleaned_chunk)
                    if cleaned_chunk and len(cleaned_chunk) > 2 and cleaned_chunk not in JD_RESUME_STOPWORDS:
                        potential_skills.add(cleaned_chunk)

            for ent in doc.ents:
                if ent.label_ in ["ORG", "PRODUCT", "WORK_OF_ART", "LANGUAGE", "NORP", "TECH", "SKILL"] and len(ent.text.strip()) > 2: # Add more relevant ENT labels if needed
                    ent_text_lower = ent.text.lower().strip()
                    if ent_text_lower not in JD_RESUME_STOPWORDS and not ent_text_lower.isnumeric():
                        potential_skills.add(ent_text_lower)

            for token in doc:
                if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop and not token.is_punct and len(token.lemma_) > 1: # Allow 2 char skills like AI, ML
                    lemma = token.lemma_.lower()
                    if lemma not in JD_RESUME_STOPWORDS and not lemma.isnumeric():
                        if lemma in COMMON_TECH_DOMAINS or (not token.is_stop and len(lemma) > 2): # Keep 3+ for general nouns
                            potential_skills.add(lemma)
                        if token.i > 0 and doc[token.i-1].pos_ == "ADJ" and not doc[token.i-1].is_stop:
                            compound_skill = f"{doc[token.i-1].lemma_.lower()} {lemma}"
                            if compound_skill not in JD_RESUME_STOPWORDS and len(compound_skill.split()) > 1: # Ensure it's actually a compound
                                potential_skills.add(compound_skill)

            text_lower_for_regex = parsed_text.lower()
            for tech_skill in COMMON_TECH_DOMAINS:
                if re.search(r'\b' + re.escape(tech_skill.lower()) + r'\b', text_lower_for_regex):
                    potential_skills.add(tech_skill.lower())

            # Filter out too-short skills unless they are known acronyms/tech
            known_short_skills = {'c', 'r', 'ai', 'ml', 'dl', 'cv', 'nlp', 'ui', 'ux', 'qa', 'bi', 'db', 'os', 'k8s', 'api'}
            potential_skills = {
                skill for skill in potential_skills 
                if (len(skill) > 2 or skill in known_short_skills) and not skill.isnumeric()
            }


            sorted_skills = sorted(list(s for s in potential_skills if s), key=len, reverse=True)

            final_resume_skills = []
            temp_skill_set_for_dedupe = set()
            for skill_cand in sorted_skills:
                if skill_cand not in JD_RESUME_STOPWORDS and skill_cand not in temp_skill_set_for_dedupe:
                    final_resume_skills.append(skill_cand)
                    temp_skill_set_for_dedupe.add(skill_cand)

            parsed_info["skills"] = final_resume_skills[:300] # Increased limit slightly

        elif parsed_text: # Basic fallback if no NLP but text exists
            found_skills = set(ts.lower() for ts in COMMON_TECH_DOMAINS if re.search(r'\b' + re.escape(ts.lower()) + r'\b', parsed_text.lower()))
            parsed_info["skills"] = list(found_skills)

        logger.info(f"--- Resume Skills for '{resume_file.filename}' ({len(parsed_info['skills'])}) ---")
        logger.info(f"Skills (first 50): {parsed_info['skills'][:50]}")
        logger.info(f"Parsed resume: {resume_file.filename}, Text Length: {len(parsed_text)}, Skills Extracted: {len(parsed_info['skills'])}")


    except Exception as e:
        logger.error(f"Error parsing resume {resume_file.filename}: {e}", exc_info=True)
        # Fallback logic if the main try block fails (e.g. before text extraction)
        try:
            if resume_file and hasattr(resume_file, 'read') and hasattr(resume_file, 'seek'):
                await resume_file.seek(0) # Needs await if UploadFile.seek becomes async
                content_bytes = await resume_file.read() # Needs await if UploadFile.read becomes async
                raw_parsed_text_fallback = content_bytes.decode('utf-8', errors='replace').strip()
                parsed_text_fallback = clean_extracted_text(raw_parsed_text_fallback)

                parsed_info["parsed_text"] = parsed_text_fallback
                parsed_info["raw_content"] = raw_parsed_text_fallback

                if parsed_text_fallback and sentence_model:
                    try: parsed_info["embedding"] = sentence_model.encode(parsed_text_fallback[:10000])
                    except: pass # nosec
                if parsed_text_fallback:
                    found_skills = set(ts.lower() for ts in COMMON_TECH_DOMAINS if re.search(r'\b' + re.escape(ts.lower()) + r'\b', parsed_text_fallback.lower()))
                    parsed_info["skills"] = list(found_skills)
                logger.info(f"Fallback: Read resume {resume_file.filename} as plain text. Skills: {len(parsed_info['skills'])}")
            else:
                logger.error(f"Resume file object was not valid for fallback parsing: {resume_file.filename}")

        except Exception as e_fallback:
            logger.error(f"Plain text fallback also failed for resume {resume_file.filename}: {e_fallback}")
            # Ensure keys exist even on total failure
            parsed_info["parsed_text"] = ""
            parsed_info["raw_content"] = ""
            parsed_info["embedding"] = None
            parsed_info["skills"] = []
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e_remove:
                 logger.warning(f"Could not remove temp file {temp_file_path}: {e_remove}")
        if resume_file and hasattr(resume_file, 'file') and resume_file.file and not resume_file.file.closed:
            try:
                # FastAPI UploadFile.close() is synchronous.
                # If it were an async file object, you'd use await.
                resume_file.file.close()
            except Exception as e_close:
                logger.warning(f"Error closing UploadFile {resume_file.filename}: {e_close}")

    return parsed_info

async def parse_resumes(resume_files: List[UploadFile]) -> List[Dict[str, Any]]:
    tasks = [parse_resume_file(resume) for resume in resume_files]
    parsed_resumes_data = await asyncio.gather(*tasks)
    # Filter out resumes that couldn't be parsed meaningfully (e.g., too short or no text extracted)
    return [data for data in parsed_resumes_data if data.get("parsed_text", "").strip() and len(data.get("parsed_text", "").split()) > 25] # Reduced min words slightly