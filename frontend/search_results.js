const md = window.markdownit();

const API_URL = 'http://localhost:5001/websearch';

document.getElementById('searchForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const query = document.getElementById('query').value;
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = 'Searching...';

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
        let buffer = '';
        let bingResultsDisplayed = false;
        let aiResponseStarted = false;

        resultsDiv.innerHTML = '';
        const aiResponseDiv = document.createElement('div');
        aiResponseDiv.className = 'ai-response';
        aiResponseDiv.innerHTML = '<h2>GenAI Answer</h2><div class="spinner"></div>';
        resultsDiv.appendChild(aiResponseDiv);

        const bingResultsDiv = document.createElement('div');
        bingResultsDiv.className = 'bing-results';
        bingResultsDiv.innerHTML = '<h2>Bing Custom Search Results</h2><p>Loading...</p>';
        resultsDiv.appendChild(bingResultsDiv);

        function readStream() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    return;
                }
                buffer += decoder.decode(value, { stream: true });
                
                // Check for complete JSON objects
                let jsonEndIndex;
                while ((jsonEndIndex = buffer.indexOf('}\n\n')) !== -1) {
                    const jsonStr = buffer.substring(0, jsonEndIndex + 1);
                    buffer = buffer.substring(jsonEndIndex + 3);
                    
                    try {
                        const data = JSON.parse(jsonStr);
                        if (data['Bing Search Results'] && !bingResultsDisplayed) {
                            displayBingResults(data['Bing Search Results']);
                            bingResultsDisplayed = true;
                        }
                    } catch (e) {
                        console.error('Error parsing JSON:', e);
                    }
                }

                // Append any remaining buffer to AI response
                if (buffer.trim()) {
                    if (!aiResponseStarted) {
                        aiResponseDiv.innerHTML = '<h2>GenAI Answer</h2>';
                        aiResponseStarted = true;
                    }
                    aiResponseDiv.innerHTML = '<h2>GenAI Answer</h2>' + md.render(buffer);
                }

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

function displayBingResults(bingResults) {
    const bingResultsDiv = document.querySelector('.bing-results');
    bingResultsDiv.innerHTML = '<h2>Bing Custom Search Results</h2>';

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
