import streamlit as st


def apply_theme():
    theme = st.session_state.ui_theme

    if theme == "Dark":
        bg_color     = "#0e1117"
        side_bg      = "#1d2129"
        text_color   = "#fafafa"
        card_bg      = "#262730"
        overlay_bg   = "#262730"
        border_color = "rgba(150, 150, 150, 0.2)"
    elif theme == "Light":
        bg_color     = "#ffffff"
        side_bg      = "#f0f2f6"
        text_color   = "#1a1c22"
        card_bg      = "#f9f9fb"
        overlay_bg   = "#f9f9fb"
        border_color = "#d1d5db"
    else:  # System
        bg_color     = "transparent"
        side_bg      = "transparent"
        text_color   = "inherit"
        card_bg      = "transparent"
        overlay_bg   = "var(--secondary-background-color)"
        border_color = "rgba(150, 150, 150, 0.2)"

    if theme != "System":
        st.markdown(f"""
        <style>
            .stApp, [data-testid="stHeader"] {{
                background-color: {bg_color} !important;
                color: {text_color} !important;
            }}
            .stApp p, .stApp span, .stApp label, .stApp div,
            .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
            .stApp li, .stApp td, .stApp th, .stApp caption,
            [data-testid="stMarkdownContainer"] p,
            [data-testid="stMarkdownContainer"] li,
            [data-testid="stMarkdownContainer"] span {{
                color: {text_color} !important;
            }}
            [data-testid="stSidebar"] {{
                background-color: {side_bg} !important;
            }}
            [data-testid="stSidebar"] * {{
                color: {text_color} !important;
            }}
            [data-testid="stSidebar"] [data-testid="stVerticalBlock"] button {{
                background-color: {card_bg} !important;
                color: {text_color} !important;
                border: 1px solid {border_color} !important;
            }}
            [data-testid="stSelectbox"] > div > div,
            [data-baseweb="select"] > div,
            [data-baseweb="select"] {{
                background-color: {card_bg} !important;
                color: {text_color} !important;
                border-color: {border_color} !important;
            }}
            [data-baseweb="select"] span,
            [data-baseweb="select"] div {{
                background-color: {card_bg} !important;
                color: {text_color} !important;
            }}
            [data-baseweb="popover"], [data-baseweb="popover"] > div,
            [data-baseweb="popover"] ul, [data-baseweb="popover"] li,
            [data-baseweb="menu"], [data-baseweb="menu"] > ul,
            [data-baseweb="menu"] li, [role="listbox"],
            [role="listbox"] > div, [role="option"],
            [role="option"] > div, li[role="option"] {{
                background-color: {overlay_bg} !important;
                color: {text_color} !important;
            }}
            [role="option"]:hover {{
                filter: brightness({'0.85' if theme == 'Dark' else '0.95'});
                background-color: {overlay_bg} !important;
            }}
            [role="option"][aria-selected="true"] {{
                background-color: {'rgba(255,255,255,0.12)' if theme == 'Dark' else 'rgba(0,0,0,0.08)'} !important;
            }}
            [data-testid="stTextInput"] input,
            [data-testid="stTextArea"] textarea,
            .stChatInput textarea,
            [data-testid="stChatInput"] textarea,
            [data-baseweb="input"] input,
            [data-baseweb="textarea"] textarea {{
                background-color: {card_bg} !important;
                color: {text_color} !important;
                border-color: {border_color} !important;
                caret-color: {text_color} !important;
            }}
            [data-testid="stTextInput"] input::placeholder,
            [data-testid="stTextArea"] textarea::placeholder,
            [data-testid="stChatInput"] textarea::placeholder {{
                color: {'rgba(250,250,250,0.4)' if theme == 'Dark' else 'rgba(26,28,34,0.4)'} !important;
            }}
            [data-testid="stChatInput"],
            [data-testid="stChatInputContainer"],
            .stChatInput > div {{
                background-color: {card_bg} !important;
                border-color: {border_color} !important;
            }}
            [data-testid="stButton"] > button:not([kind="primary"]),
            [data-testid="baseButton-secondary"] {{
                background-color: {card_bg} !important;
                color: {text_color} !important;
                border-color: {border_color} !important;
            }}
            [data-testid="stPopover"] > button,
            [data-testid="stPopover"] button,
            button[data-testid="baseButton-secondary"],
            [data-baseweb="button"] {{
                background-color: {card_bg} !important;
                color: {text_color} !important;
                border: 1px solid {border_color} !important;
            }}
            [data-testid="stPopoverBody"],
            [data-baseweb="popover"] > div,
            [data-baseweb="popover"] [role="dialog"],
            div[data-baseweb="popover"] {{
                background-color: {overlay_bg} !important;
                border: 1px solid {border_color} !important;
                color: {text_color} !important;
            }}
            [data-testid="stPopoverBody"] > div {{
                background-color: {overlay_bg} !important;
            }}
            [data-testid="stPopoverBody"] *,
            [data-baseweb="popover"] * {{
                color: {text_color} !important;
            }}
            [data-testid="stPopover"] button svg,
            [data-testid="stPopover"] button span {{
                background-color: transparent !important;
            }}
            [data-testid="stFileUploader"],
            [data-testid="stFileUploader"] > div,
            [data-testid="stFileUploaderDropzone"],
            [data-testid="stFileUploaderDropzoneInstructions"] {{
                background-color: {overlay_bg} !important;
                color: {text_color} !important;
                border-color: {'rgba(150,150,150,0.5)' if theme == 'Dark' else 'rgba(0,0,0,0.2)'} !important;
                opacity: 1 !important;
            }}
            [data-testid="stFileUploaderDropzone"] {{
                border: 2px dashed {'rgba(150,150,150,0.5)' if theme == 'Dark' else 'rgba(0,0,0,0.2)'} !important;
                background-color: {overlay_bg} !important;
                opacity: 1 !important;
            }}
            [data-testid="stFileUploaderDropzone"] button {{
                background-color: {overlay_bg} !important;
                color: {text_color} !important;
                border: 1px solid {'rgba(150,150,150,0.5)' if theme == 'Dark' else 'rgba(0,0,0,0.2)'} !important;
                opacity: 1 !important;
            }}
            [data-testid="stFileUploaderDropzoneInstructions"] small,
            [data-testid="stFileUploaderDropzoneInstructions"] span {{
                color: {text_color} !important;
                opacity: 0.55 !important;
            }}
            [data-testid="stFileUploaderDropzone"] button span,
            [data-testid="stFileUploaderDropzone"] button p {{
                color: {text_color} !important;
                opacity: 1 !important;
            }}
            [data-testid="stFileUploaderFile"],
            [data-testid="stFileUploaderFileName"] {{
                background-color: {card_bg} !important;
                color: {text_color} !important;
                opacity: 1 !important;
            }}
            [data-testid="stExpander"],
            [data-testid="stExpander"] > details,
            [data-testid="stExpander"] summary,
            [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"],
            .stContainer > div {{
                background-color: {card_bg} !important;
                color: {text_color} !important;
                border-color: {border_color} !important;
            }}
            [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {{
                background-color: {card_bg} !important;
                border-color: {border_color} !important;
            }}
            [data-testid="stChatMessage"] {{
                background-color: {card_bg} !important;
                border: 1px solid {border_color} !important;
            }}
            [data-testid="stChatMessage"] p,
            [data-testid="stChatMessage"] span {{
                color: {text_color} !important;
            }}
            [data-baseweb="tab-list"] {{
                background-color: {bg_color} !important;
            }}
            [data-baseweb="tab"] {{
                color: {text_color} !important;
                background-color: transparent !important;
            }}
            [data-baseweb="tab-panel"] {{
                background-color: {bg_color} !important;
            }}
            [data-testid="stPopover"],
            [data-testid="stPopoverBody"] {{
                background-color: {card_bg} !important;
                color: {text_color} !important;
                border-color: {border_color} !important;
            }}
            [data-testid="stPopoverBody"] * {{
                color: {text_color} !important;
            }}
            [data-testid="stSlider"] span {{
                color: {text_color} !important;
            }}
            hr {{
                border-color: {border_color} !important;
            }}
            [data-testid="stAlert"] {{
                background-color: {card_bg} !important;
                border-color: {border_color} !important;
            }}
            [data-testid="stAlert"] p {{
                color: {text_color} !important;
            }}
            header[data-testid="stHeader"] {{
                visibility: visible !important;
                background-color: transparent !important;
                border-bottom: none !important;
                box-shadow: none !important;
            }}
            header[data-testid="stHeader"] button,
            [data-testid="stSidebarCollapsedControl"] button,
            [data-testid="stSidebarCollapsedControl"] {{
                visibility: visible !important;
                display: flex !important;
                color: {text_color} !important;
                background-color: transparent !important;
            }}
            [data-testid="stToolbar"] {{
                visibility: hidden !important;
            }}
            [data-testid="stTooltipHoverTarget"] + div,
            [role="tooltip"],
            div[data-baseweb="tooltip"],
            div[data-baseweb="tooltip"] div {{
                background-color: {'#1a1c22' if theme == 'Dark' else '#ffffff'} !important;
                color: {'#fafafa' if theme == 'Dark' else '#1a1c22'} !important;
                border: 1px solid {border_color} !important;
                box-shadow: 0 2px 8px rgba(0,0,0,{'0.4' if theme == 'Dark' else '0.12'}) !important;
            }}
            [data-testid="stCaptionContainer"] p {{
                color: {'rgba(250,250,250,0.6)' if theme == 'Dark' else 'rgba(26,28,34,0.6)'} !important;
            }}
            [data-testid="stSidebar"] ::-webkit-scrollbar,
            [data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar,
            .stApp ::-webkit-scrollbar {{
                width: 6px !important;
                height: 6px !important;
            }}
            [data-testid="stSidebar"] ::-webkit-scrollbar-track,
            [data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-track {{
                background: {'rgba(255,255,255,0.05)' if theme == 'Dark' else 'rgba(0,0,0,0.05)'} !important;
                border-radius: 10px !important;
            }}
            [data-testid="stSidebar"] ::-webkit-scrollbar-thumb,
            [data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-thumb {{
                background: {'rgba(255,255,255,0.35)' if theme == 'Dark' else 'rgba(0,0,0,0.25)'} !important;
                border-radius: 10px !important;
            }}
            [data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover,
            [data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-thumb:hover {{
                background: {'rgba(255,255,255,0.55)' if theme == 'Dark' else 'rgba(0,0,0,0.45)'} !important;
            }}
        </style>
        """, unsafe_allow_html=True)

    # ── Layout overrides — always applied regardless of theme ─────────────────
    if theme == "System":
        padding_top = "1rem"
        margin_top  = "0rem"
    else:
        padding_top = "1rem"
        margin_top  = "-2rem"

    # FIX: use bg_color only when it's defined for Dark/Light; fall back to
    # var(--background-color) for System so the f-string never references
    # an undefined variable path.
    tab_bg = "var(--background-color)" if theme == "System" else bg_color

    st.markdown(f"""
    <style>
        /* Always hide Streamlit toolbar (Deploy button etc.) */
        [data-testid="stToolbar"],
        [data-testid="stDeployButton"],
        .stDeployButton,
        header [data-testid="stToolbar"] {{
            visibility: hidden !important;
            display: none !important;
        }}
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
            visibility: visible !important;
        }}
        .main .block-container {{
            padding-top: {padding_top} !important;
            padding-bottom: 120px !important;
            margin-top: {margin_top} !important;
        }}
        section[data-testid="stMain"] > div {{
            padding-top: 0 !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            position: sticky !important;
            top: 0 !important;
            z-index: 999 !important;
            background-color: {tab_bg} !important;
            padding-top: 10px !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    # ── Floating scroll button CSS — defined ONCE here, used by chat_tab.py ───
    # The button is hidden by default. It becomes visible only when its parent
    # tab-panel is the active one (Streamlit sets display:none on inactive panels),
    # detected via the :not([hidden]) and display-block selector chain.
    # This requires zero JS and never leaks onto other tabs or pages.
    st.markdown("""
    <style>
    .floating-scroll-btn {
        position: fixed;
        bottom: 110px;
        right: 35px;
        z-index: 9999;
        width: 44px;
        height: 44px;
        border-radius: 12px;
        background: rgba(255, 75, 75, 0.9);
        backdrop-filter: blur(4px);
        color: white !important;
        text-decoration: none !important;
        display: none;   /* hidden unless overridden by the rule below */
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
        transition: all 0.3s ease;
        border: 1px solid rgba(255,255,255,0.2);
    }
    .floating-scroll-btn:hover {
        transform: translateY(-3px);
        background: #ff4b4b;
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.4);
    }
    /* Show ONLY when the button's ancestor tab-panel is the visible one.
       Streamlit marks inactive panels with display:none via inline style;
       active panels have no such style, so [style*="display: none"] excludes them. */
    [data-baseweb="tab-panel"]:not([style*="display: none"]) .floating-scroll-btn,
    [data-baseweb="tab-panel"]:not([hidden]) .floating-scroll-btn {
        display: flex !important;
    }
    </style>
    """, unsafe_allow_html=True)