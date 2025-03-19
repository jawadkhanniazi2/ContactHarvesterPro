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
    
    // Upload form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!this.checkValidity()) {
            this.classList.add('was-validated');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('headless', document.getElementById('headless-mode').checked);
        
        startJob(formData);
    });
    
    // Manual form submission
    manualForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!this.checkValidity()) {
            this.classList.add('was-validated');
            return;
        }
        
        const urlsText = document.getElementById('manual-urls').value;
        const urls = urlsText.split('\n').filter(url => url.trim() !== '');
        
        if (urls.length === 0) {
            showAlert('Please enter at least one valid URL.', 'danger');
            return;
        }
        
        const data = {
            urls: urls,
            headless: document.getElementById('manual-headless-mode').checked
        };
        
        startManualJob(data);
    });
    
    /**
     * Job Management
     */
    
    // Start job from file upload
    function startJob(formData) {
        // Show loading state
        const submitBtn = uploadForm.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
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
            showAlert('Failed to start scraping job. Please try again.', 'danger');
        });
    }
    
    // Start job from manual URLs
    function startManualJob(data) {
        // Show loading state
        const submitBtn = manualForm.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        fetch('/api/manual', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
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
            showAlert('Failed to start scraping job. Please try again.', 'danger');
        });
    }
    
    // Show job modal with initial data
    function showJobModal(data) {
        document.getElementById('total-urls').textContent = data.total_urls;
        document.getElementById('completed-urls').textContent = '0';
        document.getElementById('job-progress-bar').style.width = '0%';
        document.getElementById('job-status-message').textContent = 'Initializing scraping process...';
        document.getElementById('job-time').textContent = 'Elapsed time: 0 seconds';
        document.getElementById('download-results').classList.add('d-none');
        
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
        const completedUrls = document.getElementById('completed-urls');
        const totalUrls = document.getElementById('total-urls');
        const progressBar = document.getElementById('job-progress-bar');
        const statusMessage = document.getElementById('job-status-message');
        const timeElement = document.getElementById('job-time');
        const downloadBtn = document.getElementById('download-results');
        const resultsSection = document.getElementById('results-section');
        
        // Update basic stats
        completedUrls.textContent = job.completed_urls;
        totalUrls.textContent = job.total_urls;
        
        // Update progress bar
        progressBar.style.width = `${job.progress}%`;
        progressBar.textContent = `${Math.round(job.progress)}%`;
        
        // Update status message
        let message = '';
        switch(job.status) {
            case 'initializing':
                message = 'Initializing scraping process...';
                break;
            case 'running':
                message = `Processing URLs (${job.completed_urls} of ${job.total_urls})`;
                
                // If we have result preview, show them
                if (job.result_preview && job.result_preview.length > 0) {
                    updateResultsTable(job.result_preview);
                    resultsSection.classList.remove('d-none');
                }
                break;
            case 'completed':
                message = 'Scraping completed successfully!';
                progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                progressBar.classList.add('bg-success');
                downloadBtn.classList.remove('d-none');
                downloadBtn.href = `/api/download/${job.job_id}`;
                
                // Fetch and display full results
                fetchJobResults(job.job_id);
                resultsSection.classList.remove('d-none');
                break;
            case 'error':
                message = `Error: ${job.error || 'Unknown error occurred'}`;
                progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                progressBar.classList.add('bg-danger');
                break;
        }
        statusMessage.textContent = message;
        
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
        
        timeElement.textContent = timeText;
        
        // Update jobs list if on jobs tab
        fetchJobs();
    }
    
    // Fetch job results
    function fetchJobResults(jobId) {
        fetch(`/api/results/${jobId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error("Error fetching results:", data.error);
                    return;
                }
                
                updateResultsTable(data.results);
            })
            .catch(error => {
                console.error("Error fetching job results:", error);
            });
    }
    
    // Update results table
    function updateResultsTable(results, maxRows = 10) {
        const tableBody = document.getElementById('results-table-body');
        const showMoreBtn = document.getElementById('show-more-results');
        
        // Clear existing rows
        tableBody.innerHTML = '';
        
        // Limit the number of results to display initially
        const displayResults = results.slice(0, maxRows);
        
        // Show/hide show more button based on results count
        if (results.length > maxRows) {
            showMoreBtn.classList.remove('d-none');
            showMoreBtn.textContent = `Show More Results (${maxRows} of ${results.length})`;
            
            // Handle show more button click
            showMoreBtn.onclick = () => {
                updateResultsTable(results, results.length); // Show all results
            };
        } else {
            showMoreBtn.classList.add('d-none');
        }
        
        // Add results to the table
        displayResults.forEach(result => {
            const row = document.createElement('tr');
            
            // URL column
            const urlCell = document.createElement('td');
            urlCell.textContent = result.domain || result.url;
            urlCell.title = result.url;
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
        });
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
                            `<a href="/api/download/${job.job_id}" class="btn btn-sm btn-success">
                                <i class="fas fa-download me-1"></i>Download
                             </a>` : 
                            ''
                        }
                    </div>
                </div>
            `;
        });
        
        jobsList.innerHTML = jobsHtml;
    }
    
    /**
     * Utilities
     */
    
    // Show alert message
    function showAlert(message, type = 'success') {
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