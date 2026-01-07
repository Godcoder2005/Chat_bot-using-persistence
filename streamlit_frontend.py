import streamlit as st
from backend_chat_bot import workflow
from langchain_core.messages import HumanMessage


st.set_page_config(page_title="Akshith's Langgraph Chatbot", page_icon="🤖")
st.title("🤖 Akshith's Langgraph Chatbot")

# Initialize the chat history and thread_id
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "streamlit_session_1"

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_input := st.chat_input("Ask Something"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    # Show a spinner while generating response
    with st.spinner("Thinking..."):
        try:
            config = {'configurable': {'thread_id': st.session_state.thread_id}}
            response = workflow.invoke({'messages':[HumanMessage(content=user_input)]}, config=config)
            ai_response = response['messages'][-1].content
        except Exception as e:
            ai_response = f"Error: {str(e)}"
    
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.write(ai_response)