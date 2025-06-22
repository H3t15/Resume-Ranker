import os
import fitz  # PyMuPDF
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SKILL_KEYWORDS = ["python", "flask", "django", "sql", "machine learning", "nlp", "aws"]

def extract_text_from_pdf(path):
    doc = fitz.open(path)
    return " ".join(page.get_text() for page in doc)

def extract_experience(text):
    matches = re.findall(r'(\d+)\+?\s+(years?|yrs?)', text.lower())
    return max([int(m[0]) for m in matches], default=0)

def extract_skills(text):
    return [skill for skill in SKILL_KEYWORDS if skill.lower() in text.lower()]

def process_resumes(paths, job_desc):
    results = []
    texts = [extract_text_from_pdf(p) for p in paths]

    tfidf = TfidfVectorizer().fit_transform([job_desc] + texts)
    scores = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    for i, text in enumerate(texts):
        skills = extract_skills(text)
        exp = extract_experience(text)
        results.append({
            "name": os.path.basename(paths[i]),
            "skills": ", ".join(skills),
            "experience": exp,
            "score": round(scores[i], 4)
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results
