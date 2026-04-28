document.addEventListener("DOMContentLoaded", function () {
    setupApproveConfirmations();
    setupRejectValidation();
});

function setupApproveConfirmations() {
    const approveForms = document.querySelectorAll(".approve-form");

    approveForms.forEach((form) => {
        form.addEventListener("submit", function (event) {
            const deedNumber = form.dataset.deed || "this deed";
            const confirmed = window.confirm(
                `Are you sure you want to approve the transaction request for deed ${deedNumber}?`
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
}

function setupRejectValidation() {
    const rejectForms = document.querySelectorAll(".reject-form");

    rejectForms.forEach((form) => {
        form.addEventListener("submit", function (event) {
            const deedNumber = form.dataset.deed || "this deed";
            const reasonField = form.querySelector("textarea[name='admin_comment']");

            if (!reasonField) {
                return;
            }

            const reason = reasonField.value.trim();

            if (reason.length < 5) {
                event.preventDefault();
                alert("Please enter a clear rejection reason with at least 5 characters.");
                reasonField.focus();
                return;
            }

            const confirmed = window.confirm(
                `Reject the transaction request for deed ${deedNumber}?`
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
}