import streamlit as st

Lab1 = st.Page('labs/lab1.py',
    title = "Lab 1",
    icon = "📄",
    url_path = None,
    default = False)
Lab2 = st.Page('labs/lab2.py',
    title = "Lab 2",
    icon = "🥼",
    url_path = None,
    default = False)

pg = st.navigation ( [Lab1, Lab2])
st.set_page_config(page_title='Lab Manager')
pg. run ()
