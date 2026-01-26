import streamlit as st
from openai import OpenAI
from pypdf import PdfReader

st.title("HW 1")

openai_api_key = st.text_input("OpenAI API Key", type="password")

if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.")
else:
    client = OpenAI(api_key=openai_api_key)

    uploaded_file = st.file_uploader(
        "Upload a document (.txt or .pdf)", type=("txt", "pdf")
    )

    question = st.text_area(
        "Now ask a question about the document!",
        disabled=not uploaded_file,
    )

    if uploaded_file and question:

        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            document = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            document = uploaded_file.read().decode("utf-8")

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"Here is a document:\n{document}\n\nQuestion: {question}",
            stream=True,
        )

        def stream_text():
            for event in response:
                if event.type == "response.output_text.delta":
                    yield event.delta

        st.write_stream(stream_text())