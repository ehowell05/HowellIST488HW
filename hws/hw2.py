import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
from bs4 import BeautifulSoup
import requests
from anthropic import Anthropic

# Show title and description.
st.title("HW 2")
st.write(
    "Enter a url below and ask a question about it – GPT will answer! "
)
st.sidebar.title("HW 2 Settings")
add_LLM_sbox = st.sidebar.selectbox("Which LLM would you like to use?", ["ChatGPT", "Claude"])
add_sum_sbox = st.sidebar.selectbox("Which kind of summary would you like to use?", ["in 100 Words", "in 2 Paragraphs", "in 5 Bullet Points"])
add_lang_sbox = st.sidebar.selectbox("Output language", ["English", "French", "Spanish"])
add_model_checkbox = st.sidebar.checkbox("Would you like to use the stonger model?", value = False)


def read_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text()
    except requests.RequestException as e:
        print(f"Error reading {url}: {e}")
        return None

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
openai_api_key = st.secrets.EddieOpenAPIKey
claude_api_key = st.secrets.EddieClaudeAPIKey


anthropic_client = Anthropic(api_key=claude_api_key)
openAI_client = OpenAI(api_key=openai_api_key)


# Let the user upload a file via `st.file_uploader`.
uploaded_link = st.text_input("Enter a URL")



if uploaded_link:

    document = read_url_content(uploaded_link)

    if add_LLM_sbox == "ChatGPT":
        if add_model_checkbox:
            model_check = "gpt-5-mini"
        else:
            model_check = "gpt-5-nano"
        response = openAI_client.responses.create(
        model=model_check,
        input=f"Here is a document:\n{document}\n\nSummarize this document {add_sum_sbox}. Respond in {add_lang_sbox}.",
        stream=True,
    )
    else:
        if add_model_checkbox:
            model_check = "claude-sonnet-4-5-20250929"
        else:
            model_check = "claude-haiku-4-5-20251001"
        response = anthropic_client.responses.create(
            model=model_check,
            input=f"Here is a document:\n{document}\n\nSummarize this document {add_sum_sbox}. Respond in {add_lang_sbox}.",
            stream=True,
        )


    def stream_text():
        for event in response:
            if event.type == "response.output_text.delta":
                yield event.delta

    st.write_stream(stream_text())