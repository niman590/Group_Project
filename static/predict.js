document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("landPredictionForm");

    if (form) {
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            predictLandValue();
        });
    }
});

async function predictLandValue() {
    const message = document.getElementById("message");
    const currentValue = document.getElementById("current_value");
    const predicted1Year = document.getElementById("predicted_1_year");
    const predicted5Year = document.getElementById("predicted_5_year");
    const predictBtn = document.getElementById("predictBtn");

    message.innerText = "";
    message.className = "message";

    currentValue.innerText = "-";
    predicted1Year.innerText = "-";
    predicted5Year.innerText = "-";

    const landSize = parseFloat(document.getElementById("land_size").value);

    if (isNaN(landSize)) {
        message.innerText = "Please enter land size.";
        message.className = "message error";
        return;
    }

    if (landSize < 6) {
        message.innerText = "Land size must be 6 perches or more.";
        message.className = "message error";
        return;
    }

    const payload = {
        publication_year: parseInt(document.getElementById("publication_year").value),
        land_size: landSize,
        access_road_size: parseInt(document.getElementById("access_road_size").value),
        location: document.getElementById("location").value,
        distance_to_city: parseFloat(document.getElementById("distance_to_city").value),
        zone_type: document.getElementById("zone_type").value,
        electricity: parseInt(document.getElementById("electricity").value),
        water: parseInt(document.getElementById("water").value),
        flood_risk: parseInt(document.getElementById("flood_risk").value)
    };

    try {
        if (predictBtn) {
            predictBtn.classList.add("loading");
            predictBtn.textContent = "Predicting...";
        }

        const response = await fetch("/predict-land-value", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.error) {
            message.innerText = result.error;
            message.className = "message error";
            return;
        }

        message.innerText = "Land valuation estimated successfully.";
        message.className = "message success";

        currentValue.innerText = result.current_value;
        predicted1Year.innerText = result.predicted_1_year;
        predicted5Year.innerText = result.predicted_5_year;
    } catch (error) {
        message.innerText = "Something went wrong while predicting land value.";
        message.className = "message error";
    } finally {
        if (predictBtn) {
            predictBtn.classList.remove("loading");
            predictBtn.textContent = "Predict";
        }
    }
}