# 🧠 AI-Powered Resume Ranker

A smart, web-based application that helps HRs and recruiters automatically **rank resumes** based on job descriptions using NLP and ML. Built with Flask, TF-IDF, and customizable scoring logic.

---

## 🚀 Features

- 📄 **PDF Resume Parsing** using PyMuPDF
- 🧠 **TF-IDF + Custom Weighted Scoring**
- ✅ **Skill & Experience Extraction**
- 💼 **Admin Panel** to define job roles & descriptions
- 👤 **User Dashboard** to upload resumes
- 📊 **Score in Percentage (%)** for easier HR evaluation
- ⬇️ **CSV Report Download**
- 🔐 **Login & Role-Based Access (Admin/User)**

---

## 🧮 Scoring Logic

Final score is calculated using a weighted formula:

score = (cosine_similarity * 0.6 + skill_match_ratio * 0.3 + experience_score * 0.1) * 100

- **Cosine Similarity**: TF-IDF match between job desc and resume
- **Skill Match Ratio**: Matching from a predefined skill list
- **Experience Score**: Based on match with ideal experience
---

## 🛠️ Tech Stack

- Python (Flask)
- SQLite
- PyMuPDF (`fitz`)
- Scikit-learn (TF-IDF + Cosine Similarity)
- Bootstrap (for UI)
- Pandas (for CSV export)

---
