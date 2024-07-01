import os
import json
import logging
import random
import time
import httpx
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from lxml import html
import openai
import concurrent.futures
import urllib.parse
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging to show INFO level messages
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Load configuration from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
BING_SUBSCRIPTION_KEY = os.getenv('BING_SUBSCRIPTION_KEY')
CUSTOM_CONFIG_ID = os.getenv('CUSTOM_CONFIG_ID')

# Sample User-Agents for web requests
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.105 Mobile Safari/537.36'
]

def get_random_user_agent():
    """Return a random User-Agent string from the list."""
    return random.choice(USER_AGENTS)

def bing_search(query, subscription_key, custom_config_id, count=1, market="en-US"):
    """
    Perform a Bing custom search and return the results.
    
    :param query: Search query string
    :param subscription_key: Bing API subscription key
    :param custom_config_id: Bing custom search configuration ID
    :param count: Number of results to return
    :param market: Market for the search (e.g., "en-US")
    :return: Tuple of (search results JSON, timing information)
    """
    encoded_query = urllib.parse.quote(query)
    url = f'https://api.bing.microsoft.com/v7.0/custom/search?q={encoded_query}&customconfig={custom_config_id}&mkt={market}&count={count}'
    headers = {'Ocp-Apim-Subscription-Key': subscription_key}
    
    start_time = time.time()
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    timings = {'bing_search': time.time() - start_time}
    
    return response.json(), timings

def extract_urls(response):
    """
    Extract URLs and their metadata from Bing search results.
    
    :param response: JSON response from Bing search
    :return: List of dictionaries containing URL information
    """
    urls = []
    if 'webPages' in response and 'value' in response['webPages']:
        for page in response['webPages']['value']:
            urls.append({
                'url': page['url'],
                'name': page.get('name', 'No title provided'),
                'snippet': page.get('snippet', 'No snippet provided')
            })
            if 'deepLinks' in page:
                for deep_link in page['deepLinks']:
                    urls.append({
                        'url': deep_link['url'],
                        'name': deep_link.get('name', 'No title provided'),
                        'snippet': deep_link.get('snippet', 'No snippet provided')
                    })
    return urls

def fetch_and_parse_url(url, headers, timeout):
    """
    Fetch and parse the content of a given URL.
    
    :param url: URL to fetch and parse
    :param headers: HTTP headers for the request
    :param timeout: Timeout for the request
    :return: Tuple of (parsed content, fetch start time, fetch duration, parse start time, parse duration)
    """
    fetch_start_time = time.time()
    with httpx.Client(http2=True, follow_redirects=True) as client:
        response = client.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    fetch_time = time.time() - fetch_start_time

    parse_start_time = time.time()
    parser = html.HTMLParser(recover=True)
    tree = html.fromstring(response.text, parser=parser)

    # Remove unnecessary elements
    for element in tree.xpath('//header | //nav | //footer | //aside | //script | //style | //div[contains(@class, "modal")] | //div[contains(@class, "popup")] | //div[contains(@class, "overlay")]'):
        if element.getparent() is not None:
            element.getparent().remove(element)

    meaningful_content = tree.xpath('//body//text()')
    parsed_content = ' '.join(meaningful_content).strip()
    parsed_content = ' '.join(parsed_content.split())
    parse_time = time.time() - parse_start_time

    return parsed_content, fetch_start_time, fetch_time, parse_start_time, parse_time

def extract_meaningful_content_concurrently(urls, yield_func):
    """
    Fetch and parse content from multiple URLs concurrently.
    
    :param urls: List of URL dictionaries to process
    :param yield_func: Function to yield status updates
    :return: Tuple of (list of content dictionaries, list of timing dictionaries)
    """
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    timeout = 5.0

    contents = []
    timings = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_and_parse_url, url['url'], headers, timeout): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                content, fetch_start_time, fetch_time, parse_start_time, parse_time = future.result()
                timings.append({
                    'url': url['url'],
                    'fetch_start_time': fetch_start_time,
                    'fetch_time': fetch_time,
                    'parse_start_time': parse_start_time,
                    'parse_time': parse_time
                })
                contents.append({
                    "title": url.get('name', 'No title provided'),
                    "url": url['url'],
                    "content": content,
                    "snippet": url.get('snippet', 'No snippet provided')
                })
                # Yield an event for each URL processed
                yield_func(json.dumps({"event": "url_processed", "data": {"url": url.get('name', 'No title provided')}}))
            except Exception as exc:
                logging.error(f"URL {url['url']} generated an exception: {exc}")

    return contents, timings

def call_openai_chat_completion(system_message, user_message, set_model, json_response=False, max_tokens=2048, stream=False):
    """
    Call OpenAI's chat completion API.
    
    :param system_message: System message for the chat
    :param user_message: User message for the chat
    :param set_model: OpenAI model to use
    :param json_response: Whether to request a JSON response
    :param max_tokens: Maximum number of tokens in the response
    :param stream: Whether to stream the response
    :return: Tuple of (API response content, timing information, token usage)
    """
    openai.api_key = OPENAI_API_KEY
    client = openai.OpenAI()
    start_time = time.time()
    completion_args = {
        "model": set_model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "stream": stream
    }
    if json_response:
        completion_args["response_format"] = {"type": "json_object"}
    
    response = client.chat.completions.create(**completion_args)
    timings = {'openai_request': time.time() - start_time}
    token_usage = {}
    if not stream:
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    return response.choices[0].message.content, timings, token_usage

def stream_openai_chat_completion(system_message, user_message, model, max_tokens=2048):
    """
    Stream OpenAI's chat completion API response.
    
    :param system_message: System message for the chat
    :param user_message: User message for the chat
    :param model: OpenAI model to use
    :param max_tokens: Maximum number of tokens in the response
    :return: Streaming response from OpenAI
    """
    openai.api_key = OPENAI_API_KEY
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        max_tokens=max_tokens,
        stream=True
    )
    return response

def select_best_urls(urls, query, max_tokens, deep_search_quantity, deep_search_model):
    """
    Select the best URLs based on the query using OpenAI's API.
    
    :param urls: List of URLs to choose from
    :param query: User's search query
    :param max_tokens: Maximum number of tokens for the API response
    :param deep_search_quantity: Number of URLs to select
    :param deep_search_model: OpenAI model to use for selection
    :return: Tuple of (selected URLs JSON, timing information, token usage)
    """
    system_message = f"""
    Please select up to {deep_search_quantity} URLs from the provided list that best answer the query. Provide reasons for your selection along with each of the URLs selected in JSON format.
    Example format:
    {{
        "selected_urls": [
            {{
                "url": "URL1",
                "reason": "Reason1"
            }},
            {{
                "url": "URL2",
                "reason": "Reason2"
            }}
        ]
    }}
    """
    user_message = f"Query: {query}\n\nURLs:\n{urls}"
    response, timings, token_usage = call_openai_chat_completion(system_message, user_message, deep_search_model, json_response=True, max_tokens=max_tokens)
    return json.loads(response), timings, token_usage

def fetch_system_prompt():
    """
    Fetch the system prompt from a local file.
    
    :return: Tuple of (prompt content, timing information)
    """
    start_time = time.time()
    with open('backend/sysprompt.txt', 'r') as file:
        prompt = file.read()
    timings = {'prompt_load': time.time() - start_time}
    logging.info("Prompt loaded from local file.")
    return prompt, timings

def calculate_total_content_timing(timings):
    """
    Calculate the total time taken for content fetching and parsing.
    
    :param timings: List of timing dictionaries
    :return: Total time taken
    """
    if not timings:
        return 0
    fetch_start_times = [t['fetch_start_time'] for t in timings]
    parse_end_times = [t['parse_start_time'] + t['parse_time'] for t in timings]
    return max(parse_end_times) - min(fetch_start_times)

@app.route('/websearch', methods=['POST'])
def websearch():
    """
    Handle web search requests.
    
    This function orchestrates the entire web search process, including:
    1. Performing a Bing search
    2. Selecting the best URLs
    3. Fetching and parsing content from selected URLs
    4. Generating an AI response based on the content
    
    :return: Streaming response containing search results and AI-generated content
    """
    data = request.get_json()
    query = data.get('query')
    app.logger.info(f"Received query: {query}")

    # Fixed configuration
    deepsearch = True
    initial_search_results = 5
    deep_search_quantity = 3
    deep_search_model = 'gpt-4o'
    set_model = 'gpt-4o'
    max_tokens = 1000
    context_only = False

    def generate():
        try:
            # Perform Bing search immediately
            bing_response, bing_timings = bing_search(query, BING_SUBSCRIPTION_KEY, CUSTOM_CONFIG_ID, initial_search_results, "en-US")
            
            # Prepare the initial response with Bing results
            initial_response = {
                "event": "initial_response",
                "data": {
                    "User Query": query,
                    "Bing Search Results": bing_response,
                    "Headers": {
                        "Set-Model": set_model,
                        "Max-Tokens": max_tokens,
                        "Initial-Search-Results": initial_search_results,
                        "Deep-Search-Quantity": deep_search_quantity,
                        "Deep-Search-Model": deep_search_model,
                        "Deep-Search": deepsearch,
                        "Context-Only": context_only
                    }
                }
            }
            yield json.dumps(initial_response) + "\n"

            # Continue with the rest of the processing
            urls = extract_urls(bing_response)
            url_dict = {url['url']: url for url in urls}

            # Yield event for determining best URLs
            yield json.dumps({"event": "processing_status", "data": {"status": "Determining which Search results to leverage..."}}) + "\n"
            selection_response, open_ai_pick_urls_timings, selection_token_usage = select_best_urls(urls, query, max_tokens, deep_search_quantity, deep_search_model)
            selected_urls = selection_response.get('selected_urls', [])

            for selected_url in selected_urls:
                selected_url.update(url_dict.get(selected_url['url'], {}))

            # Yield event for visiting pages
            yield json.dumps({"event": "processing_status", "data": {"status": "Visiting pages and reading contents..."}}) + "\n"
            contents, content_timings = extract_meaningful_content_concurrently(selected_urls[:deep_search_quantity], lambda x: (yield x + "\n"))

            if not context_only:
                system_message, prompt_timings = fetch_system_prompt()
                user_message = "User Message: " + query + "\nContextual Content: " + "\n".join([f"{c['title']} {c['url']} {c['content']}" for c in contents])
                
                # Yield event for generating response
                yield json.dumps({"event": "processing_status", "data": {"status": "Generating response from OpenAI..."}}) + "\n"
                stream = stream_openai_chat_completion(system_message, user_message, set_model, max_tokens=max_tokens)
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content is not None:
                        yield json.dumps({"event": "ai_response", "data": {"content": chunk.choices[0].delta.content}}) + "\n"
        except Exception as e:
            app.logger.error(f"Error in generate function: {str(e)}")
            yield json.dumps({"event": "error", "data": {"message": f"An error occurred: {str(e)}"}}) + "\n"

    return Response(generate(), content_type='text/event-stream')

# Main execution block
if __name__ == '__main__':
    # Run the Flask app
    # The host '0.0.0.0' makes the server publicly available
    # Debug mode is set to True for development purposes
    app.run(host='0.0.0.0', port=5001, debug=True)
