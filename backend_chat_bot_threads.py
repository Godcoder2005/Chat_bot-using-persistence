from langgraph.graph import StateGraph
from langgraph.constants import START, END
from langgraph.graph.message import add_messages
from typing import TypedDict,Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage,BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint,ChatHuggingFace

load_dotenv()

class chat_bot(TypedDict):
    messages:Annotated[list[BaseMessage],add_messages]

llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
    task="text-generation",
    max_new_tokens=1000,
    temperature=0.5
)

chat_model = ChatHuggingFace(llm=llm)

def chat(state:chat_bot)->chat_bot:
    message = state['messages']
    response = chat_model.invoke(message)
    return {'messages':[response]}

check_point = MemorySaver()
graph = StateGraph(chat_bot)

# Add node to the graph
graph.add_node('chat',chat)

# Connecting the edges of the graph
graph.add_edge(START,'chat')
graph.add_edge('chat',END)

# Compile the graph
workflow = graph.compile(checkpointer=check_point)