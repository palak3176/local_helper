// Multiple Selection logic for service tiles
document.querySelectorAll('.service-tile').forEach(tile => {
    tile.addEventListener('click', () => {
        tile.classList.toggle('active');
    });
});

// SOS Button Alert
document.querySelector('.sos-btn').addEventListener('click', () => {
    alert("SOS Signal Dispatched to local Mumbai emergency contacts!");
});

// Status change monitoring
document.getElementById('statusToggle').addEventListener('change', (e) => {
    console.log("Provider Status Changed:", e.target.checked ? "Online" : "Offline");
});