document.addEventListener("DOMContentLoaded", function () {
    const steps = document.querySelectorAll(".form-step");
    const jumpButtons = document.querySelectorAll(".jump-btn");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");
    const stepPill = document.getElementById("stepPill");
    const progressText = document.getElementById("progressText");
    const progressFill = document.getElementById("progressFill");

    let currentStep = 1;
    const totalSteps = steps.length;

    function updateJumpButtons(step) {
        jumpButtons.forEach((btn) => {
            const btnStep = Number(btn.dataset.jumpStep);
            btn.classList.toggle("active", btnStep === step);
        });
    }

    function showStep(step) {
        steps.forEach((section) => {
            const sectionStep = Number(section.dataset.step);
            section.classList.toggle("active", sectionStep === step);
        });

        if (stepPill) {
            stepPill.textContent = `Step ${step}`;
        }

        if (progressText) {
            progressText.textContent = `Step ${step} of ${totalSteps}`;
        }

        if (progressFill && totalSteps > 0) {
            progressFill.style.width = `${(step / totalSteps) * 100}%`;
        }

        if (prevBtn) {
            prevBtn.disabled = step === 1;
            prevBtn.style.opacity = step === 1 ? "0.6" : "1";
        }

        if (nextBtn) {
            nextBtn.disabled = step === totalSteps;
            nextBtn.style.opacity = step === totalSteps ? "0.6" : "1";
        }

        updateJumpButtons(step);
    }

    jumpButtons.forEach((btn) => {
        btn.addEventListener("click", function () {
            const targetStep = Number(this.dataset.jumpStep);

            if (!Number.isNaN(targetStep) && targetStep >= 1 && targetStep <= totalSteps) {
                currentStep = targetStep;
                showStep(currentStep);
            }
        });
    });

    if (prevBtn) {
        prevBtn.addEventListener("click", function () {
            if (currentStep > 1) {
                currentStep -= 1;
                showStep(currentStep);
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener("click", function () {
            if (currentStep < totalSteps) {
                currentStep += 1;
                showStep(currentStep);
            }
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "ArrowLeft" && currentStep > 1) {
            currentStep -= 1;
            showStep(currentStep);
        }

        if (event.key === "ArrowRight" && currentStep < totalSteps) {
            currentStep += 1;
            showStep(currentStep);
        }
    });

    if (totalSteps > 0) {
        showStep(currentStep);
    }
});
