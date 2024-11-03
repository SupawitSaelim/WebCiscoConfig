function updateDateTime() {
    const now = new Date();
    const options = { 
        timeZone: 'Asia/Bangkok',  // ระบุเขตเวลาเป็นกรุงเทพฯ
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit', 
        hour12: true 
    };
    const formattedDateTime = now.toLocaleString('en-US', options);
    document.getElementById('datetime').innerText = formattedDateTime;
    // Store the last updated time in sessionStorage
    sessionStorage.setItem('lastUpdated', formattedDateTime);
}

// Check if there's a stored datetime and display it
const lastUpdated = sessionStorage.getItem('lastUpdated');
if (lastUpdated) {
    document.getElementById('datetime').innerText = lastUpdated;
} else {
    // Initial call to display immediately
    updateDateTime();
}

// Update the datetime every second
setInterval(updateDateTime, 1000);
