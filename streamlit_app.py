import streamlit as st

Lab1 = st.Page('hws/hw1.py',
    title = "HW 1",
    icon = "📄",
    url_path = None,
    default = False)

Lab2 = st.Page('hws/hw2.py',
    title = "HW 2",
    icon = "📄",
    url_path = None,
    default = False)

pg = st.navigation ([Lab1,Lab2])
st.set_page_config(page_title='Lab Manager')
pg.run()
