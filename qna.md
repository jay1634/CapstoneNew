## 0. Big Picture (What your system actually is)

Your app = **Agentic Travel Planner** with:

* **FastAPI backend** – REST API: `/chat`, `/generate_itinerary`, `/routes`
* **LangChain Agent** – decides when to call:

  * `weather_tool` → *live weather*
  * `routes_tool` → *multi-modal routes*
  * `rag_tool` → *company knowledge (RAG)*
* **RAG pipeline** – TF-IDF + FAISS over your text corpus
* **Groq LLM** – `llama-3.1-8b-instant` for fast reasoning
* **SQLite memory** – stores chat + user prefs per `session_id` with TTL (auto delete after some time) 

Front-end (Streamlit) just calls these APIs and displays:

* Smart itinerary
* Chat responses
* Route suggestions

---

## 1️⃣ `config.py` – Central configuration

**What it contains:**

* `BASE_DIR` – base project path
* `CORPUS_DIR = "data/corpus"` – where your RAG text files live
* `OLLAMA_MODEL_NAME` – for local models (currently `mistral` but not critical)
* `GROQ_API_KEY`, `OPENWEATHER_API_KEY` – secrets for LLM and weather

**Concepts:**

* Central config → avoids hard-coding paths and keys inside logic files
* Easier to switch folders or models later

**Why not `.env` + `python-dotenv` here?**

* For a capstone project, **keeping config in one file** is easier to show in viva and debug.
* In production you *would* use env vars, but here clarity > enterprise setup, and you can still mention that.

**Viva answer example:**

> *“I centralized all project paths and API keys in `config.py` to avoid scattering constants across files. For a production app I’d move secrets to environment variables, but here this makes the codebase easy to understand for reviewers.”*

---

## 2️⃣ `memory.py` – Persistent conversation + prefs with TTL

This is your **session memory**, implemented using **SQLite** with an automatic **time-to-live (TTL)**. 

### What it does

* Creates `memory.db` with 2 tables:

  * `chat_history(session_id, role, content, ts)`
  * `user_prefs(session_id, prefs JSON)`
* Exposes:

  * `get_history(session_id)` → list of `"User: ..." / "Assistant: ..."` lines
  * `add_turn(session_id, text)` → insert a message with timestamp
  * `get_prefs(session_id)` / `update_prefs(session_id, updates)` → JSON blob per session
  * `cleanup_old_data()` → delete messages older than `TTL_SECONDS` (e.g. 30 mins)
  * `delete_session_data(session_id)` → explicit delete if needed

### Key concepts

* **SQLite**: lightweight, file-based database – no external DB server.
* **TTL logic**:

  * At startup: `self.cleanup_old_data()` deletes old rows
  * On every `get_history()` and `add_turn()` you call `cleanup_old_data()` again → ensures expired sessions are cleaned frequently. 
* **JSON prefs**:

  * `prefs` column holds a JSON string; Python dict is serialized with `json.dumps`/`loads`.

### Why SQLite and not:

* **In-memory Python dict only?**

  * Would be lost when server restarts.
  * Harder to debug / inspect.
  * SQLite lets you *open the DB in a viewer* and show it in viva.

* **Redis / Postgres?**

  * Overkill for a local capstone.
  * Needs extra service to run.
  * SQLite is built into Python, zero extra infra.

**Viva-style defence:**

> *“I used SQLite instead of an in-memory dict so that session history and preferences survive backend restarts and can be inspected with any SQLite viewer. To avoid unbounded growth, I added a TTL mechanism which deletes chat messages older than 30 minutes; this gives the effect of ‘session auto-expiry’ without needing Redis.”* 

---

## 3️⃣ `rag_pipeline.py` – TF-IDF + FAISS RAG engine

This file is your **knowledge retrieval engine** over company docs. 

### What it does

* Reads `.txt` files from `CORPUS_DIR` (`data/corpus`)
* Splits long text into **chunks** with `RecursiveCharacterTextSplitter`:

  * `chunk_size=700`, `chunk_overlap=100`
* Converts each chunk to TF-IDF vector with `TfidfVectorizer`
* Indexes the vectors in **FAISS** (`IndexFlatL2`)
* Saves:

  * FAISS index → `tfidf.index`
  * vectorizer → `tfidf_vectorizer.pkl`
  * chunks → `tfidf_chunks.pkl`
* `retrieve_context(question, k=4)`:

  * Lazily calls `_build_vectorstore()` once
  * Encodes question with same vectorizer
  * Searches FAISS for top-`k` similar chunks
  * Returns `combined_text` (joined content) and the underlying `Document` objects

### Key concepts

* **TF-IDF** (classic IR, not deep embeddings):

  * Term Frequency–Inverse Document Frequency
  * Gives weight to words that are frequent in a document but rare in the corpus.

* **FAISS**:

  * High-performance similarity search library.
  * Even though TF-IDF is traditional, it’s still just vectors → FAISS works fine.

* **Lazy build**:

  * First time `retrieve_context()` is called, it builds the vector store if files don’t exist.
  * Later calls just load from disk, so retrieval is fast. 

### Why TF-IDF + FAISS and not embeddings?

* **Embeddings (e.g., sentence-transformers)**:

  * Better semantic matching, but:
  * Heavier dependencies, often require GPU or slow CPU runtime.
  * Might need external services (OpenAI embeddings, etc.).

* **Your constraints:**

  * Offline / low-resource environment.
  * Corpus is small and domain-specific (company policies, packages).
  * TF-IDF is **deterministic, fast, simple**, and good enough.

**Viva answer example:**

> *“For RAG, I chose a TF-IDF + FAISS approach. The corpus is small and highly specific (company policies, package details), so classical IR is sufficient and more lightweight than deep embeddings. FAISS gives me fast similarity search even with TF-IDF vectors, and I persist the index and vectorizer to disk so I don’t recompute them every time.”* 

---

## 4️⃣ `llm_client.py` – Thin wrapper over Groq LLM

**What it does:**

* Creates a `Groq` client using `GROQ_API_KEY`.
* Defines `chat_with_llm(prompt, system_message, history)`:

  * Builds `messages` = `[system, ...history..., user]`
  * Calls `client.chat.completions.create(...)` with:

    * `model="llama-3.1-8b-instant"`
    * `temperature=0.4`
    * `max_tokens=800`
  * Returns the `content` of the first choice.

### Concepts

* **Separation of concerns**:

  * All raw LLM calls in one file → easier to swap Groq with Gemini / OpenAI later.
* **System vs user messages**:

  * `system_message` sets global behavior.
  * `history` reconstructs chat context from `memory`.

### Why this vs using LangChain LLM object here?

* You already use **LangChain** for *agentic tools*, but `chat_with_llm` is a **simple, non-agent** direct call (used e.g. in itinerary).
* Direct API use:

  * Fewer layers.
  * More control over params.
  * Easier to explain in viva.

> *“I kept a direct Groq client wrapper for simple generation tasks like itinerary creation, instead of going through LangChain’s abstractions everywhere. This makes the control plane simpler and shows I understand the raw API as well.”*

---

## 5️⃣ `langchain_agent.py` – Your agent “brain”

This file configures the **Agentic tool-calling logic**.

### Main parts

1. **Input schemas**: `WeatherInput`, `RoutesInput`, `RagInput`

   * Using `pydantic.BaseModel` ensures structured args and validation.

2. **Tools**:

   * `weather_tool` → wraps `get_live_weather(city)`
   * `routes_tool` → wraps `get_multiple_routes(origin, destination)`
   * `rag_tool` → wraps `rag_fn(query)` which calls `retrieve_context(query, k=4)`

3. **LLM**:

   * `ChatGroq(...)` using `llama-3.1-8b-instant`

4. **Prompt template**:

   * System message with strict rules:

     * Must use tool output if tool is called
     * Must use actual weather numbers
     * Must not talk about tools/APIs
   * History: `MessagesPlaceholder("chat_history")`
   * Current user message: `"{input}"`
   * `agent_scratchpad`: tool reasoning steps

5. **Agent + Executor**:

   * `create_tool_calling_agent(llm, tools, prompt)` → returns agent
   * `AgentExecutor(agent=agent, tools=tools, return_intermediate_steps=True)`

6. **`agentic_answer(session_id, message, name)`**:

   * Saves user name into prefs (optional personalization)
   * Loads chat history + prefs from SQLite memory
   * Builds `context_block` from user prefs and appends to input
   * Calls `agent_executor.invoke({"input": message + context_block, "chat_history": chat_history})`
   * If tools were used (`intermediate_steps` not empty), it **forces a second pass**:

     * Builds `final_prompt` containing:

       * The user question
       * Raw tool results
       * Instruction: “Use ONLY this live data”
     * Calls `llm.invoke(final_prompt)` to get final grounded answer
   * Stores user + assistant turns via `memory.add_turn(...)`

### Why LangChain Agent and not manual calling?

* Without an agent:

  * You’d manually parse prompts, decide when to call `weather_tool`, etc.
  * More boilerplate, harder to extend as you add more tools (e.g., alert tool).
* With LangChain:

  * The LLM decides when to call which tool.
  * `StructuredTool` + `pydantic` keep args safe.
  * `AgentExecutor` manages the “Thought → Action → Observation → Answer” loop.

**Why the second LLM pass after tools?**

* Sometimes agents call a tool but then generate a generic answer, *ignoring* numbers.
* Your second pass uses *only* tool outputs and user question → reduces hallucination, more controlled.

**Viva defence:**

> *“I used LangChain’s tool-calling agent because I needed the model to autonomously decide when to call live APIs like weather and routes. To make sure the model doesn’t ignore tool results, I add a second, constrained LLM pass where I give it only the tool outputs and user question. This makes the response tightly grounded to real data.”*

---

## 6️⃣ `itinerary.py` – Structured itinerary generator

* Takes: `destination, days, budget, interests, food_pref, rag_context`
* Builds:

  * `system_prompt` = “You are a professional travel planner…” with **formatting rules**:

    * Use headings, bullet points, tables
    * No long paragraphs
* `user_prompt`:

  * Inserts all user parameters + example structure:

    * Destination Overview
    * Daily Itinerary (Day 1, Day 2, …)
    * Food & Restaurants
    * Local Transport
    * Safety & Rules
    * Final Budget Summary
  * Appends `rag_context[:4000]` so it includes actual city info
* Calls `chat_with_llm(...)` and returns the **Markdown** itinerary.

**Why LLM and not hard-coded templates?**

* Every trip can be very different (days, interests, budget).
* LLM can naturally vary text while respecting the skeleton structure.

**Why Markdown?**

* Perfect for Streamlit `st.markdown()`
* Easy to read in console or docs.
* Can be converted to HTML/PDF later if needed.

---

## 7️⃣ `guardrails.py` – Safety filter (hard gate)

You didn’t paste it here, but from our earlier conversation:

* Uses simple **profanity / sensitive topic detection** (e.g., word lists).
* `violates_guardrails(text)` → boolean
* `guardrail_response()` → safe generic message

In `main.py`:

```python
if violates_guardrails(body.message):
    return ChatResponse(
        reply=guardrail_response(),
        used_rag=False
    )
```

So unsafe queries never even reach the agent / LLM.

**Why simple Python guardrails and not AI-based moderation?**

* Deterministic
* Always-on
* No extra API cost
* Easy to show in viva and explain

---

## 8️⃣ `main.py` – FastAPI backend glue

Defines:

* Data models with `pydantic`:

  * `ChatRequest`, `ChatResponse`
  * `ItineraryRequest`, `ItineraryResponse`
  * `RouteRequest`
* FastAPI app + CORS config
* Endpoints:

  * `GET /` – health check string
  * `POST /chat`:

    * Runs guardrails
    * Calls `agentic_answer`
    * Returns `ChatResponse`
  * `POST /generate_itinerary`:

    * Calls `retrieve_context` with destination
    * Calls `build_itinerary`
    * Stores itinerary and prefs into `memory.update_prefs`
    * Returns itinerary text
  * `POST /routes`:

    * Calls `get_multiple_routes(origin, destination)` → returns structured routes

**Why FastAPI vs Flask/Django?**

* Automatic docs at `/docs` → brilliant for debugging and viva demo.
* Async-first if you need it.
* Very popular for modern ML backends.

**Viva answer:**

> *“I chose FastAPI for the backend because it provides automatic Swagger documentation, type-checked request/response models via Pydantic, and async support if I later want to parallelize API calls. It fits the microservice-style design of an LLM backend better than a heavy framework like Django.”*

---

## 9️⃣ `build_vector_store.py` – One-off FAISS builder (if you keep it)

If you have this script, it’s essentially a CLI to:

* Scan `data/corpus`
* Chunk docs
* Build FAISS + vectorizer + chunks pickle

You *can* rely only on `rag_pipeline.py` (which lazy-builds), but having this script is useful when:

* You want to precompute and test index building
* You want to rebuild index manually after adding docs

---

## 🔟 Sample Viva Questions + Strong Answers

**Q1. Why did you use RAG instead of just LLM?**

> “LLMs are powerful but can hallucinate or miss company-specific policies like cancellation rules or partner hotels. By adding RAG, I constrain the model to answer based on my curated corpus. That means: cancellation/ refund answers come from `cancellation_policy.txt` or `company_policy.txt`, not from the model’s imagination. It also lets the system stay up-to-date by just updating text files and rebuilding the index.”

---

**Q2. Why TF-IDF instead of sentence embeddings? Aren’t embeddings better?**

> “Embeddings are better for very large, diverse corpora, but they come with compute and dependency overhead. My corpus is small, domain-specific and mostly formal text. TF-IDF captures keyword-based relevance very well here, with deterministic behavior and low resource use. It also avoids depending on additional paid APIs or huge models, which is appropriate for a student capstone running on modest hardware.” 

---

**Q3. Why Groq Llama-3.1-8B and not GPT-4?**

> “GPT-4 is stronger, but it is slower and more expensive. For an interactive travel assistant, latency is critical — responses must feel instant. Groq’s Llama-3.1-8B on LPUs gives very fast inference and is strong enough to handle itinerary generation, tool calling and reasoning. That’s a better trade-off for a real-time system where user experience is important.”

---

**Q4. How is your memory stored and why do you delete it after some time?**

> “I store chat history and user preferences in a local SQLite database. That lets me preserve continuity across multiple API calls and even across server restarts, unlike in-memory dictionaries. To avoid unbounded growth and respect user privacy, I attached a TTL: any chat messages older than 30 minutes are automatically deleted whenever new messages are read or written. So every session naturally expires after inactivity.” 

---

**Q5. What is the advantage of using LangChain’s Agent instead of directly calling tools from Python?**

> “LangChain’s Agent lets the model itself decide when and how to call tools like weather, routes or RAG. I only define the tools and the system prompt. This makes the system extensible: adding a new tool like ‘transport alerts’ means I just wrap it as another `StructuredTool`, and the agent can start using it. If I hard-coded tool calls in Python, I would have to manually branch on every possible query type, which doesn’t scale.”

---

If you want, next step I can:

* Help you prepare **separate, short viva notes** per file (like 2–3 lines you can memorize), or
* Help you design the **alert tool** (flight/train/road) in the same pattern as weather/routes so it plugs directly into `langchain_agent.py`.

