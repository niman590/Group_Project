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
    if (!field) return;
    field.classList.add("field-invalid");
    const errorEl = field.parentElement.querySelector(".error-text");
    if (errorEl) errorEl.textContent = message;
}

function clearFieldError(field) {
    if (!field) return;
    field.classList.remove("field-invalid");
    const errorEl = field.parentElement.querySelector(".error-text");
    if (errorEl) errorEl.textContent = "";
}

function setGroupError(groupName, message) {
    const errorEl = document.querySelector(`[data-group-error="${groupName}"]`);
    const container = document.querySelector(`[data-group-container="${groupName}"]`);
    if (errorEl) errorEl.textContent = message;
    if (container) container.classList.add("group-invalid");
}

function clearGroupError(groupName) {
    const errorEl = document.querySelector(`[data-group-error="${groupName}"]`);
    const container = document.querySelector(`[data-group-container="${groupName}"]`);
    if (errorEl) errorEl.textContent = "";
    if (container) container.classList.remove("group-invalid");
}

function isNumbersOnly(value) {
    return /^\d+$/.test(value);
}

function isValidPhoneNumber(value) {
    return /^\d{10}$/.test(value);
}

function isValidGmail(value) {
    return /^[a-zA-Z0-9._%+-]+@gmail\.com$/.test(value);
}

function isValidSriLankanNIC(value) {
    const normalized = value.trim().toUpperCase();
    const oldNicPattern = /^\d{9}[VX]$/;
    const newNicPattern = /^\d{12}$/;
    return oldNicPattern.test(normalized) || newNicPattern.test(normalized);
}

function isOptionalApplicantFilled(prefix) {
    return [
        document.getElementById(`${prefix}_name`)?.value.trim(),
        document.getElementById(`${prefix}_nic`)?.value.trim(),
        document.getElementById(`${prefix}_tel`)?.value.trim(),
        document.getElementById(`${prefix}_email`)?.value.trim(),
        document.getElementById(`${prefix}_address`)?.value.trim()
    ].some(Boolean);
}

function validateDateGroups(stepIndex) {
    const activeStep = steps[stepIndex];
    const dateGroups = activeStep.querySelectorAll(".date-select-row[data-required='true']");
    let isValid = true;

    dateGroups.forEach((group) => {
        const monthSelect = group.querySelector(".date-month");
        const daySelect = group.querySelector(".date-day");
        const yearSelect = group.querySelector(".date-year");
        const hiddenFieldId = group.dataset.dateGroup;
        const hiddenField = document.getElementById(hiddenFieldId);

        [monthSelect, daySelect, yearSelect].forEach(select => select.classList.remove("field-invalid"));

        const errorEl = group.parentElement.querySelector(".error-text");
        if (errorEl) errorEl.textContent = "";

        if (!monthSelect.value || !daySelect.value || !yearSelect.value || !hiddenField.value) {
            [monthSelect, daySelect, yearSelect].forEach(select => select.classList.add("field-invalid"));
            if (errorEl) errorEl.textContent = "Please select a date.";
            if (isValid) monthSelect.focus();
            isValid = false;
        }
    });

    return isValid;
}

function validateNoFields(stepIndex) {
    const activeStep = steps[stepIndex];
    const noFields = activeStep.querySelectorAll(".number-only-no");
    let isValid = true;

    noFields.forEach((field) => {
        clearFieldError(field);
        const value = field.value.trim();

        if (value && !isNumbersOnly(value)) {
            setFieldError(field, "Only numbers are allowed.");
            if (isValid) field.focus();
            isValid = false;
        }
    });

    return isValid;
}

function validatePhoneFields(stepIndex) {
    const activeStep = steps[stepIndex];
    const phoneFields = activeStep.querySelectorAll(".phone-10");
    let isValid = true;

    phoneFields.forEach((field) => {
        clearFieldError(field);
        const value = field.value.trim();

        if (value && !isValidPhoneNumber(value)) {
            setFieldError(field, "Phone number must contain exactly 10 digits.");
            if (isValid) field.focus();
            isValid = false;
        }
    });

    return isValid;
}

function validateEmailFields(stepIndex) {
    const activeStep = steps[stepIndex];
    const emailFields = activeStep.querySelectorAll(".email-gmail");
    let isValid = true;

    emailFields.forEach((field) => {
        clearFieldError(field);
        const value = field.value.trim();

        if (value && !isValidGmail(value)) {
            setFieldError(field, "Email must be a valid @gmail.com address.");
            if (isValid) field.focus();
            isValid = false;
        }
    });

    return isValid;
}

function validateNICFields(stepIndex) {
    const activeStep = steps[stepIndex];
    const nicFields = activeStep.querySelectorAll(".nic-field");
    let isValid = true;

    nicFields.forEach((field) => {
        clearFieldError(field);
        const value = field.value.trim();

        if (value && !isValidSriLankanNIC(value)) {
            setFieldError(field, "Enter a valid Sri Lankan NIC (old: 9 digits + V/X, new: 12 digits).");
            if (isValid) field.focus();
            isValid = false;
        }
    });

    return isValid;
}

function validateRadioAndCheckboxGroups(stepIndex) {
    let isValid = true;

    if (stepIndex === 0) {
        clearGroupError("development_work_type");
        clearGroupError("land_ownership_type");
        clearGroupError("proposed_use");

        if (!document.querySelector('input[name="development_work_type"]:checked')) {
            setGroupError("development_work_type", "Please select a development work type.");
            isValid = false;
        }

        const selectedLandOwnership = document.querySelector('input[name="land_ownership_type"]:checked')?.value || "";
        const landOwnershipOther = document.getElementById("land_ownership_other");
        const landOwnershipOtherValue = landOwnershipOther ? landOwnershipOther.value.trim() : "";

        clearFieldError(landOwnershipOther);

        if (!selectedLandOwnership && !landOwnershipOtherValue) {
            setGroupError("land_ownership_type", "Please select land ownership type or fill 'If Other, Specify'.");
            isValid = false;
        }

        if (landOwnershipOtherValue) {
            clearGroupError("land_ownership_type");
        }

        const selectedProposedUses = Array.from(document.querySelectorAll('input[name="proposed_use"]:checked')).map(x => x.value);
        const proposedUseOther = document.getElementById("proposed_use_other");
        const proposedUseOtherValue = proposedUseOther ? proposedUseOther.value.trim() : "";

        clearFieldError(proposedUseOther);

        if (!selectedProposedUses.length && !proposedUseOtherValue) {
            setGroupError("proposed_use", "Select at least one proposed use or fill 'If Other, Specify'.");
            isValid = false;
        }

        if (proposedUseOtherValue) {
            clearGroupError("proposed_use");
        }
    }

    if (stepIndex === 2) {
        clearGroupError("applicant_owns_land");
        if (!document.querySelector('input[name="applicant_owns_land"]:checked')) {
            setGroupError("applicant_owns_land", "Please select whether the applicant owns the land.");
            isValid = false;
        }
    }

    if (stepIndex === 9) {
        clearGroupError("submitted_plans");
        if (!document.querySelectorAll('input[name="submitted_plans"]:checked').length) {
            setGroupError("submitted_plans", "Please select at least one submitted plan.");
            isValid = false;
        }
    }

    return isValid;
}

function validateConditionalOwnerStep() {
    const ownsLand = document.querySelector('input[name="applicant_owns_land"]:checked')?.value;
    if (ownsLand !== "No") return true;

    let isValid = true;
    const ownerRequiredFields = [
        document.getElementById("land_owner_name"),
        document.getElementById("land_owner_nic"),
        document.getElementById("land_owner_tel"),
        document.getElementById("land_owner_email"),
        document.getElementById("land_owner_address")
    ];

    ownerRequiredFields.forEach((field) => {
        clearFieldError(field);
        if (!field.value.trim()) {
            setFieldError(field, "This field is required.");
            if (isValid) field.focus();
            isValid = false;
        }
    });

    return isValid;
}

function validateOptionalApplicant2() {
    const prefix = "applicant2";
    if (!isOptionalApplicantFilled(prefix)) return true;

    let isValid = true;
    const name = document.getElementById(`${prefix}_name`);
    const nic = document.getElementById(`${prefix}_nic`);
    const tel = document.getElementById(`${prefix}_tel`);
    const email = document.getElementById(`${prefix}_email`);
    const address = document.getElementById(`${prefix}_address`);

    [name, nic, tel, email, address].forEach(clearFieldError);

    if (!name.value.trim()) {
        setFieldError(name, "Complete the name for Applicant / Owner 2.");
        if (isValid) name.focus();
        isValid = false;
    }
    if (!nic.value.trim()) {
        setFieldError(nic, "Complete the NIC for Applicant / Owner 2.");
        if (isValid) nic.focus();
        isValid = false;
    }
    if (!tel.value.trim()) {
        setFieldError(tel, "Complete the telephone number for Applicant / Owner 2.");
        if (isValid) tel.focus();
        isValid = false;
    }
    if (!email.value.trim()) {
        setFieldError(email, "Complete the email for Applicant / Owner 2.");
        if (isValid) email.focus();
        isValid = false;
    }
    if (!address.value.trim()) {
        setFieldError(address, "Complete the address for Applicant / Owner 2.");
        if (isValid) address.focus();
        isValid = false;
    }

    return isValid;
}

function validateRequiredFiles(stepIndex) {
    if (stepIndex !== 10) return true;

    let isValid = true;
    const requiredFileInputs = steps[stepIndex].querySelectorAll("[data-required-file='true']");

    requiredFileInputs.forEach((input) => {
        const uploadCard = input.closest(".upload-card");
        const errorBox = uploadCard ? uploadCard.querySelector(".file-error") : null;

        input.classList.remove("file-input-invalid");
        if (errorBox) errorBox.textContent = "";

        if (!input.files || !input.files.length) {
            input.classList.add("file-input-invalid");
            if (errorBox) errorBox.textContent = "This file is required.";
            if (isValid) input.focus();
            isValid = false;
        }
    });

    return isValid;
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

    if (!validateNoFields(stepIndex)) isValid = false;
    if (!validatePhoneFields(stepIndex)) isValid = false;
    if (!validateEmailFields(stepIndex)) isValid = false;
    if (!validateNICFields(stepIndex)) isValid = false;
    if (!validateRadioAndCheckboxGroups(stepIndex)) isValid = false;
    if (!validateDateGroups(stepIndex)) isValid = false;
    if (!validateRequiredFiles(stepIndex)) isValid = false;

    if (stepIndex === 1 && !validateOptionalApplicant2()) {
        isValid = false;
    }

    if (stepIndex === 3 && !validateConditionalOwnerStep()) {
        isValid = false;
    }

    return isValid;
}

function validateEntireFormBeforeSubmit() {
    for (let i = 0; i < steps.length - 1; i++) {
        if (!validateStep(i)) {
            currentStep = i;
            showStep(currentStep);
            showMessage("error", `Please complete all required fields in Step ${i + 1} before submitting.`);
            return false;
        }
    }
    return true;
}

function allowOnlyNumbersInput() {
    document.querySelectorAll(".number-only-no, .phone-10").forEach((field) => {
        field.addEventListener("input", () => {
            field.value = field.value.replace(/\D/g, "");
            clearFieldError(field);
        });
    });
}

function allowNICInput() {
    document.querySelectorAll(".nic-field").forEach((field) => {
        field.addEventListener("input", () => {
            field.value = field.value.replace(/[^0-9vVxX]/g, "").toUpperCase().slice(0, 12);
            clearFieldError(field);
        });
    });
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
    const step5 = getStepData(5);
    const step6 = getStepData(6);
    const step7 = getStepData(7);
    const step8 = getStepData(8);
    const step9 = getStepData(9);
    const step10 = getStepData(10);

    reviewSummary.textContent = `
Assessment No.: ${step1.assessment_no || "-"}
Road Name: ${step1.road_name || "-"}
Local Authority: ${step1.local_authority_name || "-"}
Applicant: ${step2.applicants?.[0]?.name || "-"}
Applicant NIC: ${step2.applicants?.[0]?.nic || "-"}
Architect / Planner: ${step3.architect_town_planner_name || "-"}
Engineer: ${step3.engineer_name || "-"}
Rate Clearance Ref: ${step5.rate_clearance_ref || "-"}
Existing Use: ${step6.existing_use || "-"}
Building Height: ${step7.total_building_height || "-"}
Plot Coverage: ${step8.plot_coverage || "-"}
Total Units: ${step9.total_units || "-"}
Submitted Plans: ${step10.submitted_plans?.length ? step10.submitted_plans.join(", ") : "-"}
    `.trim();
}

function updateAddressMeta(fieldId, addressText, lat = null, lon = null) {
    const metaBox = document.getElementById(`${fieldId}_meta`);
    if (!metaBox) return;

    if (!addressText && lat != null && lon != null) {
        metaBox.textContent = `GIS selected location:\nLatitude: ${Number(lat).toFixed(6)}, Longitude: ${Number(lon).toFixed(6)}`;
        return;
    }

    if (!addressText) {
        metaBox.textContent = "No GIS location selected yet.";
        return;
    }

    if (lat != null && lon != null) {
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
        currentPickedLocation = {
            address: "",
            lat,
            lon: lng
        };
        mapSelectedAddress.textContent = `Selected coordinates:\nLatitude: ${lat.toFixed(6)}, Longitude: ${lng.toFixed(6)}\nFetching address...`;
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
            currentPickedLocation = {
                address: "",
                lat,
                lon
            };
            mapSelectedAddress.textContent = `Selected coordinates:\nLatitude: ${Number(lat).toFixed(6)}, Longitude: ${Number(lon).toFixed(6)}`;
            mapStatusText.textContent = result.message || "Could not identify the selected location. You can still use the coordinates.";
            return;
        }

        currentPickedLocation = {
            address: result.address || "",
            lat: result.lat != null ? Number(result.lat) : Number(lat),
            lon: result.lon != null ? Number(result.lon) : Number(lon)
        };

        const addressText = currentPickedLocation.address
            ? currentPickedLocation.address
            : `Latitude: ${Number(currentPickedLocation.lat).toFixed(6)}, Longitude: ${Number(currentPickedLocation.lon).toFixed(6)}`;

        mapSelectedAddress.textContent = `${addressText}\nLatitude: ${Number(currentPickedLocation.lat).toFixed(6)}, Longitude: ${Number(currentPickedLocation.lon).toFixed(6)}`;
        mapStatusText.textContent = "Location selected successfully.";
    } catch (error) {
        currentPickedLocation = {
            address: "",
            lat,
            lon
        };
        mapSelectedAddress.textContent = `Selected coordinates:\nLatitude: ${Number(lat).toFixed(6)}, Longitude: ${Number(lon).toFixed(6)}`;
        mapStatusText.textContent = "Reverse geocoding failed. You can still use the coordinates.";
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

        if (!result.success || !Array.isArray(result.results) || !result.results.length) {
            mapStatusText.textContent = result.message || "No matching locations found.";
            return;
        }

        const first = result.results[0];
        const lat = parseFloat(first.lat);
        const lon = parseFloat(first.lon);

        if (Number.isNaN(lat) || Number.isNaN(lon)) {
            mapStatusText.textContent = "Invalid location data returned from search.";
            return;
        }

        placeMapMarker(lat, lon);
        currentPickedLocation = {
            address: first.display_name || "",
            lat,
            lon
        };

        const addressText = currentPickedLocation.address || `Latitude: ${lat.toFixed(6)}, Longitude: ${lon.toFixed(6)}`;
        mapSelectedAddress.textContent = `${addressText}\nLatitude: ${lat.toFixed(6)}, Longitude: ${lon.toFixed(6)}`;
        mapStatusText.textContent = "Search result selected. You can confirm or click another point on the map.";
    } catch (error) {
        mapStatusText.textContent = "Location search failed.";
    }
}

function applySelectedLocationToField() {
    if (!activeAddressFieldId) return;

    const field = document.getElementById(activeAddressFieldId);
    if (!field) return;

    if (!currentPickedLocation) {
        mapStatusText.textContent = "Please select a location from the map first.";
        return;
    }

    const lat = currentPickedLocation.lat != null ? Number(currentPickedLocation.lat) : null;
    const lon = currentPickedLocation.lon != null ? Number(currentPickedLocation.lon) : null;

    let finalValue = (currentPickedLocation.address || "").trim();

    if (!finalValue && lat != null && lon != null) {
        finalValue = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    }

    if (!finalValue) {
        mapStatusText.textContent = "Please select a valid location from the map first.";
        return;
    }

    field.value = finalValue;
    updateAddressMeta(activeAddressFieldId, currentPickedLocation.address || finalValue, lat, lon);
    clearFieldError(field);
    mapStatusText.textContent = "Selected location applied successfully.";
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

            currentPickedLocation = {
                address: "",
                lat,
                lon
            };

            mapSelectedAddress.textContent = `Current coordinates:\nLatitude: ${lat.toFixed(6)}, Longitude: ${lon.toFixed(6)}\nFetching address...`;
            await fillSelectedLocationFromCoordinates(lat, lon);
        },
        (error) => {
            if (error.code === 1) {
                mapStatusText.textContent = "Location permission was denied.";
            } else if (error.code === 2) {
                mapStatusText.textContent = "Current location is unavailable.";
            } else if (error.code === 3) {
                mapStatusText.textContent = "Location request timed out.";
            } else {
                mapStatusText.textContent = "Could not access your current location.";
            }
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

function populateDateSelectOptions(group) {
    const monthSelect = group.querySelector(".date-month");
    const daySelect = group.querySelector(".date-day");
    const yearSelect = group.querySelector(".date-year");

    if (!monthSelect || !daySelect || !yearSelect) return;

    const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    if (monthSelect.options.length === 1) {
        monthNames.forEach((month, index) => {
            const option = document.createElement("option");
            option.value = String(index + 1).padStart(2, "0");
            option.textContent = month;
            monthSelect.appendChild(option);
        });
    }

    if (yearSelect.options.length === 1) {
        const currentYear = new Date().getFullYear();
        for (let year = currentYear + 10; year >= 1950; year--) {
            const option = document.createElement("option");
            option.value = String(year);
            option.textContent = year;
            yearSelect.appendChild(option);
        }
    }

    updateDateDayOptions(group);
}

function updateDateDayOptions(group) {
    const monthSelect = group.querySelector(".date-month");
    const daySelect = group.querySelector(".date-day");
    const yearSelect = group.querySelector(".date-year");

    if (!monthSelect || !daySelect || !yearSelect) return;

    const selectedMonth = parseInt(monthSelect.value, 10);
    const selectedYear = parseInt(yearSelect.value, 10);
    const currentSelectedDay = daySelect.value;

    let daysInMonth = 31;

    if (selectedMonth && selectedYear) {
        daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
    } else if (selectedMonth) {
        daysInMonth = new Date(2000, selectedMonth, 0).getDate();
    }

    daySelect.innerHTML = '<option value="">Day</option>';

    for (let day = 1; day <= daysInMonth; day++) {
        const option = document.createElement("option");
        option.value = String(day).padStart(2, "0");
        option.textContent = day;
        if (String(day).padStart(2, "0") === currentSelectedDay) {
            option.selected = true;
        }
        daySelect.appendChild(option);
    }

    if (currentSelectedDay && parseInt(currentSelectedDay, 10) > daysInMonth) {
        daySelect.value = "";
    }
}

function syncHiddenDateField(group) {
    const hiddenFieldId = group.dataset.dateGroup;
    const hiddenField = document.getElementById(hiddenFieldId);
    const monthSelect = group.querySelector(".date-month");
    const daySelect = group.querySelector(".date-day");
    const yearSelect = group.querySelector(".date-year");

    if (!hiddenField || !monthSelect || !daySelect || !yearSelect) return;

    if (yearSelect.value && monthSelect.value && daySelect.value) {
        hiddenField.value = `${yearSelect.value}-${monthSelect.value}-${daySelect.value}`;
    } else {
        hiddenField.value = "";
    }
}

function setDateGroupValue(group, isoValue) {
    const monthSelect = group.querySelector(".date-month");
    const daySelect = group.querySelector(".date-day");
    const yearSelect = group.querySelector(".date-year");
    const hiddenFieldId = group.dataset.dateGroup;
    const hiddenField = document.getElementById(hiddenFieldId);

    if (!monthSelect || !daySelect || !yearSelect || !hiddenField) return;

    if (!isoValue) {
        monthSelect.value = "";
        yearSelect.value = "";
        updateDateDayOptions(group);
        daySelect.value = "";
        hiddenField.value = "";
        return;
    }

    const parts = isoValue.split("-");
    if (parts.length !== 3) return;

    const [year, month, day] = parts;
    yearSelect.value = year;
    monthSelect.value = month;
    updateDateDayOptions(group);
    daySelect.value = day;
    hiddenField.value = isoValue;
}

function initializeDateGroups() {
    const dateGroups = document.querySelectorAll(".date-select-row");

    dateGroups.forEach((group) => {
        populateDateSelectOptions(group);

        const monthSelect = group.querySelector(".date-month");
        const daySelect = group.querySelector(".date-day");
        const yearSelect = group.querySelector(".date-year");

        const handleChange = () => {
            updateDateDayOptions(group);
            syncHiddenDateField(group);
        };

        monthSelect.addEventListener("change", handleChange);
        daySelect.addEventListener("change", handleChange);
        yearSelect.addEventListener("change", handleChange);
    });
}

async function loadDraftFromServer() {
    try {
        const params = new URLSearchParams(window.location.search);
        const applicationId = params.get("application_id");

        let url = "/get-planning-draft";
        if (applicationId) {
            url += `?application_id=${applicationId}`;
        }

        const res = await fetch(url);
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
            setDateGroupValue(document.querySelector('[data-date-group="rate_clearance_date"]'), draft.step5.rate_clearance_date || "");

            document.querySelector('[name="water_clearance_ref"]').value = draft.step5.water_clearance_ref || "";
            setDateGroupValue(document.querySelector('[data-date-group="water_clearance_date"]'), draft.step5.water_clearance_date || "");

            document.querySelector('[name="drainage_clearance_ref"]').value = draft.step5.drainage_clearance_ref || "";
            setDateGroupValue(document.querySelector('[data-date-group="drainage_clearance_date"]'), draft.step5.drainage_clearance_date || "");

            document.querySelector('[name="uda_preliminary_ref"]').value = draft.step5.uda_preliminary_ref || "";
            setDateGroupValue(document.querySelector('[data-date-group="uda_preliminary_date"]'), draft.step5.uda_preliminary_date || "");
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
    if (!validateStep(currentStep)) {
        showMessage("error", `Please complete all required fields in Step ${currentStep + 1} before continuing.`);
        return;
    }

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
            if (!validateRequiredFiles(10)) {
                showMessage("error", "Please upload the required PDF files before saving this step.");
                return;
            }
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
    field.addEventListener("change", () => {
        const isValid = validatePDFOnly(field);
        if (isValid) updateFilePreview();
    });
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

document.querySelectorAll("input, textarea, select").forEach((field) => {
    field.addEventListener("input", () => clearFieldError(field));
    field.addEventListener("change", () => clearFieldError(field));
});

document.querySelectorAll('input[name="development_work_type"], input[name="land_ownership_type"], input[name="applicant_owns_land"], input[name="submitted_plans"], input[name="proposed_use"]').forEach((field) => {
    field.addEventListener("change", () => {
        clearGroupError(field.name);
    });
});

const landOwnershipOtherInput = document.getElementById("land_ownership_other");
const proposedUseOtherInput = document.getElementById("proposed_use_other");

if (landOwnershipOtherInput) {
    landOwnershipOtherInput.addEventListener("input", () => {
        clearFieldError(landOwnershipOtherInput);
        if (landOwnershipOtherInput.value.trim()) {
            clearGroupError("land_ownership_type");
        }
    });
}

if (proposedUseOtherInput) {
    proposedUseOtherInput.addEventListener("input", () => {
        clearFieldError(proposedUseOtherInput);
        if (proposedUseOtherInput.value.trim()) {
            clearGroupError("proposed_use");
        }
    });
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!validateEntireFormBeforeSubmit()) return;

    buildReview();

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

initializeDateGroups();
showStep(currentStep);
toggleOwnerStep();
updateFilePreview();
allowOnlyNumbersInput();
allowNICInput();
loadDraftFromServer();

function validatePDFOnly(fileInput) {
    const files = fileInput.files;
    const uploadCard = fileInput.closest(".upload-card");
    const errorBox = uploadCard ? uploadCard.querySelector(".file-error") : null;

    if (errorBox) errorBox.textContent = "";
    fileInput.classList.remove("file-input-invalid");

    if (!files || !files.length) {
        return true;
    }

    for (let file of files) {
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            fileInput.value = "";
            fileInput.classList.add("file-input-invalid");

            if (errorBox) {
                errorBox.textContent = "Rejected: only PDF files are allowed.";
            }

            updateFilePreview();
            return false;
        }
    }

    return true;
}