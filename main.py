import streamlit as st
import os, json

homePage = st.Page("home.py", title="Home Page", icon="🏡", default=True)
fetchFile = st.Page("pages/fetchFile.py", title="Download File", icon="📁")

pg = st.navigation(
    {
    "Main": [
        homePage
    ],
    "Utilities": [
        fetchFile
    ]
    
    }
)


pg.run()