// Debug script to help identify form submission issues
document.addEventListener('DOMContentLoaded', function() {
    // Debug form submission
    const debugFormSubmit = function() {
        const uploadForm = document.getElementById('upload-form');
        const manualForm = document.getElementById('manual-form');
        
        if (uploadForm) {
            const originalSubmit = uploadForm.onsubmit;
            uploadForm.onsubmit = function(e) {
                e.preventDefault();
                console.log('Debug: Upload form submitted');
                
                // Get form data
                const formData = new FormData(uploadForm);
                
                // Debug request
                fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    console.log('Debug: Response status:', response.status);
                    console.log('Debug: Response headers:', response.headers);
                    console.log('Debug: Response type:', response.type);
                    
                    // Check if the response can be parsed as JSON
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        console.log('Debug: Response is JSON');
                        return response.json().then(data => {
                            console.log('Debug: Response data:', data);
                            return data;
                        }).catch(err => {
                            console.error('Debug: JSON parse error:', err);
                            throw new Error('Invalid JSON response');
                        });
                    } else {
                        console.log('Debug: Response is not JSON');
                        return response.text().then(text => {
                            console.log('Debug: Response text:', text);
                            throw new Error('Expected JSON response but got text');
                        });
                    }
                })
                .then(data => {
                    console.log('Debug: Processed data:', data);
                    
                    if (data.error) {
                        console.error('Debug: Server error:', data.error);
                        // Remove alert - just log to console
                        return;
                    }
                    
                    console.log('Debug: Job started successfully:', data);
                    // Remove alert - just log to console
                })
                .catch(error => {
                    console.error('Debug: Fetch error:', error);
                    // Remove alert - just log to console
                });
            };
        }
        
        if (manualForm) {
            const originalSubmit = manualForm.onsubmit;
            manualForm.onsubmit = function(e) {
                e.preventDefault();
                console.log('Debug: Manual form submitted');
                
                const urlsText = document.getElementById('manual-urls').value;
                const urls = urlsText.split('\n').filter(url => url.trim() !== '');
                
                // Debug request
                fetch('/api/manual', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        urls: urls,
                        headless: document.getElementById('manual-headless-mode').checked
                    })
                })
                .then(response => {
                    console.log('Debug: Response status:', response.status);
                    console.log('Debug: Response headers:', response.headers);
                    console.log('Debug: Response type:', response.type);
                    
                    // Check if the response can be parsed as JSON
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        console.log('Debug: Response is JSON');
                        return response.json().then(data => {
                            console.log('Debug: Response data:', data);
                            return data;
                        }).catch(err => {
                            console.error('Debug: JSON parse error:', err);
                            throw new Error('Invalid JSON response');
                        });
                    } else {
                        console.log('Debug: Response is not JSON');
                        return response.text().then(text => {
                            console.log('Debug: Response text:', text);
                            throw new Error('Expected JSON response but got text');
                        });
                    }
                })
                .then(data => {
                    console.log('Debug: Processed data:', data);
                    
                    if (data.error) {
                        console.error('Debug: Server error:', data.error);
                        // Remove alert - just log to console
                        return;
                    }
                    
                    console.log('Debug: Job started successfully:', data);
                    // Remove alert - just log to console
                })
                .catch(error => {
                    console.error('Debug: Fetch error:', error);
                    // Remove alert - just log to console
                });
            };
        }
    };
    
    // Call the debug function
    setTimeout(debugFormSubmit, 1000);
    
    console.log("Debug script loaded successfully");
}); 