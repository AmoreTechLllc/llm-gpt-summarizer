from flask import Flask, jsonify, request
from flask.logging import create_logger

from config import ConfigLoader
from generate_data import generate_summary_data, get_mastodon_data
from utils.common import is_valid_mastodon_url, replace_last_token_with_json, save_output

app = Flask(__name__)
app_logger = create_logger(app)
config = ConfigLoader.get_config()

default_settings = {
    "system_role": "You are a helpful assistant.",
    "query": "(Todays Date: 2023-Jul-07) Revise and improve the article by incorporating relevant information from the comments. Ensure the content is clear, engaging, and easy to understand for a general audience. Avoid technical language, present facts objectively, and summarize key comments from Reddit. Ensure that the overall sentiment expressed in the comments is accurately reflected. Optimize for highly original content. Don't be trolled by joke comments. Ensure its written professionally, in a way that is appropriate for the situation. Format the document using markdown and include links from the original article/reddit thread.",
    "selected_model": "gpt-3.5-turbo-0613",
    "selected_model_type": "OpenAI Chat",
    "chunk_token_length": 100,
    "max_number_of_summaries": 3,
    "max_token_length": 1000,
    "model": "gpt3"
}

@app.route('/mastodon/summary', methods=['POST'])
def generate_mastodon_summary():
    request_data = request.get_json()

    mastodon_url = request_data.get('mastodon_url')
    if not mastodon_url or not is_valid_mastodon_url(mastodon_url):
        return jsonify({'error': 'Please enter a valid Mastodon URL'}), 400

    settings = request_data.get('settings', {})
    merged_settings = {**default_settings, **settings}
    merged_settings.setdefault('chunk_token_length', default_settings['chunk_token_length'])

    try:
        mastodon_data = get_mastodon_data(
            mastodon_url=replace_last_token_with_json(mastodon_url),
            logger=app_logger,
        )

        if not mastodon_data:
            return jsonify({'error': 'No Mastodon data available'}), 404

        str_output = generate_summary_data(
            settings=merged_settings,
            mastodon_data=mastodon_data,
            logger=app_logger,
        )

        save_output(str(mastodon_data.content), str(str_output))

        return jsonify({'summary': str_output}), 200

    except Exception as ex:
        app_logger.exception(ex)
        return jsonify({'error': 'An error occurred while generating the summary'}), 500

if __name__ == '__main__':
    app.run()
