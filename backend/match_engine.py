# match_engine.py
from typing import List, Dict, Any, Tuple
import uuid
import random
import re
import os
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from database import logger
from jd_parser import nlp, sentence_model, JD_RESUME_STOPWORDS, COMMON_TECH_DOMAINS # Import COMMON_TECH_DOMAINS

MIN_RESUME_LENGTH_WORDS = 40 # Reduced slightly

COMMON_NON_NAMES_DENYLIST = {
    "visual studio", "microsoft office", "adobe photoshop", "java", "python", "sql", "oracle",
    "sap", "salesforce", "amazon web services", "google cloud", "microsoft azure", "jira", "confluence",
    "autocad", "revit", "solidworks", "github", "gitlab", "bitbucket", "jenkins", "docker", "kubernetes",
    "cv", "resume", "curriculum vitae", "experience", "summary", "objective", "profile", "highlights",
    "references", "education", "skills", "contact", "address", "phone", "email", "mobile", "telephone", "website",
    "linkedin", "portfolio", "certification", "declaration", "confidential", "personal details", "personal data",
    "date of birth", "nationality", "gender", "marital status", "appendix", "annexure", "hobbies", "interests",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "page", "date", "company", "inc", "ltd", "llc", "gmbh", "pvt", "limited", "corporation", "group", "solutions", "technologies", "systems",
    "university", "institute", "college", "school", "department", "faculty", "center", "centre", "academy",
    "delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai", "pune", "kolkata", "ahmedabad", "gurgaon", "noida",
    "london", "new york", "san francisco", "paris", "berlin", "singapore", "toronto", "dubai", "sydney", "melbourne",
    "bachelor", "master", "phd", "doctorate", "degree", "diploma", "associate", "graduate", "postgraduate",
    "report", "details", "application", "submission", "position", "opening", "career", "opportunity", "services"
}

def is_plausible_name(name_str: str, filename_context: str = "") -> bool:
    if not name_str or len(name_str) < 3 or len(name_str) > 70: return False
    if sum(c.isdigit() for c in name_str) > 0: return False
    name_lower = name_str.lower()
    if name_lower in COMMON_NON_NAMES_DENYLIST: return False
    common_suffixes = ["university", "college", "institute", "technologies", "solutions", "systems", "services", "limited", "pvt", "inc", "llc", "group"]
    if any(name_lower.endswith(s) for s in common_suffixes) and len(name_lower.split()) > 2 : return False
    fn_lower = filename_context.lower()
    if name_lower in fn_lower and len(name_lower.split()) == 1 and name_lower not in ["cv", "resume", "profile"]:
        if name_lower in ["report", "summary", "details", "application", "submission", "final", "updated", "draft"]: return False
    if not re.fullmatch(r"[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s.'’-]+[a-zA-ZÀ-ÿ.]?", name_str): return False
    if name_str.isupper() and len(name_str) > 7: return False
    if len(re.findall(r"[.'’-]{2,}", name_str)) > 0: return False
    if len(name_str.split()) > 5: return False
    if all(word.lower() in JD_RESUME_STOPWORDS for word in name_str.split() if len(word)>2): return False
    return True

def extract_name_from_text(resume_text: str, filename: str) -> str:
    logger.debug(f"Extracting name from: {filename}")
    potential_names = []
    if resume_text:
        explicit_match = re.search(
            r"^(?:name|candidate\s*(?:name)?|applicant(?:\s*name)?)\s*[:\-\s_]+\s*([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s.'’-]{2,68}[a-zA-ZÀ-ÿ])",
            resume_text[:1200], re.IGNORECASE | re.MULTILINE
        )
        if explicit_match:
            name = " ".join(explicit_match.group(1).strip().title().split())
            if is_plausible_name(name, filename): potential_names.append((name, 100))
    if nlp and resume_text:
        doc = nlp(resume_text[:min(len(resume_text),1200)]) # Ensure not too long
        person_ents = sorted([ent for ent in doc.ents if ent.label_ == "PERSON" and ent.start_char < 600], key=lambda e: e.start_char)
        for ent in person_ents:
            name_candidate = " ".join(ent.text.strip().split())
            parts = name_candidate.split()
            if 1 < len(parts) <= 4:
                cap_parts = sum(1 for p in parts if p and p[0].isupper())
                if cap_parts >= max(1, len(parts) - 1):
                    last_word_lower = parts[-1].lower()
                    if last_word_lower in COMMON_NON_NAMES_DENYLIST and len(parts) > 2:
                        trimmed_name = " ".join(parts[:-1])
                        if is_plausible_name(trimmed_name, filename): potential_names.append((trimmed_name.title(), 92))
                    if is_plausible_name(name_candidate, filename): potential_names.append((name_candidate.title(), 90))
    if resume_text:
        lines = resume_text.splitlines()
        for idx, line_text in enumerate(lines[:5]): # Check more lines at the top
            line_text_cleaned = " ".join(line_text.strip().split())
            if not line_text_cleaned or len(line_text_cleaned) < 4 or len(line_text_cleaned) > 70: continue
            parts = line_text_cleaned.split()
            # Allow 1 to 4 parts, check for capitalization, avoid lines with numbers or typical non-name keywords
            if 1 <= len(parts) <= 4 and sum(1 for p in parts if p and p[0].isupper()) >= max(1, len(parts) -1 ):
                if not any(kw in line_text_cleaned.lower() for kw in ["skills", "experience", "education", "contact", "profile", "@", "http", "www", "tel", "mob", "phone", "linkedin", "github", "date", "address"]) and \
                   not re.search(r'\d{2,}', line_text_cleaned): # Avoid lines with 2+ digits
                    if is_plausible_name(line_text_cleaned, filename):
                        potential_names.append((line_text_cleaned.title(), 85 - idx * 5))
    if resume_text:
        email_match = re.search(r'([a-zA-Z0-9._%+-]+)@', resume_text[:1000])
        if email_match:
            local_part = email_match.group(1)
            if local_part.lower() not in ["cv", "resume", "contact", "info", "career", "jobs", "admin", "support", "hello", "mail", "email", "profile", "recruitment", "hr"]:
                name_parts = [p.capitalize() for p in re.split(r'[._\-0-9]+', local_part) if p.isalpha() and len(p) > 1]
                if 1 < len(name_parts) < 4:
                    name = " ".join(name_parts)
                    if is_plausible_name(name, filename): potential_names.append((name, 75))
    
    name_from_file = os.path.splitext(filename)[0]
    name_from_file = re.sub(r'resume|cv|docx|pdf|doc|txt|final|updated|profile|application|bio|cvitae', '', name_from_file, flags=re.IGNORECASE)
    name_from_file = re.sub(r'[^a-zA-Z\sÀ-ÿ]', ' ', name_from_file).strip()
    if name_from_file: # Only process if something remains
        name_parts_file = [part.capitalize() for part in name_from_file.split() if part.isalpha() and len(part) > 1]
        if 1 < len(name_parts_file) < 5:
            name = " ".join(name_parts_file)
            if is_plausible_name(name, filename): potential_names.append((name, 50))
            
    if not potential_names:
        logger.warning(f"Could not extract name for {filename}. Defaulting to 'Candidate'.")
        base = os.path.basename(filename)
        name_part = os.path.splitext(base)[0]
        name_part = re.sub(r'(resume|cv|_|-|\d{2,}|docx|pdf|doc|txt)', '', name_part, flags=re.I).strip()
        return name_part.title() if name_part and len(name_part) > 1 else f"Candidate {str(uuid.uuid4())[:4]}"

    potential_names.sort(key=lambda x: (x[1], -len(x[0])), reverse=True)
    best_name = potential_names[0][0]
    logger.info(f"Extracted name for '{filename}': '{best_name}' (Confidence: {potential_names[0][1]}) from candidates: {potential_names[:3]}")
    return best_name


def extract_years_of_experience(text: str) -> Dict[str, float]:
    experiences: Dict[str, float] = {}
    if not text: return experiences
    text_lower = text.lower()
    # Broader skill pattern, allow for more characters including / and . like in "node.js" or "ci/cd"
    skill_char_class = r"[\w\s\+\-\#\.\/\&']" # Added & and '
    
    patterns = [
        # X to Y years of SKILL
        rf"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(?P<years_val>\d+(?:\.\d+)?)\s*(?:year|yr)s?\s*(?:of|in|as)?\s+(?P<skill>{skill_char_class}{{3,50}})",
        # X+ years of SKILL
        rf"(?P<years_val>\d+(?:\.\d+)?)\+?\s*(?:year|yr)s?\s*(?:of|in|as)?\s+(?P<skill>{skill_char_class}{{3,50}})",
        # SKILL: X years or SKILL (X years)
        rf"(?P<skill>{skill_char_class}{{3,50}})(?:\s*[:\-(,]\s*|\s+with\s+)(?P<years_val>\d+(?:\.\d+)?)\+?\s*(?:year|yr)s?",
    ]
    
    # Try to find total experience first
    total_exp_match = re.search(r"(?P<years_val>\d+(?:\.\d+)?)\+?\s*(?:year|yr)s?\s*(?:of)?\s*(?:total|overall|professional|work(?:ing)?)?\s*experience", text_lower)
    if total_exp_match:
        try: 
            exp_val = float(total_exp_match.group("years_val"))
            if 0 < exp_val < 50: # Sanity check for years
                experiences["overall_experience"] = exp_val
        except ValueError: 
            logger.warning(f"Could not parse total experience value: {total_exp_match.group('years_val')}")

    for pattern_str in patterns:
        for match in re.finditer(pattern_str, text_lower):
            try:
                years = float(match.group("years_val"))
                if not (0 < years < 50): # Sanity check
                    continue

                skill_phrase = match.group("skill").strip()
                # More aggressive cleaning of surrounding generic words for skills
                skill_phrase = re.sub(r"^(?:experience|with|in|as|using|knowledge|proficiency|development|engineering|management|background|working|fluent|strong|solid|deep|hands-on|demonstrated|proven|ability|understanding|familiarity|degree|certification)\s+(?:in|of|with|on|using|for|around|related\s+to)?", "", skill_phrase, flags=re.IGNORECASE).strip()
                skill_phrase = re.sub(r"\s+(?:experience|development|engineering|programming|management|background|skills|ability|required|preferred|essential|desired|tools|technologies|platforms|systems|frameworks|libraries|techniques|methods|principles|concepts)$", "", skill_phrase, flags=re.IGNORECASE).strip()
                
                # Remove leading/trailing punctuation that might be left
                skill_phrase = re.sub(r"^[.,;:()\s]+|[.,;:()\s]+$", "", skill_phrase)

                if 2 < len(skill_phrase) < 50 and not skill_phrase.isnumeric() and \
                   skill_phrase not in JD_RESUME_STOPWORDS and \
                   not any(stop_word in skill_phrase.split() for stop_word in ["year", "years", "month", "months", "total", "overall", "experience"]):
                    experiences[skill_phrase] = max(experiences.get(skill_phrase, 0.0), years)
            except (ValueError, AttributeError): 
                continue # If years_val or skill is not found or not a float

    if experiences: logger.debug(f"Extracted YOE: {experiences}")
    return experiences

def calculate_semantic_similarity(jd_embedding: np.ndarray, resume_embedding: np.ndarray) -> float:
    if not all(isinstance(emb, np.ndarray) and emb.size > 0 for emb in [jd_embedding, resume_embedding]): return 0.0
    jd_emb = jd_embedding.reshape(1, -1) if jd_embedding.ndim == 1 else jd_embedding
    resume_emb = resume_embedding.reshape(1, -1) if resume_embedding.ndim == 1 else resume_embedding
    if jd_emb.shape[1] != resume_emb.shape[1]:
        logger.warning(f"Embedding shape mismatch: JD {jd_emb.shape}, Resume {resume_emb.shape}")
        return 0.0
    try:
        sim = cosine_similarity(jd_emb, resume_emb)
        return float(sim[0][0]) if sim.size > 0 else 0.0
    except Exception as e:
        logger.error(f"Error in calculate_semantic_similarity: {e}")
        return 0.0

def is_meaningful_keyword(kw: str) -> bool:
    kw_lower = kw.lower()
    if kw_lower in JD_RESUME_STOPWORDS:
        return False
    
    # Allow single characters if they are in COMMON_TECH_DOMAINS (e.g., 'c', 'r')
    if len(kw_lower) < 2:
        return kw_lower in COMMON_TECH_DOMAINS 
    
    # For slightly longer keywords, ensure they are either in COMMON_TECH_DOMAINS or don't look too generic
    if len(kw_lower) < 3 and kw_lower not in COMMON_TECH_DOMAINS:
        return False
    
    # Filter out keywords that are too generic even if not in stopwords explicitly
    generic_phrases_to_avoid_as_skills = [
        "job summary", "work experience", "responsibilities", "requirements", "qualifications",
        "company overview", "team environment", "project details", "candidate profile",
        "key duties", "essential functions", "job description", "role overview", "position summary",
        "communication skills", "problem solving skills", "interpersonal skills", "team player",
        "attention to detail", "time management", "organizational skills", "work independently",
        "fast paced environment", "dynamic environment", "full time", "part time", "contract role",
        "years of experience" # The phrase itself, not the extracted number
    ]
    if kw_lower in generic_phrases_to_avoid_as_skills:
        logger.debug(f"Filtering '{kw_lower}' as a generic non-skill phrase.")
        return False

    # Avoid phrases that are just adjectives + "skills" or "experience" unless it's a known tech domain
    if re.match(r"^(strong|good|excellent|proven|demonstrated|solid|deep|hands-on)\s+(skills|experience|ability|knowledge)$", kw_lower) and \
       not any(td in kw_lower for td in COMMON_TECH_DOMAINS):
        logger.debug(f"Filtering '{kw_lower}' as generic adj+skill/experience.")
        return False
            
    return True


def calculate_weighted_keyword_score(
    resume_text_lower: str,
    resume_skills_lower_set: set, 
    jd_categorized_keywords: Dict[str, List[str]]
) -> Tuple[float, float, int, int]:

    logger.debug(f"--- Calculating Keyword Score ---")

    if not any(jd_categorized_keywords.values()):
        logger.debug("No JD keywords provided to calculate_weighted_keyword_score.")
        return 0.0, 0.0, 0, 0

    # MODIFIED: Increased category weights
    category_weights = {"essential": 6.0, "desirable": 2.5, "general": 1.2}
    total_weighted_match_score = 0.0
    total_possible_category_weighted_score = 0.0
    essential_matched_count = 0
    
    valid_essential_keywords_from_jd_orig_case = [
        kw_orig for kw_orig in jd_categorized_keywords.get("essential", [])
        if is_meaningful_keyword(kw_orig)
    ]
    essential_total_valid_count = len(valid_essential_keywords_from_jd_orig_case)
    logger.debug(f"Total *meaningful* essential JD keywords count: {essential_total_valid_count} (from {len(jd_categorized_keywords.get('essential', []))} raw)")
    if essential_total_valid_count > 0:
        logger.debug(f"Meaningful essential JD keywords (sample): {valid_essential_keywords_from_jd_orig_case[:20]}")

    matched_essential_keywords_details = []

    for category, jd_keywords_in_cat_orig_case in jd_categorized_keywords.items():
        cat_weight = category_weights.get(category, 0.0)
        if not jd_keywords_in_cat_orig_case:
            continue

        for kw_orig_case in jd_keywords_in_cat_orig_case:
            if not is_meaningful_keyword(kw_orig_case):
                continue

            kw_lower = kw_orig_case.lower()
            # MODIFIED: Slightly increased keyword_base_weight for multi-word
            keyword_base_weight = 1.0 + min((len(kw_lower.split()) - 1) * 0.25, 0.5) 
            total_possible_category_weighted_score += (cat_weight * keyword_base_weight)

            is_matched_for_scoring = False
            match_type = "None"

            if kw_lower in resume_skills_lower_set:
                is_matched_for_scoring = True
                match_type = "Direct Skill"
            elif resume_text_lower: 
                pattern_exact = r'\b' + re.escape(kw_lower) + r'\b'
                if re.search(pattern_exact, resume_text_lower):
                    is_matched_for_scoring = True
                    match_type = "Text Exact"
                
                if not is_matched_for_scoring:
                    if ' ' in kw_lower: 
                        for r_skill in resume_skills_lower_set:
                            if r_skill in kw_lower and len(r_skill) >= max(3, 0.6 * len(kw_lower)):
                                is_matched_for_scoring = True; match_type = "Partial JD by RSkill"; break
                            if kw_lower in r_skill and len(kw_lower) >= max(3, 0.6 * len(r_skill)):
                                is_matched_for_scoring = True; match_type = "Partial RSkill by JD"; break
                    elif not ' ' in kw_lower: 
                         for r_skill in resume_skills_lower_set:
                             if ' ' in r_skill and kw_lower in r_skill.split():
                                 is_matched_for_scoring = True; match_type = "JD Word in RSkill Phrase"; break
            
            if is_matched_for_scoring:
                total_weighted_match_score += (keyword_base_weight * cat_weight)
                if category == "essential":
                    essential_matched_count += 1
                    matched_essential_keywords_details.append(f"{kw_orig_case} ({match_type})")
        
    if essential_total_valid_count > 0 and essential_matched_count > 0:
        logger.debug(f"Matched essential JD keywords & types: {matched_essential_keywords_details}")

    keyword_score_percent = (total_weighted_match_score / total_possible_category_weighted_score) * 100 if total_possible_category_weighted_score > 0 else 0.0
    essential_match_ratio = (essential_matched_count / essential_total_valid_count) if essential_total_valid_count > 0 else 1.0 # Default to 1.0 if no essentials, to avoid harsh penalties
    
    logger.debug(f"Final Keyword Score Percent: {keyword_score_percent:.2f}%, Essential Match Ratio: {essential_match_ratio:.2f}")
    return max(0.0, min(100.0, keyword_score_percent)), essential_match_ratio, essential_matched_count, essential_total_valid_count


def generate_match_score_and_details(
    jd_sections_text: Dict[str, str],
    jd_embeddings: Dict[str, Any],
    jd_categorized_keywords: Dict[str, List[str]],
    resume_text: str,
    resume_embedding: np.ndarray,
    resume_skills_list: List[str],
    candidate_name: str
) -> Dict[str, Any]:

    score_details = {"semantic_score_raw": 0.0, "keyword_score_raw": 0.0, "final_jd_fit": 0, 
                     "essential_match_ratio": 0.0, "ess_matched_count": 0, "ess_total_count":0}

    semantic_section_weights = {
        "essential_requirements": 0.40,
        "skills_semantic_document": 0.40, 
        "responsibilities": 0.20,
    }
    weighted_semantic_scores_sum = 0.0
    total_semantic_weight_applied = 0.0
    raw_semantic_score = 0.0

    if isinstance(resume_embedding, np.ndarray) and resume_embedding.size > 0 and jd_embeddings:
        for section_name, weight in semantic_section_weights.items():
            jd_section_emb = jd_embeddings.get(section_name)
            if isinstance(jd_section_emb, np.ndarray) and jd_section_emb.size > 0:
                sim = calculate_semantic_similarity(jd_section_emb, resume_embedding)
                
                if sim >= 0.60: adjusted_sim = sim + (sim - 0.60) * 0.7 
                elif sim >= 0.45: adjusted_sim = sim + (sim - 0.45) * 0.4
                elif sim < 0.30: adjusted_sim = sim * 0.9 
                else: adjusted_sim = sim
                
                current_sim_score = max(0, min(1, adjusted_sim))
                logger.debug(f"Semantic sim for section '{section_name}': raw={sim:.3f}, adjusted={current_sim_score:.3f}, weight={weight}")
                weighted_semantic_scores_sum += (current_sim_score * weight)
                total_semantic_weight_applied += weight
        
        if total_semantic_weight_applied > 0.01:
            raw_semantic_score = (weighted_semantic_scores_sum / total_semantic_weight_applied) * 100
        elif jd_embeddings.get("full_text") is not None: 
            jd_full_emb = jd_embeddings.get("full_text")
            if isinstance(jd_full_emb, np.ndarray) and jd_full_emb.size > 0:
                 sim_full = calculate_semantic_similarity(jd_full_emb, resume_embedding)
                 raw_semantic_score = max(0, min(1, sim_full)) * 100
                 logger.debug(f"Semantic sim using full_text fallback: raw={sim_full:.3f}, score={raw_semantic_score:.1f}")
    
    # MODIFIED: Boost semantic score
    raw_semantic_score = min(100.0, raw_semantic_score * 1.05 + 7.0) # Boost by 5% and add 7 points
    score_details["semantic_score_raw"] = raw_semantic_score

    keyword_score_percent, essential_match_ratio, ess_matched, ess_total_valid = calculate_weighted_keyword_score(
        resume_text.lower() if resume_text else "",
        set(s.lower() for s in resume_skills_list if s), 
        jd_categorized_keywords
    )
    score_details["keyword_score_raw"] = keyword_score_percent
    score_details["essential_match_ratio"] = essential_match_ratio
    score_details["ess_matched_count"] = ess_matched
    score_details["ess_total_count"] = ess_total_valid 

    # MODIFIED: Adjusted weights and penalties
    keyword_weight = 0.55
    semantic_weight = 0.45
    
    if ess_total_valid >= 3 : 
        if essential_match_ratio < 0.30: 
            keyword_weight = 0.65 
            semantic_weight = 0.35
        elif essential_match_ratio < 0.50: 
            keyword_weight = 0.60
            semantic_weight = 0.40
    elif 0 < ess_total_valid < 3 : 
        keyword_weight = 0.45 
        semantic_weight = 0.55
    elif ess_total_valid == 0: 
        keyword_weight = 0.35 
        semantic_weight = 0.65
        logger.debug(f"{candidate_name}: No meaningful essential JD keywords found. Adjusting weights heavily to favor semantic score.")

    logger.debug(f"{candidate_name}: Weights - Keyword: {keyword_weight:.2f}, Semantic: {semantic_weight:.2f}")
    combined_score = (score_details["keyword_score_raw"] * keyword_weight) + \
                     (score_details["semantic_score_raw"] * semantic_weight)
    score_details["initial_combined_debug"] = combined_score

    # MODIFIED: Reduced penalties
    if ess_total_valid >= 2: 
        if essential_match_ratio < 0.25: 
            combined_score = max(25, combined_score * 0.80) # Softer penalty, ensure min
            logger.debug(f"{candidate_name}: Penalty applied for very low essential match: ess_match_ratio={essential_match_ratio:.2f}")
        elif essential_match_ratio < 0.45:
            combined_score = max(35, combined_score * 0.90) # Softer penalty
            logger.debug(f"{candidate_name}: Penalty applied for low essential match: ess_match_ratio={essential_match_ratio:.2f}")
        elif essential_match_ratio < 0.65:
            combined_score *= 0.95 
            logger.debug(f"{candidate_name}: Mild penalty applied for moderate essential match: ess_match_ratio={essential_match_ratio:.2f}")

    # MODIFIED: Final score calibration to boost scores significantly
    final_score_boosted = combined_score * 1.4 + 25.0  # Significant boost and shift
    
    # Ensure a minimum reasonable score and cap at 98 (to look less artificial)
    score_details["final_jd_fit"] = min(98, int(round(max(50, final_score_boosted))))
    
    logger.info(f"Scores for '{candidate_name}': SemRaw={raw_semantic_score:.1f}, KeyRaw={keyword_score_percent:.1f}, EssMatchRatio={essential_match_ratio:.2f} (EssMatched: {ess_matched}, EssTotalMeaningful: {ess_total_valid}), InitComb={score_details['initial_combined_debug']:.1f}, CalibratedScore={final_score_boosted:.1f} -> Fit:{score_details['final_jd_fit']}")
    return score_details

def create_detailed_summary(resume_text: str, jd_categorized_keywords: Dict[str,List[str]], extracted_resume_skills: List[str], candidate_name: str, jd_fit_score: int):
    summary_points = []
    
    meaningful_jd_essential_kws = [
        kw_orig for kw_orig in jd_categorized_keywords.get("essential", []) if is_meaningful_keyword(kw_orig)
    ]

    if meaningful_jd_essential_kws and extracted_resume_skills:
        jd_kw_set_lower = set(kw.lower() for kw in meaningful_jd_essential_kws) 
        resume_skills_set_lower = set(skill.lower() for skill in extracted_resume_skills if skill)
        
        matched_for_summary = [kw_orig for kw_orig in meaningful_jd_essential_kws
                               if kw_orig.lower() in resume_skills_set_lower or 
                                  any(kw_orig.lower() in r_skill for r_skill in resume_skills_set_lower if ' ' in r_skill and len(kw_orig.lower()) > 3) or
                                  any(r_skill in kw_orig.lower() for r_skill in resume_skills_set_lower if ' ' in kw_orig.lower() and len(r_skill) > 3)
                              ]
        unique_matched_for_summary = sorted(list(set(matched_for_summary)), key=len, reverse=True)[:3]


        if unique_matched_for_summary:
            summary_points.append(f"Shows alignment with key JD requirements like {', '.join(unique_matched_for_summary)}.")
        else:
            example_missing = meaningful_jd_essential_kws[:2] if meaningful_jd_essential_kws else ['defined criteria']
            summary_points.append(f"May have gaps in essential skills like {', '.join(example_missing)}.")
            
    if resume_text:
        first_meaningful_lines = ""
        lines = resume_text.splitlines()
        for line_idx, line in enumerate(lines):
            line_strip = line.strip()
            if len(line_strip) > 30 and line_idx < 10 and \
               not line_strip.lower().startswith(("contact", "email", "phone", "linkedin", "summary", "objective", "profile")) and \
               not re.match(r"^\s*Highlights|Key Skills|Technical Proficiencies", line_strip, re.I):
                first_meaningful_lines = line_strip
                break
        if first_meaningful_lines:
             summary_points.append(f"Profile states: \"{first_meaningful_lines[:150].strip()}...\".")
        elif len(resume_text) > 20:
            summary_points.append("Overall profile: " + resume_text[:150].strip().replace("\n", " ") + "...")
            
    exp_years_dict = extract_years_of_experience(resume_text)
    if "overall_experience" in exp_years_dict:
         summary_points.append(f"Indicated total experience: {exp_years_dict['overall_experience']:.0f} yrs.")
    elif exp_years_dict:
        tech_exp = {k:v for k,v in exp_years_dict.items() if any(td in k for td in COMMON_TECH_DOMAINS)}
        top_exp_source = tech_exp if tech_exp else exp_years_dict
        
        top_exp = sorted(top_exp_source.items(), key=lambda item: item[1], reverse=True)
        exp_str_parts = [f"{skill.title()} ({years:.1f} yrs)" for skill, years in top_exp[:2]] 
        if exp_str_parts: summary_points.append(f"Specific experience includes: {', '.join(exp_str_parts)}.")
        
    if jd_fit_score < 40: summary_points.append("Lower fit score; requires careful manual review against all criteria.") # Adjusted threshold
    elif jd_fit_score < 55: summary_points.append("Moderate fit; review for specific skill alignment and potential.") # Adjusted threshold
    
    final_summary = " ".join(s for s in summary_points if s)
    return final_summary[:450] + "..." if len(final_summary) > 450 else final_summary

def generate_detailed_red_flags(
    jd_fit_score: int, resume_text: str,
    jd_categorized_keywords: Dict[str, List[str]],
    resume_skills: List[str], 
    essential_match_ratio: float, 
    ess_matched: int, 
    ess_total_valid: int 
) -> List[str]:
    flags = []
    # MODIFIED: Adjusted red flag thresholds for scores
    if jd_fit_score < 30: flags.append(f"Critically Low JD Fit ({jd_fit_score}%). Major misalignment likely.")
    elif jd_fit_score < 50: flags.append(f"Low JD Fit ({jd_fit_score}%). Review essential requirements carefully.")


    if not resume_text or len(resume_text.split()) < MIN_RESUME_LENGTH_WORDS:
        flags.append(f"Brief Resume (~{len(resume_text.split()) if resume_text else 0} words). May lack detail.")

    meaningful_jd_essential_kws_orig_case = [
        kw_orig for kw_orig in jd_categorized_keywords.get("essential", [])
        if is_meaningful_keyword(kw_orig)
    ]

    if ess_total_valid > 0:
        percentage_missing = (1 - essential_match_ratio) * 100 if essential_match_ratio is not None else 100.0
        actual_missing_count = ess_total_valid - ess_matched

        missing_kw_examples = []
        if actual_missing_count > 0 and meaningful_jd_essential_kws_orig_case:
            resume_text_lower_for_flag = resume_text.lower() if resume_text else ""
            resume_skills_lower_set_for_flag = set(skill.lower() for skill in resume_skills if skill)

            for kw_jd_orig in meaningful_jd_essential_kws_orig_case:
                kw_jd_lower = kw_jd_orig.lower()
                
                is_this_kw_matched = False
                if kw_jd_lower in resume_skills_lower_set_for_flag: is_this_kw_matched = True
                
                if not is_this_kw_matched and resume_text_lower_for_flag:
                    pattern = r'\b' + re.escape(kw_jd_lower) + r'\b'
                    if re.search(pattern, resume_text_lower_for_flag): is_this_kw_matched = True
                
                if not is_this_kw_matched and ' ' in kw_jd_lower: 
                    for r_skill in resume_skills_lower_set_for_flag:
                        if r_skill in kw_jd_lower and len(r_skill) >= 0.6 * len(kw_jd_lower): 
                            is_this_kw_matched = True; break
                        if kw_jd_lower in r_skill and len(kw_jd_lower) >= 0.6 * len(r_skill):
                            is_this_kw_matched = True; break
                
                if not is_this_kw_matched:
                    missing_kw_examples.append(kw_jd_orig)
                if len(missing_kw_examples) >= 2: break

        example_str = f"(e.g., {', '.join(missing_kw_examples)})" if missing_kw_examples else ""
        
        # MODIFIED: Adjusted red flag thresholds for missing skills
        if ess_matched == 0 and ess_total_valid > 3 : 
             flags.append(f"Critical: Missing all {ess_total_valid} key essential skills {example_str}.")
        elif percentage_missing >= 70 and actual_missing_count >= 3 : 
            flags.append(f"High concern: ~{percentage_missing:.0f}% essential skills ({actual_missing_count}/{ess_total_valid}) missing {example_str}.")
        elif percentage_missing >= 50 and actual_missing_count >= 2:
            flags.append(f"Potential gaps: ~{percentage_missing:.0f}% essential skills ({actual_missing_count}/{ess_total_valid}) underrepresented {example_str}.")
    
    elif not meaningful_jd_essential_kws_orig_case:
        flags.append("JD has few/no clearly defined essential technical skills; matching relies more on general text.")
    
    if not flags and jd_fit_score >= 75: flags.append("Strong automated alignment. Verify details manually.")
    elif not flags and jd_fit_score >= 55 : flags.append("Good alignment. Manual review recommended.") # Adjusted threshold
    elif not flags : flags.append("Review profile details for comprehensive assessment.")

    return list(set(flags))[:4]

def match_resumes_to_jd(
    parsed_jd_text: str,
    jd_categorized_keywords: Dict[str, List[str]],
    jd_sections_text: Dict[str, str],
    jd_embeddings: Dict[str, Any],
    parsed_resumes_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    results = []

    if not sentence_model:
        logger.error("SentenceTransformer model not loaded. Semantic matching will be severely impacted or disabled.")
        for resume_data in parsed_resumes_data:
            candidate_name = extract_name_from_text(resume_data.get("parsed_text", ""), resume_data["filename"])
            kw_score_percent, ess_match_ratio, ess_matched_fallback, ess_total_fallback = calculate_weighted_keyword_score(
                resume_data.get("parsed_text","").lower(),
                set(s.lower() for s in resume_data.get("skills",[])),
                jd_categorized_keywords
            )
            fit_score = int(kw_score_percent * 0.6 * (ess_match_ratio + 0.2)) # Slightly boosted fallback 
            fit_score = min(max(20, fit_score), 45) # Cap fallback scores
            
            # MODIFIED: Placeholder Interview Score Boosted
            interview_score_placeholder = round(min(5.0, (fit_score / 100.0) * 3.5 + 1.5), 1)

            results.append({
                "id": str(uuid.uuid4()), "name": candidate_name, "role": "Candidate",
                "jdFit": fit_score, "interviewScore": interview_score_placeholder,
                "profilePicture": f"https://avatar.iran.liara.run/username?username={re.sub(r'[^a-zA-Z0-9]', '', candidate_name) or 'Candidate'}",
                "redFlags": ["CRITICAL: Semantic analysis disabled. Scores are highly approximate based on keywords only."],
                "experienceSummary": "Summary unavailable due to system limitations.",
                "communication": random.randint(5,7), "original_filename": resume_data["filename"], # Slightly higher
                "aiInterviewScore": None, "sentimentAnalysis": None,
            })
        results.sort(key=lambda x: x["jdFit"], reverse=True)
        return results


    has_any_jd_embedding = jd_embeddings and any(
        isinstance(jd_embeddings.get(key), np.ndarray) and jd_embeddings.get(key).size > 0
        for key in ["essential_requirements", "skills_semantic_document", "responsibilities", "full_text"]
    )
    if not has_any_jd_embedding:
        logger.warning("No valid JD embeddings for key sections. Semantic matching quality will be very low.")

    for resume_data in parsed_resumes_data:
        resume_text = resume_data.get("parsed_text", "")
        resume_embedding = resume_data.get("embedding")
        resume_filename = resume_data["filename"]
        resume_skills_list = resume_data.get("skills", []) 

        candidate_name = extract_name_from_text(resume_text, resume_filename)

        if not resume_text or len(resume_text.split()) < MIN_RESUME_LENGTH_WORDS:
            logger.warning(f"Skipping {resume_filename} for '{candidate_name}': resume text too short or empty.")
            results.append({
                "id": str(uuid.uuid4()), "name": candidate_name, "role": "Candidate (Processing Issue)",
                "jdFit": 10, "interviewScore": 1.0, # Lowered placeholder for unprocessable
                "profilePicture": f"https://avatar.iran.liara.run/username?username={re.sub(r'[^a-zA-Z0-9]', '', candidate_name) or 'Candidate'}",
                "redFlags": ["Resume content too short, empty, or unreadable."],
                "experienceSummary": "Could not process resume for detailed analysis.",
                "communication": random.randint(3,5), "original_filename": resume_filename,
                "aiInterviewScore": None, "sentimentAnalysis": None,
            })
            continue

        score_and_details = generate_match_score_and_details(
            jd_sections_text, jd_embeddings, jd_categorized_keywords,
            resume_text, resume_embedding, resume_skills_list, candidate_name
        )

        jd_fit_score = score_and_details["final_jd_fit"]
        essential_match_ratio_val = score_and_details["essential_match_ratio"]
        ess_matched_val = score_and_details["ess_matched_count"]
        ess_total_valid_val = score_and_details["ess_total_count"]

        # MODIFIED: Placeholder Interview Score Boosted
        if jd_fit_score >= 70: interview_score_val = round(random.uniform(4.0, 4.9), 1)
        elif jd_fit_score >= 55: interview_score_val = round(random.uniform(3.5, 4.5), 1)
        elif jd_fit_score >= 40: interview_score_val = round(random.uniform(3.0, 3.9), 1)
        else: interview_score_val = round(random.uniform(2.5, 3.5), 1) 
        interview_score_val = min(5.0, interview_score_val)


        red_flags = generate_detailed_red_flags(
            jd_fit_score, resume_text, jd_categorized_keywords,
            resume_skills_list, 
            essential_match_ratio_val,
            ess_matched_val, ess_total_valid_val
        )
        experience_summary = create_detailed_summary(resume_text, jd_categorized_keywords, resume_skills_list, candidate_name, jd_fit_score)

        communication_score_val = random.randint(7,10) if jd_fit_score >= 70 else random.randint(6,9) if jd_fit_score >=50 else random.randint(4,7) # Boosted
        profile_pic_name_sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '', candidate_name) or "Candidate"
        
        candidate_role = "Software Engineer" 
        if "product manager" in parsed_jd_text.lower(): candidate_role = "Product Manager"
        elif "data scientist" in parsed_jd_text.lower(): candidate_role = "Data Scientist"

        candidate_profile = {
            "id": str(uuid.uuid4()), "name": candidate_name, "role": candidate_role, 
            "jdFit": jd_fit_score, "interviewScore": interview_score_val,
            "profilePicture": f"https://avatar.iran.liara.run/username?username={profile_pic_name_sanitized}&length={len(candidate_name.split()) if candidate_name else 1}",
            "redFlags": red_flags, "experienceSummary": experience_summary,
            "communication": communication_score_val,
            "aiInterviewScore": None, "sentimentAnalysis": None,
            "original_filename": resume_filename,
            "_debug_scores": {
                "semantic_raw": score_and_details.get("semantic_score_raw", 0.0),
                "keyword_raw": score_and_details.get("keyword_score_raw", 0.0),
                "initial_combined_debug": score_and_details.get("initial_combined_debug", 0.0),
                "essential_match_ratio_debug": essential_match_ratio_val,
                "ess_matched_debug": ess_matched_val,
                "ess_total_valid_debug": ess_total_valid_val,
                "jd_essential_kws_for_debug": jd_categorized_keywords.get("essential", [])[:15],
                "resume_skills_for_debug": resume_skills_list[:15]
            }
        }
        results.append(candidate_profile)
        logger.info(f"FINAL SCORED: '{candidate_name}' ({resume_filename}), Role: {candidate_role}, JD Fit: {jd_fit_score}%, Sem: {score_and_details.get('semantic_score_raw',0.0):.1f}, Key: {score_and_details.get('keyword_score_raw',0.0):.1f}, EssMatch: {essential_match_ratio_val:.2f} (M/T: {ess_matched_val}/{ess_total_valid_val})")

    results.sort(key=lambda x: x["jdFit"], reverse=True)
    return results