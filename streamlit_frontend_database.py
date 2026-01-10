import streamlit as st
from backend_using_database import workflow, get_default_threads, get_thread_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid

st.set_page_config(page_title="Akshith's Langgraph Chatbot", page_icon="🤖")
st.title("🤖 Akshith's Langgraph Chatbot")

def create_thread():
    thread_id = str(uuid.uuid4())
    return thread_id

def get_thread_name(thread_id):
    """Generate a display name for a thread based on its first message"""
    messages = st.session_state['thread_histories'].get(thread_id, [])
    
    if not isinstance(messages, list) or len(messages) == 0:
        return "New Chat"
    
    for msg in messages:
        if isinstance(msg, dict) and msg.get('role') == 'user':
            content = msg.get('content', '')
            first_msg = str(content).strip()
            if len(first_msg) > 40:
                return first_msg[:40] + "..."
            return first_msg if first_msg else "New Chat"
    
    return "New Chat"

if 'thread_histories' not in st.session_state:
    st.session_state['thread_histories'] = {}
    
    try:
        existing_threads = get_default_threads()
        for thread_id in existing_threads:
            messages = get_thread_messages(thread_id)
            st.session_state['thread_histories'][thread_id] = messages
    except Exception as e:
        st.error(f"Error loading threads: {e}")

if 'thread_id' not in st.session_state:
    if st.session_state['thread_histories']:
        st.session_state['thread_id'] = list(st.session_state['thread_histories'].keys())[-1]
    else:
        st.session_state['thread_id'] = create_thread()
        st.session_state['thread_histories'][st.session_state['thread_id']] = []

if st.session_state['thread_id'] not in st.session_state['thread_histories']:
    st.session_state['thread_histories'][st.session_state['thread_id']] = []

st.sidebar.title('Langgraph chatbot')

if st.sidebar.button('New chat'):
    new_thread_id = create_thread()
    st.session_state['thread_id'] = new_thread_id
    st.session_state['thread_histories'][new_thread_id] = []
    st.rerun()

st.sidebar.title('Your Chats')

for thread_id in list(st.session_state['thread_histories'].keys())[::-1]:
    thread_name = get_thread_name(thread_id)
    
    if thread_id == st.session_state['thread_id']:
        button_label = f"✅ {thread_name}"
    else:
        button_label = f"💬 {thread_name}"
    
    if st.sidebar.button(button_label, key=thread_id):
        st.session_state['thread_id'] = thread_id
        st.rerun()

current_messages = st.session_state['thread_histories'][st.session_state['thread_id']]

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

for message in current_messages:
    if isinstance(message, dict) and 'role' in message and 'content' in message:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

user_input = st.chat_input('Type here')

if user_input:
    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}
    
    st.session_state['thread_histories'][st.session_state['thread_id']].append(
        {'role': 'user', 'content': user_input}
    )
    
    with st.chat_message('user'):
        st.markdown(user_input)
    
    with st.chat_message('assistant'):
        response_placeholder = st.empty()
        full_response = ""
        
        final_state = None
        for event in workflow.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config=CONFIG,
            stream_mode='values'
        ):
            final_state = event
        
        if final_state and 'messages' in final_state:
            messages = final_state['messages']
            
            for message in reversed(messages):
                if isinstance(message, AIMessage):
                    if isinstance(message.content, str) and message.content.strip():
                        full_response = message.content
                        break
                    elif isinstance(message.content, list):
                        text_parts = []
                        for block in message.content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text_parts.append(block.get('text', ''))
                            elif isinstance(block, str):
                                text_parts.append(block)
                        full_response = ''.join(text_parts)
                        if full_response.strip():
                            break
        
        if full_response:
            response_placeholder.markdown(full_response)
            st.session_state['thread_histories'][st.session_state['thread_id']].append(
                {'role': 'assistant', 'content': full_response}
            )
        else:
            response_placeholder.warning("No response generated. Please try again.")