from langgraph.graph import StateGraph
from langgraph.constants import START, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import sqlite3
import requests
import json
from typing import Optional
import tempfile
import os
from dotenv import load_dotenv

# Global Variable
RETRIEVER_STORE = {}

# Loading the dotenv files
load_dotenv()

# Chat model
chat_model = ChatGoogleGenerativeAI(
    model='gemini-2.5-flash'
)

# Chat embeddings for rag
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

def ingestion(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    """
    Build a FAISS retriever for the uploaded PDF and store it for the thread.
    Returns a summary dict that can be surfaced in the UI.
    """
    if not file_bytes:
        return {"error": "No file bytes received"}
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        temp_path = tmp.name  # Fixed: was 'tep.name'
    
    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        result = splitter.split_documents(docs)

        vectorstores = FAISS.from_documents(result, embeddings)
        retriever = vectorstores.as_retriever(
            search_type='similarity',
            search_kwargs={'k': 3}
        )

        RETRIEVER_STORE[thread_id] = retriever

        return {
            "filename": filename,
            "documents": len(docs),
            "chunks": len(result)
        }
    except Exception as e:
        return {"error": f"Error processing PDF: {str(e)}"}
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

# Tool no - 1 (which is inbuilt tool via langchain_community)
search_tool = DuckDuckGoSearchResults(region="us-en")

# Tool no - 2 (which is custom tool)
@tool
def calculator(first_number: float, second_number: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            results = first_number + second_number
        elif operation == "sub":
            results = first_number - second_number
        elif operation == "mul":
            results = first_number * second_number
        elif operation == "div":
            if second_number == 0:
                return {"error": "Division by zero is not possible"}
            results = first_number / second_number
        else:
            return {"error": f"Invalid operation {operation}"}
        
        return {
            "first_number": first_number,
            "second_number": second_number,
            "operation": operation,
            "result": results
        }
    except Exception as e:
        return {"error": str(e)}

# Tool no - 3 (which is custom tool)
@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL. 
    """
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
        r = requests.get(url)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# Tool no - 4 (which is custom tool)
@tool
def get_weather(city: str) -> dict:
    """
    Fetch weather from the API using WeatherAPI
    """
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key=dfa803f3a2dc482ebfc81935261001&q={city}"
        r = requests.get(url)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# Tool - 5 Which is very important and it is RAG 
@tool
def rag_implementation(query: str, thread_id: str) -> dict:
    """
    Retrieve relevant information from the PDF or any kind of document uploaded by user.
    Use this tool to fetch the relevant document from the PDF or anything uploaded 
    that might be solved using the uploaded PDF and in order to give more intellectual answers.
    """
    retriever = RETRIEVER_STORE.get(thread_id)

    if not retriever:
        return {'error': 'No PDF uploaded here'}
    
    try:
        result = retriever.invoke(query)  # Fixed: was 'response'

        context = [doc.page_content for doc in result]
        meta_data = [doc.metadata for doc in result]  # Fixed: was 'metadata.page_content'

        return {
            "query": query,
            "context": context,
            "metadata": meta_data
        }
    except Exception as e:
        return {"error": f"RAG error: {str(e)}"}

tools_llm = [search_tool, calculator, get_stock_price, get_weather, rag_implementation]
llm_with_tools = chat_model.bind_tools(tools_llm)

class chat_bot(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat(state: chat_bot) -> chat_bot:
    """LLM may give the answer or it may use the tool"""
    message = state['messages']
    response = llm_with_tools.invoke(message)
    return {'messages': [response]}

tool_node = ToolNode(tools_llm)

# Initializing the database
conn = sqlite3.connect('chat_history.db', check_same_thread=False)
check_point = SqliteSaver(conn=conn)

# Initialize the graph
graph = StateGraph(chat_bot)

# Creating the graph node 
graph.add_node('chat', chat)
graph.add_node('tools', tool_node)

# Connecting the nodes via edges
graph.add_edge(START, 'chat')
graph.add_conditional_edges('chat', tools_condition)
graph.add_edge('tools', 'chat')

# Compiling the graph
workflow = graph.compile(checkpointer=check_point)


def get_default_threads():
    """Get all available thread IDs from the database"""
    all_threads = set()
    try:
        for checkpoint in check_point.list(None):
            if 'configurable' in checkpoint.config and 'thread_id' in checkpoint.config['configurable']:
                all_threads.add(checkpoint.config['configurable']['thread_id'])
    except Exception as e:
        print(f"Error loading threads: {e}")
    return list(all_threads)

def get_thread_messages(thread_id):
    """Get all messages for a specific thread"""
    try:
        config = {'configurable': {'thread_id': thread_id}}
        state = workflow.get_state(config)
        
        if state and hasattr(state, 'values') and 'messages' in state.values:
            # Convert BaseMessage objects to dict format
            messages = []
            for msg in state.values['messages']:
                # Skip tool messages
                if hasattr(msg, 'type') and msg.type in ['human', 'ai']:
                    role = 'user' if msg.type == 'human' else 'assistant'
                    # Handle both string and list content
                    content = msg.content
                    if isinstance(content, list):
                        # Extract text from structured content
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                text_parts.append(item.get('text', ''))
                            elif isinstance(item, str):
                                text_parts.append(item)
                        content = ''.join(text_parts)
                    
                    if content and str(content).strip():
                        messages.append({
                            'role': role,
                            'content': str(content)
                        })
            return messages
        return []
    except Exception as e:
        print(f"Error loading messages for thread {thread_id}: {e}")
        return []