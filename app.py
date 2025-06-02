import streamlit as st
import os
import tempfile
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from helper import feeding_text, extract_text_from_pdf
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

GEMINI_API_KEY = st.secrets["GOOGLE_API_KEY"]

def embedding_and_storing_data():
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    CHROMA_DB_DIR = "./chroma_resume_vectordb"
    if not os.path.exists(CHROMA_DB_DIR):
        os.mkdir(CHROMA_DB_DIR)

    vectordb = Chroma(
        persist_directory=CHROMA_DB_DIR,
        embedding_function=embedding_model
    )

    st.set_page_config(page_title="Resume Reader", layout="centered")
    st.title("Resume Matcher")

    uploaded_files = st.file_uploader("Upload your Resume (PDF only)", type=['pdf'], accept_multiple_files=True)

    resume_texts = []
    similarity_scores = []
    if uploaded_files:
        with st.spinner("Analyzing your Resumes and storing it in ChromaDB..."):
            for file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(file.read())
                    tmp_path = temp_file.name

                text = extract_text_from_pdf(tmp_path)
                if not text.strip():
                    continue
                resume_texts.append((file.name, text))

                doc = Document(
                    page_content=text,
                    metadata={"source": file.name}
                )

                vectordb.add_documents([doc])
                st.success(f"Stored: {file.name}")

            vectordb.persist()
            st.success("✅ All resumes embedded and stored in Chroma DB!")

        st.subheader("💼 Enter Job Description (JD):")
        jd_text = st.text_area("Paste the JD here", height=200)

        if jd_text:
            for filename, resume_text in resume_texts:
                score = feeding_text(resume_text=resume_text, jd_text=jd_text)
                st.write(f"🔹 **{filename}** similarity: `{score:.2f}`")
                fit = "✅ Fit" if score >= 0.6 else "❌ Not Fit"
                similarity_scores.append({"Resume":filename, "Score":score, "Fit":fit})

            if similarity_scores:
                df_scores = pd.DataFrame(similarity_scores)
                st.subheader("📊 Similarity Scores Chart")
                st.bar_chart(df_scores.set_index("Resume")["Score"])

                st.subheader("🧾 Fit Summary Table")
                st.dataframe(df_scores.style.applymap(
                    lambda x: 'background-color: lightgreen' if x == "✅ Fit" else 'background-color: pink',
                    subset=['Fit']  
                ))

        # Gemini LLM
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7, max_output_tokens=4096)

        custom_prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
                You are an expert recruiter. Given the following job description (JD) and a candidate's resume, assess whether the candidate is a good fit for the job.

                Job Description:
                {question}

                Resume Content:
                {context}

                Your analysis should:
                1. Assess the overall fit of the candidate for the job.
                2. Provide specific reasons for the fit or lack thereof.
                3. If the candidate is a good fit, mention specific skills, experience, or qualifications that align with the JD.
                4. If the candidate is not a good fit, explain the gaps and suggest improvements or training areas.
                5. Provide a recommendation (Yes/No) along with detailed reasoning.
                """
        )

        # Setup QA chain using StuffDocumentsChain
        qa_chain = load_qa_chain(llm=llm, chain_type="stuff", prompt=custom_prompt)

        st.subheader("🤖 LLM-Powered Analysis")
        if jd_text:
            st.info("Running LLM analysis for each resume...")

            for filename, resume_text in resume_texts:
                docs = [Document(page_content=resume_text, metadata={"source": filename})]
                result = qa_chain.run(input_documents=docs, question=jd_text)
                # .run method has been depricated

                st.markdown(f"### 📄 {filename}")
                st.write(result)

embedding_and_storing_data()
