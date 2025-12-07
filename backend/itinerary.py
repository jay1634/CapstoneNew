from .llm_client import chat_with_llm


def build_itinerary(
    destination: str,
    days: int,
    budget: float,
    interests: list,
    food_pref: str | None,
    rag_context: str,
) -> str:
    interests_text = ", ".join(interests) if interests else "general sightseeing"
    food_text = food_pref if food_pref else "no specific preference"

    system_prompt = """
You are a professional travel planner AI.

CRITICAL RULES (MANDATORY):
1. The FINAL TOTAL budget MUST NOT exceed the user budget.
2. ALL individual costs (stay + food + transport + activities + misc) MUST sum EXACTLY to the given budget.
3. If budget is low, you MUST reduce activity and transport costs.
4. You MUST internally adjust all values to stay within budget.
5. NEVER exceed the budget even slightly.

FORMAT RULES:
- Use clean MARKDOWN only
- Use proper headings (##, ###)
- Use bullet points (-)
- Use a proper budget table
- NO long paragraphs
- NO ===== lines
"""


    user_prompt = f"""
Create a beautiful, easy-to-read {days}-day travel itinerary.

Trip Details:
- Destination: {destination}
- Budget: ₹{budget}
- Interests: {interests_text}
- Food preference: {food_text}

You MUST follow this exact structure:



Destination Overview

- **Best time to visit:**  
  
- **Typical weather:**  
  
- **Travel tips:**  
 
---

## 🗓 Daily Itinerary

### Day 1
**Morning**
- ...
- ...

**Afternoon**
- ...
- ...

**Evening**
- ...
- ...

**Estimated Cost:** ₹...

(Repeat same structure until Day {days})

---

## 🍽 Food & Restaurants
- **Breakfast:** ...
- **Lunch:** ...
- **Dinner:** ...

---

## 🚕 Local Transport
- **Modes available:** ...
- **Average daily cost:** ₹...

---

## 🛡 Safety & Local Rules
- **Safety tips:**
  - ...
  - ...
- **Local rules:**
  - ...
  - ...

---


FINAL BUDGET SUMMARY


You MUST ensure:

Stay + Food + Transport + Activities + Misc = ₹{budget}
TOTAL MUST BE EXACTLY ₹{budget}

Create a clean markdown table with these rows:
- Stay
- Food
- Transport
- Activities
- Misc
- TOTAL


---

Use the following verified destination knowledge while generating:

{rag_context[:4000]}

Make it visually clean, well-spaced, and UI-friendly.
"""

    return chat_with_llm(
        prompt=user_prompt,
        system_message=system_prompt,
        history=None,
    )
