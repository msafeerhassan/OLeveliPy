import streamlit as st
from app import pastPaperChecker, checkAllPastPaper, checkFilePresent, fetchFile
import json, os
from typing import cast

# req: subject name, sub code, exam year, exam series, variant, question num, mark scheme path, answer images path

st.header("Get Solved Past Papers Checked by AI")

with st.form(key="pastPaperExaminer", border=False):
    subjectName = st.text_input(label="Subject Name: ", placeholder="Physics")
    subjectCode = st.number_input(label="Subject Code: ", value=5054, step=1)
    examinationYear = st.number_input(label="Examination Year: ", value=2025, step=1)
    examinationSeries = st.selectbox(label="Examination Series", options=("May/June", "October/November"))
    examVariant = st.number_input(label="Exam Variant", value=12, step=1)
    questionScope = st.radio(label="Question Scope", options=("Specific Question", "All Questions"))
    questionNum = None
    if questionScope == "Specific Question":
        questionNum = st.text_input(label="Question Number: ", placeholder="e.g. 4 or 4(b)(ii)")
    
    answerImages = st.file_uploader(label="Upload Answer Images: ", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    btn = st.form_submit_button(label="Examine & Mark!")

if btn: 
    if not answerImages:
        st.error("**Please upload at least one image of answer.**")
        st.stop()
    
    if questionScope == "Specific Question" and not questionNum:
        st.error("**Please enter a question number.**")
        st.stop()
    
    lastTwoDigs = str(int(examinationYear))[-2:]

    if examinationSeries == "May/June":
        shortenedCodeKey = "s"
        seriesP = "may-june"
    else:
        shortenedCodeKey = "w"
        seriesP = "oct-nov"

    shortenedCode = shortenedCodeKey + lastTwoDigs

    markSchemeStatus, markSchemePath = checkFilePresent(subjectName, subjectCode, examinationYear, seriesP, shortenedCode, examVariant, "ms")

    if not markSchemeStatus:
        with st.spinner(text="Downloading Mark Scheme..."):
            fetchStatus, fetchResult = fetchFile(subjectName, subjectCode, examinationYear, seriesP, shortenedCode, examVariant, fileType="ms")

            if not fetchStatus:
                st.error(f"**Failed to fetch mark scheme:** {fetchResult}")
                st.stop()
            
            markSchemePath = cast(str, fetchResult)

    currentDir = os.path.dirname(os.path.abspath(__file__))
    uploadsDir = os.path.join(currentDir, "files", "uploads")
    os.makedirs(uploadsDir, exist_ok=True)

    answerImagePaths = []

    for img in answerImages:
        savePath = os.path.join(uploadsDir, img.name)
        with open(savePath, "wb") as file:
            file.write(img.getvalue())
        
        answerImagePaths.append(savePath)
    
    with st.spinner(text="Grading Your Answer..."):
        if questionScope == "Specific Question":
            status, result = pastPaperChecker(subjectName, subjectCode, examinationYear, examinationSeries, examVariant, questionNum, markSchemePath, answerImagePaths)
        else:
            status, result = checkAllPastPaper(subjectName, subjectCode, examinationYear, examinationSeries, examVariant, markSchemePath, answerImagePaths)

    if status:
        st.success("**Grading Complete**")
        st.json(result)
    else:
        st.error(f"**Grading Failed: **{result}")