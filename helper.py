import fitz
import re
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from sklearn.metrics.pairwise import cosine_similarity
from langchain_text_splitters import CharacterTextSplitter

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text=""

    for page in doc:
        text = page.get_text()
        full_text += text + "\n"

    doc.close()

    clean_text = re.sub(r'\n+', '\n', full_text)  # Remove extra line breaks
    clean_text = re.sub(r'\s{2,}', ' ', clean_text)  # Replace multiple spaces
    clean_text = clean_text.strip()

    return clean_text


def feeding_text(resume_text, jd_text):
    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    resume_vector = embedding.embed_query(resume_text)
    jd_vector = embedding.embed_query(jd_text)

    similarity = cosine_similarity([resume_vector], [jd_vector])
    # print(f"Resume-JD similarity score: {similarity[0][0]:.2f}")
    return float(f"{similarity[0][0]:.2f}")

