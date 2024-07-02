// Initialize markdown-it for rendering markdown content
const md = window.markdownit();

// API endpoint for the websearch functionality
const API_URL = 'http://localhost:5001/websearch';

// Add event listener to the search form
document.getElementById('searchForm').addEventListener('submit', function(e) {
    e.preventDefault();  // Prevent default form submission
    const query = document.getElementById('query').value;
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = 'Searching...';

    // Fetch request to the API
    fetch(API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        // Clear previous results and set up the UI
        resultsDiv.innerHTML = '';
        const aiResponseDiv = document.createElement('div');
        aiResponseDiv.className = 'ai-response';
        aiResponseDiv.innerHTML = '<h2>GenAI Answer</h2><div id="processing-status"></div><div id="ai-content"></div><div class="spinner"></div>';
        resultsDiv.appendChild(aiResponseDiv);

        const bingResultsDiv = document.createElement('div');
        bingResultsDiv.className = 'bing-results';
        bingResultsDiv.innerHTML = '<h2>Bing Search Results</h2><p>Loading...</p>';
        resultsDiv.appendChild(bingResultsDiv);

        let aiResponseContent = '';  // Variable to accumulate AI response content
        let isFirstAIResponse = true;  // Flag to track the first AI response chunk

        // Function to process each event from the stream
        function processStreamEvent(event) {
            switch (event.event) {
                case 'initial_response':
                    displayBingResults(event.data['Bing Search Results']);
                    break;
                case 'processing_status':
                case 'url_processed':
                    updateProcessingStatus(event.data.status || `Processed: ${event.data.url}`);
                    break;
                case 'ai_response':
                    if (isFirstAIResponse) {
                        updateProcessingStatus('');  // Clear the "Generating response" message
                        isFirstAIResponse = false;
                    }
                    updateAIResponse(event.data.content);
                    break;
                case 'error':
                    handleError(event.data.message);
                    break;
                default:
                    console.log('Unknown event type:', event.event);
            }
        }

        // Function to read the stream
        function readStream() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    return;
                }
                const chunk = decoder.decode(value);
                const events = chunk.split('\n').filter(Boolean);
                
                events.forEach(eventStr => {
                    try {
                        const event = JSON.parse(eventStr);
                        processStreamEvent(event);
                    } catch (e) {
                        console.error('Error parsing JSON:', e);
                    }
                });

                readStream();
            });
        }

        readStream();
    })
    .catch(error => {
        console.error('Error:', error);
        resultsDiv.innerHTML = 'An error occurred while fetching results.';
    });
});

// Function to update the processing status
function updateProcessingStatus(status) {
    const statusDiv = document.getElementById('processing-status');
    if (statusDiv) {
        statusDiv.innerHTML = `<p>${status}</p>`;  // Replace content instead of appending
    }
}

// Variable to accumulate AI response content
let aiResponseContent = '';

// Function to update the AI response
function updateAIResponse(content) {
    const aiContentDiv = document.getElementById('ai-content');
    if (aiContentDiv) {
        document.querySelector('.spinner').style.display = 'none';
        aiResponseContent += content;  // Accumulate content
        aiContentDiv.innerHTML = md.render(aiResponseContent);  // Render accumulated content
    }
}

// Function to handle errors
function handleError(message) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML += `<p class="error">${message}</p>`;
}

// Function to display Bing search results
function displayBingResults(bingResults) {
    const bingResultsDiv = document.querySelector('.bing-results');
    bingResultsDiv.innerHTML = '<h2>Bing Search Results</h2>';

    if (bingResults.webPages && bingResults.webPages.value) {
        bingResults.webPages.value.forEach(page => {
            const pageDiv = document.createElement('div');
            pageDiv.className = 'bing-result';
            pageDiv.innerHTML = `
                <h3><a href="${page.url}" target="_blank">${page.name}</a></h3>
                <p>${page.snippet}</p>
            `;
            bingResultsDiv.appendChild(pageDiv);
        });
    } else {
        bingResultsDiv.innerHTML += '<p>No results found.</p>';
    }
}
