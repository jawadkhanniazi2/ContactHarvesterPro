/**
 * Contact Harvester Pro - Main JavaScript
 * Handles all interactive elements and AJAX functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips and popovers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Global variables
    let activeJobId = null;
    let jobStatusInterval = null;
    const jobModal = new bootstrap.Modal(document.getElementById('job-modal'));
    const uploadForm = document.getElementById('upload-form');
    const manualForm = document.getElementById('manual-form');
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    
    /**
     * File Upload Functionality
     */
    
    // Prevent defaults for all drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('dragover');
    }
    
    function unhighlight() {
        dropArea.classList.remove('dragover');
    }
    
    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
        updateFileInfo();
    }
    
    // Update file info when file is selected
    fileInput.addEventListener('change', updateFileInfo);
    
    function updateFileInfo() {
        const fileUploadMessage = document.querySelector('.file-upload-message');
        const fileUploadPreview = document.querySelector('.file-upload-preview');
        const fileName = document.querySelector('.file-name');
        const fileSize = document.querySelector('.file-size');
        
        if (fileInput.files && fileInput.files[0]) {
            const file = fileInput.files[0];
            fileUploadMessage.classList.add('d-none');
            fileUploadPreview.classList.remove('d-none');
            fileName.textContent = file.name;
            fileSize.textContent = `Size: ${formatBytes(file.size)}`;
            
            // Set file icon based on extension
            const fileIcon = document.querySelector('.file-icon');
            const ext = file.name.split('.').pop().toLowerCase();
            
            if (['csv', 'xls', 'xlsx'].includes(ext)) {
                fileIcon.className = 'file-icon fas fa-file-excel mb-2';
            } else if (ext === 'txt') {
                fileIcon.className = 'file-icon fas fa-file-alt mb-2';
            } else {
                fileIcon.className = 'file-icon fas fa-file mb-2';
            }
        } else {
            fileUploadMessage.classList.remove('d-none');
            fileUploadPreview.classList.add('d-none');
        }
    }
    
    // Remove selected file
    document.querySelector('.btn-remove-file').addEventListener('click', function() {
        fileInput.value = '';
        updateFileInfo();
    });
    
    // Format bytes to human-readable format
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    /**
     * Form Submissions
     */
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Only attach event listeners if the form exists and doesn't already have a listener
    if (uploadForm && !uploadForm._eventListenerAttached) {
        uploadForm._eventListenerAttached = true;
        
        // Upload form submission
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (!this.checkValidity()) {
                this.classList.add('was-validated');
                return;
            }
            
            if (!fileInput.files || !fileInput.files[0]) {
                showAlert('Please select a file to upload.', 'warning');
                return;
            }
            
            try {
                // Create new FormData explicitly from the form element
                const formData = new FormData();
                
                // Add file with explicit name
                formData.append('file', fileInput.files[0], fileInput.files[0].name);
                
                // Add other form fields
                formData.append('headless', document.getElementById('headless-mode').checked);
                
                // For debugging
                console.log('File selected:', fileInput.files[0].name, fileInput.files[0].size);
                
                startJob(formData);
            } catch (err) {
                console.error('Error preparing form data:', err);
                showAlert('Error preparing form: ' + err.message, 'danger');
            }
        });
    }
    
    // Only attach event listeners if the form exists and doesn't already have a listener
    if (manualForm && !manualForm._eventListenerAttached) {
        manualForm._eventListenerAttached = true;
        
        // Manual form submission
        manualForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (!this.checkValidity()) {
                this.classList.add('was-validated');
                return;
            }
            
            const urlsText = document.getElementById('manual-urls').value;
            if (!urlsText.trim()) {
                showAlert('Please enter at least one valid URL.', 'warning');
                return;
            }
            
            const urls = urlsText.split('\n').filter(url => url.trim() !== '');
            
            if (urls.length === 0) {
                showAlert('Please enter at least one valid URL.', 'danger');
                return;
            }
            
            // Check if URLs are properly formatted
            const validatedUrls = urls.map(url => {
                // Add https:// if missing
                if (!url.match(/^https?:\/\//i)) {
                    return 'https://' + url.trim();
                }
                return url.trim();
            });
            
            const data = {
                urls: validatedUrls,
                headless: document.getElementById('manual-headless-mode').checked
            };
            
            startManualJob(data);
        });
    }
    
    /**
     * Job Management
     */
    
    // Reset the results section
    function resetResultsSection() {
        const mainResultsSection = document.getElementById('main-results-section');
        mainResultsSection.classList.add('d-none');
        document.getElementById('main-results-table-body').innerHTML = '';
        document.getElementById('main-show-more-results').classList.add('d-none');
    }
    
    // Start job from file upload
    function startJob(formData) {
        // Reset results from previous jobs
        resetResultsSection();
        
        // Show loading state
        const submitBtn = uploadForm.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        // Log what we're sending
        console.log('Sending FormData with:', formData.has('file'), formData.has('headless'));
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('Upload response status:', response.status, response.statusText);
            
            // Check if response is OK before trying to parse JSON
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(`Server returned ${response.status}: ${text || response.statusText}`);
                });
            }
            
            // Try to parse as JSON
            return response.json().catch(error => {
                console.error('JSON parse error:', error);
                throw new Error('Invalid JSON response from server');
            });
        })
        .then(data => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
            
            if (data.error) {
                showAlert(data.error, 'danger');
                return;
            }
            
            // Job started successfully
            activeJobId = data.job_id;
            showJobModal(data);
            startJobStatusPolling(data.job_id);
            
            // Reset form
            fileInput.value = '';
            updateFileInfo();
            uploadForm.classList.remove('was-validated');
        })
        .catch(error => {
            console.error('Error:', error);
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
            showAlert(`Failed to start scraping job: ${error.message}. Please check browser console for details.`, 'danger');
        });
    }
    
    // Start job from manual URLs
    function startManualJob(data) {
        // Reset results from previous jobs
        resetResultsSection();
        
        // Show loading state
        const submitBtn = manualForm.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        // Log what we're sending
        console.log('Sending manual URLs:', data.urls.length, 'URLs');
        
        fetch('/api/manual', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            console.log('Manual upload response status:', response.status, response.statusText);
            
            // Check if response is OK before trying to parse JSON
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(`Server returned ${response.status}: ${text || response.statusText}`);
                });
            }
            
            // Try to parse as JSON
            return response.json().catch(error => {
                console.error('JSON parse error:', error);
                throw new Error('Invalid JSON response from server');
            });
        })
        .then(data => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
            
            if (data.error) {
                showAlert(data.error, 'danger');
                return;
            }
            
            // Job started successfully
            activeJobId = data.job_id;
            showJobModal(data);
            startJobStatusPolling(data.job_id);
            
            // Reset form
            document.getElementById('manual-urls').value = '';
            manualForm.classList.remove('was-validated');
        })
        .catch(error => {
            console.error('Error:', error);
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
            showAlert(`Failed to start scraping job: ${error.message}. Please check browser console for details.`, 'danger');
        });
    }
    
    // Show job modal with initial data
    function showJobModal(data) {
        // Make sure the elements exist before trying to access them
        const totalUrlsElement = document.getElementById('total-urls');
        const completedUrlsElement = document.getElementById('completed-urls');
        const progressBarElement = document.getElementById('job-progress-bar');
        const statusMessageElement = document.getElementById('job-status-message');
        const timeElement = document.getElementById('job-time');
        
        // Only update elements if they exist
        if (totalUrlsElement) totalUrlsElement.textContent = data.total_urls;
        if (completedUrlsElement) completedUrlsElement.textContent = '0';
        if (progressBarElement) progressBarElement.style.width = '0%';
        if (statusMessageElement) statusMessageElement.textContent = 'Initializing scraping process...';
        if (timeElement) timeElement.textContent = 'Elapsed time: 0 seconds';
        
        jobModal.show();
    }
    
    // Start polling for job status
    function startJobStatusPolling(jobId) {
        if (jobStatusInterval) {
            clearInterval(jobStatusInterval);
        }
        
        const startTime = new Date().getTime();
        
        jobStatusInterval = setInterval(() => {
            fetch(`/api/jobs/${jobId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        clearInterval(jobStatusInterval);
                        return;
                    }
                    
                    // Update UI with job status
                    updateJobStatus(data, startTime);
                    
                    // If job is completed or failed, stop polling
                    if (data.status === 'completed' || data.status === 'error') {
                        clearInterval(jobStatusInterval);
                    }
                })
                .catch(error => {
                    console.error('Error polling job status:', error);
                });
        }, 1000);
    }
    
    // Update job status in UI
    function updateJobStatus(job, startTime) {
        // Get DOM elements with null checks
        const completedUrls = document.getElementById('completed-urls');
        const totalUrls = document.getElementById('total-urls');
        const progressBar = document.getElementById('job-progress-bar');
        const statusMessage = document.getElementById('job-status-message');
        const timeElement = document.getElementById('job-time');
        const mainResultsSection = document.getElementById('main-results-section');
        const mainDownloadBtn = document.getElementById('main-download-results');
        
        // Update basic stats (with null checks)
        if (completedUrls) completedUrls.textContent = job.completed_urls;
        if (totalUrls) totalUrls.textContent = job.total_urls;
        
        // Update progress bar (with null check)
        if (progressBar) {
            progressBar.style.width = `${job.progress}%`;
            progressBar.textContent = `${Math.round(job.progress)}%`;
        }
        
        // Update status message
        let message = '';
        switch(job.status) {
            case 'initializing':
                message = 'Initializing scraping process...';
                break;
            case 'running':
                message = `Processing URLs (${job.completed_urls} of ${job.total_urls})`;
                break;
            case 'completed':
                message = 'Scraping completed successfully!';
                
                // Update progress bar classes (with null check)
                if (progressBar) {
                    progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                    progressBar.classList.add('bg-success');
                }
                
                // Close the modal automatically when complete
                setTimeout(() => {
                    const closeButton = document.querySelector('#job-modal .btn-close');
                    if (closeButton) closeButton.click();
                }, 1000);
                
                // Show the main results section (with null check)
                if (mainResultsSection) mainResultsSection.classList.remove('d-none');
                
                // Set up download button (with null check)
                if (mainDownloadBtn) {
                    mainDownloadBtn.href = `/api/download/${job.job_id}`;
                    mainDownloadBtn.setAttribute('download', `scrape_results_${job.job_id}.xlsx`);
                    
                    // Add click event handler to ensure download works
                    mainDownloadBtn.onclick = function(e) {
                        e.preventDefault();
                        
                        // Use fetch API to download the file
                        fetch(`/api/download/${job.job_id}`)
                            .then(response => response.blob())
                            .then(blob => {
                                const url = window.URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.style.display = 'none';
                                a.href = url;
                                a.download = `scrape_results_${job.job_id}.xlsx`;
                                document.body.appendChild(a);
                                a.click();
                                window.URL.revokeObjectURL(url);
                                document.body.removeChild(a);
                            })
                            .catch(error => {
                                console.error('Download error:', error);
                                showAlert('Error downloading results. Please try again.', 'danger');
                            });
                    };
                }
                
                // Special handling for single URL jobs
                if (job.total_urls === 1) {
                    console.log('Single URL job detected:', job);

                    // New critical fix: Try direct_results field first
                    if (job.direct_results && Array.isArray(job.direct_results) && job.direct_results.length > 0) {
                        console.log('Using direct_results for single URL job:', job.direct_results);      
                        showAlert('Single website processed successfully!', 'success');

                        // CRITICAL FIX: Manually add the first result to ensure it displays
                        const tableBody = document.getElementById('main-results-table-body');
                        if (tableBody) {
                            tableBody.innerHTML = ''; // Clear the table

                            const firstResult = job.direct_results[0];
                            console.log('First domain result from direct_results:', firstResult);
                            
                            // CRITICAL VALIDATION: Ensure firstResult has properly structured data
                            if (firstResult) {
                                console.log('Validating first result data structure:');
                                console.log('- URL:', firstResult.url);
                                console.log('- Domain:', firstResult.domain);
                                console.log('- Emails type:', typeof firstResult.emails);
                                console.log('- Emails is array:', Array.isArray(firstResult.emails));
                                if (Array.isArray(firstResult.emails)) {
                                    console.log('- Emails length:', firstResult.emails.length);
                                    console.log('- Emails contents:', firstResult.emails);
                                }
                                console.log('- Phones type:', typeof firstResult.phones);
                                console.log('- Phones is array:', Array.isArray(firstResult.phones));
                                console.log('- Social media type:', typeof firstResult.social_media);
                                
                                // Now create and add the row after validation
                                try {
                                    // Create row for first result
                                    const row = document.createElement('tr');
                                    
                                    // URL column
                                    const urlCell = document.createElement('td');
                                    urlCell.textContent = firstResult.domain || firstResult.url || 'Unknown URL';
                                    urlCell.title = firstResult.url || '';
                                    row.appendChild(urlCell);
                                    
                                    // Emails column
                                    const emailsCell = document.createElement('td');
                                    if (Array.isArray(firstResult.emails) && firstResult.emails.length > 0) {
                                        emailsCell.textContent = firstResult.emails.join(', ');
                                        console.log('Displaying emails:', firstResult.emails.join(', '));
                                    } else {
                                        emailsCell.textContent = 'None found';
                                        emailsCell.classList.add('text-muted');
                                    }
                                    row.appendChild(emailsCell);
                                    
                                    // Phones column
                                    const phonesCell = document.createElement('td');
                                    if (Array.isArray(firstResult.phones) && firstResult.phones.length > 0) {
                                        phonesCell.textContent = firstResult.phones.join(', ');
                                        console.log('Displaying phones:', firstResult.phones.join(', '));
                                    } else {
                                        phonesCell.textContent = 'None found';
                                        phonesCell.classList.add('text-muted');
                                    }
                                    row.appendChild(phonesCell);
                                    
                                    // Social media column
                                    const socialCell = document.createElement('td');
                                    const socialMedia = firstResult.social_media || {};
                                    
                                    if (Object.keys(socialMedia).length > 0) {
                                        const socialLinks = [];
                                        
                                        if (socialMedia.linkedin) {
                                            socialLinks.push(`<a href="${socialMedia.linkedin}" target="_blank" class="me-1">
                                                <i class="fab fa-linkedin" title="LinkedIn"></i>
                                            </a>`);
                                        }
                                        
                                        if (socialMedia.twitter) {
                                            socialLinks.push(`<a href="${socialMedia.twitter}" target="_blank" class="me-1">
                                                <i class="fab fa-twitter" title="Twitter"></i>
                                            </a>`);
                                        }
                                        
                                        if (socialMedia.facebook) {
                                            socialLinks.push(`<a href="${socialMedia.facebook}" target="_blank" class="me-1">
                                                <i class="fab fa-facebook" title="Facebook"></i>
                                            </a>`);
                                        }
                                        
                                        socialCell.innerHTML = socialLinks.join('');
                                    } else {
                                        socialCell.textContent = 'None found';
                                        socialCell.classList.add('text-muted');
                                    }
                                    row.appendChild(socialCell);
                                    
                                    // Status column
                                    const statusCell = document.createElement('td');
                                    const status = firstResult.status || 'Unknown';
                                    
                                    if (status.includes('success')) {
                                        statusCell.innerHTML = '<span class="badge bg-success">Success</span>';
                                    } else if (status.includes('Error')) {
                                        statusCell.innerHTML = `<span class="badge bg-danger" title="${status}">Error</span>`;
                                    } else {
                                        statusCell.textContent = status;
                                    }
                                    row.appendChild(statusCell);
                                    
                                    // Add row to table
                                    tableBody.appendChild(row);
                                    console.log('First domain row manually added from direct_results');
                                } catch (err) {
                                    console.error('Error creating row for first domain result:', err);
                                }
                            }
                        }
                        return; // Skip further processing
                    }
                    
                    // Try first_domain_result field
                    if (job.first_domain_result) {
                        console.log('Using first_domain_result for single URL job:', job.first_domain_result);
                        showAlert('Single website processed successfully!', 'success');
                        updateMainResultsTable([job.first_domain_result]);
                        return; // Skip further processing
                    }
                    
                    // Then try single_result field
                    if (job.single_result) {
                        console.log('Found single result in job data:', job.single_result);
                        showAlert('Single website processed successfully!', 'success');
                        // Display the single result immediately - wrap in array to ensure it's treated as an array
                        updateMainResultsTable([job.single_result]);
                        return; // Skip further processing
                    }
                    
                    // Then try result_preview
                    if (job.result_preview && job.result_preview.length > 0) {
                        console.log('Using result preview for single URL job:', job.result_preview);
                        showAlert('Single website processed successfully!', 'success');
                        // Immediately show preview results
                        updateMainResultsTable(job.result_preview);
                        return; // Skip further processing
                    }
                    
                    // If neither is available, try to get results directly for this single URL
                    console.log('Fetching results directly for single URL job');
                    fetchJobResults(job.job_id);
                    return; // Skip default handling
                }
                
                // Handle multi-URL jobs
                // Add a small delay before fetching results to ensure everything is ready
                console.log(`Job ${job.job_id} completed with ${job.total_urls} URLs, fetching results after delay...`);
                
                // First check if we have direct access to results preview
                if (job.result_preview && job.result_preview.length > 0) {
                    console.log(`Found ${job.result_preview.length} direct result previews`);
                    // Immediately show preview results
                    updateMainResultsTable(job.result_preview);
                }
                
                // Then fetch full results after a delay
                setTimeout(() => {
                    // Fetch and display full results 
                    fetchJobResults(job.job_id);
                }, 1500);
                break;
            case 'error':
                message = `Error: ${job.error || 'Unknown error occurred'}`;
                
                // Update progress bar classes (with null check)
                if (progressBar) {
                    progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                    progressBar.classList.add('bg-danger');
                }
                break;
        }
        if (statusMessage) statusMessage.textContent = message;
        
        // Update elapsed time
        let elapsedSeconds = Math.floor((new Date().getTime() - startTime) / 1000);
        let timeText = '';
        
        if (elapsedSeconds < 60) {
            timeText = `Elapsed time: ${elapsedSeconds} seconds`;
        } else if (elapsedSeconds < 3600) {
            const minutes = Math.floor(elapsedSeconds / 60);
            const seconds = elapsedSeconds % 60;
            timeText = `Elapsed time: ${minutes} minute${minutes > 1 ? 's' : ''} ${seconds} second${seconds !== 1 ? 's' : ''}`;
        } else {
            const hours = Math.floor(elapsedSeconds / 3600);
            const minutes = Math.floor((elapsedSeconds % 3600) / 60);
            timeText = `Elapsed time: ${hours} hour${hours > 1 ? 's' : ''} ${minutes} minute${minutes > 1 ? 's' : ''}`;
        }
        
        if (timeElement) timeElement.textContent = timeText;
        
        // Update jobs list if on jobs tab
        fetchJobs();
    }
    
    // Fetch job results
    function fetchJobResults(jobId) {
        console.log(`Fetching results for job ${jobId}`);
        
        // EMERGENCY FIX FOR FIRST DOMAIN ISSUE
        // Use XMLHttpRequest instead of fetch to rule out any potential fetch API issues
        const xhr = new XMLHttpRequest();
        xhr.open('GET', `/api/results/${jobId}`, true);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    const responseText = xhr.responseText;
                    console.log('Raw API response via XMLHttpRequest:', responseText);
                    
                    try {
                        const data = JSON.parse(responseText);
                        if (data.error) {
                            console.error("Error fetching results:", data.error);
                            showAlert(`Error fetching results: ${data.error}`, 'danger');
                            return;
                        }
                        
                        // Clear the table immediately for any case
                        const tableBody = document.getElementById('main-results-table-body');
                        if (tableBody) {
                            tableBody.innerHTML = '';
                            console.log('Cleared results table');
                        }
                        
                        console.log('Full results data object:', data);
                        
                        // Additional DEBUG: Check result structure
                        if (data.results && data.results.length > 0) {
                            console.log('Data structure validation:');
                            console.log('- results is array:', Array.isArray(data.results));
                            console.log('- results length:', data.results.length);
                            console.log('- first result complete structure:', JSON.stringify(data.results[0], null, 2));
                            
                            // Validate first result structure
                            const firstResult = data.results[0];
                            console.log('First result validation:');
                            console.log('- has URL:', Boolean(firstResult.url));
                            console.log('- has domain:', Boolean(firstResult.domain));
                            console.log('- emails is array:', Array.isArray(firstResult.emails));
                            console.log('- phones is array:', Array.isArray(firstResult.phones));
                            console.log('- social_media is object:', typeof firstResult.social_media === 'object');
                        }
                        
                        // Check if we have results at all
                        if (!data.results || !Array.isArray(data.results) || data.results.length === 0) {
                            console.warn("No results received from API or results is not an array");
                            showAlert('No results were found for this job', 'warning');
                            return;
                        }
                        
                        console.log(`Received ${data.results.length} results for job ${jobId}`);
                        console.log("Results array type:", Object.prototype.toString.call(data.results));
                        
                        // DEBUG: Specifically log and process the first result
                        if (data.results.length > 0) {
                            const firstResult = data.results[0];
                            console.log("FIRST RESULT:", JSON.stringify(firstResult));
                            
                            // CRITICAL FIX: Directly add first result to the table without using updateMainResultsTable
                            if (tableBody) {
                                const firstRow = document.createElement('tr');
                                
                                // URL column
                                const urlCell = document.createElement('td');
                                urlCell.textContent = firstResult.domain || firstResult.url || 'Unknown URL';
                                urlCell.title = firstResult.url || '';
                                firstRow.appendChild(urlCell);
                                
                                // CRITICAL FIX: Properly handle emails - ensure we have an array and join it
                                const emailsCell = document.createElement('td');
                                if (firstResult.emails && Array.isArray(firstResult.emails) && firstResult.emails.length > 0) {
                                    // Convert to string only after validation
                                    emailsCell.textContent = firstResult.emails.join(', ');
                                    console.log('Emails displayed:', firstResult.emails.join(', '));
                                } else {
                                    emailsCell.textContent = 'None found';
                                    emailsCell.classList.add('text-muted');
                                    console.log('No emails found in first result');
                                }
                                firstRow.appendChild(emailsCell);
                                
                                // CRITICAL FIX: Properly handle phones - ensure we have an array and join it
                                const phonesCell = document.createElement('td');
                                if (firstResult.phones && Array.isArray(firstResult.phones) && firstResult.phones.length > 0) {
                                    // Convert to string only after validation
                                    phonesCell.textContent = firstResult.phones.join(', ');
                                    console.log('Phones displayed:', firstResult.phones.join(', '));
                                } else {
                                    phonesCell.textContent = 'None found';
                                    phonesCell.classList.add('text-muted');
                                    console.log('No phones found in first result');
                                }
                                firstRow.appendChild(phonesCell);
                                
                                // Social media column
                                const socialCell = document.createElement('td');
                                const socialMedia = firstResult.social_media || {};
                                
                                if (Object.keys(socialMedia).length > 0) {
                                    const socialLinks = [];
                                    
                                    if (socialMedia.linkedin) {
                                        socialLinks.push(`<a href="${socialMedia.linkedin}" target="_blank" class="me-1">
                                            <i class="fab fa-linkedin" title="LinkedIn"></i>
                                        </a>`);
                                    }
                                    
                                    if (socialMedia.twitter) {
                                        socialLinks.push(`<a href="${socialMedia.twitter}" target="_blank" class="me-1">
                                            <i class="fab fa-twitter" title="Twitter"></i>
                                        </a>`);
                                    }
                                    
                                    if (socialMedia.facebook) {
                                        socialLinks.push(`<a href="${socialMedia.facebook}" target="_blank" class="me-1">
                                            <i class="fab fa-facebook" title="Facebook"></i>
                                        </a>`);
                                    }
                                    
                                    socialCell.innerHTML = socialLinks.join('');
                                    console.log('Social media links displayed:', Object.keys(socialMedia).join(', '));
                                } else {
                                    socialCell.textContent = 'None found';
                                    socialCell.classList.add('text-muted');
                                    console.log('No social media links found in first result');
                                }
                                firstRow.appendChild(socialCell);
                                
                                // Status column
                                const statusCell = document.createElement('td');
                                const status = firstResult.status || 'Unknown';
                                
                                if (status.includes('success')) {
                                    statusCell.innerHTML = '<span class="badge bg-success">Success</span>';
                                } else if (status.includes('Error')) {
                                    statusCell.innerHTML = `<span class="badge bg-danger" title="${status}">Error</span>`;
                                } else {
                                    statusCell.textContent = status;
                                }
                                firstRow.appendChild(statusCell);
                                
                                // Insert first row IMMEDIATELY
                                tableBody.appendChild(firstRow);
                                console.log("First row directly added:", firstRow.outerHTML);
                                
                                // Special handling: Add the rest of the rows manually to prevent any issues
                                if (data.results.length > 1) {
                                    for (let i = 1; i < data.results.length; i++) {
                                        const result = data.results[i];
                                        const row = document.createElement('tr');
                                        
                                        // URL column
                                        const urlCell = document.createElement('td');
                                        urlCell.textContent = result.domain || result.url || 'Unknown URL';
                                        urlCell.title = result.url || '';
                                        row.appendChild(urlCell);
                                        
                                        // Emails column
                                        const emailsCell = document.createElement('td');
                                        if (result.emails && result.emails.length > 0) {
                                            emailsCell.textContent = Array.isArray(result.emails) ? 
                                                result.emails.join(', ') : result.emails;
                                        } else {
                                            emailsCell.textContent = 'None found';
                                            emailsCell.classList.add('text-muted');
                                        }
                                        row.appendChild(emailsCell);
                                        
                                        // Phones column
                                        const phonesCell = document.createElement('td');
                                        if (result.phones && result.phones.length > 0) {
                                            phonesCell.textContent = Array.isArray(result.phones) ? 
                                                result.phones.join(', ') : result.phones;
                                        } else {
                                            phonesCell.textContent = 'None found';
                                            phonesCell.classList.add('text-muted');
                                        }
                                        row.appendChild(phonesCell);
                                        
                                        // Social media column
                                        const socialCell = document.createElement('td');
                                        const socialMedia = result.social_media || {};
                                        
                                        if (Object.keys(socialMedia).length > 0) {
                                            const socialLinks = [];
                                            
                                            if (socialMedia.linkedin) {
                                                socialLinks.push(`<a href="${socialMedia.linkedin}" target="_blank" class="me-1">
                                                    <i class="fab fa-linkedin" title="LinkedIn"></i>
                                                </a>`);
                                            }
                                            
                                            if (socialMedia.twitter) {
                                                socialLinks.push(`<a href="${socialMedia.twitter}" target="_blank" class="me-1">
                                                    <i class="fab fa-twitter" title="Twitter"></i>
                                                </a>`);
                                            }
                                            
                                            if (socialMedia.facebook) {
                                                socialLinks.push(`<a href="${socialMedia.facebook}" target="_blank" class="me-1">
                                                    <i class="fab fa-facebook" title="Facebook"></i>
                                                </a>`);
                                            }
                                            
                                            socialCell.innerHTML = socialLinks.join('');
                                        } else {
                                            socialCell.textContent = 'None found';
                                            socialCell.classList.add('text-muted');
                                        }
                                        row.appendChild(socialCell);
                                        
                                        // Status column
                                        const statusCell = document.createElement('td');
                                        const status = result.status || 'Unknown';
                                        
                                        if (status.includes('success')) {
                                            statusCell.innerHTML = '<span class="badge bg-success">Success</span>';
                                        } else if (status.includes('Error')) {
                                            statusCell.innerHTML = `<span class="badge bg-danger" title="${status}">Error</span>`;
                                        } else {
                                            statusCell.textContent = status;
                                        }
                                        row.appendChild(statusCell);
                                        
                                        tableBody.appendChild(row);
                                    }
                                }
                                
                                // Show more button handling
                                const showMoreBtn = document.getElementById('main-show-more-results');
                                if (showMoreBtn) {
                                    if (data.results.length > 25) {
                                        showMoreBtn.classList.remove('d-none');
                                        showMoreBtn.textContent = `Show All Results (showing 25 of ${data.results.length})`;
                                        showMoreBtn.onclick = function() {
                                            // We've already shown all results, so just hide the button
                                            showMoreBtn.classList.add('d-none');
                                        };
                                    } else {
                                        showMoreBtn.classList.add('d-none');
                                    }
                                }
                            } else {
                                console.error("Table body element not found!");
                            }
                        } else {
                            console.warn("No results to display");
                            const tableBody = document.getElementById('main-results-table-body');
                            if (tableBody) {
                                tableBody.innerHTML = `<tr><td colspan="5" class="text-center">No results found</td></tr>`;
                            }
                        }
                        
                        // Show results section and scroll to it
                        const mainResultsSection = document.getElementById('main-results-section');
                        if (mainResultsSection) {
                            mainResultsSection.classList.remove('d-none');
                            setTimeout(() => {
                                mainResultsSection.scrollIntoView({ behavior: 'smooth' });
                            }, 300);
                        }
                    } catch (e) {
                        console.error('Error parsing JSON response:', e);
                        showAlert(`Error processing results: ${e.message}`, 'danger');
                    }
                } else {
                    console.error(`Server returned error status: ${xhr.status}`);
                    showAlert(`Error loading results: Server returned status ${xhr.status}`, 'danger');
                }
            }
        };
        xhr.onerror = function() {
            console.error('Network error occurred');
            showAlert('Network error occurred while fetching results', 'danger');
        };
        xhr.send();
    }
    
    // Update main results table
    function updateMainResultsTable(results, maxRows = 25, skipClear = false) {
        const tableBody = document.getElementById('main-results-table-body');
        const showMoreBtn = document.getElementById('main-show-more-results');
        
        // Ensure the table body exists
        if (!tableBody) {
            console.error("Results table body element not found");
            return;
        }
        
        // Debug: Log the raw results object for inspection
        console.log('Raw results object:', JSON.stringify(results));
        
        // Only clear existing rows if not skipping clear (used when adding first row manually)
        if (!skipClear) {
            tableBody.innerHTML = '';
        }
        
        console.log(`Updating results table with ${results ? results.length : 0} results (skipClear: ${skipClear})`);
        
        // Check if results exists and has items
        if (!results || results.length === 0) {
            console.warn("No results to display");
            if (!skipClear) { // Only add "no results" row if not skipping clear
                tableBody.innerHTML = `<tr><td colspan="5" class="text-center">No results found</td></tr>`;
            }
            showMoreBtn.classList.add('d-none');
            return;
        }
        
        // Force results to be an array even if a single object was passed
        const resultsArray = Array.isArray(results) ? results : [results];
        console.log(`Processed results array with ${resultsArray.length} items`);
        
        // Log each result in the array for debugging
        resultsArray.forEach((result, index) => {
            console.log(`Result ${index}:`, result);
            console.log(`  URL: ${result.url}`);
            console.log(`  Domain: ${result.domain}`);
            console.log(`  Emails: ${JSON.stringify(result.emails)}`);
            console.log(`  Phones: ${JSON.stringify(result.phones)}`);
            console.log(`  Social media: ${JSON.stringify(result.social_media)}`);
            console.log(`  Status: ${result.status}`);
        });
        
        // Limit the number of results to display initially
        const displayResults = resultsArray.slice(0, maxRows);
        
        // Show/hide show more button based on results count
        if (resultsArray.length > maxRows) {
            showMoreBtn.classList.remove('d-none');
            showMoreBtn.textContent = `Show More Results (${maxRows} of ${resultsArray.length})`;
            
            // Handle show more button click
            showMoreBtn.onclick = () => {
                updateMainResultsTable(resultsArray, resultsArray.length); // Show all results
                showMoreBtn.classList.add('d-none');
            };
        } else {
            showMoreBtn.classList.add('d-none');
        }
        
        console.log(`Creating ${displayResults.length} table rows`);
        
        // Add results to the table one by one
        displayResults.forEach((result, index) => {
            console.log(`Creating row for result ${index}`);
            
            try {
                const row = document.createElement('tr');
                
                // URL column
                const urlCell = document.createElement('td');
                urlCell.textContent = result.domain || result.url || 'Unknown URL';
                urlCell.title = result.url || '';
                row.appendChild(urlCell);
                
                // Emails column
                const emailsCell = document.createElement('td');
                if (result.emails && result.emails.length > 0) {
                    emailsCell.textContent = Array.isArray(result.emails) ? 
                        result.emails.join(', ') : result.emails;
                } else {
                    emailsCell.textContent = 'None found';
                    emailsCell.classList.add('text-muted');
                }
                row.appendChild(emailsCell);
                
                // Phones column
                const phonesCell = document.createElement('td');
                if (result.phones && result.phones.length > 0) {
                    phonesCell.textContent = Array.isArray(result.phones) ? 
                        result.phones.join(', ') : result.phones;
                } else {
                    phonesCell.textContent = 'None found';
                    phonesCell.classList.add('text-muted');
                }
                row.appendChild(phonesCell);
                
                // Social media column
                const socialCell = document.createElement('td');
                const socialMedia = result.social_media || {};
                
                if (Object.keys(socialMedia).length > 0) {
                    const socialLinks = [];
                    
                    if (socialMedia.linkedin) {
                        socialLinks.push(`<a href="${socialMedia.linkedin}" target="_blank" class="me-1">
                            <i class="fab fa-linkedin" title="LinkedIn"></i>
                        </a>`);
                    }
                    
                    if (socialMedia.twitter) {
                        socialLinks.push(`<a href="${socialMedia.twitter}" target="_blank" class="me-1">
                            <i class="fab fa-twitter" title="Twitter"></i>
                        </a>`);
                    }
                    
                    if (socialMedia.facebook) {
                        socialLinks.push(`<a href="${socialMedia.facebook}" target="_blank" class="me-1">
                            <i class="fab fa-facebook" title="Facebook"></i>
                        </a>`);
                    }
                    
                    socialCell.innerHTML = socialLinks.join('');
                } else {
                    socialCell.textContent = 'None found';
                    socialCell.classList.add('text-muted');
                }
                row.appendChild(socialCell);
                
                // Status column
                const statusCell = document.createElement('td');
                const status = result.status || 'Unknown';
                
                if (status.includes('success')) {
                    statusCell.innerHTML = '<span class="badge bg-success">Success</span>';
                } else if (status.includes('Error')) {
                    statusCell.innerHTML = `<span class="badge bg-danger" title="${status}">Error</span>`;
                } else {
                    statusCell.textContent = status;
                }
                row.appendChild(statusCell);
                
                // Debug: log row HTML before adding to table
                console.log(`Row ${index} HTML:`, row.outerHTML);
                
                // Add the row to the table
                tableBody.appendChild(row);
                console.log(`Added row ${index} to table`);
            } catch (err) {
                console.error(`Error creating row for result ${index}:`, err, result);
            }
        });
        
        // Debug: Verify final table contents
        console.log('Final table HTML:', tableBody.innerHTML);
    }
    
    /**
     * Jobs List
     */
    
    // Refresh jobs button
    document.getElementById('refresh-jobs').addEventListener('click', fetchJobs);
    
    // Jobs tab shown event - refresh jobs list
    document.getElementById('jobs-tab').addEventListener('shown.bs.tab', fetchJobs);
    
    // Fetch jobs
    function fetchJobs() {
        fetch('/api/jobs')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    return;
                }
                
                updateJobsList(data.jobs);
            })
            .catch(error => {
                console.error('Error fetching jobs:', error);
            });
    }
    
    // Update jobs list in UI
    function updateJobsList(jobs) {
        const jobsList = document.getElementById('jobs-list');
        
        if (!jobs || jobs.length === 0) {
            jobsList.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-tasks mb-3 display-4"></i>
                    <p>No jobs found. Start a scraping job to see it here.</p>
                </div>
            `;
            return;
        }
        
        // Sort jobs by start time (newest first)
        jobs.sort((a, b) => {
            return new Date(b.start_time) - new Date(a.start_time);
        });
        
        let jobsHtml = '';
        
        jobs.forEach(job => {
            // Create status badge
            let statusBadge = '';
            switch(job.status) {
                case 'initializing':
                    statusBadge = `<span class="job-status-badge status-initializing">Initializing</span>`;
                    break;
                case 'running':
                    statusBadge = `<span class="job-status-badge status-running">Running</span>`;
                    break;
                case 'completed':
                    statusBadge = `<span class="job-status-badge status-completed">Completed</span>`;
                    break;
                case 'error':
                    statusBadge = `<span class="job-status-badge status-error">Error</span>`;
                    break;
            }
            
            // Format date
            const date = new Date(job.start_time * 1000);
            const formattedDate = date.toLocaleString();
            
            jobsHtml += `
                <div class="job-card">
                    <div class="job-header">
                        <div>
                            <h5 class="job-title">Job #${job.job_id}</h5>
                            <div class="job-meta">${formattedDate}</div>
                        </div>
                        ${statusBadge}
                    </div>
                    <div class="job-stats">
                        <div class="job-stat">
                            <div class="stat-value">${job.total_urls}</div>
                            <div class="stat-label">Total URLs</div>
                        </div>
                        <div class="job-stat">
                            <div class="stat-value">${job.completed_urls}</div>
                            <div class="stat-label">Processed</div>
                        </div>
                        <div class="job-stat">
                            <div class="stat-value">${job.elapsed_time}s</div>
                            <div class="stat-label">Elapsed Time</div>
                        </div>
                    </div>
                    <div class="job-progress progress mb-3">
                        <div class="progress-bar ${job.status === 'completed' ? 'bg-success' : job.status === 'error' ? 'bg-danger' : ''}" 
                             role="progressbar" 
                             style="width: ${job.progress}%" 
                             aria-valuenow="${job.progress}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                            ${Math.round(job.progress)}%
                        </div>
                    </div>
                    <div class="job-actions d-flex justify-content-end">
                        ${job.status === 'completed' ? 
                            `<a href="/api/download/${job.job_id}" class="btn btn-sm btn-success download-job-button" data-job-id="${job.job_id}">
                                <i class="fas fa-download me-1"></i>Download
                             </a>` : 
                            ''
                        }
                    </div>
                </div>
            `;
        });
        
        jobsList.innerHTML = jobsHtml;
        
        // Add event listeners to download buttons
        document.querySelectorAll('.download-job-button').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const jobId = this.getAttribute('data-job-id');
                
                // Use fetch API to download the file
                fetch(`/api/download/${jobId}`)
                    .then(response => response.blob())
                    .then(blob => {
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = `scrape_results_${jobId}.xlsx`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    })
                    .catch(error => {
                        console.error('Download error:', error);
                        showAlert('Error downloading results. Please try again.', 'danger');
                    });
            });
        });
    }
    
    /**
     * Utilities
     */
    
    // Show alert message
    function showAlert(message, type = 'success') {
        // Log to console for debugging
        if (type === 'danger' || type === 'warning') {
            console.error('Alert:', message);
        } else {
            console.log('Alert:', message);
        }
        
        const alertContainer = document.createElement('div');
        alertContainer.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-4`;
        alertContainer.style.zIndex = '9999';
        alertContainer.style.maxWidth = '90%';
        alertContainer.style.width = '500px';
        
        alertContainer.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        document.body.appendChild(alertContainer);
        
        // Auto close after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertContainer);
            bsAlert.close();
        }, 5000);
    }
    
    // Close modal cleanup
    document.getElementById('job-modal').addEventListener('hidden.bs.modal', function() {
        if (jobStatusInterval) {
            clearInterval(jobStatusInterval);
            jobStatusInterval = null;
        }
    });
    
    // Smooth scroll for navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });
}); 