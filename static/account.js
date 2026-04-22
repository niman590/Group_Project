document.addEventListener("DOMContentLoaded", function () {
  const flashMessages = document.querySelectorAll("[data-flash]");
  const flashCloseButtons = document.querySelectorAll("[data-flash-close]");
  const accountForm = document.getElementById("accountForm");
  const deleteAccountForm = document.getElementById("deleteAccountForm");
  const saveChangesBtn = document.getElementById("saveChangesBtn");
  const deleteAccountBtn = document.getElementById("deleteAccountBtn");
  const phoneInput = document.getElementById("phone_number");
  const emailInput = document.getElementById("email");
  const firstNameInput = document.getElementById("first_name");

  const deleteAccountModal = document.getElementById("deleteAccountModal");
  const deleteAccountModalCancel = document.getElementById("deleteAccountModalCancel");
  const deleteAccountModalConfirm = document.getElementById("deleteAccountModalConfirm");

  const isSaveLocked = saveChangesBtn ? saveChangesBtn.hasAttribute("data-locked-action") : false;
  const isDeleteLocked = deleteAccountBtn ? deleteAccountBtn.hasAttribute("data-locked-action") : false;

  function hideFlash(flash, duration = 250) {
    if (!flash) return;
    flash.style.transition = `opacity ${duration}ms ease, transform ${duration}ms ease`;
    flash.style.opacity = "0";
    flash.style.transform = "translateY(-6px)";
    setTimeout(() => {
      if (flash.parentNode) {
        flash.remove();
      }
    }, duration);
  }

  function setButtonLoading(button, loadingText) {
    if (!button || button.disabled) return;
    button.classList.add("loading");

    const textNode = button.querySelector(".btn-text");
    if (textNode) {
      textNode.dataset.originalText = textNode.textContent;
      textNode.textContent = loadingText;
    }
  }

  function trimFormFields() {
    const fields = accountForm ? accountForm.querySelectorAll("input[type='text'], input[type='email'], textarea") : [];
    fields.forEach((field) => {
      if (!field.hasAttribute("readonly")) {
        field.value = field.value.trim();
      }
    });
  }

  function openDeleteAccountModal() {
    if (!deleteAccountModal) return;
    deleteAccountModal.classList.add("open");
  }

  function closeDeleteAccountModal() {
    if (!deleteAccountModal) return;
    deleteAccountModal.classList.remove("open");
  }

  if (phoneInput && !phoneInput.hasAttribute("readonly")) {
    phoneInput.addEventListener("input", function () {
      this.value = this.value.replace(/[^0-9]/g, "").slice(0, 10);
    });
  }

  if (emailInput && !emailInput.hasAttribute("readonly")) {
    emailInput.addEventListener("blur", function () {
      this.value = this.value.trim();
    });
  }

  if (accountForm) {
    accountForm.addEventListener("submit", function (event) {
      if (isSaveLocked) {
        event.preventDefault();
        return;
      }

      trimFormFields();
      setButtonLoading(saveChangesBtn, "Saving...");
    });
  }

  if (deleteAccountForm) {
    deleteAccountForm.addEventListener("submit", function (event) {
      if (isDeleteLocked) {
        event.preventDefault();
        return;
      }

      event.preventDefault();
      openDeleteAccountModal();
    });
  }

  if (deleteAccountModalCancel) {
    deleteAccountModalCancel.addEventListener("click", function () {
      closeDeleteAccountModal();
    });
  }

  if (deleteAccountModalConfirm) {
    deleteAccountModalConfirm.addEventListener("click", function () {
      if (!deleteAccountForm) return;
      closeDeleteAccountModal();
      setButtonLoading(deleteAccountBtn, "Deleting...");
      deleteAccountForm.submit();
    });
  }

  if (deleteAccountModal) {
    deleteAccountModal.addEventListener("click", function (event) {
      if (event.target === deleteAccountModal) {
        closeDeleteAccountModal();
      }
    });
  }

  flashMessages.forEach((flash) => {
    setTimeout(() => {
      if (flash.parentNode) {
        hideFlash(flash, 300);
      }
    }, 4500);
  });

  flashCloseButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const flash = this.closest("[data-flash]");
      hideFlash(flash, 250);
    });
  });

  document.addEventListener("keydown", function (event) {
    const activeTag = document.activeElement ? document.activeElement.tagName : "";

    if (
      event.key === "/" &&
      firstNameInput &&
      !firstNameInput.hasAttribute("readonly") &&
      activeTag !== "INPUT" &&
      activeTag !== "TEXTAREA"
    ) {
      event.preventDefault();
      firstNameInput.focus();
    }

    if (event.key === "Escape" && deleteAccountModal && deleteAccountModal.classList.contains("open")) {
      closeDeleteAccountModal();
    }
  });
});