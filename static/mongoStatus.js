function updateMongoStatus() {
    fetch('/mongo_status', { cache: "no-store" })
        .then(response => response.json())
        .then(data => {
            const indicator = document.getElementById('mongo-status-indicator');
            if (data.status === 'connected') {
                indicator.classList.add('status-connected');
                indicator.classList.remove('status-disconnected');
                indicator.title = "Connected to MongoDB";
            } else {
                indicator.classList.add('status-disconnected');
                indicator.classList.remove('status-connected');
                indicator.title = "Disconnected from MongoDB";
            }
        })
        .catch(error => {
            console.error('Error fetching MongoDB status:', error);
        });
}

setInterval(updateMongoStatus, 5000);

updateMongoStatus();
