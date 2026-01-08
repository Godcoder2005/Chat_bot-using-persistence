import streamlit as st
from backend_using_database import workflow, get_default_threads, get_thread_messages
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
    
    # Ensure messages is a list
    if not isinstance(messages, list) or len(messages) == 0:
        return "New Chat"
    
    # Find the first user message
    for msg in messages:
        # Check if msg is a dictionary
        if isinstance(msg, dict) and msg.get('role') == 'user':
            # Truncate to first 40 characters and add ellipsis if needed
            content = msg.get('content', '')
            first_msg = str(content).strip()
            if len(first_msg) > 40:
                return first_msg[:40] + "..."
            return first_msg if first_msg else "New Chat"
    
    # If no messages yet, return "New Chat"
    return "New Chat"

# ************************* Session state management *************************
if 'thread_histories' not in st.session_state:
    st.session_state['thread_histories'] = {}
    
    # Load all existing threads from database
    try:
        existing_threads = get_default_threads()
        for thread_id in existing_threads:
            messages = get_thread_messages(thread_id)
            st.session_state['thread_histories'][thread_id] = messages
    except Exception as e:
        st.error(f"Error loading threads: {e}")

if 'thread_id' not in st.session_state:
    # Check if there are existing threads
    if st.session_state['thread_histories']:
        # Use the most recent thread
        st.session_state['thread_id'] = list(st.session_state['thread_histories'].keys())[-1]
    else:
        # Create a new thread
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

# Display all threads in sidebar (most recent first)
for thread_id in list(st.session_state['thread_histories'].keys())[::-1]:
    thread_name = get_thread_name(thread_id)
    
    # Highlight current thread
    if thread_id == st.session_state['thread_id']:
        button_label = f"✅ {thread_name}"
    else:
        button_label = f"💬 {thread_name}"
    
    if st.sidebar.button(button_label, key=thread_id):
        st.session_state['thread_id'] = thread_id
        st.rerun()

# Get current thread's message history
current_messages = st.session_state['thread_histories'][st.session_state['thread_id']]

# Show welcome message if no messages in current thread
if len(current_messages) == 0:
    st.markdown(
        """
        <div style='text-align: center; padding: 100px 20px;'>
            <h1 style='color: #ffffff; font-size: 48px; margin-bottom: 20px;'>
                What can I help with?
            </h1>
        </div>
        """,
        unsafe_allow_html=True
    )

# Loading the conversation history
for message in current_messages:
    # Validate message format before displaying
    if isinstance(message, dict) and 'role' in message and 'content' in message:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

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