from __future__ import annotations

import os

import streamlit as st
from langchain.chat_models import init_chat_model

from config import PROMPTS, TOPICS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODEL_NAME = "gpt-5.4"
TOKENS_PER_WORD = 1.33
DEFAULT_TARGET_WORDS = 1000

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Story Generator",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Build user message
# ---------------------------------------------------------------------------
def build_user_message(topic: str, target_words: int) -> str:
    target_tokens = round(target_words * TOKENS_PER_WORD)
    return (
        f"Story topic: {topic}\n\n"
        f"Target length: at least {target_tokens} tokens (~{target_words} words)."
    )


# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "story" not in st.session_state:
    st.session_state.story = ""
if "generating" not in st.session_state:
    st.session_state.generating = False
if "edited_prompt" not in st.session_state:
    st.session_state.edited_prompt = None
if "selected_prompt" not in st.session_state:
    st.session_state.selected_prompt = list(PROMPTS.keys())[0]


# ---------------------------------------------------------------------------
# Layout — two columns
# ---------------------------------------------------------------------------
st.title("Story Generator")

col_left, col_right = st.columns([4, 6], gap="large")

# ═══════════════════════════════════════════════════════════════════════════
# LEFT PANEL — Controls
# ═══════════════════════════════════════════════════════════════════════════
with col_left:
    with st.container(border=True):
        # ── API Key ───────────────────────────────────────────────────────
        st.subheader("OpenAI API Key")
        api_key = st.text_input(
            "API Key is not stored.",
            type="password",
            placeholder="sk-...",
            label_visibility="collapsed",
        )

        # ── Topic ─────────────────────────────────────────────────────────
        st.subheader("Topic")
        topic = st.text_area(
            "Topic",
            height=20,
            placeholder="Describe the story topic / theme…",
            label_visibility="collapsed",
        )

        # ── Target Words ──────────────────────────────────────────────────
        st.subheader("Target Words")
        target_words = st.number_input(
            "Target Words",
            min_value=100,
            max_value=10000,
            value=DEFAULT_TARGET_WORDS,
            step=100,
            label_visibility="collapsed",
        )

        # ── System Prompt ──────────────────────────────────────────
        st.subheader("Prompt")

        st.selectbox(
            "Prompt preset",
            options=list(PROMPTS.keys()),
            key="selected_prompt",
            on_change=lambda: st.session_state.update(edited_prompt=None),
            label_visibility="collapsed",
        )

        # ── Edit / Reset toggle ───────────────────────────────────────────
        edit_toggle = st.toggle("Edit prompt")
        
        if not edit_toggle and st.session_state.edited_prompt is not None:
            st.session_state.edited_prompt = None

        current_prompt = (
            st.session_state.edited_prompt
            or PROMPTS[st.session_state.selected_prompt]
        )

        if edit_toggle:
            edited = st.text_area(
                "System Prompt Editor",
                value=current_prompt,
                height=300,
                key=f"prompt_editor_{st.session_state.selected_prompt}",
                label_visibility="collapsed",
            )
            st.session_state.edited_prompt = (
                edited if edited != PROMPTS[st.session_state.selected_prompt] else None
            )
            current_prompt = (
                st.session_state.edited_prompt
                or PROMPTS[st.session_state.selected_prompt]
            )

        if st.session_state.edited_prompt:
            st.caption("⚠️ Prompt has been customized")

        st.divider()

        # ── Generate button ───────────────────────────────────────────────
        can_generate = bool(api_key) and bool(topic.strip())
        generate_clicked = st.button(
            "🚀 Generate Story",
            type="primary",
            disabled=not can_generate,
            use_container_width=True,
        )

        if not api_key:
            st.caption("⬆️ Enter your API key to begin")
        elif not topic.strip():
            st.caption("⬆️ Enter a topic to generate")


# ═══════════════════════════════════════════════════════════════════════════
# RIGHT PANEL — Story output
# ═══════════════════════════════════════════════════════════════════════════
with col_right:
    view_mode = st.radio(
        "View Mode",
        options=["HTML", "Markdown"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # ── Generate with streaming ───────────────────────────────────────
    if generate_clicked and can_generate:
        os.environ["OPENAI_API_KEY"] = api_key
        model = init_chat_model(DEFAULT_MODEL_NAME)
        messages = [
            {"role": "system", "content": current_prompt},
            {"role": "user", "content": build_user_message(topic, target_words)},
        ]

        story_placeholder = st.empty()
        full_story = ""

        with st.spinner("Generating story…"):
            for chunk in model.stream(messages):
                token = getattr(chunk, "content", "")
                if token:
                    full_story += token
                    if view_mode == "Markdown":
                        story_placeholder.code(full_story, language="markdown")
                    else:
                        with story_placeholder.container(border=True, height=450):
                            st.markdown(full_story)

        st.session_state.story = full_story

        # ── Stats ─────────────────────────────────────────────────────
        words = len(full_story.split())
        chars = len(full_story)
        tokens_est = round(words / 0.75)

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Words", f"{words:,}")
        sc2.metric("Characters", f"{chars:,}")
        sc3.metric("Tokens (est.)", f"{tokens_est:,}")

    # ── Display previously generated story ────────────────────────────
    elif st.session_state.story:
        if view_mode == "Markdown":
            st.code(st.session_state.story, language="markdown")
        else:
            with st.container(border=True, height=450):
                st.markdown(st.session_state.story)

        words = len(st.session_state.story.split())
        chars = len(st.session_state.story)
        tokens_est = round(words / 0.75)

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Words", f"{words:,}")
        sc2.metric("Characters", f"{chars:,}")
        sc3.metric("Tokens (est.)", f"{tokens_est:,}")
    else:
        st.info("Configure your settings and Generate Story.")

    # ── Download ───────────────────────────────────────────────────────
    if st.session_state.story:
        st.divider()
        btn_col1, btn_col2, _ = st.columns([1, 1, 2])
        with btn_col2:
            st.download_button(
                "📋 Download Text",
                data=st.session_state.story,
                file_name="story.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with btn_col1:
            st.download_button(
                "📄 Download Markdown",
                data=st.session_state.story,
                file_name="story.md",
                mime="text/markdown",
                use_container_width=True,
            )
        
