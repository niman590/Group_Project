function formatLKR(value) {
    return new Intl.NumberFormat("en-LK", {
        style: "currency",
        currency: "LKR",
        maximumFractionDigits: 2
    }).format(value);
}

function getLandValuationPayload() {
    return {
        land_size: parseFloat(document.getElementById("land_size").value),
        access_road_size: parseInt(document.getElementById("access_road_size").value),
        location: document.getElementById("location").value,
        distance_to_city: parseFloat(document.getElementById("distance_to_city").value),
        zone_type: document.getElementById("zone_type").value,
        electricity: parseInt(document.getElementById("electricity").value),
        water: parseInt(document.getElementById("water").value),
        flood_risk: parseInt(document.getElementById("flood_risk").value)
    };
}

function validatePayload(payload) {
    if (
        isNaN(payload.land_size) ||
        isNaN(payload.access_road_size) ||
        isNaN(payload.distance_to_city)
    ) {
        alert("Please fill all numeric fields correctly.");
        return false;
    }

    if (
        payload.land_size < 0 ||
        payload.access_road_size < 0 ||
        payload.distance_to_city < 0
    ) {
        alert("Values cannot be negative.");
        return false;
    }

    return true;
}

async function predictLandValue() {
    const payload = getLandValuationPayload();

    if (!validatePayload(payload)) {
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

        if (!response.ok) {
            alert(result.error || "Something went wrong while predicting land value.");
            return;
        }

        if (result.error) {
            alert(result.error);
            return;
        }

        document.getElementById("current_value").innerText = formatLKR(result.current_value);
        document.getElementById("predicted_1_year").innerText = formatLKR(result.predicted_1_year);
        document.getElementById("predicted_5_year").innerText = formatLKR(result.predicted_5_year);

        document.getElementById("download_pdf_btn").disabled = false;

    } catch (error) {
        alert("Something went wrong while predicting land value.");
        console.error(error);
    }
}

async function downloadLandValuationPDF() {
    const payload = getLandValuationPayload();

    if (!validatePayload(payload)) {
        return;
    }

    try {
        const response = await fetch("/download-land-valuation-pdf", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || "Failed to generate PDF.");
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = "land_valuation_report.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();

        window.URL.revokeObjectURL(url);

    } catch (error) {
        alert(error.message || "Something went wrong while downloading the PDF.");
        console.error(error);
    }
}