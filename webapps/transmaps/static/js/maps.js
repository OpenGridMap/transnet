$(document).ready(function () {
    var map_div = $('#trans-map')
    var trans_map = L.map('trans-map').setView([51, 6], 6)

    L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/streets-v9/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1IjoiZXBlemhtYW4iLCJhIjoiY2lzMzAybzhrMDAwODJ5cDd3Y3J4a2IzMSJ9.x4EEm9wcrm65fT9_2xQctA', {
        maxZoom: 25,
        attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
        '<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
        'Imagery © <a href="http://mapbox.com">Mapbox</a>',
        id: 'mapbox.streets'
    }).addTo(trans_map)

    var layer1 = L.geoJson()
    var layer2 = L.geoJson()

    trans_map.addLayer(layer1)
    trans_map.addLayer(layer2)

    var popup = L.popup();

    layer1.on('click', onMapClick);

    function onMapClick(e) {
        console.log(e)
        popup
            .setLatLng(e.latlng)
            .setContent("You clicked the map at " + e.latlng.toString())
            .openOn(trans_map);
    }

    $.getJSON(map_div.data('lines-url'), function (data) {
        layer1.addData(data)
        layer1.setStyle(function (feature) {
            switch (feature.properties.voltage) {
                case '400000':
                    return {color: "#ff8533"}
                case '380000':
                    return {color: "#ffd633"}
                case '275000':
                    return {color: "#3399ff"}
                case '22000':
                    return {color: "#009933"}
            }
        })

    })

    $.getJSON(map_div.data('stations-url'), function (data) {
        layer2.addData(data)
        layer2.setStyle(function (feature) {
            switch (feature.properties.power_type) {
                case 'substation':
                    return {color: "#e60000"}
                case 'generator':
                    return {color: "#ff0000"}
            }
        })
    })
})

