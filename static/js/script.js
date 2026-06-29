// Initialize Map (Centered on Mumbai)
const map = L.map('map').setView([19.0760, 72.8777], 13);

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png').addTo(map);

// Mock Data
const pins = [
    { name: "Guide: Rahul", pos: [19.085, 72.885], type: 'guide' },
    { name: "Helper: Amit", pos: [19.065, 72.865], type: 'helper' },
    { name: "Guide: Priya", pos: [19.100, 72.900], type: 'guide' }
];

// Add pins to map
pins.forEach(p => {
    L.marker(p.pos).addTo(map).bindPopup(`<b>${p.name}</b><br>Available for 1hr`);
});

function updateMap(service) {
    document.querySelectorAll('.service-chip').forEach(c => c.classList.remove('active'));
    event.currentTarget.classList.add('active');
    console.log("Filtering map for:", service);
}