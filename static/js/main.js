let globe;

function initGlobe() {
    globe = Globe()
        .globeImageUrl('//unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
        .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
        .pointOfView({ altitude: 2.5 })
        .width(document.getElementById('globe').offsetWidth)
        .height(document.getElementById('globe').offsetHeight)
        (document.getElementById('globe'));

    window.addEventListener('resize', () => {
        globe.width(document.getElementById('globe').offsetWidth)
            .height(document.getElementById('globe').offsetHeight);
    });

    updateGlobeMarkers();
    addTableClickHandlers();
}

function addTableClickHandlers() {
    const rows = document.querySelectorAll('tr[data-lat][data-lng]');
    rows.forEach(row => {
        row.addEventListener('click', () => {
            const lat = parseFloat(row.getAttribute('data-lat'));
            const lng = parseFloat(row.getAttribute('data-lng'));
            focusGlobe(lat, lng);
        });
    });
}

function focusGlobe(lat, lng) {
    globe.pointOfView({ lat, lng, altitude: 1.5 }, 1000);
}

function updateGlobeMarkers() {
    const markers = Array.from(document.querySelectorAll('tr[data-lat][data-lng]')).map(row => ({
        lat: parseFloat(row.getAttribute('data-lat')),
        lng: parseFloat(row.getAttribute('data-lng')),
        size: 0.1,
        color: 'red'
    }));
    
    globe.pointsData(markers);
}

// Initialize the app
initGlobe();