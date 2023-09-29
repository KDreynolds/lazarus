function uploadFile() {
    const fileInput = document.getElementById('file');
    if (fileInput.files.length === 0) {
        alert('Please select files to upload');
        return;
    }

    // Initialize overall progress
    let overallProgress = 0;

    // Upload each file individually
    Array.from(fileInput.files).forEach(file => {
        const formData = new FormData();
        formData.append('file', file);

        axios.post('http://localhost:8000/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            },
            // Track progress of individual file
            onUploadProgress: progressEvent => {
				let fileName = file.name; // assuming file is the individual file being uploaded
				let singleFileProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
				document.getElementById('singleFileProgress').value = singleFileProgress;
				
				let overallProgress = calculateOverallProgress(fileInput.files.length, singleFileProgress, fileName);
				document.getElementById('overallProgress').value = overallProgress;
			}
        }).then(response => {
            console.log(response.data);
        }).catch(error => {
            console.error('Error uploading file:', error);
        });
    });
}


function stopUpload() {
    axios.post('http://localhost:8000/stop').then(response => {
        alert(response.data.message);
        document.getElementById('upload-progress').value = 0; // Reset progress bar on stop
    }).catch(error => {
        alert('Error stopping upload: ' + error);
    });
}


function viewStatus() {
    axios.get('http://localhost:8000/status').then(response => {
        const statusContainer = document.getElementById('status-container');
        statusContainer.innerHTML = '';
        if (response.data.files && response.data.files.length > 0) {
            response.data.files.forEach(file => {
                const p = document.createElement('p');
                p.textContent = file;
                statusContainer.appendChild(p);
            });
        } else {
            statusContainer.innerHTML = '<p>No files have been uploaded</p>';
        }
    }).catch(error => {
        alert('Error fetching status: ' + error);
    });
}

let fileProgresses = {};

function calculateOverallProgress(totalFiles, singleFileProgress, fileName) {
    fileProgresses[fileName] = singleFileProgress;
    
    let sum = 0;
    Object.keys(fileProgresses).forEach(key => {
        sum += fileProgresses[key];
    });

    let overallProgress = sum / totalFiles;
    return overallProgress;
}

