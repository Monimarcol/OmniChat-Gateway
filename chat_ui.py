import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.title("OmniChat Gateway")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "stage" not in st.session_state:
    st.session_state.stage = "hardware"
if "hardware" not in st.session_state:
    st.session_state.hardware = None
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []
if "selected_model" not in st.session_state:
    st.session_state.selected_model = None
if "selected_display_name" not in st.session_state:
    st.session_state.selected_display_name = None


def _get(path: str, **kwargs):
    return requests.get(f"{API_URL}{path}", timeout=kwargs.pop("timeout", 10), **kwargs)


def _post(path: str, **kwargs):
    return requests.post(f"{API_URL}{path}", timeout=kwargs.pop("timeout", 10), **kwargs)


# ---------------------------------------------------------------------------
# Stage 1: hardware detection
# ---------------------------------------------------------------------------
if st.session_state.stage == "hardware":
    st.subheader("Step 1 of 3: checking your hardware")
    if st.session_state.hardware is None:
        try:
            resp = _get("/hardware")
            resp.raise_for_status()
            st.session_state.hardware = resp.json()
        except Exception as e:
            st.error(f"Could not reach the backend to detect hardware: {e}")
            st.stop()

    hw = st.session_state.hardware
    st.table(
        {
            "CPU": [hw["cpu_model"]],
            "Physical cores": [hw["physical_cores"]],
            "Logical cores": [hw["logical_cores"]],
            "RAM total (GB)": [hw["ram_total_gb"]],
            "RAM available (GB)": [hw["ram_available_gb"]],
            "GPU": [hw["gpu"]["name"]],
            "VRAM (GB)": [hw["gpu"]["vram_gb"] or "n/a"],
            "Tier": [hw["tier"]],
        }
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Continue"):
            st.session_state.stage = "usecase"
            st.rerun()
    with col2:
        if st.button("Re-scan hardware"):
            try:
                resp = _get("/hardware", params={"force_refresh": True})
                resp.raise_for_status()
                st.session_state.hardware = resp.json()
                st.rerun()
            except Exception as e:
                st.error(f"Re-scan failed: {e}")

# ---------------------------------------------------------------------------
# Stage 2: use case description
# ---------------------------------------------------------------------------
elif st.session_state.stage == "usecase":
    st.subheader("Step 2 of 3: what will you use this for?")
    description = st.text_area(
        "Describe what you'll primarily be doing "
        '(e.g. "drafting blog posts and brainstorming article ideas")',
        height=100,
    )
    if st.button("Get model recommendations", disabled=not description.strip()):
        try:
            with st.spinner("Thinking about the best model for your device and use case..."):
                resp = _post("/models/recommend", json={"description": description}, timeout=60)
                resp.raise_for_status()
                st.session_state.recommendations = resp.json()
            st.session_state.stage = "recommend"
            st.rerun()
        except Exception as e:
            st.error(f"Recommendation request failed: {e}")

# ---------------------------------------------------------------------------
# Stage 3: pick a model (recommended or manual), ensure it's pulled
# ---------------------------------------------------------------------------
elif st.session_state.stage == "recommend":
    st.subheader("Step 3 of 3: pick a model")
    recs = st.session_state.recommendations

    chosen_id = None
    if recs:
        labels = [f"{r['display_name']} -- {r['rationale']}" for r in recs]
        labels[0] = f"(Best match) {labels[0]}"
        choice = st.radio("Recommended for you:", labels, index=0)
        chosen_id = recs[labels.index(choice)]["id"]
    else:
        st.warning("No recommendations came back -- pick a model manually below.")

    with st.expander("Advanced: pick any model manually"):
        try:
            all_models = _get("/models").json()
        except Exception as e:
            all_models = []
            st.error(f"Could not load the model catalog: {e}")
        manual_labels = [m["display_name"] for m in all_models]
        manual_choice = st.selectbox("All catalog models", ["(use recommendation above)"] + manual_labels)
        if manual_choice != "(use recommendation above)":
            chosen_id = all_models[manual_labels.index(manual_choice)]["id"]

    if st.button("Confirm and start chat", disabled=chosen_id is None):
        try:
            with st.spinner("Setting up the model -- this can take a while the first time a model is pulled..."):
                resp = _post(f"/models/{chosen_id}/ensure", timeout=None)
                resp.raise_for_status()
                ollama_tag = resp.json()["ollama_tag"]
            all_models = _get("/models").json()
            display_name = next(m["display_name"] for m in all_models if m["id"] == chosen_id)
            st.session_state.selected_model = f"ollama/{ollama_tag}"
            st.session_state.selected_display_name = display_name
            st.session_state.stage = "chat"
            st.rerun()
        except Exception as e:
            st.error(f"Could not set up that model: {e}")

# ---------------------------------------------------------------------------
# Stage 4: chat
# ---------------------------------------------------------------------------
elif st.session_state.stage == "chat":
    st.caption(f"Using {st.session_state.selected_display_name}")
    if st.button("Change model"):
        st.session_state.stage = "recommend"
        st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []
        try:
            resp = _get(f"/history/{st.session_state.conversation_id}")
            if resp.status_code == 200:
                st.session_state.messages = resp.json()
        except Exception:
            st.warning("Could not connect to backend to load history.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask something..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            payload = {
                "model": st.session_state.selected_model,
                "conversation_id": st.session_state.conversation_id,
                "messages": st.session_state.messages,
            }
            response = _post("/chat", json=payload, timeout=120)
            if response.status_code == 200:
                ai_response = response.json()["response"]
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                with st.chat_message("assistant"):
                    st.markdown(ai_response)
            else:
                st.error("Backend Error: Could not get response.")
        except Exception as e:
            st.error(f"Connection Error: {e}")
