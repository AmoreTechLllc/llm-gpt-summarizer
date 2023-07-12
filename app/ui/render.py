"""
UI functions
"""
# Import necessary modules

import logging
from typing import Optional

import streamlit as st
from config import ConfigLoader
from data_types.summary import GenerateSettings
from generate_data import generate_summary_data, get_mastodon_data
from ui.settings import render_settings
from utils.common import is_valid_reddit_url, replace_last_token_with_json, save_output, is_valid_mastodon_url

config = ConfigLoader.get_config()


def render_input_box() -> Optional[str]:
    """
    Render the input box for the mastodon URL and return its value.
    """
    mastodon_url: Optional[str] = st.text_area("Enter Mastodon URL:", config["MASTODON_URL"])
    if not mastodon_url:
        return None

    if not is_valid_mastodon_url(mastodon_url):
        st.error("Please enter a valid MASTODON URL")
        return None
    return mastodon_url


def render_output(
        mastodon_url: str,
        app_logger: Optional[logging.Logger] = None,
        settings: Optional[GenerateSettings] = None,
) -> None:
    """
    Render the placeholder for the summary.
    """

    output_placeholder = st.empty()

    with output_placeholder.container():
        if app_logger:
            app_logger.info("Generating summary data")

        progress_text = "Operation in progress. Please wait."
        my_bar = st.progress(0, text=progress_text)

        def progress_callback(
                progress: int, idx: int, prompt: str, summary: str
        ) -> None:
            my_bar.progress(progress, text=progress_text)
            with st.expander(f"Prompt {idx}"):
                st.text(prompt)
            st.subheader(f"Response: {idx}")
            st.markdown(summary)

        try:
            mastodon_data = get_mastodon_data(
                mastodon_url=replace_last_token_with_json(mastodon_url),
                logger=app_logger,
            )

            if not mastodon_data:
                st.error("no mastodon data")
                st.stop()

            st.text("Original Content:")
            st.text(mastodon_data.content)

            str_output = generate_summary_data(
                settings=settings,
                mastodon_data=mastodon_data,
                logger=app_logger,
                progress_callback=progress_callback,
            )

            save_output(str(mastodon_data.content), str(str_output))

            if app_logger:
                app_logger.info("Summary data generated")

        except Exception as ex:
            if app_logger:
                app_logger.exception(ex)
            st.error("An error occurred while generating summary data")
            st.stop()




def render_layout(
        app_logger: Optional[logging.Logger] = None,
        mastodon_url: Optional[str] = None,
        settings: Optional[GenerateSettings] = None,
) -> None:
    """
    Render the layout of the app.
    """

    st.header("Mastodon Summarizer")

    # Create an input box for url
    if not mastodon_url:
        mastodon_url = render_input_box()
        if not mastodon_url:
            return

    settings = settings or render_settings()

    if not settings:
        st.error("No settings (not sure how this happened)")
        return

    # Create a button to submit the url
    if st.button("Generate it!"):
        render_output(
            app_logger=app_logger,
            settings=settings,
            mastodon_url=mastodon_url,
        )
def render_layout2(
        app_logger: Optional[logging.Logger] = None,
        mastodon_url: Optional[str] = None,
        settings: Optional[GenerateSettings] = None,
) -> None:
    """
    Render the layout of the app.
    """

    st.header("Mastodon Summarizer")

    # Create an input box for url
    if not mastodon_url:
        mastodon_url = render_input_box()
        if not mastodon_url:
            return

    settings = settings or render_settings()

    if not settings:
        st.error("No settings (not sure how this happened)")
        return

    # Create a button to submit the url
    if st.button("Generate it!"):
        render_output(
            app_logger=app_logger,
            settings=settings,
            reddit_url=mastodon_url,
        )
