"""Streamlit session state management."""

from __future__ import annotations

from typing import Any

import streamlit as st


def init_state(key: str, default: Any) -> Any:
    """Initialize a session state key with a default value.

    Args:
        key: The session state key.
        default: The default value if not already set.

    Returns:
        The current value of the session state key.
    """
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def get_state(key: str, default: Any = None) -> Any:
    """Get a session state value.

    Args:
        key: The session state key.
        default: Default value if key doesn't exist.

    Returns:
        The value of the session state key.
    """
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """Set a session state value.

    Args:
        key: The session state key.
        value: The value to set.
    """
    st.session_state[key] = value
