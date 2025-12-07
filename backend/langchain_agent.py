from typing import List
from pydantic import BaseModel

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import StructuredTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from .rag_pipeline import retrieve_context
from .tools.weather_tool import get_live_weather
from .tools.free_routes_tool import get_multiple_routes
from .memory import memory
from .config import GROQ_API_KEY


# =========================
# ✅ INPUT SCHEMAS
# =========================
class WeatherInput(BaseModel):
    city: str


class RoutesInput(BaseModel):
    origin: str
    destination: str


class RagInput(BaseModel):
    query: str


# =========================
# ✅ LLM
# =========================
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0.2,
)


# =========================
# ✅ TOOLS (STRUCTURED ✅)
# =========================
weather_tool = StructuredTool.from_function(
    func=get_live_weather,
    name="weather",
    description="Get LIVE real-time weather of a city.",
    args_schema=WeatherInput,
)

routes_tool = StructuredTool.from_function(
    func=get_multiple_routes,
    name="routes",
    description="Find travel routes between two cities.",
    args_schema=RoutesInput,
)

def rag_fn(query: str) -> str:
    context, _ = retrieve_context(query, k=4)
    return context

rag_tool = StructuredTool.from_function(
    func=rag_fn,
    name="rag",
    description="Search travel knowledge base.",
    args_schema=RagInput,
)

tools = [weather_tool, routes_tool, rag_tool]


# =========================
# ✅ STRICT PROMPT
# =========================
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a REAL-TIME travel assistant.

CRITICAL RULES:
1. If a tool is called, you MUST USE its output in the final answer.
2. If weather data is returned, you MUST quote exact temperature, humidity, description but don't be very formal about it just think about the weather you have provided and tell them weather it is good to go or not in a casual way
3. NEVER give generic seasonal info if live data exists.
4. NEVER mention tools, APIs, or internal processing.
5. Speak directly to the user.
""",
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)


# =========================
# ✅ AGENT
# =========================
agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt,
    
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    return_intermediate_steps=True,
)


# =========================
# ✅ MAIN AGENT ENTRY
# =========================
def agentic_answer(session_id: str, message: str, name: str | None = None) -> str:
    if name:
        memory.update_prefs(session_id, {"name": name})

    history_raw = memory.get_history(session_id)
    user_prefs = memory.get_prefs(session_id)

    context_block = ""
    if user_prefs:
        context_block = f"\n\nUSER CONTEXT (Persistent Memory):\n{user_prefs}\n"


    chat_history = []
    for msg in history_raw:
        if msg.startswith("User:"):
            chat_history.append(("human", msg.replace("User:", "").strip()))
        elif msg.startswith("Assistant:"):
            chat_history.append(("ai", msg.replace("Assistant:", "").strip()))

    result = agent_executor.invoke(
        {
            "input": message + context_block,
            "chat_history": chat_history,
        }
    )


    output = result["output"]
    steps = result.get("intermediate_steps", [])

    # =========================
    # ✅ FORCE TOOL OUTPUT (NO GENERIC REPLIES)
    # =========================
    if steps:
        tool_results = "\n".join([str(step[1]) for step in steps])

        final_prompt = f"""
USER QUESTION:
{message}

LIVE TOOL DATA (MANDATORY):
{tool_results}

INSTRUCTION:
Use ONLY this live data. Do NOT add seasonal or generic info.
Give a direct factual answer.
"""

        output = llm.invoke(final_prompt).content

    memory.add_turn(session_id, f"User: {message}")
    memory.add_turn(session_id, f"Assistant: {output}")

    return output
