// This function gets the CSRF token from localStorage
function getCSRFToken() {
    return localStorage.getItem("X-CSRF-TOKEN");
}

// Function to check the response for CSRF token and store it in localStorage
function handleResponseCSRFToken(response) {
    const csrfToken = response.headers.get("x-csrf-token");
    alert(response.headers)
    if (csrfToken) {
        localStorage.setItem("X-CSRF-TOKEN", csrfToken);
    }
}

// Intercept all fetch requests to add the CSRF token
function interceptFetchRequests() {
    const originalFetch = window.fetch;
    
    window.fetch = function(url, options = {}) {
        const csrfToken = getCSRFToken();

        if (csrfToken) {
            options.headers = options.headers || {};
            options.headers['X-CSRF-TOKEN'] = csrfToken;
            options.headers['X-CLIENT-TYPE'] = "web";
        }

        // Call the original fetch function and handle the response
        return originalFetch(url, options).then(response => {
            handleResponseCSRFToken(response);
            return response;
        });
    };
}

// Intercept all XMLHttpRequest requests to add the CSRF token
function interceptXMLHttpRequests() {
    const originalOpen = XMLHttpRequest.prototype.open;

    XMLHttpRequest.prototype.open = function(method, url, async) {
        originalOpen.call(this, method, url, async);

        const csrfToken = getCSRFToken();
        if (csrfToken) {
            this.setRequestHeader('X-CSRF-TOKEN', csrfToken);
            this.setRequestHeader("X-CLIENT-TYPE", "web")
        }
    };
}

document.addEventListener("DOMContentLoaded", function() {
    interceptFetchRequests();
    interceptXMLHttpRequests();
});
