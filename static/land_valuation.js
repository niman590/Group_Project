let valuationMap = null;
let propertyMarker = null;
let selectedLatitude = null;
let selectedLongitude = null;
let lastValuationPayload = null;
let lastValuationResult = null;

function formatLKR(value) {
    const numberValue = Number(value);

    if (Number.isNaN(numberValue)) {
        return "--";
    }

    return new Intl.NumberFormat("en-LK", {
        style: "currency",
        currency: "LKR",
        maximumFractionDigits: 2
    }).format(numberValue);
}

function sanitizePositiveDecimalInput(value) {
    let cleaned = String(value || "");
    cleaned = cleaned.replace(/[^0-9.]/g, "");

    const firstDotIndex = cleaned.indexOf(".");
    if (firstDotIndex !== -1) {
        cleaned =
            cleaned.substring(0, firstDotIndex + 1) +
            cleaned.substring(firstDotIndex + 1).replace(/\./g, "");
    }

    return cleaned;
}

function preventInvalidDecimalKey(event) {
    const allowedControlKeys = [
        "Backspace",
        "Delete",
        "Tab",
        "Escape",
        "Enter",
        "ArrowLeft",
        "ArrowRight",
        "ArrowUp",
        "ArrowDown",
        "Home",
        "End"
    ];

    if (allowedControlKeys.includes(event.key) || event.ctrlKey || event.metaKey) {
        return;
    }

    if (event.key === "-") {
        event.preventDefault();
        return;
    }

    if (event.key === ".") {
        if (event.target.value.includes(".")) {
            event.preventDefault();
        }
        return;
    }

    if (!/[0-9]/.test(event.key)) {
        event.preventDefault();
    }
}

function attachPositiveDecimalValidation(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    field.addEventListener("keydown", preventInvalidDecimalKey);

    field.addEventListener("input", function () {
        const cleanedValue = sanitizePositiveDecimalInput(this.value);

        if (this.value !== cleanedValue) {
            this.value = cleanedValue;
        }

        if (this.value !== "") {
            setFieldError(fieldId, false);
            clearValuationMessage();
        }
    });

    field.addEventListener("paste", function () {
        setTimeout(() => {
            this.value = sanitizePositiveDecimalInput(this.value);
        }, 0);
    });
}

function showValuationMessage(message, type) {
    const messageBox = document.getElementById("valuation_message");
    if (!messageBox) return;

    messageBox.textContent = message;
    messageBox.className = `valuation-message ${type}`;
    messageBox.style.display = "block";
}

function clearValuationMessage() {
    const messageBox = document.getElementById("valuation_message");
    if (!messageBox) return;

    messageBox.textContent = "";
    messageBox.className = "valuation-message";
    messageBox.style.display = "none";
}

function setFieldError(fieldId, hasError) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    const wrap = field.closest(".input-wrap");

    field.classList.toggle("input-error", hasError);

    if (wrap) {
        wrap.classList.toggle("has-error", hasError);
    }
}

function clearAllFieldErrors() {
    [
        "land_size",
        "access_road_size",
        "zone_type",
        "electricity",
        "water",
        "flood_risk"
    ].forEach((fieldId) => setFieldError(fieldId, false));
}

function setButtonLoading(buttonId, loadingText) {
    const button = document.getElementById(buttonId);
    if (!button) return;

    button.classList.add("loading");
    button.disabled = true;

    const textSpan = button.querySelector(".btn-text");
    if (textSpan) {
        textSpan.dataset.originalText = textSpan.innerHTML;
        textSpan.innerHTML = loadingText;
    }
}

function clearButtonLoading(buttonId) {
    const button = document.getElementById(buttonId);
    if (!button) return;

    button.classList.remove("loading");

    if (buttonId === "download_pdf_btn" && !lastValuationResult) {
        button.disabled = true;
    } else {
        button.disabled = false;
    }

    const textSpan = button.querySelector(".btn-text");
    if (textSpan && textSpan.dataset.originalText) {
        textSpan.innerHTML = textSpan.dataset.originalText;
    }
}

function initValuationMap() {
    const mapElement = document.getElementById("valuation_map");
    if (!mapElement) return;

    valuationMap = L.map("valuation_map").setView([6.9271, 79.8612], 11);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(valuationMap);

    valuationMap.on("click", function (event) {
        setSelectedLocation(
            event.latlng.lat,
            event.latlng.lng,
            "Selected property location"
        );
    });
}

function setSelectedLocation(latitude, longitude, popupText = "Selected property location") {
    selectedLatitude = Number(latitude);
    selectedLongitude = Number(longitude);

    document.getElementById("selected_latitude").textContent = selectedLatitude.toFixed(6);
    document.getElementById("selected_longitude").textContent = selectedLongitude.toFixed(6);

    if (propertyMarker) {
        propertyMarker.setLatLng([selectedLatitude, selectedLongitude]);
    } else {
        propertyMarker = L.marker([selectedLatitude, selectedLongitude]).addTo(valuationMap);
    }

    propertyMarker.bindPopup(popupText).openPopup();

    lastValuationPayload = null;
    lastValuationResult = null;

    const pdfButton = document.getElementById("download_pdf_btn");
    if (pdfButton) {
        pdfButton.disabled = true;
    }

    clearValuationMessage();
    resetResultValues();
    getGisPreview();
}

async function searchMapLocation() {
    const searchInput = document.getElementById("map_search");
    const query = searchInput.value.trim();

    if (!query) {
        showValuationMessage("Please enter a location to search.", "error");
        return;
    }

    const searchButton = document.getElementById("map_search_btn");

    try {
        if (searchButton) {
            searchButton.disabled = true;
            searchButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Searching';
        }

        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`;

        const response = await fetch(url, {
            headers: {
                "Accept": "application/json"
            }
        });

        const results = await response.json();

        if (!results || results.length === 0) {
            showValuationMessage("Location not found. Try a more specific location.", "error");
            return;
        }

        const latitude = parseFloat(results[0].lat);
        const longitude = parseFloat(results[0].lon);

        valuationMap.setView([latitude, longitude], 16);
        setSelectedLocation(latitude, longitude, "Searched property location");

    } catch (error) {
        console.error(error);
        showValuationMessage("Unable to search location right now.", "error");
    } finally {
        if (searchButton) {
            searchButton.disabled = false;
            searchButton.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Search';
        }
    }
}

function getCurrentBrowserPosition() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error("Current location is not supported by this browser."));
            return;
        }

        navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 12000,
            maximumAge: 0
        });
    });
}

async function useCurrentLocation() {
    const currentLocationButton = document.getElementById("current_location_btn");

    try {
        if (!valuationMap) {
            showValuationMessage("Map is not ready yet. Please refresh the page.", "error");
            return;
        }

        if (currentLocationButton) {
            currentLocationButton.disabled = true;
            currentLocationButton.innerHTML =
                '<i class="fa-solid fa-spinner fa-spin"></i> Locating';
        }

        showValuationMessage("Finding your current location...", "warning");

        const position = await getCurrentBrowserPosition();

        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        valuationMap.setView([latitude, longitude], 16);
        setSelectedLocation(latitude, longitude, "Your current location");

    } catch (error) {
        console.error(error);

        let message = "Unable to get your current location.";

        if (error.code === 1) {
            message = "Location permission denied. Please allow location access in your browser.";
        } else if (error.code === 2) {
            message = "Your current location is unavailable right now.";
        } else if (error.code === 3) {
            message = "Getting your current location took too long. Please try again.";
        } else if (error.message) {
            message = error.message;
        }

        showValuationMessage(message, "error");

    } finally {
        if (currentLocationButton) {
            currentLocationButton.disabled = false;
            currentLocationButton.innerHTML =
                '<i class="fa-solid fa-location-crosshairs"></i> Current Location';
        }
    }
}

async function getGisPreview() {
    if (selectedLatitude === null || selectedLongitude === null) {
        return;
    }

    try {
        const response = await fetch("/api/valuation/gis-check", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                latitude: selectedLatitude,
                longitude: selectedLongitude
            })
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            document.getElementById("nearest_city_display").textContent =
                result.nearest_supported_city || "Unsupported";

            document.getElementById("distance_display").textContent =
                result.distance_to_city_km !== undefined && result.distance_to_city_km !== null
                    ? `${result.distance_to_city_km} km`
                    : "—";

            showValuationMessage(
                result.error || "This selected location is outside the supported valuation area.",
                "error"
            );

            return;
        }

        document.getElementById("nearest_city_display").textContent =
            result.nearest_supported_city || "—";

        document.getElementById("distance_display").textContent =
            result.distance_to_city_km !== undefined
                ? `${result.distance_to_city_km} km`
                : "—";

        clearValuationMessage();

    } catch (error) {
        console.error(error);
        showValuationMessage("Unable to check GIS location right now.", "error");
    }
}

function getLandValuationPayload() {
    return {
        land_size: parseFloat(document.getElementById("land_size").value),
        access_road_size: parseFloat(document.getElementById("access_road_size").value),
        latitude: selectedLatitude,
        longitude: selectedLongitude,
        zone_type: document.getElementById("zone_type").value,
        electricity: parseInt(document.getElementById("electricity").value),
        water: parseInt(document.getElementById("water").value),
        flood_risk: parseInt(document.getElementById("flood_risk").value)
    };
}

function validatePayload(payload) {
    clearAllFieldErrors();

    let isValid = true;

    if (payload.latitude === null || payload.longitude === null) {
        showValuationMessage("Please select the property location on the map.", "error");
        return false;
    }

    if (Number.isNaN(payload.land_size)) {
        setFieldError("land_size", true);
        isValid = false;
    }

    if (Number.isNaN(payload.access_road_size)) {
        setFieldError("access_road_size", true);
        isValid = false;
    }

    if (!payload.zone_type) {
        setFieldError("zone_type", true);
        isValid = false;
    }

    if (!isValid) {
        showValuationMessage("Please fill all required fields correctly.", "error");
        return false;
    }

    if (payload.land_size < 6) {
        setFieldError("land_size", true);
        showValuationMessage("Land size must be 6 perches or more.", "error");
        return false;
    }

    if (payload.access_road_size <= 0) {
        setFieldError("access_road_size", true);
        showValuationMessage("Access road size must be greater than 0 feet.", "error");
        return false;
    }

    clearValuationMessage();
    return true;
}

function resetResultValues() {
    const fields = [
        "current_value",
        "predicted_1_year",
        "predicted_5_year",
        "price_per_perch",
        "summary_location",
        "summary_distance",
        "summary_zone",
        "summary_size",
        "summary_address"
    ];

    fields.forEach((id) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = id.includes("summary") ? "—" : "--";
        }
    });
}

function updateResultSummaryFromResponse(responseData, payload) {
    const gis = responseData.gis_result || {};
    const inputLocation = responseData.input_location || {};

    document.getElementById("summary_location").textContent =
        gis.nearest_supported_city || "—";

    document.getElementById("summary_distance").textContent =
        gis.distance_to_city_km !== undefined
            ? `${gis.distance_to_city_km} km`
            : "—";

    document.getElementById("summary_zone").textContent =
        payload.zone_type || "—";

    document.getElementById("summary_size").textContent =
        `${payload.land_size} perches`;

    document.getElementById("summary_address").textContent =
        inputLocation.address || "Address unavailable";

    document.getElementById("nearest_city_display").textContent =
        gis.nearest_supported_city || "—";

    document.getElementById("distance_display").textContent =
        gis.distance_to_city_km !== undefined
            ? `${gis.distance_to_city_km} km`
            : "—";
}

async function predictLandValue() {
    const payload = getLandValuationPayload();

    if (!validatePayload(payload)) {
        return;
    }

    try {
        setButtonLoading("predict_btn", "Estimating...");

        const response = await fetch("/api/valuation/estimate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            showValuationMessage(
                result.error || "Something went wrong while predicting land value.",
                "error"
            );
            return;
        }

        const valuation = result.valuation;

        document.getElementById("current_value").textContent =
            formatLKR(valuation.current_value);

        document.getElementById("predicted_1_year").textContent =
            formatLKR(valuation.predicted_1_year);

        document.getElementById("predicted_5_year").textContent =
            formatLKR(valuation.predicted_5_year);

        document.getElementById("price_per_perch").textContent =
            formatLKR(valuation.estimated_price_per_perch);

        updateResultSummaryFromResponse(result, payload);

        lastValuationPayload = payload;
        lastValuationResult = result;

        const pdfButton = document.getElementById("download_pdf_btn");
        if (pdfButton) {
            pdfButton.disabled = false;
        }

        showValuationMessage("Land valuation estimated successfully.", "success");

    } catch (error) {
        console.error(error);
        showValuationMessage(
            "Something went wrong while predicting land value.",
            "error"
        );
    } finally {
        clearButtonLoading("predict_btn");
    }
}

async function downloadLandValuationPDF() {
    const payload = getLandValuationPayload();

    if (!validatePayload(payload)) {
        return;
    }

    try {
        setButtonLoading("download_pdf_btn", "Preparing PDF...");

        const response = await fetch("/download-land-valuation-pdf", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            let errorMessage = "Failed to generate PDF.";

            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // Ignore JSON parsing error.
            }

            throw new Error(errorMessage);
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

        showValuationMessage("PDF report downloaded successfully.", "success");

    } catch (error) {
        console.error(error);
        showValuationMessage(
            error.message || "Something went wrong while downloading the PDF.",
            "error"
        );
    } finally {
        clearButtonLoading("download_pdf_btn");

        const pdfButton = document.getElementById("download_pdf_btn");
        if (pdfButton && !lastValuationResult) {
            pdfButton.disabled = true;
        }
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const revealItems = document.querySelectorAll(".reveal-up");

    function revealOnScroll() {
        revealItems.forEach((item) => {
            const rect = item.getBoundingClientRect();

            if (rect.top < window.innerHeight - 70) {
                item.classList.add("revealed");
            }
        });
    }

    attachPositiveDecimalValidation("land_size");
    attachPositiveDecimalValidation("access_road_size");

    const mapSearchInput = document.getElementById("map_search");
    if (mapSearchInput) {
        mapSearchInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                searchMapLocation();
            }
        });
    }

    const currentLocationButton = document.getElementById("current_location_btn");
    if (currentLocationButton) {
        currentLocationButton.addEventListener("click", useCurrentLocation);
    }

    initValuationMap();

    window.addEventListener("scroll", revealOnScroll);
    revealOnScroll();
});