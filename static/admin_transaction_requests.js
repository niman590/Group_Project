document.addEventListener("DOMContentLoaded", function () {
    createSystemConfirmModal();
    setupApproveConfirmations();
    setupRejectValidation();
});

let pendingSubmitForm = null;

function createSystemConfirmModal() {
    if (document.getElementById("systemConfirmOverlay")) {
        return;
    }

    const modalHTML = `
        <div class="system-confirm-overlay" id="systemConfirmOverlay">
            <div class="system-confirm-modal">
                <div class="system-confirm-icon" id="systemConfirmIcon">
                    <i class="fa-solid fa-circle-question"></i>
                </div>

                <div class="system-confirm-content">
                    <span class="system-confirm-kicker" id="systemConfirmKicker">Confirmation Required</span>
                    <h3 id="systemConfirmTitle">Are you sure?</h3>
                    <p id="systemConfirmMessage">Please confirm this action.</p>
                </div>

                <div class="system-confirm-actions">
                    <button type="button" class="system-btn-cancel" id="systemConfirmCancel">
                        Cancel
                    </button>
                    <button type="button" class="system-btn-confirm" id="systemConfirmOk">
                        Confirm
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHTML);

    document.getElementById("systemConfirmCancel").addEventListener("click", closeSystemConfirm);
    document.getElementById("systemConfirmOverlay").addEventListener("click", function (event) {
        if (event.target === this) {
            closeSystemConfirm();
        }
    });

    document.getElementById("systemConfirmOk").addEventListener("click", function () {
        const form = pendingSubmitForm;
        pendingSubmitForm = null;
        closeSystemConfirm();

        if (form) {
            form.dataset.confirmed = "true";
            form.submit();
        }
    });
}

function openSystemConfirm(options) {
    const overlay = document.getElementById("systemConfirmOverlay");
    const title = document.getElementById("systemConfirmTitle");
    const message = document.getElementById("systemConfirmMessage");
    const kicker = document.getElementById("systemConfirmKicker");
    const icon = document.getElementById("systemConfirmIcon");
    const okButton = document.getElementById("systemConfirmOk");

    title.textContent = options.title || "Are you sure?";
    message.textContent = options.message || "Please confirm this action.";
    kicker.textContent = options.kicker || "Confirmation Required";
    okButton.textContent = options.confirmText || "Confirm";

    icon.className = "system-confirm-icon";
    okButton.className = "system-btn-confirm";

    if (options.type === "approve") {
        icon.classList.add("approve");
        okButton.classList.add("approve");
        icon.innerHTML = `<i class="fa-solid fa-check"></i>`;
    } else if (options.type === "reject") {
        icon.classList.add("reject");
        okButton.classList.add("reject");
        icon.innerHTML = `<i class="fa-solid fa-xmark"></i>`;
    } else {
        icon.classList.add("default");
        okButton.classList.add("default");
        icon.innerHTML = `<i class="fa-solid fa-circle-question"></i>`;
    }

    overlay.classList.add("show");
    document.body.classList.add("modal-open");
}

function closeSystemConfirm() {
    const overlay = document.getElementById("systemConfirmOverlay");
    overlay.classList.remove("show");
    document.body.classList.remove("modal-open");
    pendingSubmitForm = null;
}

function setupApproveConfirmations() {
    const approveForms = document.querySelectorAll(".approve-form");

    approveForms.forEach((form) => {
        form.addEventListener("submit", function (event) {
            if (form.dataset.confirmed === "true") {
                delete form.dataset.confirmed;
                return;
            }

            event.preventDefault();

            const deedNumber = form.dataset.deed || "this deed";
            pendingSubmitForm = form;

            openSystemConfirm({
                type: "approve",
                kicker: "Approve Transaction Request",
                title: "Approve deed request?",
                message: `Are you sure you want to approve the transaction request for deed ${deedNumber}? This action will apply the ownership record update.`,
                confirmText: "Approve Request"
            });
        });
    });
}

function setupRejectValidation() {
    const rejectForms = document.querySelectorAll(".reject-form");

    rejectForms.forEach((form) => {
        form.addEventListener("submit", function (event) {
            if (form.dataset.confirmed === "true") {
                delete form.dataset.confirmed;
                return;
            }

            const deedNumber = form.dataset.deed || "this deed";
            const reasonField = form.querySelector("textarea[name='admin_comment']");

            if (!reasonField) {
                return;
            }

            const reason = reasonField.value.trim();

            if (reason.length < 5) {
                event.preventDefault();
                showSystemAlert(
                    "Rejection reason required",
                    "Please enter a clear rejection reason with at least 5 characters."
                );
                reasonField.focus();
                return;
            }

            event.preventDefault();
            pendingSubmitForm = form;

            openSystemConfirm({
                type: "reject",
                kicker: "Reject Transaction Request",
                title: "Reject deed request?",
                message: `Are you sure you want to reject the transaction request for deed ${deedNumber}? The applicant will see the rejection reason.`,
                confirmText: "Reject Request"
            });
        });
    });
}

function showSystemAlert(title, message) {
    openSystemConfirm({
        type: "reject",
        kicker: "Validation Required",
        title: title,
        message: message,
        confirmText: "Okay"
    });

    const okButton = document.getElementById("systemConfirmOk");
    const clonedButton = okButton.cloneNode(true);
    okButton.parentNode.replaceChild(clonedButton, okButton);

    clonedButton.addEventListener("click", function () {
        closeSystemConfirm();
        createSystemConfirmModal();
    });
}