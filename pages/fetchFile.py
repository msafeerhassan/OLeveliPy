import streamlit as st
import os, json
from typing import cast
from app import fetchFile

st.header("Download any Mark Scheme or Question Paper")

with st.form(key="fetchFile", border=False):
    subjectName = st.text_input(label="Subject Name: ", placeholder="Physics")
    subjectCode = st.number_input(label="Subject Code: ", value=5054, step=1)
    examinationYear = st.number_input(label="Examination Year", value=2025, step=1)
    examinationSeries = st.selectbox(label="Examination Series", options=("May/June", "October/November"))
    variant = st.number_input(label="Variant: ", value=11, step=1)
    fileType = st.selectbox(label="File Type: ", options=("Question Paper", "Mark Scheme"))

    btn = st.form_submit_button(label="Download File!")

if btn:
    lastTwoDigits = str(int(examinationYear))[-2:]
    if examinationSeries == "May/June":
        shortenedCodeKey = "s"
        seriesP = "may-june"
    else:
        shortenedCodeKey = "w"
        seriesP = "oct-nov"

    shortenedCode = shortenedCodeKey + lastTwoDigits

    if fileType == "Mark Scheme":
        fileTypeShort = "ms"
    else:
        fileTypeShort = "qp"

    with st.spinner(text="Downloading File..."):
        status, result = fetchFile(subjectName, subjectCode, examinationYear, seriesP, shortenedCode, variant, fileTypeShort)

        if status:
            st.success(f"**Successfully Fetched File**")

            filePath = cast(str, result)

            with open(filePath, "rb") as file:
                fileBytes = file.read()

                st.download_button(
                    label="Click here to download file!",
                    data=fileBytes,
                    file_name=os.path.basename(filePath),
                    mime="application/pdf"
                )
        else:
            st.error(f"**Failed to download file.** Error: {result}")