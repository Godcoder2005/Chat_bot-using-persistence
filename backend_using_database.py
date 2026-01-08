from langgraph.graph import StateGraph
from langgraph.constants import START, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
import sqlite3

load_dotenv()

class chat_bot(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
    task="text-generation",
    max_new_tokens=1000,
    temperature=0.5
)

chat_model = ChatHuggingFace(llm=llm)

def chat(state: chat_bot) -> chat_bot:
    message = state['messages']
    response = chat_model.invoke(message)
    return {'messages': [response]}

conn = sqlite3.connect('chat_history.db', check_same_thread=False)
check_point = SqliteSaver(conn=conn)
graph = StateGraph(chat_bot)

# Add node to the graph
graph.add_node('chat', chat)

# Connecting the edges of the graph
graph.add_edge(START, 'chat')
graph.add_edge('chat', END)

# Compile the graph
workflow = graph.compile(checkpointer=check_point)

def get_default_threads():
    """Get all available thread IDs from the database"""
    all_threads = set()
    for checkpoint in check_point.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)

def get_thread_messages(thread_id):
    """Get all messages for a specific thread"""
    try:
        config = {'configurable': {'thread_id': thread_id}}
        state = workflow.get_state(config)
        
        if state and 'messages' in state.values:
            # Convert BaseMessage objects to dict format
            messages = []
            for msg in state.values['messages']:
                if hasattr(msg, 'type'):
                    role = 'user' if msg.type == 'human' else 'assistant'
                    messages.append({
                        'role': role,
                        'content': msg.content
                    })
            return messages
        return []
    except Exception as e:
        print(f"Error loading messages for thread {thread_id}: {e}")
        return []