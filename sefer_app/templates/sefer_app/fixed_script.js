$(document).ready(function() {
    // This is a replacement for the end of the script
    // The issue is that there are nested document.ready functions
    // Let's fix the structure by removing one of them
    
    function drawStraightLine(originLat, originLng, destLat, destLng) {
        console.log("Düz çizgi çiziliyor");
        
        // Düz çizgi oluştur
        var latlngs = [
            [originLat, originLng],
            [destLat, destLng]
        ];
        
        routeLine = L.polyline(latlngs, {color: '#f6c23e', weight: 4, dashArray: '5, 10'}).addTo(map);
        
        // Harita görünümünü çizgiye sığdır
        map.fitBounds(routeLine.getBounds(), {padding: [30, 30]});
        
        // Yaklaşık mesafeyi hesapla (düz çizgi)
        var distance = calculateDistance(originLat, originLng, destLat, destLng);
        var duration = distance / 70; // Ortalama 70 km/saat hız varsayımı
        var days = duration / 9.00; // 9 saatlik sürüş günü varsayımı (yuvarlanmadan)
        
        $('#total-distance').text(Math.round(distance));
        $('#total-duration').text(duration.toFixed(2));
        $('#total-days').text(days.toFixed(1)); // Ondalık gösterim (1 basamak)
        $('#route-info').show();
        
        // Mesafe alanını güncelle
        $('#mesafe').val(Math.round(distance));
        updateKilometerValues();
        
        // Varış tarihini hesapla
        calculateArrivalDate(days);
    }
});

// The correct ending should be just one closing brace and parenthesis
// }); 