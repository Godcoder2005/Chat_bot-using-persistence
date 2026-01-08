import streamlit as st
from backend_chat_bot import workflow
from langchain_core.messages import HumanMessage
import uuid

st.set_page_config(page_title="Akshith's Langgraph Chatbot", page_icon="🤖")
st.title("🤖 Akshith's Langgraph Chatbot")

# ************************* Utility thread function ****************
def create_thread():
    thread_id = str(uuid.uuid4())
    return thread_id

def get_thread_name(thread_id):
    """Generate a display name for a thread based on its first message"""
    messages = st.session_state['thread_histories'].get(thread_id, [])
    
    # Find the first user message
    for msg in messages:
        if msg['role'] == 'user':
            # Truncate to first 40 characters and add ellipsis if needed
            first_msg = msg['content'].strip()
            if len(first_msg) > 40:
                return first_msg[:40] + "..."
            return first_msg
    
    # If no messages yet, return "New Chat"
    return "New Chat"

# ************************* Session state management *************************
if 'thread_histories' not in st.session_state:
    st.session_state['thread_histories'] = {}  # Store all thread conversations

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = create_thread()
    st.session_state['thread_histories'][st.session_state['thread_id']] = []

# Ensure current thread_id exists in thread_histories (fix for KeyError)
if st.session_state['thread_id'] not in st.session_state['thread_histories']:
    st.session_state['thread_histories'][st.session_state['thread_id']] = []

# ************************* Side bar ui *************************
st.sidebar.title('Langgraph chatbot')

# Add functionality to "New chat" button
if st.sidebar.button('New chat'):
    new_thread_id = create_thread()
    st.session_state['thread_id'] = new_thread_id
    st.session_state['thread_histories'][new_thread_id] = []
    st.rerun()

st.sidebar.title('Your Chats')
#st.sidebar.divider()

# Display all threads in sidebar (most recent first)
for thread_id in list(st.session_state['thread_histories'].keys())[::-1]:
    thread_name = get_thread_name(thread_id)
    
    # Highlight current thread
    if thread_id == st.session_state['thread_id']:
        button_label = f"✅{thread_name}"
    else:
        button_label = f"💬{thread_name}"
    
    if st.sidebar.button(button_label, key=thread_id):
        st.session_state['thread_id'] = thread_id
        st.rerun()

# Get current thread's message history
current_messages = st.session_state['thread_histories'][st.session_state['thread_id']]

# Loading the conversation history
for message in current_messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])  # Use markdown instead of text for better formatting

# User input
user_input = st.chat_input('Type here')

if user_input:
    # Define CONFIG inside the if block where it's needed
    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}
    
    # Add user message
    st.session_state['thread_histories'][st.session_state['thread_id']].append(
        {'role': 'user', 'content': user_input}
    )
    
    with st.chat_message('user'):
        st.markdown(user_input)
    
    with st.chat_message('assistant'):
        ai_message = st.write_stream(
            message_chunk.content 
            for message_chunk, metadata in workflow.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            )
        )
        # Add assistant message
        st.session_state['thread_histories'][st.session_state['thread_id']].append(
            {'role': 'assistant', 'content': ai_message}
        )