import streamlit as st
from openai import OpenAI
import chromadb
from pathlib import Path
from bs4 import BeautifulSoup

st.title("iSchool Student Organizations Chatbot")


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
    

    text = soup.get_text(separator=" ", strip=True)
    return text


def chunk_document(text, filename):
    '''
    I am chunking this document using the "split in the middle and then look for a nearby sentence boundary" approach. 
    I chose this because it creates two reasonably sized chunks while trying to preserve sentence integrity. 
    The 200 character lookahead is a simple to find a natural split point without making the chunks too small.
    '''
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
        st.error(f"No HTML files found in {folder_path}. Please add the student organization HTML files.")
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


def query_vector_db(collection, query, n_results=3):
    client = st.session_state.openai_client
    
    response = client.embeddings.create(
        input=[query],
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    return results


def result_context(results):
    context = ""
    retrieved_docs = results["documents"][0]
    retrieved_metadatas = results["metadatas"][0]
    
    for i in range(len(retrieved_docs)):
        source = retrieved_metadatas[i]["source"]
        context += f"\n\n--- Source: {source} ---\n{retrieved_docs[i]}"
    
    return context


def convo_context():
    history = st.session_state.conversation_history[-5:]  
    
    messages = []
    for interaction in history:
        messages.append({"role": "user", "content": interaction["user"]})
        messages.append({"role": "assistant", "content": interaction["assistant"]})
    
    return messages


def generate_response(query, context):
    """Generate a response using the LLM with RAG context and conversation memory."""
    client = st.session_state.openai_client
    
    system_prompt = """You are a helpful iSchool Student Organizations assistant chatbot. 
Your role is to answer questions about student organizations at the Syracuse University iSchool.

Guidelines:
- Use the provided documentation as your primary knowledge source
- If your answer comes from a specific document, cite the source clearly (e.g., "According to [Organization Name]...")
- If the documents don't contain relevant information, say "I don't have information about that in my knowledge base"
- Be friendly and helpful to students looking for organization information
- Keep responses concise but informative"""

    rag_context = f"""
Relevant Documentation:
{context}

Use the above documentation to answer the user's question. Cite sources when applicable.
"""
    
    messages = [{"role": "system", "content": system_prompt}]
    
    messages.extend(convo_context())
    
    messages.append({"role": "user", "content": f"{rag_context}\n\nQuestion: {query}"})
    
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=messages
    )
    
    return response.choices[0].message.content



if "HW4_VectorDB" not in st.session_state:
    with st.spinner("Initializing vector database..."):
        st.session_state.HW4_VectorDB = initialize_vector_db()

collection = st.session_state.HW4_VectorDB


st.sidebar.header("About")
st.sidebar.info("""
This chatbot uses RAG (Retrieval-Augmented Generation) to answer questions about iSchool student organizations.

**Features:**
- Searches through organization documentation
- Remembers last 5 conversation exchanges
- Cites sources in responses
""")


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input("Ask about student organizations..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    

    with st.chat_message("assistant"):
        with st.spinner("Searching and thinking..."):

            results = query_vector_db(collection, prompt)
            context = result_context(results)
            

            response = generate_response(prompt, context)
            
            st.markdown(response)
    

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.conversation_history.append({
        "user": prompt,
        "assistant": response
    })
    

    if len(st.session_state.conversation_history) > 5:
        st.session_state.conversation_history = st.session_state.conversation_history[-5:]