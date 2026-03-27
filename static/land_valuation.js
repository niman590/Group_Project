function formatLKR(value) {
    return new Intl.NumberFormat("en-LK", {
        style: "currency",
        currency: "LKR",
        maximumFractionDigits: 2
    }).format(value);
}

async function predictLandValue() {
    const payload = {
        land_size: parseFloat(document.getElementById("land_size").value),
        access_road_size: parseInt(document.getElementById("access_road_size").value),
        location: document.getElementById("location").value,
        distance_to_city: parseFloat(document.getElementById("distance_to_city").value),
        zone_type: document.getElementById("zone_type").value,
        electricity: parseInt(document.getElementById("electricity").value),
        water: parseInt(document.getElementById("water").value),
        flood_risk: parseInt(document.getElementById("flood_risk").value)
    };

    if (
        isNaN(payload.land_size) ||
        isNaN(payload.access_road_size) ||
        isNaN(payload.distance_to_city)
    ) {
        alert("Please fill all numeric fields correctly.");
        return;
    }

    try {
        const response = await fetch("/predict-land-value", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.error) {
            alert(result.error);
            return;
        }

        document.getElementById("current_value").innerText = formatLKR(result.current_value);
        document.getElementById("predicted_1_year").innerText = formatLKR(result.predicted_1_year);
        document.getElementById("predicted_5_year").innerText = formatLKR(result.predicted_5_year);

    } catch (error) {
        alert("Something went wrong while predicting land value.");
        console.error(error);
    }
}