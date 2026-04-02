const steps = document.querySelectorAll(".form-step");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");
const progressHint = document.getElementById("progressHint");
const stepPill = document.getElementById("stepPill");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const submitBtn = document.getElementById("submitBtn");
const saveDraftBtn = document.getElementById("saveDraftBtn");
const form = document.getElementById("planApprovalForm");
const responseBox = document.getElementById("responseBox");
const reviewSummary = document.getElementById("reviewSummary");
const generateReviewBtn = document.getElementById("generateReviewBtn");
const clearDraftBtn = document.getElementById("clearDraftBtn");
const autosaveStatus = document.getElementById("autosaveStatus");
const ownerStepNote = document.getElementById("ownerStepNote");
const filePreviewBox = document.getElementById("filePreviewBox");

const mapModal = document.getElementById("mapModal");
const mapModalBackdrop = document.getElementById("mapModalBackdrop");
const mapCloseBtn = document.getElementById("mapCloseBtn");
const mapSearchInput = document.getElementById("mapSearchInput");
const mapSearchBtn = document.getElementById("mapSearchBtn");
const mapStatusText = document.getElementById("mapStatusText");
const mapSelectedAddress = document.getElementById("mapSelectedAddress");
const confirmMapSelectionBtn = document.getElementById("confirmMapSelectionBtn");
const useCurrentLocationBtn = document.getElementById("useCurrentLocationBtn");

let currentStep = 0;
let mapInstance = null;
let mapMarker = null;
let activeAddressFieldId = null;
let currentPickedLocation = null;

const stepHints = [
    "Start with the development summary.",
    "Add the main applicant details.",
    "Enter technical service providers.",
    "Provide owner details if different from the applicant.",
    "Record all relevant clearances.",
    "Describe site usage and access.",
    "Add building distances and height.",
    "Provide development metrics.",
    "Enter housing and parking details.",
    "Select submitted plans and compliance items.",
    "Upload the key supporting files.",
    "Review everything before final submission."
];

function showMessage(type, text) {
    responseBox.className = `response-box ${type}`;
    responseBox.style.display = "block";
    responseBox.textContent = text;
}

function showStep(stepIndex) {
    steps.forEach((step, index) => {
        step.classList.toggle("active", index === stepIndex);
    });

    const percent = ((stepIndex + 1) / steps.length) * 100;
    progressFill.style.width = `${percent}%`;
    progressText.textContent = `Step ${stepIndex + 1} of ${steps.length}`;
    stepPill.textContent = `Step ${stepIndex + 1}`;
    progressHint.textContent = stepHints[stepIndex] || "";

    prevBtn.style.visibility = stepIndex === 0 ? "hidden" : "visible";
    nextBtn.style.display = stepIndex === steps.length - 1 ? "none" : "inline-block";
    submitBtn.style.display = stepIndex === steps.length - 1 ? "inline-block" : "none";

    window.scrollTo({ top: 0, behavior: "smooth" });
}

function setFieldError(field, message) {
    field.classList.add("field-invalid");
    const errorEl = field.parentElement.querySelector(".error-text");
    if (errorEl) errorEl.textContent = message;
}

function clearFieldError(field) {
    field.classList.remove("field-invalid");
    const errorEl = field.parentElement.querySelector(".error-text");
    if (errorEl) errorEl.textContent = "";
}

function validateStep(stepIndex) {
    const activeStep = steps[stepIndex];
    const requiredFields = activeStep.querySelectorAll("[required]");
    let isValid = true;

    requiredFields.forEach((field) => {
        clearFieldError(field);
        if (!field.value.trim()) {
            setFieldError(field, "This field is required.");
            if (isValid) field.focus();
            isValid = false;
        }
    });

    return isValid;
}

function toggleOwnerStep() {
    const ownsLand = document.querySelector('input[name="applicant_owns_land"]:checked')?.value;
    if (!ownerStepNote) return;

    ownerStepNote.textContent = ownsLand === "Yes"
        ? "This section is optional because the applicant currently owns the land."
        : "Please complete this section because the applicant is not the land owner.";
}

function getStepData(stepNumber) {
    if (stepNumber === 1) {
        return {
            development_work_type: document.querySelector('input[name="development_work_type"]:checked')?.value || "",
            previous_plan_no: document.getElementById("previous_plan_no")?.value || "",
            assessment_no: document.getElementById("assessment_no")?.value || "",
            road_name: document.getElementById("road_name")?.value || "",
            postal_code: document.getElementById("postal_code")?.value || "",
            local_authority_name: document.getElementById("local_authority_name")?.value || "",
            gnd_name: document.getElementById("gnd_name")?.value || "",
            land_ownership_type: document.querySelector('input[name="land_ownership_type"]:checked')?.value || "",
            land_ownership_other: document.getElementById("land_ownership_other")?.value || "",
            proposed_use: Array.from(document.querySelectorAll('input[name="proposed_use"]:checked')).map(x => x.value),
            proposed_use_other: document.getElementById("proposed_use_other")?.value || ""
        };
    }

    if (stepNumber === 2) {
        return {
            applicants: [
                {
                    name: document.getElementById("applicant1_name")?.value || "",
                    nic: document.getElementById("applicant1_nic")?.value || "",
                    telephone: document.getElementById("applicant1_tel")?.value || "",
                    email: document.getElementById("applicant1_email")?.value || "",
                    address: document.getElementById("applicant1_address")?.value || ""
                },
                {
                    name: document.getElementById("applicant2_name")?.value || "",
                    nic: document.getElementById("applicant2_nic")?.value || "",
                    telephone: document.getElementById("applicant2_tel")?.value || "",
                    email: document.getElementById("applicant2_email")?.value || "",
                    address: document.getElementById("applicant2_address")?.value || ""
                }
            ].filter(a => a.name || a.nic || a.telephone || a.email || a.address)
        };
    }

    if (stepNumber === 3) {
        return {
            architect_town_planner_name: document.getElementById("architect_town_planner_name")?.value || "",
            draughtsman_name: document.getElementById("draughtsman_name")?.value || "",
            engineer_name: document.getElementById("engineer_name")?.value || "",
            applicant_owns_land: document.querySelector('input[name="applicant_owns_land"]:checked')?.value || "Yes"
        };
    }

    if (stepNumber === 4) {
        return {
            owner_name: document.getElementById("land_owner_name")?.value || "",
            owner_nic: document.getElementById("land_owner_nic")?.value || "",
            owner_tel: document.getElementById("land_owner_tel")?.value || "",
            owner_email: document.getElementById("land_owner_email")?.value || "",
            owner_address: document.getElementById("land_owner_address")?.value || ""
        };
    }

    if (stepNumber === 5) {
        return {
            rate_clearance_ref: document.querySelector('[name="rate_clearance_ref"]')?.value || "",
            rate_clearance_date: document.querySelector('[name="rate_clearance_date"]')?.value || "",
            water_clearance_ref: document.querySelector('[name="water_clearance_ref"]')?.value || "",
            water_clearance_date: document.querySelector('[name="water_clearance_date"]')?.value || "",
            drainage_clearance_ref: document.querySelector('[name="drainage_clearance_ref"]')?.value || "",
            drainage_clearance_date: document.querySelector('[name="drainage_clearance_date"]')?.value || "",
            uda_preliminary_ref: document.querySelector('[name="uda_preliminary_ref"]')?.value || "",
            uda_preliminary_date: document.querySelector('[name="uda_preliminary_date"]')?.value || ""
        };
    }

    if (stepNumber === 6) {
        return {
            existing_use: document.getElementById("existing_use")?.value || "",
            proposed_use_text: document.getElementById("proposed_use_text")?.value || "",
            zoning_category: document.getElementById("zoning_category")?.value || "",
            site_extent: document.getElementById("site_extent")?.value || "",
            site_frontage_width: document.getElementById("site_frontage_width")?.value || "",
            physical_width_of_road: document.getElementById("physical_width_of_road")?.value || ""
        };
    }

    if (stepNumber === 7) {
        return {
            distance_street_boundary: document.getElementById("distance_street_boundary")?.value || "",
            distance_rear_boundary: document.getElementById("distance_rear_boundary")?.value || "",
            distance_left_boundary: document.getElementById("distance_left_boundary")?.value || "",
            distance_right_boundary: document.getElementById("distance_right_boundary")?.value || "",
            no_of_floors: document.getElementById("no_of_floors")?.value || "",
            total_building_height: document.getElementById("total_building_height")?.value || ""
        };
    }

    if (stepNumber === 8) {
        return {
            plot_coverage: document.getElementById("plot_coverage")?.value || "",
            floor_area_ratio: document.getElementById("floor_area_ratio")?.value || "",
            water_usage_liters: document.getElementById("water_usage_liters")?.value || "",
            electricity_usage_kw: document.getElementById("electricity_usage_kw")?.value || "",
            site_development_notes: document.getElementById("site_development_notes")?.value || ""
        };
    }

    if (stepNumber === 9) {
        return {
            existing_units: document.getElementById("existing_units")?.value || "",
            proposed_units: document.getElementById("proposed_units")?.value || "",
            total_units: document.getElementById("total_units")?.value || "",
            parking_car_proposed: document.getElementById("parking_car_proposed")?.value || ""
        };
    }

    if (stepNumber === 10) {
        return {
            submitted_plans: Array.from(document.querySelectorAll('input[name="submitted_plans"]:checked')).map(x => x.value)
        };
    }

    return {};
}

async function saveCurrentStep(stepNumber) {
    const res = await fetch("/save-planning-draft-step", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            step: stepNumber,
            data: getStepData(stepNumber)
        })
    });

    return await res.json();
}

async function saveFilesStep() {
    const formData = new FormData();

    const sitePlan = document.getElementById("site_plan_file");
    const surveyPlan = document.getElementById("survey_plan_file");
    const clearanceDocs = document.getElementById("clearance_docs_file");
    const otherDocs = document.getElementById("other_docs_file");

    if (sitePlan) Array.from(sitePlan.files).forEach(file => formData.append("site_plan_file", file));
    if (surveyPlan) Array.from(surveyPlan.files).forEach(file => formData.append("survey_plan_file", file));
    if (clearanceDocs) Array.from(clearanceDocs.files).forEach(file => formData.append("clearance_docs_file", file));
    if (otherDocs) Array.from(otherDocs.files).forEach(file => formData.append("other_docs_file", file));

    const res = await fetch("/save-planning-draft-files", {
        method: "POST",
        body: formData
    });

    return await res.json();
}

function updateFilePreview() {
    if (!filePreviewBox) return;

    const fileInputs = form.querySelectorAll('input[type="file"]');
    const lines = [];

    fileInputs.forEach((input) => {
        if (!input.files.length) return;
        const label = input.previousElementSibling?.textContent || input.name;
        const names = Array.from(input.files).map(file => file.name);
        lines.push(`${label}: ${names.join(", ")}`);
    });

    filePreviewBox.textContent = lines.length ? lines.join("\n") : "No files selected yet.";
}

function buildReview() {
    const step1 = getStepData(1);
    const step2 = getStepData(2);
    const step3 = getStepData(3);

    reviewSummary.textContent = `
Assessment No.: ${step1.assessment_no || "-"}
Road Name: ${step1.road_name || "-"}
Local Authority: ${step1.local_authority_name || "-"}
Applicant: ${step2.applicants?.[0]?.name || "-"}
Applicant NIC: ${step2.applicants?.[0]?.nic || "-"}
Architect / Planner: ${step3.architect_town_planner_name || "-"}
Engineer: ${step3.engineer_name || "-"}
    `.trim();
}

function updateAddressMeta(fieldId, addressText, lat = null, lon = null) {
    const metaBox = document.getElementById(`${fieldId}_meta`);
    if (!metaBox) return;

    if (!addressText) {
        metaBox.textContent = "No GIS location selected yet.";
        return;
    }

    if (lat && lon) {
        metaBox.textContent = `GIS selected location: ${addressText}\nLatitude: ${Number(lat).toFixed(6)}, Longitude: ${Number(lon).toFixed(6)}`;
    } else {
        metaBox.textContent = `Address loaded: ${addressText}`;
    }
}

function initMapIfNeeded() {
    if (mapInstance) {
        setTimeout(() => mapInstance.invalidateSize(), 150);
        return;
    }

    mapInstance = L.map("gisMap").setView([7.8731, 80.7718], 7);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(mapInstance);

    mapInstance.on("click", async (event) => {
        const { lat, lng } = event.latlng;
        placeMapMarker(lat, lng);
        await fillSelectedLocationFromCoordinates(lat, lng);
    });

    setTimeout(() => mapInstance.invalidateSize(), 150);
}

function placeMapMarker(lat, lon) {
    if (!mapInstance) return;

    if (mapMarker) {
        mapMarker.setLatLng([lat, lon]);
    } else {
        mapMarker = L.marker([lat, lon]).addTo(mapInstance);
    }

    mapInstance.setView([lat, lon], 17);
}

async function searchLocation(query) {
    const res = await fetch(`/gis-search-location?q=${encodeURIComponent(query)}`);
    return await res.json();
}

async function reverseGeocode(lat, lon) {
    const res = await fetch(`/gis-reverse-geocode?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`);
    return await res.json();
}

async function fillSelectedLocationFromCoordinates(lat, lon) {
    mapStatusText.textContent = "Fetching address from selected map point...";

    try {
        const result = await reverseGeocode(lat, lon);

        if (!result.success) {
            mapStatusText.textContent = result.message || "Could not identify the selected location.";
            return;
        }

        currentPickedLocation = {
            address: result.address || "",
            lat: result.lat,
            lon: result.lon
        };

        mapSelectedAddress.textContent = `${currentPickedLocation.address}\nLatitude: ${Number(currentPickedLocation.lat).toFixed(6)}, Longitude: ${Number(currentPickedLocation.lon).toFixed(6)}`;
        mapStatusText.textContent = "Location selected successfully.";
    } catch (error) {
        mapStatusText.textContent = "Reverse geocoding failed.";
    }
}

function openMapPicker(fieldId) {
    activeAddressFieldId = fieldId;
    currentPickedLocation = null;
    mapSelectedAddress.textContent = "No location selected yet.";
    mapStatusText.textContent = "Click on the map to choose a location.";
    mapSearchInput.value = "";

    mapModal.classList.remove("hidden");
    document.body.style.overflow = "hidden";

    initMapIfNeeded();

    const targetField = document.getElementById(fieldId);
    const existingText = targetField?.value?.trim();

    if (existingText) {
        mapStatusText.textContent = "Existing address found. You can search again or click on the map to update it.";
        mapSelectedAddress.textContent = existingText;
    }

    setTimeout(() => {
        if (mapInstance) mapInstance.invalidateSize();
    }, 200);
}

function closeMapPicker() {
    mapModal.classList.add("hidden");
    document.body.style.overflow = "";
}

async function handleMapSearch() {
    const query = mapSearchInput.value.trim();

    if (!query) {
        mapStatusText.textContent = "Please enter a location to search.";
        return;
    }

    mapStatusText.textContent = "Searching location...";

    try {
        const result = await searchLocation(query);

        if (!result.success || !result.results?.length) {
            mapStatusText.textContent = "No matching locations found.";
            return;
        }

        const first = result.results[0];
        const lat = parseFloat(first.lat);
        const lon = parseFloat(first.lon);

        placeMapMarker(lat, lon);
        currentPickedLocation = {
            address: first.display_name || "",
            lat,
            lon
        };

        mapSelectedAddress.textContent = `${currentPickedLocation.address}\nLatitude: ${lat.toFixed(6)}, Longitude: ${lon.toFixed(6)}`;
        mapStatusText.textContent = "Search result selected. You can confirm or click another point on the map.";
    } catch (error) {
        mapStatusText.textContent = "Location search failed.";
    }
}

function applySelectedLocationToField() {
    if (!activeAddressFieldId) return;

    const field = document.getElementById(activeAddressFieldId);
    if (!field) return;

    if (!currentPickedLocation || !currentPickedLocation.address) {
        mapStatusText.textContent = "Please select a location from the map first.";
        return;
    }

    field.value = currentPickedLocation.address;
    updateAddressMeta(
        activeAddressFieldId,
        currentPickedLocation.address,
        currentPickedLocation.lat,
        currentPickedLocation.lon
    );

    closeMapPicker();
}

function useBrowserCurrentLocation() {
    if (!navigator.geolocation) {
        mapStatusText.textContent = "Geolocation is not supported by this browser.";
        return;
    }

    mapStatusText.textContent = "Fetching your current location...";

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            placeMapMarker(lat, lon);
            await fillSelectedLocationFromCoordinates(lat, lon);
        },
        () => {
            mapStatusText.textContent = "Could not access your current location.";
        },
        {
            enableHighAccuracy: true,
            timeout: 10000
        }
    );
}

async function loadDraftFromServer() {
    try {
        const res = await fetch("/get-planning-draft");
        const result = await res.json();

        if (!result.success || !result.draft) return;

        const draft = result.draft;

        const fill = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.value = value || "";
        };

        if (draft.step1) {
            if (draft.step1.development_work_type) {
                const radio = document.querySelector(`input[name="development_work_type"][value="${draft.step1.development_work_type}"]`);
                if (radio) radio.checked = true;
            }

            if (draft.step1.land_ownership_type) {
                const radio = document.querySelector(`input[name="land_ownership_type"][value="${draft.step1.land_ownership_type}"]`);
                if (radio) radio.checked = true;
            }

            fill("previous_plan_no", draft.step1.previous_plan_no);
            fill("assessment_no", draft.step1.assessment_no);
            fill("road_name", draft.step1.road_name);
            fill("postal_code", draft.step1.postal_code);
            fill("local_authority_name", draft.step1.local_authority_name);
            fill("gnd_name", draft.step1.gnd_name);
            fill("land_ownership_other", draft.step1.land_ownership_other);
            fill("proposed_use_other", draft.step1.proposed_use_other);

            if (draft.step1.proposed_use) {
                draft.step1.proposed_use.forEach(value => {
                    const checkbox = document.querySelector(`input[name="proposed_use"][value="${value}"]`);
                    if (checkbox) checkbox.checked = true;
                });
            }
        }

        if (draft.step2 && draft.step2[0]) {
            fill("applicant1_name", draft.step2[0].name);
            fill("applicant1_nic", draft.step2[0].nic);
            fill("applicant1_tel", draft.step2[0].telephone);
            fill("applicant1_email", draft.step2[0].email);
            fill("applicant1_address", draft.step2[0].address);
            updateAddressMeta("applicant1_address", draft.step2[0].address);
        }

        if (draft.step2 && draft.step2[1]) {
            fill("applicant2_name", draft.step2[1].name);
            fill("applicant2_nic", draft.step2[1].nic);
            fill("applicant2_tel", draft.step2[1].telephone);
            fill("applicant2_email", draft.step2[1].email);
            fill("applicant2_address", draft.step2[1].address);
            updateAddressMeta("applicant2_address", draft.step2[1].address);
        }

        if (draft.step3) {
            fill("architect_town_planner_name", draft.step3.architect_town_planner_name);
            fill("draughtsman_name", draft.step3.draughtsman_name);
            fill("engineer_name", draft.step3.engineer_name);

            if (draft.step3.applicant_owns_land) {
                const radio = document.querySelector(`input[name="applicant_owns_land"][value="${draft.step3.applicant_owns_land}"]`);
                if (radio) radio.checked = true;
            }
        }

        if (draft.step4) {
            fill("land_owner_name", draft.step4.owner_name);
            fill("land_owner_nic", draft.step4.owner_nic);
            fill("land_owner_tel", draft.step4.owner_tel);
            fill("land_owner_email", draft.step4.owner_email);
            fill("land_owner_address", draft.step4.owner_address);
            updateAddressMeta("land_owner_address", draft.step4.owner_address);
        }

        if (draft.step5) {
            document.querySelector('[name="rate_clearance_ref"]').value = draft.step5.rate_clearance_ref || "";
            document.querySelector('[name="rate_clearance_date"]').value = draft.step5.rate_clearance_date || "";
            document.querySelector('[name="water_clearance_ref"]').value = draft.step5.water_clearance_ref || "";
            document.querySelector('[name="water_clearance_date"]').value = draft.step5.water_clearance_date || "";
            document.querySelector('[name="drainage_clearance_ref"]').value = draft.step5.drainage_clearance_ref || "";
            document.querySelector('[name="drainage_clearance_date"]').value = draft.step5.drainage_clearance_date || "";
            document.querySelector('[name="uda_preliminary_ref"]').value = draft.step5.uda_preliminary_ref || "";
            document.querySelector('[name="uda_preliminary_date"]').value = draft.step5.uda_preliminary_date || "";
        }

        if (draft.step6) {
            fill("existing_use", draft.step6.existing_use);
            fill("proposed_use_text", draft.step6.proposed_use_text);
            fill("zoning_category", draft.step6.zoning_category);
            fill("site_extent", draft.step6.site_extent);
            fill("site_frontage_width", draft.step6.site_frontage_width);
            fill("physical_width_of_road", draft.step6.physical_width_of_road);
        }

        if (draft.step7) {
            fill("distance_street_boundary", draft.step7.distance_street_boundary);
            fill("distance_rear_boundary", draft.step7.distance_rear_boundary);
            fill("distance_left_boundary", draft.step7.distance_left_boundary);
            fill("distance_right_boundary", draft.step7.distance_right_boundary);
            fill("no_of_floors", draft.step7.no_of_floors);
            fill("total_building_height", draft.step7.total_building_height);
        }

        if (draft.step8) {
            fill("plot_coverage", draft.step8.plot_coverage);
            fill("floor_area_ratio", draft.step8.floor_area_ratio);
            fill("water_usage_liters", draft.step8.water_usage_liters);
            fill("electricity_usage_kw", draft.step8.electricity_usage_kw);
            fill("site_development_notes", draft.step8.site_development_notes);
        }

        if (draft.step9) {
            fill("existing_units", draft.step9.existing_units);
            fill("proposed_units", draft.step9.proposed_units);
            fill("total_units", draft.step9.total_units);
            fill("parking_car_proposed", draft.step9.parking_car_proposed);
        }

        if (draft.step10) {
            draft.step10.forEach(value => {
                const checkbox = document.querySelector(`input[name="submitted_plans"][value="${value}"]`);
                if (checkbox) checkbox.checked = true;
            });
        }

        currentStep = (draft.current_step || 1) - 1;
        toggleOwnerStep();
        showStep(currentStep);
        autosaveStatus.textContent = "Draft restored from server";
    } catch (error) {
        console.error("Draft load failed", error);
    }
}

prevBtn.addEventListener("click", () => {
    if (currentStep > 0) {
        currentStep--;
        showStep(currentStep);
    }
});

nextBtn.addEventListener("click", async () => {
    if (!validateStep(currentStep)) return;

    const stepNumber = currentStep + 1;

    try {
        if (stepNumber === 11) {
            const result = await saveFilesStep();
            showMessage("success", result.message || "Files saved successfully.");
        } else {
            const result = await saveCurrentStep(stepNumber);
            showMessage("success", result.message || "Step saved successfully.");
        }

        if (currentStep < steps.length - 1) {
            currentStep++;
            showStep(currentStep);
            toggleOwnerStep();
        }
    } catch (error) {
        showMessage("error", "Could not save this step.");
    }
});

saveDraftBtn.addEventListener("click", async () => {
    try {
        const stepNumber = currentStep + 1;
        let result;

        if (stepNumber === 11) {
            result = await saveFilesStep();
        } else {
            result = await saveCurrentStep(stepNumber);
        }

        autosaveStatus.textContent = `Draft saved at ${new Date().toLocaleTimeString()}`;
        showMessage("success", result.message || "Draft saved successfully.");
    } catch (error) {
        showMessage("error", "Could not save draft.");
    }
});

generateReviewBtn.addEventListener("click", buildReview);

clearDraftBtn.addEventListener("click", () => {
    location.reload();
});

document.querySelectorAll('input[name="applicant_owns_land"]').forEach((radio) => {
    radio.addEventListener("change", toggleOwnerStep);
});

form.querySelectorAll('input[type="file"]').forEach((field) => {
    field.addEventListener("change", updateFilePreview);
});

document.querySelectorAll(".map-picker-btn").forEach((button) => {
    button.addEventListener("click", () => {
        openMapPicker(button.dataset.target);
    });
});

if (mapModalBackdrop) {
    mapModalBackdrop.addEventListener("click", closeMapPicker);
}

if (mapCloseBtn) {
    mapCloseBtn.addEventListener("click", closeMapPicker);
}

if (mapSearchBtn) {
    mapSearchBtn.addEventListener("click", handleMapSearch);
}

if (mapSearchInput) {
    mapSearchInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            handleMapSearch();
        }
    });
}

if (confirmMapSelectionBtn) {
    confirmMapSelectionBtn.addEventListener("click", applySelectedLocationToField);
}

if (useCurrentLocationBtn) {
    useCurrentLocationBtn.addEventListener("click", useBrowserCurrentLocation);
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    try {
        const res = await fetch("/submit-planning-application", {
            method: "POST"
        });

        const result = await res.json();

        if (result.success) {
            showMessage("success", result.message);
        } else {
            showMessage("error", result.message || "Submission failed.");
        }
    } catch (error) {
        showMessage("error", "Submission failed.");
    }
});

showStep(currentStep);
toggleOwnerStep();
updateFilePreview();
loadDraftFromServer();