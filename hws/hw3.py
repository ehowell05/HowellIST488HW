import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from anthropic import Anthropic

st.title("HW3: Chatbot with URL Context")

st.write(
    """
    This chatbot allows you to:
    • Choose between two large language models (OpenAI GPT-5 or Anthropic Claude Sonnet)
    • Provide up to two URLs as permanent context
    • Chat with short-term conversation memory (last 3 user–assistant exchanges)

    The URL content is added as system context and is never discarded.
    """
)


st.sidebar.header("Configuration")

model_choice = st.sidebar.selectbox(
    "Choose a model:",
    ["GPT-5 (OpenAI)", "Claude Sonnet (Anthropic)"]
)

url1 = st.sidebar.text_input("URL 1 (optional)")
url2 = st.sidebar.text_input("URL 2 (optional)")


if "messages" not in st.session_state:
    st.session_state.messages = []

if "url_context" not in st.session_state:
    st.session_state.url_context = ""


openai_client = OpenAI(api_key=st.secrets["EddieOpenAPIKey"])
anthropic_client = Anthropic(api_key=st.secrets["EddieClaudeAPIKey"])


def read_url_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        return f"Error reading {url}: {e}"

if (url1 or url2) and not st.session_state.url_context:
    combined_text = ""

    if url1:
        combined_text += read_url_content(url1) + "\n\n"

    if url2:
        combined_text += read_url_content(url2)

    st.session_state.url_context = combined_text[:4000]


system_prompt = {
    "role": "system",
    "content": (
        f"You are an assistant. Explain answers so someone with no prior knowledge can understand. Use the following URL content as background knowledge: {st.session_state.url_context}"
    )
}


user_input = st.text_input("Ask a question:")

if user_input:
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )


    message_buffer = st.session_state.messages[-6:]

    full_messages = [system_prompt] + message_buffer


    if model_choice == "GPT-5 (OpenAI)":
        response = openai_client.responses.create(
            model="gpt-5",
            input=full_messages
        )
        bot_reply = response.output_text


    else:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=full_messages
        )
        bot_reply = response.content[0].text

    st.session_state.messages.append(
        {"role": "assistant", "content": bot_reply}
    )


for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"])
