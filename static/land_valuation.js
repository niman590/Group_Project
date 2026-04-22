function formatLKR(value) {
    return new Intl.NumberFormat("en-LK", {
        style: "currency",
        currency: "LKR",
        maximumFractionDigits: 2
    }).format(value);
}

<<<<<<< HEAD
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

    field.addEventListener("keydown", function (event) {
        preventInvalidDecimalKey(event);
    });

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
            if (this.value !== "") {
                setFieldError(fieldId, false);
                clearValuationMessage();
            }
        }, 0);
    });
}

function getLandValuationPayload() {
    return {
        land_size: parseFloat(document.getElementById("land_size").value),
        access_road_size: parseFloat(document.getElementById("access_road_size").value),
=======
function getLandValuationPayload() {
    return {
        land_size: parseFloat(document.getElementById("land_size").value),
        access_road_size: parseInt(document.getElementById("access_road_size").value),
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
        location: document.getElementById("location").value,
        distance_to_city: parseFloat(document.getElementById("distance_to_city").value),
        zone_type: document.getElementById("zone_type").value,
        electricity: parseInt(document.getElementById("electricity").value),
        water: parseInt(document.getElementById("water").value),
        flood_risk: parseInt(document.getElementById("flood_risk").value)
    };
}

<<<<<<< HEAD
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
        "location",
        "distance_to_city",
        "zone_type",
        "electricity",
        "water",
        "flood_risk"
    ].forEach((fieldId) => setFieldError(fieldId, false));
}

function validatePayload(payload) {
    clearAllFieldErrors();

    if (isNaN(payload.land_size)) {
        setFieldError("land_size", true);
    }

    if (isNaN(payload.access_road_size)) {
        setFieldError("access_road_size", true);
    }

    if (isNaN(payload.distance_to_city)) {
        setFieldError("distance_to_city", true);
    }

=======
function validatePayload(payload) {
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    if (
        isNaN(payload.land_size) ||
        isNaN(payload.access_road_size) ||
        isNaN(payload.distance_to_city)
    ) {
<<<<<<< HEAD
        showValuationMessage("Please fill all numeric fields correctly.", "error");
        return false;
    }

    if (payload.land_size < 0) {
        setFieldError("land_size", true);
    }

    if (payload.access_road_size < 0) {
        setFieldError("access_road_size", true);
    }

    if (payload.distance_to_city < 0) {
        setFieldError("distance_to_city", true);
    }

=======
        alert("Please fill all numeric fields correctly.");
        return false;
    }

>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    if (
        payload.land_size < 0 ||
        payload.access_road_size < 0 ||
        payload.distance_to_city < 0
    ) {
<<<<<<< HEAD
        showValuationMessage("Values cannot be negative.", "error");
        return false;
    }

    clearValuationMessage();
    return true;
}

function updateResultSummary(payload) {
    const summaryLocation = document.getElementById("summary_location");
    const summaryZone = document.getElementById("summary_zone");
    const summarySize = document.getElementById("summary_size");

    if (summaryLocation) {
        summaryLocation.textContent = payload.location || "—";
    }

    if (summaryZone) {
        summaryZone.textContent = payload.zone_type || "—";
    }

    if (summarySize) {
        summarySize.textContent = Number.isNaN(payload.land_size) ? "—" : `${payload.land_size} perches`;
    }
}

function setButtonLoading(buttonId, loadingText) {
    const button = document.getElementById(buttonId);
    if (!button) return;

    button.classList.add("loading");
    const textSpan = button.querySelector(".btn-text");
    if (textSpan) {
        textSpan.dataset.originalText = textSpan.textContent;
        textSpan.textContent = loadingText;
    }
}

function clearButtonLoading(buttonId) {
    const button = document.getElementById(buttonId);
    if (!button) return;

    button.classList.remove("loading");
    const textSpan = button.querySelector(".btn-text");
    if (textSpan && textSpan.dataset.originalText) {
        textSpan.textContent = textSpan.dataset.originalText;
    }
}

=======
        alert("Values cannot be negative.");
        return false;
    }

    return true;
}

>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
async function predictLandValue() {
    const payload = getLandValuationPayload();

    if (!validatePayload(payload)) {
        return;
    }

    try {
<<<<<<< HEAD
        setButtonLoading("predict_btn", "Estimating...");
=======
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
        const response = await fetch("/predict-land-value", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (!response.ok) {
<<<<<<< HEAD
            showValuationMessage(result.error || "Something went wrong while predicting land value.", "error");
=======
            alert(result.error || "Something went wrong while predicting land value.");
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
            return;
        }

        if (result.error) {
<<<<<<< HEAD
            showValuationMessage(result.error, "error");
=======
            alert(result.error);
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
            return;
        }

        document.getElementById("current_value").innerText = formatLKR(result.current_value);
        document.getElementById("predicted_1_year").innerText = formatLKR(result.predicted_1_year);
        document.getElementById("predicted_5_year").innerText = formatLKR(result.predicted_5_year);

<<<<<<< HEAD
        updateResultSummary(payload);
        document.getElementById("download_pdf_btn").disabled = false;
        showValuationMessage("Land valuation estimated successfully.", "success");

    } catch (error) {
        showValuationMessage("Something went wrong while predicting land value.", "error");
        console.error(error);
    } finally {
        clearButtonLoading("predict_btn");
=======
        document.getElementById("download_pdf_btn").disabled = false;

    } catch (error) {
        alert("Something went wrong while predicting land value.");
        console.error(error);
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    }
}

async function downloadLandValuationPDF() {
    const payload = getLandValuationPayload();

    if (!validatePayload(payload)) {
        return;
    }

    try {
<<<<<<< HEAD
        setButtonLoading("download_pdf_btn", "Preparing PDF...");
=======
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
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
<<<<<<< HEAD
        showValuationMessage("PDF report downloaded successfully.", "success");

    } catch (error) {
        showValuationMessage(error.message || "Something went wrong while downloading the PDF.", "error");
        console.error(error);
    } finally {
        clearButtonLoading("download_pdf_btn");
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const revealItems = document.querySelectorAll(".reveal-up");
    const numericFields = ["land_size", "access_road_size", "distance_to_city"];

    function revealOnScroll() {
        revealItems.forEach((item) => {
            const rect = item.getBoundingClientRect();
            if (rect.top < window.innerHeight - 70) {
                item.classList.add("revealed");
            }
        });
    }

    numericFields.forEach((fieldId) => {
        attachPositiveDecimalValidation(fieldId);
    });

    const selects = ["location", "zone_type", "electricity", "water", "flood_risk"];
    selects.forEach((fieldId) => {
        const field = document.getElementById(fieldId);
        if (!field) return;

        field.addEventListener("change", function () {
            updateResultSummary(getLandValuationPayload());
        });
    });

    document.addEventListener("keydown", function (event) {
        const landSizeInput = document.getElementById("land_size");
        const activeTag = document.activeElement ? document.activeElement.tagName : "";

        if (event.key === "/" && landSizeInput && activeTag !== "INPUT" && activeTag !== "TEXTAREA" && activeTag !== "SELECT") {
            event.preventDefault();
            landSizeInput.focus();
        }
    });

    updateResultSummary(getLandValuationPayload());
    window.addEventListener("scroll", revealOnScroll);
    revealOnScroll();
});
=======

    } catch (error) {
        alert(error.message || "Something went wrong while downloading the PDF.");
        console.error(error);
    }
}
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
