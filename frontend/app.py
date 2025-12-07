import uuid
import streamlit as st
import requests
from api_client import api_chat, api_generate_itinerary

# =========================
# ✅ PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Travel Planner AI",
    layout="wide",
)

# =========================
# ✅ GLOBAL THEME
# =========================
st.markdown(
    """
<style>
.main {
    padding-top: 1.5rem;
}
.block-container {
    padding-left: 3rem;
    padding-right: 3rem;
}

.card {
    background: rgba(255,255,255,0.05);
    padding: 1.2rem;
    border-radius: 16px;
    margin-bottom: 1rem;
    border: 1px solid rgba(255,255,255,0.08);
}

.big-title {
    font-size: 2.3rem;
    font-weight: 700;
}

.subtle {
    color: #bbb;
    font-size: 0.9rem;
}

.route-box {
    padding: 1rem;
    border-radius: 14px;
    background: rgba(0,0,0,0.35);
    border: 1px solid rgba(255,255,255,0.07);
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# ✅ SESSION STATE
# =========================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "itinerary_text" not in st.session_state:
    st.session_state.itinerary_text = ""

if "routes" not in st.session_state:
    st.session_state.routes = None

# =========================
# ✅ HEADER
# =========================
st.markdown("<div class='big-title'>🧳 Travel Planner AI</div>", unsafe_allow_html=True)
st.markdown("<div class='subtle'>Agentic RAG • Live Weather • Smart Routing</div>", unsafe_allow_html=True)
st.markdown("---")

# =========================
# ✅ SIDEBAR (ITINERARY INPUT)
# =========================
with st.sidebar:
    st.header("🧭 Trip Preferences")

    destination = st.text_input("Destination city", value="Goa")
    days = st.number_input("Days", min_value=1, max_value=10, value=3)
    budget = st.number_input("Total budget (₹)", min_value=100.0, value=500.0)

    interests = st.multiselect(
        "Interests",
        ["beach", "culture", "history", "shopping", "nightlife", "food"],
        default=["food", "culture"],
    )

    food_pref = st.selectbox(
        "Food preference",
        ["no preference", "vegetarian", "non-veg"],
        index=0,
    )

    st.markdown("---")

    if st.button("✨ Generate Itinerary", use_container_width=True):
        try:
            with st.spinner("Planning your trip..."):
                res = api_generate_itinerary(
                    st.session_state.session_id,
                    destination,
                    int(days),
                    float(budget),
                    interests,
                    food_pref,
                )
                st.session_state.itinerary_text = res["itinerary_text"]
            st.success("Itinerary Ready ✅")
        except Exception as e:
            st.error(f"❌ {e}")

    if st.button("🔄 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.success("Chat cleared!")

# =========================
# ✅ TABS LAYOUT
# =========================
tab1, tab2 = st.tabs(
    ["🧭 Itinerary & Chat", "🗺️ Routes"]
)

with tab1:
    # =========================
    # ✅ ITINERARY DISPLAY (TOP)
    # =========================
    st.markdown("### 🧾 Your Travel Itinerary")

    if st.session_state.itinerary_text:
        st.markdown(
            """
        <style>
        .itinerary-box {
            background: rgba(255,255,255,0.05);
            padding: 1.5rem;
            border-radius: 14px;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255,255,255,0.08);
        }

        .itinerary-box h1 { font-size: 16px; }
        .itinerary-box h2 { font-size: 16px; }
        .itinerary-box h3 { font-size: 14px; }
        .itinerary-box h4 { font-size: 14px; }

        .itinerary-box p,
        .itinerary-box li {
            font-size: 12px;
            line-height: 1.6;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<div class='itinerary-box'>{st.session_state.itinerary_text}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Generate an itinerary using the sidebar to view it here.")

    st.markdown("---")

    # =========================
    # ✅ CHAT SECTION (BOTTOM)
    # =========================
    st.markdown("### 💬 Chat with Travel Assistant")

    chat_card_style = """
    <style>
    .chat-box {
        background: rgba(0,0,0,0.25);
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    </style>
    """
    st.markdown(chat_card_style, unsafe_allow_html=True)

    st.markdown("<div class='chat-box'>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    name = st.text_input("Your name", value="Traveler")

    user_msg = st.chat_input("Ask anything about your trip...")

    if user_msg:
        try:
            st.session_state.messages.append(
                {"role": "user", "content": user_msg}
            )

            with st.spinner("Thinking..."):
                res = api_chat(
                    st.session_state.session_id,
                    user_msg,
                    name if name.strip() else None,
                )

            st.session_state.messages.append(
                {"role": "assistant", "content": res["reply"]}
            )

            st.rerun()

        except Exception as e:
            st.error(f"❌ Backend error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ✅ TAB 2 — ROUTE PLANNER
# =========================================================
with tab2:
    st.markdown("### 🗺️ Smart Route Planner")

    col1, col2, col3 = st.columns([1, 1, 0.6])

    with col1:
        route_origin = st.text_input("From City", value="Mumbai")

    with col2:
        route_destination = st.text_input("To City", value="Goa")

    with col3:
        if st.button("🔎 Find Routes", use_container_width=True):
            try:
                with st.spinner("Calculating best routes..."):
                    res = requests.post(
                        "http://127.0.0.1:8000/routes",
                        json={
                            "origin": route_origin,
                            "destination": route_destination,
                        },
                        timeout=30,
                    )
                    res.raise_for_status()
                    st.session_state.routes = res.json()

                st.success("Routes loaded ✅")

            except Exception as e:
                st.error(f"❌ {e}")

    st.markdown("---")

    routes = st.session_state.get("routes")

    if routes and isinstance(routes, dict) and "recommended" in routes:

        st.subheader(
            f"🚦 Travel options from **{route_origin} → {route_destination}**"
        )

        def route_card(title, badge, icon, route_data):
            hours = route_data["total_time_min"] // 60
            mins = route_data["total_time_min"] % 60
            distance = route_data["total_distance_km"]

            with st.expander(
                f"{icon} {title}  |  ⏱ {hours}h {mins}m  |  📏 {distance} km  |  {badge}"
            ):
                st.markdown("<div class='route-box'>", unsafe_allow_html=True)
                for seg in route_data["segments"]:
                    st.markdown(
                        f"- **{seg['mode'].upper()}**  \n"
                        f"  {seg['from']} → {seg['to']}  \n"
                        f"  📏 {seg['distance_km']} km • ⏱ {seg['time_min']} min"
                    )
                st.markdown("</div>", unsafe_allow_html=True)

        route_card(
            "Train + Taxi (Balanced)", "⭐ BEST", "⭐", routes["recommended"]
        )

        route_card(
            "Mostly Train", "⚡ FASTEST", "⚡", routes["fastest"]
        )

        route_card(
            "Full Bus Journey", "💸 CHEAPEST", "💸", routes["cheapest"]
        )

    elif routes and "error" in routes:
        st.error(f"Backend error: {routes['error']}")
