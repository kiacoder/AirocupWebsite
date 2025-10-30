"use strict";

const Helpers = {
  debounce(functionToDebounce, waitTime = 150) {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => functionToDebounce(...args), waitTime);
    };
  },

  safeClipboardWrite(textToCopy) {
    if (navigator.clipboard?.writeText) {
      return navigator.clipboard.writeText(textToCopy);
    }
    return new Promise((resolve, reject) => {
      try {
        const textAreaElement = document.createElement("textarea");
        textAreaElement.value = String(textToCopy || "");
        textAreaElement.style.position = "fixed";
        textAreaElement.style.left = "-9999px";
        document.body.appendChild(textAreaElement);
        textAreaElement.select();
        document.execCommand("copy");
        textAreaElement.remove();
        resolve();
      } catch (error) {
        reject(error);
      }
    });
  },

  safeSocket() {
    if (typeof io === "undefined") return null;
    try {
      return io();
    } catch (error) {
      console.warn("Socket connection failed:", error);
      return null;
    }
  },

  parseTimestamp(timestampString) {
    if (!timestampString) return null;
    const rawTimestamp = String(timestampString);
    const dateObject = new Date(rawTimestamp);
    if (!isNaN(dateObject)) {
      return dateObject;
    }
    const isoAttempt = new Date(rawTimestamp.replace(" ", "T"));
    if (!isNaN(isoAttempt)) {
      return isoAttempt;
    }
    return null;
  },
};

const Utils = {
  showNotification(message, options = {}) {
    createFlash(options.type || "Info", String(message || ""), options);
  },
};

function createFlash(type, message, options = {}) {
  const normalizedType =
    typeof type === "string" && type
      ? type.charAt(0).toUpperCase() + type.slice(1)
      : "Info";

  let flashContainer = document.getElementById("FlashContainer");
  if (!flashContainer) {
    flashContainer = document.createElement("div");
    flashContainer.id = "FlashContainer";
    flashContainer.setAttribute("aria-live", "polite");
    flashContainer.setAttribute("aria-atomic", "true");
    document.body.appendChild(flashContainer);
    initializeFlashSystem();
  }

  const flashItem = document.createElement("div");
  flashItem.className = `FlashMessage Flash${normalizedType}`;
  flashItem.setAttribute("role", "alert");

  const flashIcon = document.createElement("i");
  const iconMapping = {
    Success: "fa-check-circle",
    Error: "fa-exclamation-triangle",
    Warning: "fa-exclamation-circle",
    Info: "fa-info-circle",
  };
  flashIcon.className = `fas ${
    iconMapping[normalizedType] || iconMapping.Info
  }`;
  flashIcon.setAttribute("aria-hidden", "true");

  const flashText = document.createElement("span");
  flashText.textContent = message || "";

  const closeButton = document.createElement("button");
  closeButton.className = "FlashCloseBtn";
  closeButton.dataset.action = "dismiss-flash";
  closeButton.setAttribute("aria-label", "Close notification");
  closeButton.innerHTML = "&times;";

  flashItem.appendChild(flashIcon);
  flashItem.appendChild(flashText);
  flashItem.appendChild(closeButton);
  flashContainer.appendChild(flashItem);

  const displayDuration = options.duration || 5000;
  setTimeout(() => {
    dismissFlash(flashItem);
  }, displayDuration);

  return flashItem;
}

function dismissFlash(flashElement) {
  if (!flashElement || flashElement.classList.contains("FlashMessageClosing"))
    return;
  flashElement.classList.add("FlashMessageClosing");
  setTimeout(() => {
    flashElement.remove();
  }, 350);
}

function initializeFlashSystem() {
  const flashContainer = document.getElementById("FlashContainer");
  if (!flashContainer || flashContainer._flashInitialized) return;

  flashContainer._flashInitialized = true;

  flashContainer.addEventListener("click", function (event) {
    const clickTarget = event.target.closest("[data-action='dismiss-flash']");
    if (clickTarget) {
      dismissFlash(clickTarget.closest(".FlashMessage"));
    }
  });

  Array.from(flashContainer.querySelectorAll(".FlashMessage")).forEach(
    (flashElement, index) => {
      setTimeout(() => dismissFlash(flashElement), 5000 + index * 120);
    }
  );
}

const Validators = {
  isValidIranianPhone(phoneNumber) {
    if (!phoneNumber) return false;
    const cleanPhoneNumber = String(phoneNumber).replace(/\s+/g, "");
    return /^(?:\+98|0)?9\d{9}$/.test(cleanPhoneNumber);
  },

  isValidNationalId(nationalId) {
    if (!nationalId) return false;
    const cleanNationalId = String(nationalId).trim();
    if (!/^\d{10}$/.test(cleanNationalId)) return false;
    if (new Set(cleanNationalId).size === 1) return false;

    const checkDigit = parseInt(cleanNationalId[9], 10);
    let sum = 0;

    for (let index = 0; index < 9; index++) {
      sum += parseInt(cleanNationalId[index], 10) * (10 - index);
    }

    const remainder = sum % 11;
    return remainder < 2
      ? checkDigit === remainder
      : checkDigit === 11 - remainder;
  },

  isValidTeamName(teamName) {
    const airocupData = window.AirocupData || {};
    if (!teamName) {
      return { isValid: false, message: "Team name cannot be empty." };
    }
    const trimmedTeamName = teamName.trim();
    if (trimmedTeamName.length < 3 || trimmedTeamName.length > 30) {
      return {
        isValid: false,
        message: "Team name must be between 3 and 30 characters.",
      };
    }
    if (!/^[A-Za-z\u0600-\u06FF0-9_ ]+$/.test(trimmedTeamName)) {
      return {
        isValid: false,
        message:
          "Team name can only contain letters, numbers, spaces, and underscores.",
      };
    }
    const forbiddenWords = airocupData.forbiddenWords || [];
    const lowerCaseName = trimmedTeamName.toLowerCase();
    for (let word of forbiddenWords) {
      if (lowerCaseName.includes(String(word).toLowerCase())) {
        return {
          isValid: false,
          message: "Team name contains forbidden words.",
        };
      }
    }
    return { isValid: true };
  },

  isValidEmail(email) {
    if (!email) return false;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email).toLowerCase());
  },
};

const ModalHelpers = {
  trapFocus(modalElement) {
    if (!modalElement) return;
    const focusableElements = Array.from(
      modalElement.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    );
    if (!focusableElements.length) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const keyHandler = (keyboardEvent) => {
      if (keyboardEvent.key !== "Tab") return;
      if (keyboardEvent.shiftKey && document.activeElement === firstElement) {
        keyboardEvent.preventDefault();
        lastElement.focus();
      } else if (
        !keyboardEvent.shiftKey &&
        document.activeElement === lastElement
      ) {
        keyboardEvent.preventDefault();
        firstElement.focus();
      }
    };
    modalElement.addEventListener("keydown", keyHandler);
    return () => modalElement.removeEventListener("keydown", keyHandler);
  },

  openModal(modalElement, triggerElement) {
    if (!modalElement) return;
    modalElement.classList.add("IsVisible");
    modalElement.setAttribute("aria-hidden", "false");
    modalElement._triggerElement = triggerElement || document.activeElement;
    modalElement.querySelector("button, a, input")?.focus();
    if (modalElement._releaseTrap) {
      modalElement._releaseTrap();
    }
    modalElement._releaseTrap = this.trapFocus(modalElement);
    document.body.classList.add("BodyNoScroll");
  },

  closeModal(modalElement) {
    if (!modalElement) return;
    modalElement.classList.remove("IsVisible");
    modalElement.setAttribute("aria-hidden", "true");
    if (modalElement._releaseTrap) {
      modalElement._releaseTrap();
    }
    modalElement._triggerElement?.focus();
    document.body.classList.remove("BodyNoScroll");
  },
};

const FormHelpers = {
  initialize() {
    if (this._initialized) return;
    this._initialized = true;

    this.aiocupData = window.AirocupData || {};
    if (!window.AirocupData) {
      console.warn(
        "AirocupData object not found. Forms may not function correctly."
      );
    }
    this.daysInMonth = this.aiocupData.daysInMonth || {};
    this.provinces = this.aiocupData.provinces || {};
    this.allowedYears = this.aiocupData.allowedYears || [];
    this.persianMonths = this.aiocupData.persianMonths || {};
    this.allowedExtensions = this.aiocupData.allowedExtensions || [
      "png",
      "jpg",
      "jpeg",
      "gif",
      "pdf",
      "docx",
      "doc",
      "xlsx",
      "xls",
      "ppt",
      "pptx",
      "mp4",
      "mov",
      "avi",
      "mkv",
      "webm",
    ];
  },

  populateProvinces(selectElement) {
    if (!selectElement) return;
    const fragment = document.createDocumentFragment();
    fragment.appendChild(new Option("Select Province", ""));
    Object.keys(this.provinces || {})
      .sort((a, b) => a.localeCompare(b, "fa"))
      .forEach((provinceName) => {
        fragment.appendChild(new Option(provinceName, provinceName));
      });
    selectElement.innerHTML = "";
    selectElement.appendChild(fragment);
  },

  updateCities(provinceName, citySelectElement) {
    if (!citySelectElement) return;
    citySelectElement.innerHTML = "";
    citySelectElement.add(new Option("Select City", ""));
    citySelectElement.disabled = true;
    const cities = this.provinces ? this.provinces[provinceName] : null;
    if (!provinceName || !cities) return;
    cities.forEach((cityName) => {
      citySelectElement.add(new Option(cityName, cityName));
    });
    citySelectElement.disabled = false;
  },

  setupProvinceCityListener(formElement) {
    if (!formElement) return;
    const provinceSelect = formElement.querySelector('[name="Province"]');
    const citySelect = formElement.querySelector('[name="City"]');
    if (!provinceSelect || !citySelect) return;
    provinceSelect.addEventListener("change", () => {
      this.updateCities(provinceSelect.value, citySelect);
    });
    if (provinceSelect.value) {
      this.updateCities(provinceSelect.value, citySelect);
      citySelect.value = citySelect.getAttribute("data-initial-city") || "";
    }
  },

  setupDatePicker(formElement) {
    if (!formElement) return;
    const daySelect = formElement.querySelector('[name="BirthDay"]');
    const monthSelect = formElement.querySelector('[name="BirthMonth"]');
    const yearSelect = formElement.querySelector('[name="BirthYear"]');
    if (!daySelect || !monthSelect || !yearSelect) return;

    monthSelect.innerHTML = "";
    monthSelect.add(new Option("Month", ""));
    for (const [number, name] of Object.entries(this.persianMonths || {})) {
      monthSelect.add(new Option(name, number));
    }
    yearSelect.innerHTML = "";
    yearSelect.add(new Option("Year", ""));
    (this.allowedYears || []).forEach((year) => {
      yearSelect.add(new Option(year, year));
    });

    const isLeapYear = (year) =>
      [1, 5, 9, 13, 17, 22, 26, 30].includes((year + 12) % 33);
    const updateDays = () => {
      const selectedMonth = parseInt(monthSelect.value, 10);
      const selectedYear = parseInt(yearSelect.value, 10);
      let maxDays = selectedMonth ? this.daysInMonth[selectedMonth] || 31 : 31;
      if (selectedMonth === 12 && selectedYear && isLeapYear(selectedYear)) {
        maxDays = 30;
      }
      const currentDay = daySelect.value;
      daySelect.innerHTML = "";
      daySelect.add(new Option("Day", ""));
      for (let day = 1; day <= maxDays; day++) {
        daySelect.add(new Option(day, day));
      }
      if (currentDay && parseInt(currentDay, 10) <= maxDays) {
        daySelect.value = currentDay;
      }
    };
    yearSelect.addEventListener("input", updateDays);
    monthSelect.addEventListener("change", updateDays);
    updateDays();
  },
};

const UI = {
  initializeMobileMenu() {
    const menuButton = document.querySelector(".MobileMenuBtn");
    const navigation = document.querySelector(".NavItems");
    if (!menuButton || !navigation) return;
    const toggleMenu = (shouldShow) => {
      navigation.classList.toggle("Show", shouldShow);
      const icon = menuButton.querySelector("i");
      if (icon) icon.className = shouldShow ? "fas fa-times" : "fas fa-bars";
      document.body.classList.toggle("BodyNoScroll", shouldShow);
    };
    menuButton.addEventListener("click", () =>
      toggleMenu(!navigation.classList.contains("Show"))
    );
  },

  initializeLazyLoad() {
    const lazyElements = document.querySelectorAll(
      "iframe.lazy-video, .FadeInElement"
    );
    if (!("IntersectionObserver" in window)) {
      lazyElements.forEach((element) => {
        if (element.tagName === "IFRAME") element.src = element.dataset.src;
        element.classList.add("IsVisible");
      });
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const element = entry.target;
            if (element.tagName === "IFRAME") element.src = element.dataset.src;
            else element.classList.add("IsVisible");
            observer.unobserve(element);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );
    lazyElements.forEach((element) => observer.observe(element));
  },

  initializeSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach((link) => {
      link.addEventListener("click", function (event) {
        const href = this.getAttribute("href");
        const isInternal =
          href.startsWith("#") &&
          this.pathname === window.location.pathname &&
          this.hostname === window.location.hostname;

        if (!isInternal || href === "#") return;

        try {
          const target = document.querySelector(href);
          if (target) {
            event.preventDefault();
            target.scrollIntoView({ behavior: "smooth" });
          }
        } catch (error) {
          console.warn("Smooth scroll error:", error);
        }
      });
    });
  },

  initializeAccordion() {
    document.querySelectorAll(".AccordionHeader").forEach((header) => {
      const button = header.querySelector("button");
      if (!button) return;
      button.addEventListener("click", () => {
        const isExpanded = button.getAttribute("aria-expanded") === "true";
        const panel = header.nextElementSibling;

        document
          .querySelectorAll(".AccordionHeader button")
          .forEach((otherButton) => {
            otherButton.setAttribute("aria-expanded", "false");
            otherButton.closest(".AccordionHeader").classList.remove("active");
            const otherPanel =
              otherButton.closest(".AccordionHeader").nextElementSibling;
            if (otherPanel) otherPanel.classList.remove("active");
          });

        if (!isExpanded) {
          button.setAttribute("aria-expanded", "true");
          header.classList.add("active");
          if (panel) panel.classList.add("active");
        }
      });
    });
  },

  initializeGalleryModal() {
    const modal = document.getElementById("ImageModal");
    if (!modal) return;
    const modalImage = modal.querySelector(".ModalImage");
    document
      .querySelector(".GalleryGrid")
      ?.addEventListener("click", (event) => {
        const image = event.target.closest("img");
        if (image) {
          modalImage.src = image.src;
          ModalHelpers.openModal(modal, image);
        }
      });
    modal
      .querySelector(".CloseBtn")
      ?.addEventListener("click", () => ModalHelpers.closeModal(modal));
    modal.addEventListener("click", (event) => {
      if (event.target === modal) ModalHelpers.closeModal(modal);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && modal.classList.contains("IsVisible")) {
        ModalHelpers.closeModal(modal);
      }
    });
  },

  initializeCopyButtons() {
    document.querySelectorAll(".CopyBtn").forEach((button) => {
      button.addEventListener("click", function () {
        const textToCopy = this.dataset.copy || "";
        Helpers.safeClipboardWrite(textToCopy)
          .then(() => {
            const originalHTML = this.innerHTML;
            this.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => (this.innerHTML = originalHTML), 1500);
          })
          .catch((error) => {
            console.error("Copy failed:", error);
            createFlash("Error", "Copy failed.");
          });
      });
    });
  },

  initializePasswordToggle(toggleId) {
    const toggleButton = document.getElementById(toggleId);
    if (!toggleButton || !toggleButton.dataset.target) return;
    const passwordInput = document.querySelector(toggleButton.dataset.target);
    if (!passwordInput) return;
    toggleButton.addEventListener("click", function () {
      const newType =
        passwordInput.getAttribute("type") === "password" ? "text" : "password";
      passwordInput.setAttribute("type", newType);
      const icon = this.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-eye");
        icon.classList.toggle("fa-eye-slash");
      }
    });
  },

  initializeConfirmationModal() {
    const modal = document.getElementById("deleteConfirmModal");
    if (!modal) return;
    const modalTitle = modal.querySelector("h3");
    const modalText = modal.querySelector("p");
    const confirmBtn = modal.querySelector("#confirmDeleteBtn");
    let formToSubmit = null;

    document.body.addEventListener("click", (event) => {
      const triggerBtn = event.target.closest(".DeleteBtn, .ConfirmDeleteBtn");
      if (!triggerBtn || triggerBtn.disabled) return;
      event.preventDefault();
      formToSubmit = triggerBtn.closest("form");
      const {
        memberName,
        teamName,
        modalTitle: title,
        modalText: text,
        modalConfirm,
      } = triggerBtn.dataset;

      modalTitle.textContent =
        title ||
        (memberName ? "Confirm Member Deletion" : "Confirm Team Archive");
      modalText.innerHTML =
        text ||
        (memberName
          ? `Are you sure you want to delete <strong>${memberName}</strong>? This cannot be undone.`
          : `Are you sure you want to archive team <strong>${teamName}</strong>?`);
      confirmBtn.textContent =
        modalConfirm || (memberName ? "Yes, delete" : "Yes, archive");
      ModalHelpers.openModal(modal, triggerBtn);
    });
    confirmBtn.addEventListener("click", () => {
      if (formToSubmit) formToSubmit.submit();
    });
    modal.addEventListener("click", (event) => {
      if (
        event.target.matches('[data-dismiss="modal"], .CloseBtn') ||
        event.target === modal
      ) {
        ModalHelpers.closeModal(modal);
      }
    });
  },
};

const App = {
  initialize() {
    if (this._initialized) return;
    this._initialized = true;

    FormHelpers.initialize();
    initializeFlashSystem();
    UI.initializeMobileMenu();
    UI.initializeLazyLoad();
    UI.initializeSmoothScroll();
    UI.initializeCopyButtons();
    UI.initializeConfirmationModal();
    UI.initializePasswordToggle("password-toggle");
    UI.initializePasswordToggle("confirm-password-toggle");

    if (document.querySelector(".AccordionContainer")) UI.initializeAccordion();
    if (document.querySelector(".GalleryGrid")) UI.initializeGalleryModal();
    if (document.getElementById("CreateTeamForm"))
      this.initializeCreateTeamForm();
    if (document.querySelector(".MembersPage")) this.initializeMembersPage();
    if (document.getElementById("SignUpForm")) this.initializeSignUpForm();
    if (document.getElementById("ResetForm")) this.initializeResetForm();
    if (document.querySelector("form[action*='/Payment']"))
      this.initializePaymentForm();
    if (document.getElementById("SelectLeagueForm"))
      this.initializeLeagueSelector();
    if (document.getElementById("chat-box")) this.initializeSupportChat();
    if (document.getElementById("EditForm")) {
      const form = document.getElementById("EditForm");
      FormHelpers.populateProvinces(form.querySelector('[name="Province"]'));
      FormHelpers.setupProvinceCityListener(form);
      FormHelpers.setupDatePicker(form);
    }
    if (document.getElementById("DocumentUploadForm"))
      this.initializeDocumentUpload();
  },

  initializeCreateTeamForm() {
    const form = document.getElementById("CreateTeamForm");
    if (!form) return;
    FormHelpers.populateProvinces(form.querySelector('[name="Province"]'));
    FormHelpers.setupProvinceCityListener(form);
    FormHelpers.setupDatePicker(form);
    form.addEventListener("submit", (event) => {
      const teamName = form.querySelector('[name="TeamName"]')?.value || "";
      const validation = Validators.isValidTeamName(teamName);
      if (!validation.isValid) {
        event.preventDefault();
        createFlash("Error", validation.message);
      }
    });
  },

  initializeResetForm() {
    this.initializePasswordConfirmation(
      "ResetForm",
      "newPassword",
      "confirmPassword",
      "passwordError"
    );
  },

  initializeSupportChat() {
    const container = document.querySelector(".ClientChatContainer");
    if (!container) return;
    const chatBox = document.getElementById("chat-box");
    const messageInput = document.getElementById("message-input");
    const sendButton = document.getElementById("send-button");
    if (!chatBox || !messageInput || !sendButton) return;

    const roomId = container.dataset.clientId;
    const historyUrl = container.dataset.historyUrl;
    const socket = Helpers.safeSocket();

    const addMessage = (data) => {
      const isSentByUser = data.sender === "You";
      const messageElement = document.createElement("div");
      messageElement.className = `ChatMessage ${
        isSentByUser ? "Message--sent" : "Message--received"
      }`;
      const meta = document.createElement("div");
      meta.className = "Meta";
      const messageDate = Helpers.parseTimestamp(data.timestamp) || new Date();
      meta.textContent = `${
        data.sender
      } at ${messageDate.toLocaleTimeString()}`;
      const text = document.createElement("p");
      text.textContent = data.message;
      messageElement.append(meta, text);
      chatBox.appendChild(messageElement);
    };

    const scrollToBottom = () => (chatBox.scrollTop = chatBox.scrollHeight);

    const sendMessage = () => {
      const messageText = messageInput.value.trim();
      if (messageText && socket) {
        socket.emit("send_message", { room: roomId, message: messageText });
        addMessage({
          sender: "You",
          message: messageText,
          timestamp: new Date().toISOString(),
        });
        messageInput.value = "";
        messageInput.focus();
        scrollToBottom();
      }
    };

    const loadHistory = async () => {
      if (!historyUrl) return;
      try {
        const response = await fetch(historyUrl);
        if (!response.ok)
          throw new Error(`Server response: ${response.status}`);
        const data = await response.json();
        chatBox.innerHTML = "";
        if (data.messages?.length) {
          data.messages.forEach((msg) =>
            addMessage({
              sender: msg.sender,
              message: msg.messageText,
              timestamp: msg.timestamp,
            })
          );
        } else {
          chatBox.innerHTML =
            '<div style="text-align:center; color:#888;">No messages yet. Say hello!</div>';
        }
      } catch (error) {
        console.error("Error loading chat history:", error);
        chatBox.innerHTML =
          '<div style="text-align:center; color:red;">Error loading history. Please refresh.</div>';
      } finally {
        scrollToBottom();
      }
    };

    sendButton.addEventListener("click", sendMessage);
    messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });

    if (socket) {
      socket.on("connect", () => socket.emit("join", { room: roomId }));
      socket.on("new_message", (data) => {
        addMessage({
          sender: data.sender,
          message: data.message,
          timestamp: data.timestamp,
        });
        scrollToBottom();
      });
    }

    loadHistory();
  },

  initializeLeagueSelector() {
    const form = document.getElementById("SelectLeagueForm");
    if (!form) return;
    const leagueOne = form.querySelector("#leagueOne");
    const leagueTwo = form.querySelector("#leagueTwo");
    if (!leagueOne || !leagueTwo) return;

    const syncOptions = () => {
      const oneValue = leagueOne.value;
      const twoValue = leagueTwo.value;
      for (const option of leagueTwo.options)
        option.disabled = option.value === oneValue && option.value !== "";
      for (const option of leagueOne.options)
        option.disabled = option.value === twoValue && option.value !== "";
    };
    leagueOne.addEventListener("change", syncOptions);
    leagueTwo.addEventListener("change", syncOptions);
    syncOptions();
  },

  initializePasswordConfirmation(formId, passwordId, confirmId, errorId) {
    const form = document.getElementById(formId);
    if (!form) return;
    const passwordInput = form.querySelector(`#${passwordId}`);
    const confirmInput = form.querySelector(`#${confirmId}`);
    const errorElement = form.querySelector(`#${errorId}`);
    if (!passwordInput || !confirmInput) return;

    const validateMatch = () => {
      const isMatch = passwordInput.value === confirmInput.value;
      if (errorElement)
        errorElement.classList.toggle(
          "IsVisible",
          !isMatch && confirmInput.value.length > 0
        );
      confirmInput.classList.toggle(
        "IsInvalid",
        !isMatch && confirmInput.value.length > 0
      );
      return isMatch;
    };

    form.addEventListener("submit", (event) => {
      if (!validateMatch()) {
        event.preventDefault();
        createFlash("Error", "Passwords do not match!");
      }
    });
    passwordInput.addEventListener("input", validateMatch);
    confirmInput.addEventListener("input", validateMatch);
  },

  initializeMembersPage() {
    const page = document.querySelector(".MembersPage");
    if (!page) return;
    const addForm = page.querySelector("#AddMemberForm");
    const editModal = document.getElementById("EditModal");
    const editForm = page.querySelector("#EditForm");

    if (addForm) {
      FormHelpers.populateProvinces(addForm.querySelector('[name="Province"]'));
      FormHelpers.setupProvinceCityListener(addForm);
      FormHelpers.setupDatePicker(addForm);
    }
    if (editModal && editForm) {
      FormHelpers.populateProvinces(
        editForm.querySelector('[name="Province"]')
      );
      FormHelpers.setupDatePicker(editForm);
      FormHelpers.setupProvinceCityListener(editForm);
      page.addEventListener("click", (event) => {
        const editButton = event.target.closest(".EditBtn");
        if (!editButton) return;
        const data = editButton.dataset;
        const teamId = page.dataset.teamId;
        const memberId = data.memberId;
        editForm.action = `/Team/${teamId}/EditMember/${memberId}`;
        for (const key in data) {
          const input = editForm.querySelector(
            `[name="${key.charAt(0).toUpperCase() + key.slice(1)}"]`
          );
          if (input) input.value = data[key];
        }
        const provinceSelect = editForm.querySelector('[name="Province"]');
        provinceSelect.value = data.province || "";
        FormHelpers.updateCities(
          provinceSelect.value,
          editForm.querySelector('[name="City"]')
        );
        editForm.querySelector('[name="City"]').value = data.city || "";
        if (data.birthDate) {
          const [year, month, day] = data.birthDate.split("-");
          editForm.querySelector('[name="BirthYear"]').value = year || "";
          editForm.querySelector('[name="BirthMonth"]').value = month || "";
          editForm.querySelector('[name="BirthDay"]').value = day || "";
        }
        ModalHelpers.openModal(editModal, editButton);
      });
      editModal
        .querySelector(".CloseBtn")
        ?.addEventListener("click", () => ModalHelpers.closeModal(editModal));
    }
  },

  initializeSignUpForm() {
    const form = document.getElementById("SignUpForm");
    if (!form) return;
    const passwordInput = form.querySelector("#password");
    if (!passwordInput) return;

    const requirements = {
      length: document.getElementById("req-length"),
      upper: document.getElementById("req-upper"),
      lower: document.getElementById("req-lower"),
      number: document.getElementById("req-number"),
      special: document.getElementById("req-special"),
    };

    let liveRegion = document.getElementById("password-strength-announcer");
    if (!liveRegion) {
      liveRegion = document.createElement("div");
      liveRegion.id = "password-strength-announcer";
      liveRegion.className = "VisuallyHidden";
      liveRegion.setAttribute("aria-live", "polite");
      form.appendChild(liveRegion);
    }

    const validatePasswordStrength = () => {
      const password = passwordInput.value;
      let allValid = true;
      let announcements = [];

      const check = (key, regex, message) => {
        const isValid = regex.test(password);
        if (requirements[key]) {
          const wasValid = requirements[key].classList.contains("valid");
          requirements[key].className = isValid ? "valid" : "invalid";
          if (isValid && !wasValid) announcements.push(message);
        }
        if (!isValid) allValid = false;
      };

      check("length", /.{8,}/, "Length requirement met.");
      check("upper", /[A-Z]/, "Uppercase requirement met.");
      check("lower", /[a-z]/, "Lowercase requirement met.");
      check("number", /[0-9]/, "Number requirement met.");
      check(
        "special",
        /[!@#$%^&*(),.?":{}|<>]/,
        "Special character requirement met."
      );

      if (announcements.length > 0) {
        liveRegion.textContent = announcements.join(" ");
      }
      return allValid;
    };

    this.initializePasswordConfirmation(
      "SignUpForm",
      "password",
      "confirm_password",
      "passwordError"
    );
    passwordInput.addEventListener("input", validatePasswordStrength);
    form.addEventListener("submit", (event) => {
      if (!validatePasswordStrength()) {
        event.preventDefault();
        createFlash("Error", "Please fix the errors in the form.");
      }
    });
  },

  initializePaymentForm() {
    const receiptInput = document.querySelector(
      'input[type="file"][name="receipt"]'
    );
    if (!receiptInput) return;
    receiptInput.addEventListener("change", () => {
      const file = receiptInput.files[0];
      if (!file) return;
      const extension = file.name.split(".").pop().toLowerCase();
      if (!FormHelpers.allowedExtensions.includes(extension)) {
        createFlash("Error", "Unsupported file format.");
        receiptInput.value = "";
      }
    });
  },

  initializeDocumentUpload() {
    const form = document.getElementById("DocumentUploadForm");
    if (!form) return;
    const fileInput = form.querySelector('input[type="file"]');
    fileInput.addEventListener("change", () => {
      const file = fileInput.files[0];
      if (!file) return;
      const isVideo = ["mp4", "mov", "avi", "mkv", "webm"].includes(
        file.name.split(".").pop().toLowerCase()
      );
      const isImage = ["png", "jpg", "jpeg", "gif", "svg"].includes(
        file.name.split(".").pop().toLowerCase()
      );
      if (isVideo && file.size > 300 * 1024 * 1024) {
        createFlash("Error", "Video size cannot exceed 300 MB.");
        fileInput.value = "";
      } else if (isImage && file.size > 50 * 1024 * 1024) {
        createFlash("Error", "Image size cannot exceed 50 MB.");
        fileInput.value = "";
      } else if (!isVideo && !isImage && file.size > 100 * 1024 * 1024) {
        createFlash("Error", "File size cannot exceed 100 MB.");
        fileInput.value = "";
      }
    });
  },
};

const AdminApp = {
  initialize() {
    if (this._initialized) return;
    this._initialized = true;

    FormHelpers.initialize();
    initializeFlashSystem();
    UI.initializeConfirmationModal();

    this.initializeMenu();
    this.initializeChat();
    this.initializeRelativeTime();
    this.initializeAdminModals();
    this.initializeClientSearch();
    this.initializeAdminMembersPage();

    if (document.querySelector(".ChartGrid")) this.initializeDashboardCharts();
    UI.initializePasswordToggle("password-toggle");
    UI.initializePasswordToggle("EditPasswordToggle");
    if (document.getElementById("AddMemberForm"))
      this.initializeAdminAddMemberPage?.();
  },

  initializeAdminMembersPage() {
    const page = document.querySelector(".AdminMembersPage");
    if (!page) return;
    const addForm = document.getElementById("AddMemberForm");
    if (addForm) {
      FormHelpers.populateProvinces(addForm.querySelector('[name="Province"]'));
      FormHelpers.setupProvinceCityListener(addForm);
      FormHelpers.setupDatePicker(addForm);
    }
    const memberModal = document.getElementById("MemberModal");
    const memberForm = document.getElementById("MemberForm");
    const modalTitle = document.getElementById("MemberModalTitle");
    if (memberModal && memberForm && modalTitle) {
      FormHelpers.populateProvinces(
        memberForm.querySelector('[name="Province"]')
      );
      FormHelpers.setupProvinceCityListener(memberForm);
      FormHelpers.setupDatePicker(memberForm);
      page.addEventListener("click", (event) => {
        const trigger = event.target.closest(
          '[data-modal-target="MemberModal"]'
        );
        if (!trigger) return;
        const data = trigger.dataset;
        const teamId = page.dataset.teamId;
        modalTitle.textContent = `Edit ${data.memberName}`;
        memberForm.action = `/Admin/Team/${teamId}/EditMember/${data.memberId}`;
        memberForm.querySelector('[name="Name"]').value = data.memberName || "";
        memberForm.querySelector('[name="NationalID"]').value =
          data.memberNid || "";
        memberForm.querySelector('[name="PhoneNumber"]').value =
          data.memberPhone || "";
        memberForm.querySelector('[name="Role"]').value = data.memberRole || "";
        const provinceSelect = memberForm.querySelector('[name="Province"]');
        provinceSelect.value = data.memberProvince || "";
        FormHelpers.updateCities(
          provinceSelect.value,
          memberForm.querySelector('[name="City"]')
        );
        memberForm.querySelector('[name="City"]').value = data.memberCity || "";
        ModalHelpers.openModal(memberModal, trigger);
      });
    }
  },

  initializeMenu() {
    const toggleButton = document.querySelector(".AdminHeader__mobile-toggle");
    const navigation = document.querySelector(".AdminHeader__nav");
    if (!toggleButton || !navigation) return;
    toggleButton.addEventListener("click", () => {
      const isOpen = navigation.classList.toggle("is-open");
      toggleButton.setAttribute("aria-expanded", String(isOpen));
      const icon = toggleButton.querySelector("i");
      if (icon) icon.className = isOpen ? "fas fa-times" : "fas fa-bars";
    });
  },

  initializeRelativeTime() {
    const timeElements = Array.from(
      document.querySelectorAll(
        "[data-timestamp].RelativeTime, [data-timestamp].relative-time"
      )
    );
    if (!timeElements.length) return;
    const formatTime = (dateObject) => {
      if (!dateObject) return "";
      const diff = Math.floor((new Date() - dateObject) / 1000);
      if (diff < 5) return "just now";
      if (diff < 60) return `${diff} seconds ago`;
      if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
      if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
      if (diff < 2592000) return `${Math.floor(diff / 86400)} days ago`;
      if (diff < 31536000) return `${Math.floor(diff / 2592000)} months ago`;
      return `${Math.floor(diff / 31536000)} years ago`;
    };
    const updateAllTimes = () => {
      timeElements.forEach((element) => {
        const rawTimestamp = element.dataset.timestamp || "";
        const dateObject = Helpers.parseTimestamp(rawTimestamp);
        element.textContent = dateObject
          ? formatTime(dateObject)
          : rawTimestamp;
        if (dateObject)
          element.setAttribute("title", dateObject.toLocaleString());
      });
    };
    updateAllTimes();
    if (this._relativeTimeInterval) clearInterval(this._relativeTimeInterval);
    this._relativeTimeInterval = setInterval(updateAllTimes, 60000);
  },

  initializeAdminAddMemberPage() {
    const addForm = document.getElementById("AddMemberForm");
    if (!addForm) return;
    FormHelpers.populateProvinces(addForm.querySelector('[name="Province"]'));
    FormHelpers.setupProvinceCityListener(addForm);
    FormHelpers.setupDatePicker(addForm);
  },

  initializeDashboardCharts() {
    const loadCharts = () => {
      const createChart = async (canvas, url, type, label, indexAxis = "x") => {
        if (!canvas) return;
        try {
          const response = await fetch(url);
          if (!response.ok) throw new Error("Network response failed");
          const chartData = await response.json();
          new Chart(canvas.getContext("2d"), {
            type: type,
            data: {
              labels: chartData.Labels,
              datasets: [
                {
                  label: label,
                  data: chartData.Data,
                  backgroundColor: [
                    "#3182ce",
                    "#2b6cb0",
                    "#2c7a7b",
                    "#2d3748",
                    "#805ad5",
                    "#b7791f",
                  ],
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              indexAxis: indexAxis,
              plugins: {
                legend: {
                  position: type === "doughnut" ? "bottom" : "top",
                  display: type !== "bar",
                },
              },
            },
          });
        } catch (error) {
          console.error(`Failed to load chart data from ${url}:`, error);
        }
      };
      createChart(
        document.getElementById("ProvinceChart"),
        "/API/Admin/ProvinceDistribution",
        "doughnut",
        "Provincial Distribution"
      );
      createChart(
        document.getElementById("CityChart"),
        "/API/AdminCityDistribution",
        "bar",
        "Participant Count",
        "y"
      );
    };
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/chart.js";
    script.onload = loadCharts;
    document.body.appendChild(script);
  },

  initializeAdminModals() {
    document.body.addEventListener("click", (event) => {
      const trigger = event.target.closest("[data-modal-target]");
      if (trigger)
        ModalHelpers.openModal(
          document.getElementById(trigger.dataset.modalTarget),
          trigger
        );
      if (event.target.matches(".CloseBtn, [data-dismiss='modal']"))
        ModalHelpers.closeModal(event.target.closest(".Modal"));
    });
    window.addEventListener("click", (event) => {
      if (event.target.classList.contains("Modal"))
        ModalHelpers.closeModal(event.target);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape")
        document
          .querySelectorAll(".Modal.IsVisible")
          .forEach(ModalHelpers.closeModal);
    });
  },

  initializeClientSearch() {
    const searchInput = document.getElementById("ClientSearchInput");
    const tableBody = document.querySelector("#clients-table tbody");
    if (!searchInput || !tableBody) return;
    const tableRows = Array.from(tableBody.querySelectorAll("tr"));
    const noResultsMessage = document.getElementById("NoResultsMessage");
    const performSearch = () => {
      const searchTerm = searchInput.value.toLowerCase().trim();
      let visibleCount = 0;
      tableRows.forEach((row) => {
        if (row.classList.contains("EmptyStateRow")) return;
        const isMatch = row.textContent.toLowerCase().includes(searchTerm);
        row.style.display = isMatch ? "" : "none";
        if (isMatch) visibleCount++;
      });
      if (noResultsMessage)
        noResultsMessage.style.display =
          visibleCount === 0 ? "table-row" : "none";
    };
    searchInput.addEventListener("input", Helpers.debounce(performSearch, 180));
  },

  initializeChat() {
    const container = document.querySelector(".AdminChatContainer");
    if (!container) return;
    const elements = {
      chatBox: document.getElementById("ChatBox"),
      messageInput: document.getElementById("MessageInput"),
      sendButton: document.getElementById("SendButton"),
      personaSelect: document.getElementById("PersonaSelect"),
    };
    const socket = Helpers.safeSocket();
    const state = {
      roomId: container.dataset.clientId,
      historyUrl: container.dataset.historyUrl,
      socket: socket,
    };
    if (!state.roomId || !state.historyUrl || !elements.chatBox) {
      if (elements.chatBox)
        elements.chatBox.innerHTML =
          '<div class="EmptyStateRow">Error: Chat dependencies not found.</div>';
      return;
    }

    const scrollToBottom = () =>
      (elements.chatBox.scrollTop = elements.chatBox.scrollHeight);
    const appendMessage = (message) => {
      if (!message || !message.messageText) return;
      const isClient = String(message.sender) === state.roomId;
      const messageElement = document.createElement("div");
      messageElement.className = `ChatMessage ${
        isClient ? "is-client" : "is-admin"
      }`;
      const senderDiv = document.createElement("div");
      senderDiv.className = "ChatMessage__sender";
      senderDiv.textContent = isClient ? "User" : message.sender;
      const textElement = document.createElement("p");
      textElement.className = "ChatMessage__text";
      textElement.textContent = message.messageText;
      const metaDiv = document.createElement("div");
      metaDiv.className = "ChatMessage__meta";
      metaDiv.textContent = new Date(
        message.timestamp || Date.now()
      ).toLocaleTimeString();
      messageElement.append(senderDiv, textElement, metaDiv);
      elements.chatBox.appendChild(messageElement);
    };

    const loadChatHistory = async () => {
      try {
        const response = await fetch(state.historyUrl);
        if (!response.ok) throw new Error("Failed to fetch chat history");
        const data = await response.json();
        elements.chatBox.innerHTML = "";
        if (data?.messages?.length > 0) {
          data.messages.forEach((msg) =>
            appendMessage({
              ...msg,
              sender: msg.sender,
              messageText: msg.messageText,
              timestamp: msg.timestamp,
            })
          );
        } else {
          elements.chatBox.innerHTML =
            '<div class="EmptyStateRow">No message history found.</div>';
        }
        scrollToBottom();
      } catch (error) {
        console.error(error);
        elements.chatBox.innerHTML =
          '<div class="EmptyStateRow">Error loading chat history.</div>';
      }
    };

    const sendMessage = () => {
      const messageText = elements.messageInput.value.trim();
      if (!messageText) return;
      const sender = elements.personaSelect
        ? elements.personaSelect.value
        : "Admin";
      if (state.socket) {
        state.socket.emit("send_message", {
          room: state.roomId,
          sender: sender,
          message: messageText,
        });
      }
      appendMessage({
        sender: sender,
        messageText: messageText,
        timestamp: new Date().toISOString(),
      });
      elements.messageInput.value = "";
      elements.messageInput.focus();
      scrollToBottom();
    };

    if (elements.sendButton)
      elements.sendButton.addEventListener("click", sendMessage);
    if (elements.messageInput)
      elements.messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });

    if (state.socket) {
      state.socket.on("connect", () =>
        state.socket.emit("join", { room: state.roomId })
      );
      state.socket.on("new_message", (message) => {
        elements.chatBox.querySelector(".EmptyStateRow")?.remove();
        appendMessage({
          sender: message.sender,
          messageText: message.message,
          timestamp: message.timestamp,
        });
        scrollToBottom();
      });
    }

    loadChatHistory();
  },
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.classList.contains("AdminBody")) {
    AdminApp.initialize();
  } else {
    App.initialize();
  }
});
