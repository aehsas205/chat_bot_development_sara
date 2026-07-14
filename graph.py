from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from chatbot import chatmodel, tools, State
from config import memory

# Initialize the graph builder with the correct State schema
graph_builder = StateGraph(State)

tool_node = ToolNode(tools=tools)

graph_builder.add_node("chatbot", chatmodel)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

