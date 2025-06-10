import streamlit as st
st.set_page_config(page_title="InterviewCoach Pro", layout="wide")
import openai
import fitz  # PyMuPDF for PDF text extraction
import re
import os

# --- Page Title ---
st.title("🎯 InterviewCoach Pro")
st.markdown("Your AI Mock Interviewer for High-Performance Roles")

# --- API KEY SETUP ---
openai.api_key = st.secrets["openai_api_key"]

if "step" not in st.session_state:
    st.session_state.step = 1

# --- Step 1: Upload & Setup ---
if st.session_state.step == 1:
    st.header("🗕️ Step 1: Upload Job Description & Resume")
    jd_input = st.text_area("📌 Paste the Job Description:")
    cv_file = st.file_uploader("📄 Upload your resume (PDF only):", type=["pdf"])
    jd_q_count = st.number_input("🎯 How many questions from the Job Description?", min_value=0, max_value=10, value=2)
    cv_q_count = st.number_input("📚 How many questions from your Resume?", min_value=0, max_value=10, value=2)

    if jd_input and cv_file:
        cv_text = ""
        with fitz.open(stream=cv_file.read(), filetype="pdf") as doc:
            for page in doc:
                cv_text += page.get_text()
        st.session_state['jd'] = jd_input
        st.session_state['cv'] = cv_text
        st.session_state['jd_q_count'] = jd_q_count
        st.session_state['cv_q_count'] = cv_q_count
        with st.expander("🔍 Preview Extracted Resume Text"):
            st.text_area("Extracted CV Text:", value=cv_text, height=300)
        if st.button("➡️ Proceed to Step 2"):
            st.session_state.step = 2

# --- Step 2: Generate Questions ---
elif st.session_state.step == 2:
    st.header("❓ Step 2: Answer Tailored Mock Interview Questions")
    with st.expander("💡 Need help with STAR format?"):
        st.markdown("""
        **S – Situation:** Set the scene  
        **T – Task:** What you had to achieve  
        **A – Action:** Steps you took  
        **R – Result:** Outcome & impact (preferably with numbers)
        """)

    if 'questions' not in st.session_state:
        prompt = f"""
        You are a mock interview coach. Generate a total of {st.session_state['jd_q_count'] + st.session_state['cv_q_count']} behavioral interview questions.
        - First, generate {st.session_state['jd_q_count']} questions based strictly on the Job Description below.
        - Then, generate {st.session_state['cv_q_count']} questions based on the candidate's resume.
        Job Description:
        {st.session_state['jd']}
        Resume:
        {st.session_state['cv']}
        Format: Numbered list.
        """
        try:
            with st.spinner("Generating questions..."):
                response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
            raw = response.choices[0].message.content.strip().split('\n')
            filtered = []
            for line in raw:
                if re.match(r"^\d+\.\s.+", line):
                    parts = line.split(". ", 1)
                    if len(parts) == 2:
                        q = parts[1].strip()
                        if q:
                            filtered.append(q)
            total_qs = st.session_state['jd_q_count'] + st.session_state['cv_q_count']
            st.session_state['questions'] = filtered[:total_qs]
        except Exception as e:
            st.error(f"Question generation failed: {e}")
            st.stop()

    all_answered = True
    for i, q in enumerate(st.session_state['questions']):
        st.markdown(f"**Q{i+1}:** {q}")
        answer = st.text_area(f"Your Answer to Q{i+1}", key=f"answer_{i}")
        if not answer.strip():
            all_answered = False

    if all_answered and st.button("➡️ Proceed to Step 3"):
        st.session_state.step = 3

# --- Step 3: Get Feedback (Fully Refined UI/UX) ---
elif st.session_state.step == 3:
    st.header("🧠 Step 3: Receive STAR Feedback & Rewrite Suggestions")
    final_score_total = 0
    valid_scores = 0
    feedback_export = []

    for i, q in enumerate(st.session_state['questions']):
        answer = st.session_state.get(f"answer_{i}", "")

        feedback_prompt = f'''
You are a mock interview coach. Evaluate this behavioral interview answer using the STAR framework. Structure your reply in three clearly labeled sections:

1. **STAR Feedback** — break into bold-labeled **Situation**, **Task**, **Action**, **Result**, and follow with bullet points if needed.
2. **Final Score (out of 10)** — start with "Score: X/10".
3. **Resume-Based Enhancement** — suggest how the resume supports or can enhance the answer.

Question: {q}  
Answer: {answer}  
Resume: {st.session_state['cv']}
'''

        rewrite_prompt = f"""
Rewrite the following answer as a single, fluent STAR-format story.
- DO NOT label Situation, Task, Action, or Result.
- Write it like a confident consultant answering in one paragraph.

Question: {q}
Answer: {answer}
"""

        try:
            with st.spinner(f"Analyzing Q{i+1}..."):
                feedback_response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": feedback_prompt}]
                )
                feedback = feedback_response.choices[0].message.content.strip()

                rewrite_response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": rewrite_prompt}]
                )
                rewrite = rewrite_response.choices[0].message.content.strip()

            with st.container():
                st.markdown(f"### 📌 Feedback for Q{i+1}")
                st.markdown(f"**🔹 Question:** {q}")

                with st.expander("🧾 Original Answer"):
                    st.text_area("Your Answer", value=answer, height=150, key=f"orig_answer_{i}", disabled=True)

                # Extract STAR, Score, Enhancement using regex (for layout separation)
                star_match = re.search(r"\*\*STAR Feedback\*\*(.*?)(?:\*\*Final Score|$)", feedback, re.DOTALL)
                score_match = re.search(r"Score:\s*(\d+(\.\d+)?)\s*/\s*10", feedback)
                enh_match = re.search(r"\*\*Resume-Based Enhancement\*\*(.*)", feedback, re.DOTALL)

                star_text = star_match.group(1).strip() if star_match else "STAR structure not detected."
                enh_text = enh_match.group(1).strip() if enh_match else "No enhancement advice provided."

                cols = st.columns(2)
                with cols[0]:
                    st.markdown("🔍 **STAR Feedback**")
                    st.text_area("Feedback", value=star_text, key=f"feedback_{i}", disabled=True, height=300)

                with cols[1]:
                    st.markdown("🔁 **Suggested Rewrite**")
                    st.text_area("Rewrite", value=rewrite, key=f"rewrite_{i}", disabled=True, height=300)

                if score_match:
                    score_val = float(score_match.group(1))
                    final_score_total += score_val
                    valid_scores += 1
                    score_color = "🟢" if score_val >= 8 else "🟡" if score_val >= 6 else "🔴"
                    st.markdown(f"**{score_color} Score:** {score_val}/10")
                else:
                    st.warning("⚠️ Score not found.")

                with st.expander("📈 Resume-Based Enhancement"):
                    st.markdown(enh_text)

                feedback_export.append(f"Q{i+1}: {q}\n\nFEEDBACK:\n{feedback}\n\nREWRITE:\n{rewrite}")
                st.markdown("---")

        except Exception as e:
            st.error(f"Error generating feedback: {e}")

    # --- Step 4: Final Score & Fit Report ---
    if feedback_export:
        st.subheader("📊 Step 4: Summary Report & Final Recommendation")
        if valid_scores:
            avg_score = final_score_total / valid_scores
            st.success(f"✅ Average STAR Answer Score: {avg_score:.1f}/10")
        else:
            avg_score = 0
            st.warning("⚠️ No valid scores available.")

        fit_prompt = f"""
You are a senior hiring manager trained in candidate evaluation. Assess this candidate based on:

- Technical Tools
- Domain Experience
- Problem Solving
- Communication
- Leadership

Provide each as 'Dimension: Score' and an explanation. Conclude with score out of 50 and a one-line hiring recommendation.

Job Description:
{st.session_state['jd']}

Resume:
{st.session_state['cv']}

Interview Answers:
{[st.session_state.get(f"answer_{i}", '') for i in range(len(st.session_state['questions']))]}
"""

        try:
            with st.spinner("Evaluating fit..."):
                fit_response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": fit_prompt}]
                )
                fit_result = fit_response.choices[0].message.content.strip()
                st.info(f"📌 Fit Evaluation:\n\n{fit_result}")

                recommendation = (
                    "✅ Recommendation: Proceed to interview"
                    if avg_score >= 8 else (
                        "🚫 Recommendation: Not ready for interview"
                        if avg_score < 7 else
                        "⚠️ Recommendation: Practice more before the interview but you're close"
                    )
                )
                st.markdown(recommendation)

        except Exception as e:
            st.error(f"Error evaluating fit: {e}")

        # --- Export Feedback as Word Doc ---
        from docx import Document
        from io import BytesIO

        doc = Document()
        doc.add_heading("InterviewCoach Pro - Feedback Report", level=1)
        for i, content in enumerate(feedback_export):
            doc.add_page_break()
            doc.add_heading(f"Question {i+1}", level=2)
            for block in content.split("\n\n"):
                doc.add_paragraph(block.strip())

        word_file = BytesIO()
        doc.save(word_file)
        word_file.seek(0)

        st.download_button(
            label="🗕️ Download Full Feedback Report (.docx)",
            data=word_file,
            file_name="InterviewCoach_Feedback.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
