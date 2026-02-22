import streamlit as st
from openai import OpenAI
import chromadb
import json
from pathlib import Path
from bs4 import BeautifulSoup

st.title("Syracuse University Student Organizations Chatbot (HW5)")

if "openai_client" not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets["EddieOpenAPIKey"])

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "messages" not in st.session_state:
    st.session_state.messages = []


def extract_text_from_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for element in soup(["script", "style"]):
        element.decompose()
    return soup.get_text(separator=" ", strip=True)


def chunk_document(text, filename):
    midpoint = len(text) // 2
    split_point = midpoint
    for i in range(midpoint, min(midpoint + 200, len(text))):
        if text[i] in '.!?\n':
            split_point = i + 1
            break
    chunk1 = text[:split_point].strip()
    chunk2 = text[split_point:].strip()
    return [
        {"text": chunk1, "id": f"{filename}_chunk1", "metadata": {"source": filename, "chunk": 1}},
        {"text": chunk2, "id": f"{filename}_chunk2", "metadata": {"source": filename, "chunk": 2}}
    ]


def add_chunks_to_collection(collection, chunks):
    client = st.session_state.openai_client
    for chunk in chunks:
        if not chunk["text"]:
            continue
        response = client.embeddings.create(
            input=[chunk["text"]],
            model="text-embedding-3-small"
        )
        embedding = response.data[0].embedding
        collection.add(
            documents=[chunk["text"]],
            embeddings=[embedding],
            ids=[chunk["id"]],
            metadatas=[chunk["metadata"]]
        )


def initialize_vector_db():
    db_path = "./ChromaDB_for_HW4"
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection("StudentOrgsCollection")

    if collection.count() > 0:
        st.sidebar.success(f"Vector DB loaded with {collection.count()} chunks")
        return collection

    folder_path = "data/HW-04-Data/su_orgs"
    html_files = list(Path(folder_path).glob("*.html"))

    if not html_files:
        st.error(f"No HTML files found in {folder_path}.")
        return collection

    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()

    for i, file in enumerate(html_files):
        status_text.text(f"Processing: {file.name}")
        text = extract_text_from_html(file)
        chunks = chunk_document(text, file.name)
        add_chunks_to_collection(collection, chunks)
        progress_bar.progress((i + 1) / len(html_files))

    status_text.text(f"Indexed {len(html_files)} files ({collection.count()} chunks)")
    progress_bar.empty()
    return collection


def relevant_club_info(query: str, n_results: int = 3) -> str:
    """
    Performs a vector search in ChromaDB for the given query and returns
    the relevant document chunks with their source filenames.
    """
    client = st.session_state.openai_client
    collection = st.session_state.HW5_VectorDB

    response = client.embeddings.create(
        input=[query],
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    retrieved_docs = results["documents"][0]
    retrieved_metadatas = results["metadatas"][0]

    context = ""
    for i in range(len(retrieved_docs)):
        source = retrieved_metadatas[i]["source"]
        context += f"\n\n--- Source: {source} ---\n{retrieved_docs[i]}"

    return context if context.strip() else "No relevant information found in the knowledge base."


tools = [
    {
        "type": "function",
        "function": {
            "name": "relevant_club_info",
            "description": (
                "Searches the Syracuse University iSchool student organizations knowledge base "
                "and returns relevant information for a given query. Call this whenever you need "
                "to answer questions about student organizations, clubs, membership, events, or "
                "any organization-specific details."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant club information."
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of document chunks to retrieve. Defaults to 3.",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def build_messages(user_query: str) -> list:
    system_prompt = (
        "You are a helpful Syracuse University iSchool Student Organizations assistant. "
        "You answer questions about student clubs and organizations. "
        "When you need information about a specific club or topic, call the relevant_club_info function. "
        "Always cite the source document when referencing retrieved information (e.g., 'According to [filename]...'). "
        "If the knowledge base does not contain the answer, say so clearly. "
        "Do not fabricate information. Do not include links in your responses."
    )

    messages = [{"role": "system", "content": system_prompt}]

    for interaction in st.session_state.conversation_history[-5:]:
        messages.append({"role": "user", "content": interaction["user"]})
        messages.append({"role": "assistant", "content": interaction["assistant"]})

    messages.append({"role": "user", "content": user_query})
    return messages


def generate_response(user_query: str) -> str:
    client = st.session_state.openai_client
    messages = build_messages(user_query)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message

    if response_message.tool_calls:
        messages.append(response_message) 

        for tool_call in response_message.tool_calls:
            if tool_call.function.name == "relevant_club_info":
                args = json.loads(tool_call.function.arguments)
                function_result = relevant_club_info(
                    query=args.get("query", user_query),
                    n_results=args.get("n_results", 3)
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": function_result
                })

        final_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        return final_response.choices[0].message.content

    return response_message.content


if "HW5_VectorDB" not in st.session_state:
    with st.spinner("Initializing vector database..."):
        st.session_state.HW5_VectorDB = initialize_vector_db()


st.sidebar.header("About")
st.sidebar.info(
    "This chatbot uses RAG with OpenAI Function Calling to answer questions "
    "about Syracuse University iSchool student organizations.\n\n"
    "Features:\n"
    "- Function calling (LLM decides when to search)\n"
    "- ChromaDB vector search\n"
    "- Short-term memory (last 5 exchanges)\n"
    "- Source citations in responses"
)


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about student organizations..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = generate_response(prompt)
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.conversation_history.append({
        "user": prompt,
        "assistant": response
    })

    if len(st.session_state.conversation_history) > 5:
        st.session_state.conversation_history = st.session_state.conversation_history[-5:]