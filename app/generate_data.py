"""data functions for Mastodon Scraper project."""
import logging
from datetime import datetime
from typing import Any, Callable, List, Optional, Tuple

import praw  # type: ignore
from mastodon import Mastodon, MastodonAPIError

from config import ConfigLoader
from data_types.summary import GenerateSettings
from env import EnvVarsLoader
from llm_handler import complete_text
from log_tools import Logger
from utils.llm_utils import (
    estimate_word_count,
    group_bodies_into_chunks,
    num_tokens_from_string,
)
from utils.streamlit_decorators import spinner_decorator

config = ConfigLoader.get_config()
env_vars = EnvVarsLoader.load_env()

app_logger = Logger.get_app_logger()
ProgressCallback = Optional[Callable[[int, int, str, str], None]]


@Logger.log
def summarize_summary(
        selftext: str,
        settings: GenerateSettings,
        title: Optional[str] = None,
        max_tokens: int = config["MAX_BODY_TOKEN_SIZE"],
) -> str:
    """Summarize the response."""

    summary_string = (
        f"shorten this text to ~{max_tokens} GPT tokens through summarization:"
        f" {selftext}"
    )

    out_text = complete_text(
        prompt=summary_string, max_tokens=max_tokens, settings=settings
    )

    if title is None:
        return out_text
    return f"{title}\n{out_text}"


def format_date(timestamp: float) -> str:
    """Format a timestamp into a human-readable date."""
    date: datetime = datetime.fromtimestamp(timestamp)
    return date.strftime("%Y-%b-%d %H:%M")


def get_comments(comment_data : Any, level : int = 0 ) -> str:
    """Get comments from mastodon post"""
    result = ""

    author_name = comment_data["account"]["username"]
    created_date = format_date(comment_data["created_at"])

    result += f"{created_date} [{author_name}] {comment_data['content']} \n"

    if "replies" in comment_data:
        replies = sorted(comment_data["replies"], key= lambda reply: reply["created_at"], reverse= True)
        for reply in replies:
            result += " " * level
            result += "> " + get_comments(reply, level + 1)

    return  result


# def get_comments(comment: Any, level: int = 0) -> str:
#     """Get the comments from a Reddit thread."""
#     result = ""
#
#     author_name = comment.author.name if comment.author else "[deleted]"
#     created_date = format_date(comment.created_utc)
#
#     result += f"{created_date} [{author_name}] {comment.body}\n"
#
#     for reply in sorted(
#         comment.replies, key=lambda reply: reply.created_utc, reverse=True
#     ):
#         result += "    " * level
#         result += "> " + get_comments(reply, level + 1)
#
#     return result

mastodon = Mastodon(
    access_token='3FBZYtsShFIpzlD9zCy3uU4u9lZMe0TAhxT_xdwVBaQ',
    api_base_url='https://mastodon.social'
)
class MastodonData:
    def __init__(self, content: Optional[str], username: Optional[str], comments: List[str]):
        self.content = content
        self.username = username
        self.comments = comments

def get_mastodon_data(mastodon_url: str,
                      logger: logging.Logger) -> MastodonData:
    """
    Process the Mastodon URL and retrieve data from the Mastodon instance.
    """
    try:
        # Extract the post ID from the Mastodon URL
        post_id = mastodon_url.split("/")[-1].split(".")[0]
        try:
            post = mastodon.status(post_id)
            # Retrieve the post content
            content = post["content"]

            comments =[]
            context  = mastodon.status_context(post_id)
            if "ancestors"  in context:
                for ancestor in context["ancestors"]:
                    comments.append(ancestor["content"])
            if "descendants" in context:
                for reply in context["descendants"]:
                    comments.append(reply["content"])

            return MastodonData(content=content, username=post["account"]["username"], comments= comments)

        except MastodonAPIError as ex:
            logger.error(f"Error getting Mastodon data: {ex}")
            raise ex

        # if match:
        #     instance = match.group(1)
        #     username = match.group(2)
        # else:
        #     raise ValueError("No instance or username found in URL")
        #
        # # Create a Mastodon client
        # # mastodon = Mastodon(api_base_url=f"https://{instance}")
        #
        # # Fetch the user's profile
        # user = mastodon.account_search(username)
        # if not user:
        #     raise ValueError("User not found")
        #
        # # Fetch the user's latest toot
        # toots = mastodon.account_statuses(user[0]["id"])
        # if not toots:
        #     raise ValueError("No toots found for the user")
        #
        # latest_toot = toots[0]["content"]
        #
        # return MastodonData(content=latest_toot, username=username)

    except Exception as ex:
        logger.error(f"Error getting Mastodon data: {ex}")
        raise ex



@spinner_decorator("Generating Summary Data")
def generate_summary_data(
        settings: GenerateSettings,
        mastodon_data: MastodonData,
        logger: logging.Logger,
        progress_callback: ProgressCallback = None,
) -> str:
    """
    Process the Mastodon data and generate a summary.
    """
    try:
        content = mastodon_data.content
        comments = mastodon_data.comments


        if not content:
            content = "No Content"

        groups = group_bodies_into_chunks(content, settings["chunk_token_length"])
        if len(groups) == 0:
            groups = ["No Content"]
        # Append comment to the post content
        if comments:
            content += "\n".join(comments)

        init_prompt = (
            summarize_summary(content, settings)
            if len(content) > estimate_word_count(settings["max_token_length"])
            else content
        )

        prompts, summaries = generate_summaries(
            settings=settings,
            groups=groups[: settings["max_number_of_summaries"]],
            prompt=init_prompt,
            progress_callback=progress_callback,
        )

        output = ""
        for i, summary in enumerate(summaries):
            prompt = prompts[i]
            output += f"============\nSUMMARY COUNT: {i}\n============\n"
            output += f"PROMPT: {prompt}\n\n{summary}\n===========================\n\n"

        return output

    except Exception as ex:
        logger.error(f"Error generating summary data: {ex}")
        raise


@Logger.log
def generate_summaries(
        settings: GenerateSettings,
        groups: List[str],
        prompt: str,
        progress_callback: ProgressCallback = None,
) -> Tuple[List[str], List[str]]:
    """Generate the summaries from the prompts."""

    prompts: List[str] = []
    summaries: List[str] = []
    total_groups = len(groups)
    system_role, query, max_tokens = (
        settings["system_role"],
        settings["query"],
        settings["max_token_length"],
    )

    for i, comment_group in enumerate(groups):
        complete_prompt = (
                f"{query}\n\n"
                + "```"
                + f"Title: {summarize_summary(prompt, settings) if i > 0 else prompt}\n\n"
                + f'<Comments>\n{comment_group}\n</Comments>\n'
                + "```"
        )

        prompts.append(complete_prompt)
        try:
            summary = complete_text(
                prompt=complete_prompt,
                max_tokens=max_tokens
                           - num_tokens_from_string(complete_prompt, settings["selected_model_type"])
                           - num_tokens_from_string(system_role, settings["selected_model_type"])
                           - 4,
                settings=settings,
            )
        except MastodonAPIError as ex:
            logging.error(f"Error generating summary: {ex}")
            raise ex

        if progress_callback:
            progress = int(((i + 1) / total_groups) * 100)
            progress_callback(progress, i + 1, complete_prompt, summary)

        prompt = summary

        summaries.append(summary)

    return prompts, summaries
