import streamlit as st
import requests

# CONFIGURATION
API_URL = "http://127.0.0.1:8000"
CONVERSATION_ID = "session_1" # You can make this dynamic later!

st.title("OmniChat Gateway")

# 1. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
    
    # Optional: Load existing history from backend on startup
    try:
        response = requests.get(f"{API_URL}/history/{CONVERSATION_ID}")
        if response.status_code == 200:
            st.session_state.messages = response.json()
    except:
        st.warning("Could not connect to backend to load history.")

# 2. Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. Handle User Input
if prompt := st.chat_input("Ask something..."):
    # Display user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 4. Call FastAPI Backend
    try:
        payload = {
            "model": "ollama/llama3",
            "conversation_id": CONVERSATION_ID,
            "messages": st.session_state.messages
        }
        
        response = requests.post(f"{API_URL}/chat", json=payload)
        
        if response.status_code == 200:
            ai_response = response.json()["response"]
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.markdown(ai_response)
        else:
            st.error("Backend Error: Could not get response.")
            
    except Exception as e:
        st.error(f"Connection Error: {e}")