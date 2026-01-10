import streamlit as st
from backend_using_database import workflow, get_default_threads, get_thread_messages, ingestion
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid

st.set_page_config(page_title="Akshith's Langgraph Chatbot", page_icon="🤖")
st.title("🤖 Akshith's Langgraph Chatbot")

def create_thread():
    """Create a new thread with unique ID"""
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

# Initialize thread histories
if 'thread_histories' not in st.session_state:
    st.session_state['thread_histories'] = {}
    
    try:
        existing_threads = get_default_threads()
        for thread_id in existing_threads:
            messages = get_thread_messages(thread_id)
            st.session_state['thread_histories'][thread_id] = messages
    except Exception as e:
        st.error(f"Error loading threads: {e}")

# Initialize current thread
if 'thread_id' not in st.session_state:
    if st.session_state['thread_histories']:
        st.session_state['thread_id'] = list(st.session_state['thread_histories'].keys())[-1]
    else:
        st.session_state['thread_id'] = create_thread()
        st.session_state['thread_histories'][st.session_state['thread_id']] = []

# Initialize processed files tracker per thread
if 'processed_files' not in st.session_state:
    st.session_state['processed_files'] = {}

# Initialize thread order for proper sorting
if 'thread_order' not in st.session_state:
    st.session_state['thread_order'] = list(st.session_state['thread_histories'].keys())

# Ensure current thread exists in histories
if st.session_state['thread_id'] not in st.session_state['thread_histories']:
    st.session_state['thread_histories'][st.session_state['thread_id']] = []

# Sidebar
st.sidebar.title('Langgraph Chatbot')

# New chat button
if st.sidebar.button('➕ New Chat', use_container_width=True):
    new_thread_id = create_thread()
    st.session_state['thread_id'] = new_thread_id
    st.session_state['thread_histories'][new_thread_id] = []
    # Add to front of thread order
    if new_thread_id not in st.session_state['thread_order']:
        st.session_state['thread_order'].insert(0, new_thread_id)
    st.rerun()

# PDF Upload Section
st.sidebar.markdown("---")
st.sidebar.header("📄 Upload PDF")
upload_pdf = st.sidebar.file_uploader(
    "Upload a PDF for this chat", 
    type=["pdf"], 
    key="pdf_uploader",
    help="Upload a PDF to ask questions about its content"
)

if upload_pdf:
    # Create unique file identifier for current thread
    file_key = f"{st.session_state['thread_id']}_{upload_pdf.name}_{upload_pdf.size}"
    
    # Only process if not already processed for this thread
    if file_key not in st.session_state['processed_files']:
        try:
            with st.spinner("📚 Indexing document... This may take a moment."):
                result = ingestion(
                    file_bytes=upload_pdf.read(),
                    thread_id=st.session_state['thread_id'],
                    filename=upload_pdf.name
                )

            if "error" in result:
                st.sidebar.error(f"❌ {result['error']}")
            else:
                st.sidebar.success(
                    f"✅ Successfully indexed **{result['filename']}**\n\n"
                    f"📄 {result['documents']} pages → {result['chunks']} chunks"
                )
                # Mark as processed
                st.session_state['processed_files'][file_key] = {
                    'filename': upload_pdf.name,
                    'chunks': result['chunks']
                }
        except Exception as e:
            st.sidebar.error(f"❌ Error processing PDF: {str(e)}")
    else:
        # Show info about already indexed file
        file_info = st.session_state['processed_files'][file_key]
        st.sidebar.info(
            f"📄 **{file_info['filename']}** already indexed\n\n"
            f"✓ {file_info['chunks']} chunks available"
        )

# Show indexed PDFs for current thread
thread_files = [
    info for key, info in st.session_state['processed_files'].items() 
    if key.startswith(st.session_state['thread_id'])
]
if thread_files:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📚 Indexed Documents:**")
    for file_info in thread_files:
        st.sidebar.markdown(f"• {file_info['filename']}")

# Chat History Sidebar
st.sidebar.markdown("---")
st.sidebar.title('💬 Your Chats')

# Update thread order to ensure current thread is at top
if st.session_state['thread_id'] in st.session_state['thread_order']:
    st.session_state['thread_order'].remove(st.session_state['thread_id'])
st.session_state['thread_order'].insert(0, st.session_state['thread_id'])

# Display threads in order
for thread_id in st.session_state['thread_order']:
    # Skip if thread was deleted
    if thread_id not in st.session_state['thread_histories']:
        continue
        
    thread_name = get_thread_name(thread_id)
    
    if thread_id == st.session_state['thread_id']:
        button_label = f"✅ {thread_name}"
    else:
        button_label = f"💬 {thread_name}"
    
    if st.sidebar.button(button_label, key=f"thread_{thread_id}", use_container_width=True):
        st.session_state['thread_id'] = thread_id
        st.rerun()

# Main Chat Area
current_messages = st.session_state['thread_histories'][st.session_state['thread_id']]

# Welcome message for empty chats
if len(current_messages) == 0:
    st.markdown(
        """
        <div style='text-align: center; padding: 100px 20px;'>
            <h1 style='color: #ffffff; font-size: 48px; margin-bottom: 20px;'>
                What can I help with?
            </h1>
            <p style='color: #a0a0a0; font-size: 18px;'>
                Ask me anything, upload a PDF, or use my tools for calculations, weather, stocks, and web search!
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# Display chat messages
for message in current_messages:
    if isinstance(message, dict) and 'role' in message and 'content' in message:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

# Chat input
user_input = st.chat_input('Type your message here...')

if user_input:
    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}
    
    # Add user message to history
    st.session_state['thread_histories'][st.session_state['thread_id']].append(
        {'role': 'user', 'content': user_input}
    )
    
    # Display user message
    with st.chat_message('user'):
        st.markdown(user_input)
    
    # Generate and display assistant response
    with st.chat_message('assistant'):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # Show thinking indicator
            with st.spinner('🤔 Thinking...'):
                # Stream workflow events
                final_state = None
                for event in workflow.stream(
                    {'messages': [HumanMessage(content=user_input)]},
                    config=CONFIG,
                    stream_mode='values'
                ):
                    final_state = event
            
            # Extract response from final state
            if final_state and 'messages' in final_state:
                messages = final_state['messages']
                
                # Look for the last AI message with content
                for message in reversed(messages):
                    if isinstance(message, AIMessage):
                        # Handle string content
                        if isinstance(message.content, str) and message.content.strip():
                            full_response = message.content
                            break
                        # Handle list content (structured output)
                        elif isinstance(message.content, list):
                            text_parts = []
                            for block in message.content:
                                if isinstance(block, dict) and block.get('type') == 'text':
                                    text_parts.append(block.get('text', ''))
                                elif hasattr(block, 'text'):
                                    text_parts.append(block.text)
                                elif isinstance(block, str):
                                    text_parts.append(block)
                            full_response = ''.join(text_parts)
                            if full_response.strip():
                                break
            
            # Display response or error
            if full_response and full_response.strip():
                response_placeholder.markdown(full_response)
                st.session_state['thread_histories'][st.session_state['thread_id']].append(
                    {'role': 'assistant', 'content': full_response}
                )
            else:
                error_msg = "⚠️ No response generated. Please try rephrasing your question."
                response_placeholder.warning(error_msg)
                # Don't save error messages to history
        
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            response_placeholder.error(error_msg)
            # Log detailed error for debugging
            st.error(f"Detailed error: {type(e).__name__}: {str(e)}")
            # Don't save error messages to history