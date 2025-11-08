# jd_parser.py
import tempfile
import os
import shutil
import spacy
from fastapi import UploadFile
import asyncio
import re
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Any, Tuple

# --- New Imports for Text Extraction ---
import docx # For .docx files (from python-docx)
import PyPDF2 # For .pdf files
# --- End New Imports ---

from database import logger

nlp = None
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("'en_core_web_sm' model loaded.")
except OSError:
    logger.warning("Spacy 'en_core_web_sm' model not found. Attempting to download...")
    try:
        spacy.cli.download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")
        logger.info("'en_core_web_sm' model downloaded and loaded.")
    except Exception as e:
        logger.error(f"Failed to download or load spaCy model: {e}. spaCy-dependent features will be limited.")

sentence_model = None
try:
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("'all-MiniLM-L6-v2' sentence transformer model loaded.")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {e}. Semantic matching will be significantly impacted.")

COMMON_TECH_DOMAINS = [
    "python", "java", "javascript", "c++", "c#", "c", "r", "ruby", "php", "swift", "kotlin", "golang", "scala", "typescript", "perl", "rust", "dart", # Added 'r'
    "react", "react.js", "angular", "vue", "vue.js", "next.js", "ember.js", "svelte", "jquery", "backbone.js",
    "spring", "spring boot", "django", "flask", ".net", ".net core", "asp.net", "laravel", "ruby on rails", "express.js", "fastapi", "node.js",
    "html", "html5", "css", "css3", "sass", "scss", "less", "tailwind css", "bootstrap", "material ui", "vuetify",
    "sql", "mysql", "postgresql", "mssql", "mongodb", "redis", "elasticsearch", "cassandra", "oracle", "sqlite", "dynamodb", "firebase", "realm",
    "aws", "azure", "gcp", "google cloud platform", "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins", "git", "svn", "cicd", "ci/cd",
    "machine learning", "ml", "deep learning", "dl", "nlp", "natural language processing", "computer vision", "cv",
    "data science", "data analysis", "data engineering", "big data", "spark", "apache spark", "hadoop", "kafka", "apache kafka", "airflow", "apache airflow",
    "project management", "agile", "scrum", "kanban", "product management", "business analysis", "technical writing", "program management",
    "devops", "sre", "site reliability", "api design", "rest", "restful", "soap", "graphql", "microservices", "serverless", "api", "apis",
    "cybersecurity", "network security", "penetration testing", "infosec", "information security", "siem", "soc",
    "ui/ux", "ui design", "ux design", "figma", "adobe xd", "sketch", "invision", "user research", "wireframing", "prototyping",
    "power bi", "tableau", "qlik", "qlik sense", "data visualization", "linux", "unix", "windows server", "macos", "bash", "powershell",
    "jira", "confluence", "trello", "asana", "salesforce", "sap", "oracle fusion", "netsuite", "dynamics 365",
    "object-oriented programming", "oop", "functional programming", "data structures", "algorithms", "system design",
    "cloud computing", "virtualization", "vmware", "hyper-v", "iot", "blockchain", "rpa", "artificial intelligence", "ai",
    "qa", "quality assurance" # Added QA related
]
JD_RESUME_STOPWORDS = { # Expanded and slightly refined
    "experience", "skills", "responsibilities", "requirements", "education", "qualifications", "summary", "objective", "profile",
    "ability", "knowledge", "strong", "excellent", "good", "proficient", "demonstrated", "proven", "solid", "deep", "hands-on", "understanding",
    "work", "team", "project", "projects", "role", "company", "client", "clients", "customer", "stakeholder",
    "technology", "technologies", "solution", "solutions", "development", "design", "management", "leadership", "strategy", "planning",
    "analysis", "testing", "support", "communication", "problem-solving", "years", "year", "months", "month", "yrs", "yr",
    "including", "such as", "etc", "various", "multiple", "related", "ensure", "provide", "required", "essential", "mandator",
    "preferred", "desired", "plus", "bonus", "background", "familiarity", "degree", "certification", "qualification",
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "should", "can", "could", "may", "might", "must", "and", "but", "or", "if", "as", "at", "by",
    "for", "from", "in", "into", "of", "on", "onto", "out", "over", "to", "under", "up", "with", "within", "without",
    "activities", "tasks", "duties", "key", "daily", "based", "etc.", "e.g.", "responsible for", "looking for",
    "others", "other", "equivalent", "relevant", "appropriate", "applicable", "effective", "efficient", "successful",
    "timely", "manner", "environment", "industry", "field", "area", "domain", "sector", "market", "business",
    "level", "grade", "standard", "quality", "performance", "goals", "objectives", "targets", "results", "outcomes",
    "candidate", "individual", "person", "professional", "expert", "specialist", "consultant", "engineer", "developer", "manager", "lead", "senior", "junior",
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "operations", "process", "procedures", "methodologies", "framework", "platform", "system", "tool",
    "function", "aspect", "component", "element", "factor", "item", "part", "section", "segment",
    "type", "kind", "sort", "form", "nature", "variety", "range", "scope", "extent",
    "description", "detail", "information", "overview", "report", "statement", "specification",
    "benefit", "advantage", "opportunity", "challenge", "issue", "problem", "concern",
    "job", "position", "career", "opening", "assignment", "engagement",
    "our", "us", "we", "you", "your", "they", "their", "them", "he", "she", "him", "her", "it", "its",
    "title" # "job title" is a common phrase, "title" itself is too generic for a skill
}

def clean_extracted_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\S+@\S*\s?', '', text)
    # Slightly more permissive regex for allowed characters, includes '&', '@', '*', "'"
    text = re.sub(r'[^\w\s\.\,\-\/\(\)\+\#\:\%\&\@\*\']', '', text)
    text = ''.join(filter(lambda x: x.isprintable() or x in '\n\r\t', text))
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    return text.strip()

def extract_jd_sections(text: str) -> Dict[str, str]:
    sections = {
        "full_text": text, "essential_requirements": "", "desirable_requirements": "",
        "responsibilities": "", "general_skills": "", "education": ""
    }
    # text_lower_for_search = text.lower() # Not strictly needed if regex is case-insensitive

    # Regex patterns for section headers (more comprehensive and flexible)
    essential_headers = r"(?:must\s+have|essential\s+(?:criteria|requirements|skills|experience|qualifications)|required\s+(?:skills|qualifications|experience)|core\s+requirements|key\s+requirements|mandatory\s+(?:skills|experience)|minimum\s+(?:qualifications|requirements)|what\s+you(?:\s*'?ll)?\s+bring|you\s+should\s+have|basic\s+qualifications)"
    desirable_headers = r"(?:nice\s+to\s+have|desirable\s+(?:skills|experience|qualifications)|preferred\s+(?:qualifications|skills|experience)|plus\s+points|bonus|good\s+to\s+have|advantageous|additional\s+(?:skills|requirements|qualifications)|would\s+be\s+a\s+plus|extra\s+points|even\s+better\s+if)"
    resp_headers = r"(?:responsibilities|key\s+responsibilities|duties|job\s+duties|your\s+role|what\s+you\s*'?ll\s+do|scope\s+of\s+work|accountabilities|role\s+and\s+responsibilities|tasks\s+and\s+responsibilities|day-to-day\s+responsibilities|what\s+your\s+day\s+will\s+look\s+like|primary\s+responsibilities)"
    skills_headers = r"(?:skills|technical\s+skills|proficiencies|technologies|tools|expertis[ea]|core\s+competencies|technical\s+environment|knowledge\s+of|required\s+toolset|stack|technical\s+qualifications|skill\s+set|our\s+tech\s+stack)"
    edu_headers = r"(?:education|academic\s+background|qualifications\s+required|degree\s+required|educational\s+requirements)"

    all_header_patterns_map = {
        "essential_requirements": essential_headers,
        "desirable_requirements": desirable_headers,
        "responsibilities": resp_headers,
        "general_skills": skills_headers,
        "education": edu_headers
    }
    other_terminators = [
        r"company\s+overview", r"about\s+us", r"about\s+the\s+company",r"benefits", r"what\s+we\s+offer", r"application\s+process",
        r"salary", r"location", r"reporting\s+to", r"how\s+to\s+apply", r"culture", r"values", r"diversity\s+and\s+inclusion",
        r"equal\s+opportunity\s+employer", r"contact\s+us", r"more\s+about"
    ]
    ordered_sections_to_extract = [
        "essential_requirements", "desirable_requirements", "responsibilities",
        "general_skills", "education"
    ]
    
    # Use a copy of the text to manipulate for section extraction
    text_to_process = text 
    extracted_section_indices = [] # To keep track of extracted parts

    for i, current_section_key in enumerate(ordered_sections_to_extract):
        current_header_regex = all_header_patterns_map[current_section_key]
        # Look for the header, ensuring it's somewhat prominent (e.g., start of line, or after substantial whitespace)
        # The (?P<header_match_point>...) captures the point *before* the header text itself for slicing.
        start_match = re.search(rf"(?P<header_match_point>^(?:.*?))(?P<header_text>{current_header_regex})[:\s\n]", text_to_process, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        
        if start_match:
            header_start_char_in_text_to_process = start_match.start('header_text')
            content_start_char_in_text_to_process = start_match.end() # Text after the matched header and colon/space/newline
            
            # Determine end of current section
            terminator_patterns_for_current_section = []
            for j in range(i + 1, len(ordered_sections_to_extract)): # Headers of subsequent defined sections
                next_section_key_ordered = ordered_sections_to_extract[j]
                terminator_patterns_for_current_section.append(all_header_patterns_map[next_section_key_ordered])
            
            # General terminators (company info, etc.)
            terminator_patterns_for_current_section.extend(other_terminators)
            
            # Generic pattern for any other capitalized section-like header that wasn't explicitly defined
            # Looks for "TwoNewlines CapitalizedWord(s) Colon Newline"
            terminator_patterns_for_current_section.append(r"\n\s*\n\s*(?:[A-Z][\w\s\(\)\,\-\/\&\']{4,50}:\s*\n|[A-Z]{3,}[\w\s]{4,50}:\s*\n)")

            end_match_char_in_text_to_process = len(text_to_process) # Default to end of current text_to_process

            if terminator_patterns_for_current_section:
                # Combine all terminator patterns. They should match at the start of a line or after significant whitespace.
                # We search for these terminators *after* the current header's content starts.
                search_space_for_terminators = text_to_process[content_start_char_in_text_to_process:]
                
                min_terminator_pos_in_search_space = len(search_space_for_terminators)

                for term_pattern in terminator_patterns_for_current_section:
                    # Ensure terminator patterns look for start-of-line or prominent breaks
                    effective_term_pattern = rf"(?:(?:^[\t ]*)|(?:\n\s*\n\s*)){term_pattern}"
                    for m in re.finditer(effective_term_pattern, search_space_for_terminators, re.IGNORECASE | re.MULTILINE):
                        if m.start() < min_terminator_pos_in_search_space:
                            min_terminator_pos_in_search_space = m.start()
                
                if min_terminator_pos_in_search_space < len(search_space_for_terminators):
                    end_match_char_in_text_to_process = content_start_char_in_text_to_process + min_terminator_pos_in_search_space
            
            extracted_content = text_to_process[content_start_char_in_text_to_process:end_match_char_in_text_to_process].strip()
            sections[current_section_key] = extracted_content
            
            # Record extracted part to avoid re-extracting (optional, complex if sections overlap)
            # For simplicity, we'll assume sections are mostly distinct or later ones refine earlier ones.
            # Or, we could modify text_to_process by removing the extracted part, but that's trickier.

    # Fallback for "essential_requirements" if not found by specific headers
    if not sections["essential_requirements"]:
        broad_req_headers = r"(?:requirements|qualifications|what\s+we\s+are\s+looking\s+for|your\s+profile|who\s+you\s+are|candidate\s+profile|the\s+ideal\s+candidate|key\s+qualifications)"
        start_match_broad = re.search(rf"^(?:.*?)(?P<header>{broad_req_headers})[:\s\n]", text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if start_match_broad:
            content_after_broad_header = text[start_match_broad.end():]
            # Try to find the end of this broad section
            end_match_broad_terminator = re.search(r"(\n\s*\n\s*([A-Z][a-zA-Z\s()]{3,}:|[A-Z]{2,}[A-Z\s]{5,}:)|\Z)", content_after_broad_header, re.MULTILINE)
            if end_match_broad_terminator:
                sections["essential_requirements"] = content_after_broad_header[:end_match_broad_terminator.start()].strip()
            else:
                sections["essential_requirements"] = content_after_broad_header[:min(len(content_after_broad_header), 2000)].strip()

    # Consolidate "general_skills" if not found but others are
    if not sections["general_skills"]:
        # Prefer "essential_requirements" text for general skills if available and seems skill-like
        essential_text = sections.get("essential_requirements", "")
        responsibilities_text = sections.get("responsibilities", "")
        
        combined_for_skills_fallback = essential_text + "\n" + responsibilities_text
        
        # If a "skills_headers" regex matches within essential or responsibilities, prioritize that part
        skills_header_match_in_essential = re.search(skills_headers, essential_text, re.IGNORECASE)
        if skills_header_match_in_essential:
            sections["general_skills"] = essential_text[skills_header_match_in_essential.end():].strip()
        elif "skills" in combined_for_skills_fallback.lower() or "technologies" in combined_for_skills_fallback.lower():
            sections["general_skills"] = combined_for_skills_fallback
        elif essential_text: # Fallback to essential if no other indicators
            sections["general_skills"] = essential_text
        elif responsibilities_text: # Then responsibilities
            sections["general_skills"] = responsibilities_text


    if not sections["essential_requirements"] and not sections["responsibilities"] and not sections["general_skills"]:
        logger.warning("No clear JD sections found, using first part of text for 'essential_requirements'.")
        first_chunk_match = re.search(r"(.*?)(?:\n\s*\n\s*\n|\Z)", text, re.DOTALL)
        if first_chunk_match:
            first_chunk = first_chunk_match.group(1).strip()
            sections["essential_requirements"] = first_chunk[:min(len(first_chunk), 2000)]
        else:
            sections["essential_requirements"] = text[:min(len(text), 2000)]

    for key in sections:
        if key != "full_text": sections[key] = clean_extracted_text(sections[key])
    return sections


def extract_keywords_from_section(section_text: str, is_essential: bool = False) -> set:
    if not nlp or not section_text:
        return set()

    keyword_candidates = set()
    max_len = nlp.max_length 
    
    text_chunks = [section_text[i:i+max_len] for i in range(0, len(section_text), max_len)]
    
    processed_noun_phrases = set()

    for chunk_text_doc_str in text_chunks:
        doc = nlp(chunk_text_doc_str)

        # 1. Noun Chunks - More refined
        for chunk in doc.noun_chunks:
            text = chunk.text.lower().strip()
            
            if not (2 < len(text) < 50 and not text.isnumeric()):
                continue
            if text in JD_RESUME_STOPWORDS: # Check raw chunk against stopwords
                continue
            if all(t.is_stop or t.is_punct or t.is_space for t in chunk):
                continue

            if len(text.split()) > 4: 
                non_stopwords_count = sum(1 for word_token in chunk if not word_token.is_stop and not word_token.is_punct and not word_token.is_space)
                if non_stopwords_count < 2 and not any(ctd in text for ctd in COMMON_TECH_DOMAINS):
                    # logger.debug(f"Skipping long generic noun chunk: '{text}' (non_stop: {non_stopwords_count})")
                    continue
            
            # Avoid phrases that mostly describe experience level or type rather than a skill
            if text.endswith((" experience", " development", " management", " skills", " ability", " knowledge", " background", " understanding", " familiarity", " degree", " certification", " proficiency")):
                first_word = text.split()[0]
                if first_word in JD_RESUME_STOPWORDS or first_word in ["strong", "good", "excellent", "proven", "demonstrated", "solid", "deep", "hands-on", "years", "year", "minimum", "required", "preferred", "plus"]:
                    # logger.debug(f"Skipping noun chunk likely describing experience level/type: '{text}'")
                    continue

            original_text_for_cleaning = text
            # Aggressive cleaning of prefixes
            text = re.sub(r"^(?:experience|proficiency|knowledge|expertise|background|understanding|familiarity|degree|certification|competency|skill\s+in|track\s+record\s+in|history\s+of|proven\s+ability\s+to|demonstrated\s+ability\s+in)\s+(?:in|of|with|on|using|for|around|related\s+to|working\s+with)\s+", "", text, flags=re.IGNORECASE).strip()
            # Aggressive cleaning of suffixes
            text = re.sub(r"\s+(?:experience|development|management|skills|ability|required|preferred|essential|desired|tools|technologies|platforms|systems|frameworks|libraries|techniques|methods|principles|concepts|competencies|proficiency|expertise|knowledge)$", "", text, flags=re.IGNORECASE).strip()
            # Remove leading adjectives and determiners
            text = re.sub(r"^(?:a|an|the|strong|good|excellent|proven|demonstrated|solid|deep|hands-on|some|any|various|multiple|related|ensure|provide|required|essential|preferred|desired|plus|bonus|minimum|key|core|basic|advanced|expert)\s+", "", text, flags=re.IGNORECASE).strip()
            
            # Remove trailing punctuation or list markers
            text = re.sub(r"^[-\*\u2022\s]+|[.,;:!?]$", "", text).strip()


            if text != original_text_for_cleaning:
                logger.debug(f"Cleaned noun chunk: '{original_text_for_cleaning}' -> '{text}'")

            if text and text not in JD_RESUME_STOPWORDS and 1 < len(text) < 50 and len(text.split()) <=4 : 
                if len(text.split()) > 1 and all(word in JD_RESUME_STOPWORDS for word in text.split()):
                    # logger.debug(f"Skipping noun chunk composed of stopwords after cleaning: '{text}'")
                    continue
                if len(text.split()) == 1 and text in ["required", "preferred", "desired", "essential", "bonus", "plus", "strong", "good", "excellent", "proven", "solid", "minimum", "key", "core", "basic", "advanced", "expert"]:
                    # logger.debug(f"Skipping single generic adjective/verb as keyword: '{text}'")
                    continue
                if len(text) > 1: # Ensure it's not an empty string after cleaning
                    processed_noun_phrases.add(text)

        # 2. Named Entities (NER) - More selective
        for ent in doc.ents:
            if ent.label_ in ["PRODUCT", "WORK_OF_ART", "LANGUAGE", "LAW", "TECH", "SKILL", "ORG"]: 
                 ent_text_lower = ent.text.lower().strip()
                 if ent_text_lower not in JD_RESUME_STOPWORDS and len(ent_text_lower) > 1 and len(ent_text_lower.split()) <=4:
                    if ent.label_ == "ORG" and (ent_text_lower in JD_RESUME_STOPWORDS or ent_text_lower in ["company", "client", "team", "group", "organization", "inc", "llc", "ltd", "corp", "corporation", "solutions", "systems", "services", "technologies", "university", "institute", "college", "department"]):
                        continue
                    if not any(stop_frag in ent_text_lower for stop_frag in [" role", " team", " company", " client", " project", " summary", " description", " experience", " management"]):
                        keyword_candidates.add(ent_text_lower)

    keyword_candidates.update(processed_noun_phrases)

    doc_full = nlp(section_text[:max_len]) # Re-process full section for token-level if needed
    for token in doc_full:
        if token.pos_ in ["PROPN", "NOUN"] and not token.is_stop and not token.is_punct and len(token.lemma_) > 0: # Allow single char like 'c'
            lemma = token.lemma_.lower().strip()
            if lemma and lemma not in JD_RESUME_STOPWORDS and len(lemma.split()) <=3 :
                is_tech_domain_match = any(re.fullmatch(re.escape(domain_skill), lemma) for domain_skill in COMMON_TECH_DOMAINS)
                
                if is_tech_domain_match or \
                   (lemma in ['c', 'r', 'ai', 'ml', 'dl', 'cv', 'nlp', 'ui', "ux", 'qa', 'bi', 'iot', 'erp', 'crm', 'devops', 'sre']) or \
                   (len(lemma) >= 2 and re.match(r"^[a-z0-9+#.-]+[a-z0-9]$", lemma) and not lemma.isnumeric()) or \
                   (token.is_upper and len(lemma) >=2 and len(lemma) <=5 and lemma not in JD_RESUME_STOPWORDS): # Likely an acronym
                     keyword_candidates.add(lemma)

    section_text_lower_for_search = section_text.lower()
    for domain_skill in COMMON_TECH_DOMAINS:
        if re.search(r'\b' + re.escape(domain_skill.lower()) + r'\b', section_text_lower_for_search):
            keyword_candidates.add(domain_skill.lower())
    
    # Filter out candidates that are only numbers or single punctuation
    keyword_candidates = {k for k in keyword_candidates if not (k.isnumeric() or (len(k) == 1 and not k.isalnum() and k not in ['c','r']))}


    sorted_candidates = sorted(list(k for k in keyword_candidates if k and len(k)>0), key=lambda x: (-len(x.split()),-len(x), x)) # Sort by num words, then length
    
    final_keywords = set()
    for kw_cand_idx, kw in enumerate(sorted_candidates):
        if kw in JD_RESUME_STOPWORDS: 
            continue
        
        is_subsumed = False
        # Check if kw is subsumed by an already added *longer* and more specific keyword
        for existing_kw in final_keywords:
            if kw != existing_kw and kw in existing_kw and \
               (len(existing_kw) > len(kw) + 2 or (len(existing_kw.split()) > len(kw.split()))):
                # logger.debug(f"Subsuming '{kw}' by existing '{existing_kw}'")
                is_subsumed = True
                break
        if is_subsumed:
            continue

        # Check if kw subsumes any *shorter* already added keyword
        # This helps prefer longer, more specific phrases
        # e.g., if "java" is in final_keywords, and "java spring boot" comes later, "java" should be removed.
        # However, our sorting (longer first) should mostly handle this.
        # For safety, we can add a check here.
        # This part can be complex; for now, rely on primary sort and above subsumption.

        if is_essential: 
            generic_indicators = [
                "summary", "description", "requirement", "qualification", "responsibility", "duty", 
                "role", "team", "project", "client", "customer", "solution", 
                "communication", "problem solving", "skill", "years of experience", "overview",
                "candidate profile", "ideal candidate", "looking for a", "responsible for", "work environment",
                "company culture", "benefits package", "application process", "equal opportunity"
            ]
            kw_lower_for_check = kw.lower()
            if kw_lower_for_check in generic_indicators:
                # logger.debug(f"Filtering essential generic indicator kw: '{kw}'")
                continue
            if (kw_lower_for_check.startswith("experience in") or kw_lower_for_check.startswith("knowledge of") or \
                kw_lower_for_check.startswith("ability to") or kw_lower_for_check.startswith("understanding of") or \
                kw_lower_for_check.startswith("familiarity with")) and \
               not any(ctd in kw_lower_for_check for ctd in COMMON_TECH_DOMAINS):
                # logger.debug(f"Filtering essential generic phrase kw: '{kw}'")
                continue
        
        final_keywords.add(kw)

    # Final pass to remove keywords that are substrings of OTHERS in the final_keywords set
    # This is after the initial sort and subsumption.
    # This is a bit computationally intensive but can clean up well.
    refined_final_keywords = set()
    sorted_for_final_pass = sorted(list(final_keywords), key=lambda x: (-len(x.split()), -len(x), x))
    for kw1 in sorted_for_final_pass:
        is_truly_subsumed = False
        for kw2 in sorted_for_final_pass: # Compare against all, including itself
            if kw1 != kw2 and kw1 in kw2 and (len(kw2) > len(kw1) + 1 or len(kw2.split()) > len(kw1.split())):
                # If kw1 is "java" and kw2 is "java spring", kw1 is subsumed if "java spring" is better.
                # We prefer longer, more specific phrases.
                is_truly_subsumed = True
                break
        if not is_truly_subsumed:
            refined_final_keywords.add(kw1)
    
    final_keywords = refined_final_keywords

    logger.debug(f"Extracted keywords for section (is_essential={is_essential}, count={len(final_keywords)}): {list(final_keywords)[:30]}")
    return final_keywords


async def _extract_text_from_file(filepath: str, original_filename: str) -> str:
    """Helper function to extract text based on file extension."""
    _, file_extension = os.path.splitext(original_filename)
    file_extension = file_extension.lower()
    raw_text = ""

    try:
        logger.info(f"Attempting to extract text from: {original_filename} (extension: {file_extension})")
        if file_extension == ".pdf":
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f, strict=False) # Added strict=False for more tolerance
                if reader.is_encrypted:
                    try:
                        reader.decrypt('') 
                        logger.info(f"Decrypted PDF: {original_filename}")
                    except Exception as decrypt_err:
                        logger.warning(f"Could not decrypt PDF {original_filename}: {decrypt_err}. Text extraction may fail or be incomplete.")

                text_parts = []
                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as page_err: # Catch broad exceptions during page extraction
                        logger.warning(f"Error extracting text from page {i+1} of {original_filename}: {page_err}")
                raw_text = "\n".join(text_parts)
                if not raw_text.strip() and len(reader.pages) > 0:
                    logger.warning(f"PyPDF2 extracted no text from {original_filename}, though it has pages. PDF might be image-based or have complex encoding.")

        elif file_extension == ".docx":
            doc = docx.Document(filepath)
            raw_text = "\n".join([para.text for para in doc.paragraphs])
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
                try:
                    with open(filepath, 'rb') as f_doc_latin:
                        content_bytes = f_doc_latin.read()
                    raw_text = content_bytes.decode('latin-1', errors='replace') 
                except Exception as e_doc_latin:
                    logger.error(f"Failed to decode .doc file {original_filename} with latin-1: {e_doc_latin}")
                    raw_text = ""
            except Exception as e_doc_open:
                logger.error(f"Failed to open or read .doc file {original_filename} as binary: {e_doc_open}")
                raw_text = ""
        else:
            logger.warning(f"Unsupported file extension '{file_extension}' for {original_filename}. Attempting to read as plain text.")
            try:
                with open(filepath, 'rb') as f_unknown: 
                    content_bytes = f_unknown.read()
                raw_text = content_bytes.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                 try:
                    with open(filepath, 'rb') as f_unknown_latin:
                        content_bytes = f_unknown_latin.read()
                    raw_text = content_bytes.decode('latin-1', errors='replace')
                 except Exception as e_unknown_latin:
                    logger.error(f"Failed to decode unknown file {original_filename} with latin-1: {e_unknown_latin}")
                    raw_text = ""
            except Exception as e_unknown_open:
                logger.error(f"Failed to open or read unknown file {original_filename} as binary: {e_unknown_open}")
                raw_text = ""


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


async def parse_jd_file(jd_file: UploadFile) -> Tuple[str, Dict[str, List[str]], Dict[str, str], Dict[str, Any]]:
    parsed_text = ""
    categorized_keywords: Dict[str, List[str]] = {"essential": [], "desirable": [], "general": []}
    jd_sections_text: Dict[str, str] = {}
    jd_embeddings: Dict[str, Any] = {}
    temp_file_path = None

    try:
        suffix = os.path.splitext(jd_file.filename)[1] if jd_file.filename else '.tmp'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(jd_file.file, tmp)
            temp_file_path = tmp.name
        
        raw_parsed_text = await _extract_text_from_file(temp_file_path, jd_file.filename)
        
        parsed_text = clean_extracted_text(raw_parsed_text)
        logger.info(f"Parsed JD: {jd_file.filename}, Cleaned Full Text Length: {len(parsed_text)}")
        if not parsed_text.strip():
             logger.warning(f"No text could be extracted or cleaned from JD: {jd_file.filename}")
             return "", {"essential": [], "desirable": [], "general": []}, {}, {}

        jd_sections_text = extract_jd_sections(parsed_text)
        logger.info(f"JD Sections Extracted (keys): {list(jd_sections_text.keys())}")
        for section_name, section_content in jd_sections_text.items():
            if section_name != "full_text" and section_content: # Log only if content exists
                 logger.debug(f"JD Section '{section_name}' (first 300 chars): {section_content[:300]}")
            elif section_name != "full_text":
                 logger.debug(f"JD Section '{section_name}': No content extracted.")


        essential_kws_set = extract_keywords_from_section(jd_sections_text.get("essential_requirements", ""), is_essential=True)
        desirable_kws_set = extract_keywords_from_section(jd_sections_text.get("desirable_requirements", ""), is_essential=False) # is_essential is false here
        
        skills_section_text_for_general_kws = jd_sections_text.get("general_skills", "")
        if not skills_section_text_for_general_kws:
            skills_section_text_for_general_kws = jd_sections_text.get("responsibilities", "")
        if not skills_section_text_for_general_kws and (jd_sections_text.get("essential_requirements") or jd_sections_text.get("responsibilities")):
             skills_section_text_for_general_kws = jd_sections_text.get("essential_requirements", "") + "\n" + jd_sections_text.get("responsibilities", "")
        
        general_kws_set = extract_keywords_from_section(skills_section_text_for_general_kws, is_essential=False)

        categorized_keywords["essential"] = sorted(list(essential_kws_set), key=lambda x: (-len(x.split()), -len(x), x))
        categorized_keywords["desirable"] = sorted(list(desirable_kws_set - essential_kws_set), key=lambda x: (-len(x.split()), -len(x), x))
        current_categorized_kws_for_general = essential_kws_set.union(desirable_kws_set)
        categorized_keywords["general"] = sorted(list(general_kws_set - current_categorized_kws_for_general), key=lambda x: (-len(x.split()), -len(x), x))

        logger.info(f"--- JD Categorized Keywords for '{jd_file.filename}' (Post-processing) ---")
        logger.info(f"Essential ({len(categorized_keywords['essential'])}): {categorized_keywords['essential'][:20]}...")
        logger.info(f"Desirable ({len(categorized_keywords['desirable'])}): {categorized_keywords['desirable'][:20]}...")
        logger.info(f"General ({len(categorized_keywords['general'])}): {categorized_keywords['general'][:20]}...")

        if not categorized_keywords["essential"] and (categorized_keywords["desirable"] or categorized_keywords["general"]):
            promoted = []
            # Promote more aggressively if essentials are empty
            if categorized_keywords["desirable"]:
                promoted.extend(categorized_keywords["desirable"][:15]) # Promote up to 15
            if categorized_keywords["general"] and len(promoted) < 15 :
                 promoted.extend(categorized_keywords["general"][:(15 - len(promoted))])
            
            if promoted:
                promoted_set = set(promoted)
                categorized_keywords["essential"] = sorted(list(promoted_set), key=lambda x: (-len(x.split()), -len(x), x))
                categorized_keywords["desirable"] = [kw for kw in categorized_keywords["desirable"] if kw not in promoted_set]
                categorized_keywords["general"] = [kw for kw in categorized_keywords["general"] if kw not in promoted_set]
                logger.info(f"--- JD Categorized Keywords AFTER PROMOTION for '{jd_file.filename}' ---")
                logger.info(f"Essential ({len(categorized_keywords['essential'])}): {categorized_keywords['essential']}")


        if sentence_model:
            # Build skills_semantic_document from the most relevant text parts
            # This should ideally use the text that yields the best keywords
            skills_semantic_document_parts = []
            if jd_sections_text.get("essential_requirements"):
                skills_semantic_document_parts.append(jd_sections_text["essential_requirements"])
            if jd_sections_text.get("general_skills") and jd_sections_text["general_skills"] not in skills_semantic_document_parts: # Avoid duplicate if general_skills was essential
                skills_semantic_document_parts.append(jd_sections_text["general_skills"])
            if jd_sections_text.get("responsibilities") and jd_sections_text["responsibilities"] not in skills_semantic_document_parts:
                skills_semantic_document_parts.append(jd_sections_text["responsibilities"])
            
            # Add top categorized keywords to reinforce their semantic meaning
            if categorized_keywords["essential"]:
                skills_semantic_document_parts.append(". ".join(categorized_keywords["essential"][:15])) # Join with period for sentence structure
            if categorized_keywords["desirable"]:
                skills_semantic_document_parts.append(". ".join(categorized_keywords["desirable"][:10]))
            
            skills_semantic_document_text = " \n\n ".join(filter(None, skills_semantic_document_parts)).strip()


            sections_to_embed = {
                "essential_requirements": jd_sections_text.get("essential_requirements"),
                "skills_semantic_document": skills_semantic_document_text, 
                "responsibilities": jd_sections_text.get("responsibilities"),
                "desirable_requirements": jd_sections_text.get("desirable_requirements"),
                "full_text": parsed_text
            }
            
            for key, text_content in sections_to_embed.items():
                if text_content and text_content.strip(): # Ensure content exists
                    try:
                        # Limit length of text for embedding to avoid excessive processing time/memory for very long sections
                        max_embed_len = 10000 # Characters, adjust as needed. Sentence transformers have input limits too.
                        text_to_embed = text_content[:max_embed_len]
                        
                        jd_embeddings[key] = sentence_model.encode(text_to_embed)
                        logger.debug(f"Embedded section '{key}' (text length: {len(text_to_embed)})")
                    except Exception as emb_ex:
                        logger.error(f"Error embedding section {key} for JD {jd_file.filename}: {emb_ex}")
            logger.info(f"Generated embeddings for JD sections: {list(jd_embeddings.keys())}")

    except Exception as e:
        logger.error(f"Major error parsing JD file {jd_file.filename}: {e}", exc_info=True)
        try:
            # Fallback for general errors
            if jd_file and hasattr(jd_file, 'read') and hasattr(jd_file, 'seek'):
                await jd_file.seek(0)
                content_bytes = await jd_file.read()
                raw_parsed_text_fb = content_bytes.decode('utf-8', errors='replace').strip()
                parsed_text_fb = clean_extracted_text(raw_parsed_text_fb)
                jd_sections_text = {"full_text": parsed_text_fb} 
                if parsed_text_fb:
                    raw_kws_fb = re.findall(r'\b[a-zA-Z]{3,}\b', parsed_text_fb)
                    general_kws_fallback_fb = list(set(kw.lower() for kw in raw_kws_fb if kw.lower() not in JD_RESUME_STOPWORDS and len(kw)>2))[:50]
                    categorized_keywords["essential"] = general_kws_fallback_fb[:15]
                    categorized_keywords["general"] = general_kws_fallback_fb[15:]
                    logger.info(f"--- JD Categorized Keywords (EMERGENCY FALLBACK) for '{jd_file.filename}' ---")

                if sentence_model and parsed_text_fb:
                    try:
                        jd_embeddings["full_text"] = sentence_model.encode(parsed_text_fb[:10000])
                    except Exception as emb_fb_ex:
                        logger.error(f"Error embedding full_text in emergency fallback for JD {jd_file.filename}: {emb_fb_ex}")
            else:
                logger.error(f"JD file object was not valid for emergency fallback parsing: {jd_file.filename}")
        except Exception as e_fallback_inner:
            logger.error(f"Emergency fallback also failed for JD {jd_file.filename}: {e_fallback_inner}")
        # Ensure returning the defined tuple structure even on complete failure
        return "", {"essential": [], "desirable": [], "general": []}, {}, {}
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e_remove:
                 logger.warning(f"Could not remove temp file {temp_file_path}: {e_remove}")
        if jd_file and hasattr(jd_file, 'file') and jd_file.file and not jd_file.file.closed:
            try:
                jd_file.file.close()
            except Exception as e_close:
                logger.warning(f"Error closing UploadFile {jd_file.filename}: {e_close}")
        
    return parsed_text, categorized_keywords, jd_sections_text, jd_embeddings