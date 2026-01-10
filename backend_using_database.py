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
import sqlite3
import requests
import json
from dotenv import load_dotenv

load_dotenv()

chat_model = ChatGoogleGenerativeAI(
    model='gemini-2.5-flash'
)

search_tool = DuckDuckGoSearchResults(region="us-en")

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
            return {"error": f"invalid operation {operation}"}
        
        return {
            "first_number": first_number,
            "second_number": second_number,
            "operation": operation,
            "result": results
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL. 
    """
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
        r = requests.get(url)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@tool
def get_weather(city:str)->dict:
    """
    fetch weather from the api using openweather
    """
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key=dfa803f3a2dc482ebfc81935261001&q={city}"
        r = requests.get(url)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

tools_llm = [search_tool, calculator, get_stock_price, get_weather]
llm_with_tools = chat_model.bind_tools(tools_llm)

class chat_bot(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat(state: chat_bot) -> chat_bot:
    """LLM may give the answer or it may use the tool"""
    message = state['messages']
    response = llm_with_tools.invoke(message)
    return {'messages': [response]}

tool_node = ToolNode(tools_llm)

conn = sqlite3.connect('chat_history.db', check_same_thread=False)
check_point = SqliteSaver(conn=conn)

graph = StateGraph(chat_bot)

graph.add_node('chat', chat)
graph.add_node('tools', tool_node)

graph.add_edge(START, 'chat')
graph.add_conditional_edges('chat', tools_condition)
graph.add_edge('tools', 'chat')

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