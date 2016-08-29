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


    function onEachFeature(feature, layer) {
        if (feature.properties) {
            var popUpContent = 'name : ' + feature.properties.name + '<br>'
                + 'voltage : ' + feature.properties.voltage + '<br>'
                + 'lon : ' + feature.properties.lon + '<br>'
                + 'lat : ' + feature.properties.lat + '<br>'
                + 'type : ' + feature.properties.power_type + '<br>'

            layer.bindPopup(popUpContent);
        }
    }

    $.getJSON(map_div.data('lines-url'), function (data) {
        L.geoJson(data, {
            onEachFeature: onEachFeature,
            style: function (feature) {
                switch (feature.properties.voltage) {
                    case '400000':
                        return {color: "#990033"}
                    case '380000':
                        return {color: "#333300"}
                    case '275000':
                        return {color: "#000066"}
                    case '225000':
                        return {color: "#ff3399"}
                    case '220000':
                        return {color: "#660066"}
                }
            }
        }).addTo(trans_map)
    })

    $.getJSON(map_div.data('stations-url'), function (data) {
        L.geoJson(data, {
            onEachFeature: onEachFeature,
            style: function (feature) {
                switch (feature.properties.power_type) {
                    case 'substation':
                        return {color: "#e60000"}
                    case 'generator':
                        return {color: "#ff0000"}
                }
            }
        }).addTo(trans_map)
    })

})

