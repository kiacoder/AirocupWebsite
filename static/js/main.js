/**
 * Airocup Global JavaScript
 *
 * Handles global UI interactions like mobile navigation,
 * flash messages, and other site-wide behaviors.
 */

// Strict mode helps catch common coding errors
"use strict";

const Validators = {
  IsValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  },

  IsValidIranianPhone(phone) {
    return /^09\d{9}$/.test(phone);
  },
};

const airocupApp = {
  constants: {
    SELECTORS: {
      MODAL: ".modal",
      MODAL_DIALOG: ".modal-dialog",
      MODAL_CONTENT: ".modal-content",
      MODAL_TITLE: ".modal-title",
      MODAL_BODY: ".modal-body",
      CLOSE_BTN: ".close-btn",
      FLASH_CONTAINER: "#flash-container",
      FLASH_MESSAGE: ".flash-message",
      CLOSE_FLASH_BTN: '[data-action="dismiss-flash"]',
      COPY_BTN: ".copy-btn",
      DELETE_BTN: ".delete-btn",
      CONFIRMATION_MODAL: "#confirmationModal",
      CONFIRM_MODAL_BTN: "#confirmModalBtn",
      PASSWORD_TOGGLE_BTN: '[data-action="toggle-password"]',
      LAZY_ELEMENT: "iframe.lazy-video, .fade-in-element",
      VIDEO_WRAPPER_LAZY: ".video-wrapper.lazy-video",
      MOBILE_MENU_BTN: ".mobile-menu-btn",
      NAV_ITEMS: ".nav-items",
      ACCORDION_CONTAINER: ".accordion-container",
      ACCORDION_BUTTON: ".accordion-button",
      ACCORDION_ITEM: ".accordion-item",
      GALLERY_GRID: ".gallery-grid",
      IMAGE_MODAL: "#image-modal",
      MODAL_IMAGE: ".modal-image",
      GALLERY_ITEM_IMG: ".gallery-item img",
      LOGIN_FORM: "#login-form",
      FORGOT_PASSWORD_FORM: "#forgot-password-form",
      SIGN_UP_FORM: "#signUpForm",
      PASSWORD_INPUT: "#password",
      CONFIRM_PASSWORD_INPUT: "#confirm_password",
      PASSWORD_STRENGTH_VALIDATOR: "#password-strength-validator",
      CLIENT_CHAT_CONTAINER: ".client-chat-container",
      CHAT_BOX: "#chat-box",
      MESSAGE_INPUT: "#message-input",
      SEND_BUTTON: "#send-button",
      LEAGUE_FILTER_INPUT: "#leagueFilter",
      NO_RESULTS_MESSAGE: "#noResultsMessage",
      ADMIN_BODY: ".admin-body",
      ADMIN_HEADER_MOBILE_TOGGLE: ".admin-header-mobile-toggle",
      ADMIN_HEADER_NAV: ".admin-header-nav",
      PROVINCE_CHART: "#provinceChart",
      CITY_CHART: "#cityChart",
      CLIENT_SEARCH_INPUT: "#clientSearchInput",
      CLIENTS_TABLE_BODY: "#clients-table tbody",
      ADMIN_CHAT_CONTAINER: ".admin-chat-container",
      RELATIVE_TIME: "[data-timestamp]",
      POSTER_TRIGGER: ".poster-zoom-trigger",
      POSTER_MODAL: "#posterZoomModal",
      POSTER_MODAL_CLOSE: "[data-action=\"close-poster-modal\"]",
    },
    CLASSES: {
      IS_VISIBLE: "is-visible",
      SHOW: "show",
      BODY_NO_SCROLL: "body-no-scroll",
      ACTIVE: "active",
      FLASH_MESSAGE_CLOSING: "flash-message-closing",
      VALID: "valid",
      INVALID: "is-invalid",
      IS_OPEN: "is-open",
      POSTER_MODAL_OPEN: "poster-modal-open",
    },
    ATTRIBUTES: {
      ARIA_HIDDEN: "aria-hidden",
      DATA_MODAL_TARGET: "data-modal-target",
      DATA_DISMISS: "data-dismiss",
      DATA_COPY: "data-copy",
    },
  },

  helpers: {
    debounce(func, wait = 200) {
      let timeoutId;
      return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), wait);
      };
    },

    safeClipboardWrite(text) {
      return (
        navigator.clipboard?.writeText(text) ??
        Promise.reject("Clipboard API not available")
      );
    },

    toPersianDigits(value) {
      const digitsMap = {
        0: "۰",
        1: "۱",
        2: "۲",
        3: "۳",
        4: "۴",
        5: "۵",
        6: "۶",
        7: "۷",
        8: "۸",
        9: "۹",
      };
      return String(value).replace(/[0-9]/g, (digit) => digitsMap[digit] || digit);
    },

    safeSocket() {
      try {
        return typeof io !== "undefined" ? io() : null;
      } catch (error) {
        console.warn("Socket.IO connection failed:", error);
        return null;
      }
    },

    async fetchJSON(url) {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.statusText}`);
      }
      return response.json();
    },

    parseTimestamp(timestampString) {
      if (!timestampString) return null;
      const rawTimestamp = String(timestampString);
      const isoDate = new Date(rawTimestamp.replace(" ", "T"));
      if (!isNaN(isoDate)) return isoDate;
      const simpleDate = new Date(rawTimestamp);
      if (!isNaN(simpleDate)) return simpleDate;

      return null;
    },
  },

  ui: {
    init() {
      this.initializeHeaderLayout();
      this.initializeFlashMessages();
      this.initializeModals();
      this.initializeCopyButtons();
      this.initializePasswordToggles();
      this.initializeLazyLoad();
      this.initializeVideoPlayer();
      this.initializeRelativeTime();
      this.initializeSmoothScroll();
      this.initializePosterZoom();
    },

    initializeHeaderLayout() {
      const header =
        document.querySelector(".site-header") ||
        document.querySelector(".admin-header");

      if (!header) return;

      const root = document.documentElement;
      const setHeight = () => {
        const height = Math.round(header.getBoundingClientRect().height);
        if (height > 0) {
          root.style.setProperty("--site-header-height", `${height}px`);
        }
      };

      const debouncedUpdate = airocupApp.helpers.debounce(setHeight, 160);
      window.addEventListener("resize", debouncedUpdate);
      window.addEventListener("orientationchange", debouncedUpdate);
      window.addEventListener("load", setHeight);

      if ("ResizeObserver" in window) {
        const resizeObserver = new ResizeObserver(() => setHeight());
        resizeObserver.observe(header);
      }

      setHeight();

      if (header.classList.contains("site-header")) {
        const toggleCondensed = () => {
          header.classList.toggle(
            "site-header--condensed",
            window.scrollY > 10
          );
        };

        window.addEventListener("scroll", toggleCondensed, { passive: true });
        toggleCondensed();
      }
    },

    createFlash(type = "info", message = "", duration = 5000) {
      const container = document.querySelector(
        airocupApp.constants.SELECTORS.FLASH_CONTAINER
      );
      if (!container) return;

      const iconMap = {
        success: "fa-check-circle",
        error: "fa-exclamation-triangle",
        warning: "fa-exclamation-circle",
        info: "fa-info-circle",
      };

      const flash = document.createElement("div");
      flash.className = `flash-message flash-${type}`;
      flash.setAttribute("role", "alert");
      flash.innerHTML = `
                <i class="fas ${
                  iconMap[type] || iconMap.info
                }" aria-hidden="true"></i>
                <span>${message}</span>
                <button class="flash-close-btn" data-action="dismiss-flash" aria-label="بستن اعلان">&times;</button>
            `;
      container.appendChild(flash);

      setTimeout(() => this.dismissFlash(flash), duration);
    },

    dismissFlash(flashElement) {
      if (
        !flashElement ||
        flashElement.classList.contains(
          airocupApp.constants.CLASSES.FLASH_MESSAGE_CLOSING
        )
      )
        return;
      flashElement.classList.add(
        airocupApp.constants.CLASSES.FLASH_MESSAGE_CLOSING
      );
      setTimeout(() => flashElement.remove(), 350);
    },

    initializeFlashMessages() {
      const container = document.querySelector(
        airocupApp.constants.SELECTORS.FLASH_CONTAINER
      );
      if (!container) return;

      container.addEventListener("click", (e) => {
        if (e.target.closest(airocupApp.constants.SELECTORS.CLOSE_FLASH_BTN)) {
          this.dismissFlash(
            e.target.closest(airocupApp.constants.SELECTORS.FLASH_MESSAGE)
          );
        }
      });

      document
        .querySelectorAll(airocupApp.constants.SELECTORS.FLASH_MESSAGE)
        .forEach((flash, i) => {
          setTimeout(() => this.dismissFlash(flash), 5000 + i * 150);
        });
    },

    trapFocus(modalElement) {
      const focusableElements = Array.from(
        modalElement.querySelectorAll(
          'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
      ).filter((el) => !el.disabled);

      if (!focusableElements.length) return () => {};

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      const keyHandler = (e) => {
        if (e.key !== "Tab") return;
        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      };

      modalElement.addEventListener("keydown", keyHandler);
      return () => modalElement.removeEventListener("keydown", keyHandler);
    },

    openModal(modalElement, triggerElement) {
      if (!modalElement) return;
      modalElement.classList.add(airocupApp.constants.CLASSES.IS_VISIBLE);
      modalElement.setAttribute(
        airocupApp.constants.ATTRIBUTES.ARIA_HIDDEN,
        "false"
      );
      modalElement._triggerElement = triggerElement || document.activeElement;
      modalElement.querySelector("button, a, input")?.focus();
      modalElement._releaseTrap = this.trapFocus(modalElement);
      document.body.classList.add(airocupApp.constants.CLASSES.BODY_NO_SCROLL);
    },

    closeModal(modalElement) {
      if (!modalElement) return;
      modalElement.classList.remove(airocupApp.constants.CLASSES.IS_VISIBLE);
      modalElement.setAttribute(
        airocupApp.constants.ATTRIBUTES.ARIA_HIDDEN,
        "true"
      );
      if (modalElement._releaseTrap) modalElement._releaseTrap();
      modalElement._triggerElement?.focus();
      document.body.classList.remove(
        airocupApp.constants.CLASSES.BODY_NO_SCROLL
      );
    },

    initializeModals() {
      document.body.addEventListener("click", (e) => {
        const trigger = e.target.closest(
          `[${airocupApp.constants.ATTRIBUTES.DATA_MODAL_TARGET}]`
        );
        if (trigger) {
          const modal = document.getElementById(trigger.dataset.modalTarget);
          if (modal) this.openModal(modal, trigger);
        }
        if (
          e.target.closest(
            `[${airocupApp.constants.ATTRIBUTES.DATA_DISMISS}="modal"]`
          )
        ) {
          const modal = e.target.closest(airocupApp.constants.SELECTORS.MODAL);
          if (modal) this.closeModal(modal);
        }
      });
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          document
            .querySelectorAll(
              `${airocupApp.constants.SELECTORS.MODAL}.${airocupApp.constants.CLASSES.IS_VISIBLE}`
            )
            .forEach(this.closeModal);
        }
      });
    },

    initializeCopyButtons() {
      document.body.addEventListener("click", (e) => {
        const copyBtn = e.target.closest(
          airocupApp.constants.SELECTORS.COPY_BTN
        );
        if (!copyBtn) return;

        const textToCopy = copyBtn.dataset.copy || "";
        airocupApp.helpers
          .safeClipboardWrite(textToCopy)
          .then(() => {
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i class="fas fa-check"></i> کپی شد';
            copyBtn.disabled = true;
            setTimeout(() => {
              copyBtn.innerHTML = originalHTML;
              copyBtn.disabled = false;
            }, 2000);
          })
          .catch((err) => {
            console.error("Copy failed:", err);
            this.createFlash("error", "خطا در کپی کردن.");
          });
      });
    },

    initializePasswordToggles() {
      document.body.addEventListener("click", (e) => {
        const toggleBtn = e.target.closest(
          airocupApp.constants.SELECTORS.PASSWORD_TOGGLE_BTN
        );
        if (!toggleBtn) return;

        const targetInput = document.querySelector(toggleBtn.dataset.target);
        if (!targetInput) return;

        const isPassword = targetInput.type === "password";
        targetInput.type = isPassword ? "text" : "password";
        const icon = toggleBtn.querySelector("i");
        if (icon) {
          icon.classList.toggle("fa-eye", !isPassword);
          icon.classList.toggle("fa-eye-slash", isPassword);
        }
      });
    },

    initializeLazyLoad() {
      const lazyElements = document.querySelectorAll(
        airocupApp.constants.SELECTORS.LAZY_ELEMENT
      );
      if (!lazyElements.length) return;

      if (!("IntersectionObserver" in window)) {
        lazyElements.forEach((el) => {
          if (el.tagName === "IFRAME") {
            el.src = el.dataset.src;
          }
          el.classList.add(airocupApp.constants.CLASSES.IS_VISIBLE);
        });
        return;
      }

      const observer = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const el = entry.target;
              if (el.tagName === "IFRAME") {
                el.src = el.dataset.src;
              }
              el.classList.add(airocupApp.constants.CLASSES.IS_VISIBLE);
              obs.unobserve(el);
            }
          });
        },
        {
          threshold: 0.1,
          rootMargin: "0px 0px -50px 0px",
        }
      );

      lazyElements.forEach((el) => observer.observe(el));
    },

    initializeVideoPlayer() {
      const videoWrapper = document.querySelector(
        airocupApp.constants.SELECTORS.VIDEO_WRAPPER_LAZY
      );
      if (!videoWrapper) return;

      videoWrapper.addEventListener(
        "click",
        () => {
          const iframe = document.createElement("iframe");
          iframe.setAttribute("src", `${videoWrapper.dataset.src}&autoplay=1`);
          iframe.setAttribute(
            "title",
            videoWrapper.dataset.title || "Video Player"
          );
          iframe.setAttribute(
            "allow",
            "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          );
          iframe.setAttribute("allowfullscreen", "");
          iframe.setAttribute("loading", "lazy");
          videoWrapper.innerHTML = "";
          videoWrapper.appendChild(iframe);
          videoWrapper.classList.remove("lazy-video");
        },
        {
          once: true,
        }
      );
    },
    initializeRelativeTime() {
      const timeElements = document.querySelectorAll(
        airocupApp.constants.SELECTORS.RELATIVE_TIME
      );
      if (!timeElements.length) return;

      const formatTime = (dateObject) => {
        if (!dateObject) return "";
        const now = new Date();
        const diffSeconds = Math.floor((now - dateObject) / 1000);

        if (diffSeconds < 5) return "همین الان";
        if (diffSeconds < 60) return `${diffSeconds} ثانیه پیش`;
        if (diffSeconds < 3600)
          return `${Math.floor(diffSeconds / 60)} دقیقه پیش`;
        if (diffSeconds < 86400)
          return `${Math.floor(diffSeconds / 3600)} ساعت پیش`;
        if (diffSeconds < 2592000)
          return `${Math.floor(diffSeconds / 86400)} روز پیش`;
        if (diffSeconds < 31536000)
          return `${Math.floor(diffSeconds / 2592000)} ماه پیش`;
        return `${Math.floor(diffSeconds / 31536000)} سال پیش`;
      };

      const updateAllTimes = () => {
        timeElements.forEach((element) => {
          const rawTimestamp = element.dataset.timestamp || "";
          const dateObject = airocupApp.helpers.parseTimestamp(rawTimestamp);
          if (dateObject) {
            element.textContent = formatTime(dateObject);
            element.title = dateObject.toLocaleString("fa-IR");
          }
        });
      };

      updateAllTimes();
      if (this._relativeTimeInterval) clearInterval(this._relativeTimeInterval);
      this._relativeTimeInterval = setInterval(updateAllTimes, 60000);
    },
    initializeSmoothScroll() {
      document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener("click", function (e) {
          const href = this.getAttribute("href");
          if (href === "#" || href === "") return;
          try {
            const targetElement = document.querySelector(href);
            if (targetElement) {
              e.preventDefault();
              targetElement.scrollIntoView({ behavior: "smooth" });
            }
          } catch (error) {
            console.warn(`Smooth scroll failed for selector "${href}":`, error);
          }
        });
      });
    },

    initializePosterZoom() {
      const triggers = document.querySelectorAll(
        airocupApp.constants.SELECTORS.POSTER_TRIGGER
      );
      const modal = document.querySelector(
        airocupApp.constants.SELECTORS.POSTER_MODAL
      );

      if (!modal || !triggers.length) {
        return;
      }

      const modalImage = modal.querySelector("img");
      const closeTargets = modal.querySelectorAll(
        airocupApp.constants.SELECTORS.POSTER_MODAL_CLOSE
      );
      const backdrop = modal.querySelector(".poster-modal__backdrop");

      const openModal = (posterSrc) => {
        if (posterSrc && modalImage) {
          modalImage.setAttribute("src", posterSrc);
        }
        modal.classList.add(airocupApp.constants.CLASSES.IS_VISIBLE);
        modal.setAttribute(
          airocupApp.constants.ATTRIBUTES.ARIA_HIDDEN,
          "false"
        );
        document.body.classList.add(
          airocupApp.constants.CLASSES.POSTER_MODAL_OPEN
        );
      };

      const closeModal = () => {
        modal.classList.remove(airocupApp.constants.CLASSES.IS_VISIBLE);
        modal.setAttribute(
          airocupApp.constants.ATTRIBUTES.ARIA_HIDDEN,
          "true"
        );
        document.body.classList.remove(
          airocupApp.constants.CLASSES.POSTER_MODAL_OPEN
        );
      };

      triggers.forEach((trigger) => {
        trigger.addEventListener("click", () => {
          const posterImage = trigger.querySelector("img");
          const source = posterImage?.getAttribute("src");
          openModal(source || modalImage?.getAttribute("src"));
        });
      });

      closeTargets.forEach((btn) => btn.addEventListener("click", closeModal));
      backdrop?.addEventListener("click", closeModal);

      document.addEventListener("keydown", (event) => {
        if (
          event.key === "Escape" &&
          modal.classList.contains(airocupApp.constants.CLASSES.IS_VISIBLE)
        ) {
          closeModal();
        }
      });
    },
  },
  formHelpers: {
    populateProvinces(selectElement) {
      if (!selectElement) return;
      const provinces = window.AirocupData?.provinces_data || {};
      const fragment = document.createDocumentFragment();
      fragment.appendChild(new Option("استان را انتخاب کنید", ""));
      Object.keys(provinces)
        .sort((a, b) => a.localeCompare(b, "fa"))
        .forEach((name) => fragment.appendChild(new Option(name, name)));
      selectElement.innerHTML = "";
      selectElement.appendChild(fragment);
    },

    updateCities(provinceName, citySelectElement) {
      if (!citySelectElement) return;
      const cities =
        (window.AirocupData?.provinces_data || {})[provinceName] || [];
      citySelectElement.innerHTML = "";
      citySelectElement.add(new Option("شهر را انتخاب کنید", ""));
      citySelectElement.disabled = !cities.length;
      cities.forEach((name) => citySelectElement.add(new Option(name, name)));
    },
    setupDatePicker(formElement) {
      if (!formElement) return;

      const daySelect = formElement.querySelector('[name="birth_day"]');
      const monthSelect = formElement.querySelector('[name="birth_month"]');
      const yearSelect = formElement.querySelector('[name="birth_year"]');

      if (!daySelect || !monthSelect || !yearSelect) return;
      if (monthSelect.options.length <= 1) {
        const months = window.AirocupData?.persian_months || {};
        for (const [num, name] of Object.entries(months)) {
          monthSelect.add(new Option(name, num));
        }
      }
      if (yearSelect.options.length <= 1) {
        const years = window.AirocupData?.allowed_years || [];
        years.forEach((year) => {
          const label = airocupApp.helpers.toPersianDigits(year);
          yearSelect.add(new Option(label, year));
        });
      }

      const isLeapYear = (year) => {
        const remainder = (year + 12) % 33;
        return [1, 5, 9, 13, 17, 22, 26, 30].includes(remainder);
      };

      const updateDays = () => {
        const selectedMonth = parseInt(monthSelect.value, 10);
        const selectedYear = parseInt(yearSelect.value, 10);
        let maxDays = 31;

        if (selectedMonth >= 7 && selectedMonth <= 11) {
          maxDays = 30;
        } else if (selectedMonth === 12) {
          maxDays = isLeapYear(selectedYear) ? 30 : 29;
        }

        const currentDay = daySelect.value;
        daySelect.innerHTML = "";
        daySelect.add(new Option("روز", ""));
        for (let day = 1; day <= maxDays; day++) {
          const label = airocupApp.helpers.toPersianDigits(day);
          daySelect.add(new Option(label, day));
        }

        if (currentDay && parseInt(currentDay, 10) <= maxDays) {
          daySelect.value = currentDay;
        }
      };

      yearSelect.addEventListener("change", updateDays);
      monthSelect.addEventListener("change", updateDays);
      updateDays();
    },

    initializeDynamicSelects(formElement) {
      if (!formElement) return;
      const provinceSelect = formElement.querySelector('[name="province"]');
      const citySelect = formElement.querySelector('[name="city"]');

      if (provinceSelect && citySelect) {
        this.populateProvinces(provinceSelect);
        provinceSelect.addEventListener("change", () => {
          this.updateCities(provinceSelect.value, citySelect);
        });

        if (provinceSelect.dataset.initialValue) {
          provinceSelect.value = provinceSelect.dataset.initialValue;
          this.updateCities(provinceSelect.value, citySelect);
          if (citySelect.dataset.initialValue) {
            citySelect.value = citySelect.dataset.initialValue;
          }
        }
      }
    },
  },

  forms: {
    init() {
      this.initializeDeleteConfirmation();
      this.initializeLegacyConfirmActions();
    },

    initializeDeleteConfirmation() {
      const modal = document.querySelector(
        airocupApp.constants.SELECTORS.CONFIRMATION_MODAL
      );
      const confirmBtn = modal?.querySelector(
        airocupApp.constants.SELECTORS.CONFIRM_MODAL_BTN
      );
      const titleEl = modal?.querySelector(
        airocupApp.constants.SELECTORS.MODAL_TITLE
      );
      const bodyEl = modal?.querySelector(
        airocupApp.constants.SELECTORS.MODAL_BODY
      );
      let formToSubmit = null;

      const getFallbackMessage = (deleteBtn) => {
        const rawMessage =
          deleteBtn.dataset.modalBody || "آیا از انجام این عملیات اطمینان دارید؟";
        const temp = document.createElement("div");
        temp.innerHTML = rawMessage;
        return temp.textContent?.trim() || temp.innerText?.trim() || rawMessage;
      };

      document.body.addEventListener("click", (event) => {
        const deleteBtn = event.target.closest(
          airocupApp.constants.SELECTORS.DELETE_BTN
        );
        if (!deleteBtn) return;

        const form = deleteBtn.closest("form");
        if (!form) return;

        event.preventDefault();

        if (!modal || !confirmBtn || !titleEl || !bodyEl) {
          const confirmationMessage = getFallbackMessage(deleteBtn);
          if (window.confirm(confirmationMessage)) {
            form.submit();
          }
          return;
        }

        formToSubmit = form;
        titleEl.textContent = deleteBtn.dataset.modalTitle || "تایید عملیات";
        bodyEl.innerHTML =
          deleteBtn.dataset.modalBody ||
          "آیا از انجام این عملیات اطمینان دارید؟";
        confirmBtn.textContent = deleteBtn.dataset.modalConfirmText || "تایید";
        confirmBtn.className = `btn ${
          deleteBtn.dataset.modalConfirmClass || "btn-danger"
        }`;

        airocupApp.ui.openModal(modal, deleteBtn);
      });

      if (confirmBtn) {
        confirmBtn.addEventListener("click", () => {
          if (formToSubmit) {
            formToSubmit.submit();
            formToSubmit = null;
            airocupApp.ui.closeModal(modal);
          }
        });
      }
    },
    initializeLegacyConfirmActions() {
      const forms = document.querySelectorAll("form.ConfirmAction");
      forms.forEach((form) => {
        if (form.dataset.confirmBound === "true") return;
        form.dataset.confirmBound = "true";
        form.addEventListener("submit", (event) => {
          const message =
            form.dataset.confirm || "آیا از انجام این عملیات اطمینان دارید؟";
          if (!window.confirm(message)) {
            event.preventDefault();
          }
        });
      });
    },
    initializePasswordConfirmation(form, passwordInput, confirmInput) {
      if (!form || !passwordInput || !confirmInput) return;

      const validateMatch = () => {
        const isMatch = passwordInput.value === confirmInput.value;
        confirmInput.classList.toggle(
          airocupApp.constants.CLASSES.INVALID,
          !isMatch && confirmInput.value.length > 0
        );
        return isMatch;
      };

      form.addEventListener("submit", (event) => {
        if (!validateMatch()) {
          event.preventDefault();
          airocupApp.ui.createFlash(
            "error",
            "رمز عبور و تکرار آن یکسان نیستند."
          );
        }
      });

      passwordInput.addEventListener("input", validateMatch);
      confirmInput.addEventListener("input", validateMatch);
    },

    validatePasswordStrength(passwordInput, validatorElement) {
      if (!passwordInput || !validatorElement) return false;

      const password = passwordInput.value;
      const validations = {
        length: password.length >= 8,
        upper: /[A-Z]/.test(password),
        lower: /[a-z]/.test(password),
        number: /[0-9]/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
      };

      let allValid = true;
      for (const [key, isValid] of Object.entries(validations)) {
        const el = validatorElement.querySelector(`#req-${key}`);
        if (el)
          el.className = isValid
            ? airocupApp.constants.CLASSES.VALID
            : airocupApp.constants.CLASSES.INVALID;
        if (!isValid) allValid = false;
      }
      return allValid;
    },

    validateIdentifierField(inputElement, errorElement) {
      if (!inputElement) return true;

      const rawValue = inputElement.value || "";
      const value = rawValue.trim();
      inputElement.value = value;

      let errorMessage = "";
      const isEmail = Validators.IsValidEmail(value);
      const isPhone = Validators.IsValidIranianPhone(value);

      if (!value) {
        errorMessage = "لطفا ایمیل یا شماره موبایل خود را وارد کنید.";
      } else if (!isEmail && !isPhone) {
        errorMessage = "لطفا یک ایمیل یا شماره موبایل معتبر وارد کنید.";
      }

      if (errorElement) errorElement.textContent = errorMessage;
      inputElement.classList.toggle(
        airocupApp.constants.CLASSES.INVALID,
        Boolean(errorMessage)
      );

      return !errorMessage;
    },

    initializeLoginForm(form) {
      if (!form) return;

      const identifierInput = form.querySelector('[name="identifier"]');
      const errorElement = form.querySelector("#identifier-error");

      if (!identifierInput) return;

      const validate = () =>
        this.validateIdentifierField(identifierInput, errorElement);

      identifierInput.addEventListener("input", () => {
        if (errorElement && errorElement.textContent) {
          validate();
        }
      });

      form.addEventListener("submit", (event) => {
        const isValid = validate();
        if (!isValid) {
          event.preventDefault();
          identifierInput.focus();
        }
      });
    },

    initializeForgotPasswordForm(form) {
      if (!form) return;

      const identifierInput = form.querySelector('[name="identifier"]');
      const errorElement = form.querySelector("#identifier-error");

      if (!identifierInput) return;

      const validate = () =>
        this.validateIdentifierField(identifierInput, errorElement);

      identifierInput.addEventListener("input", () => {
        if (errorElement && errorElement.textContent) {
          validate();
        }
      });

      form.addEventListener("submit", (event) => {
        const isValid = validate();
        if (!isValid) {
          event.preventDefault();
          identifierInput.focus();
        }
      });
    },
  },

  initializeChat(container) {
    const app = this;
    const { SELECTORS } = app.constants;

    const elements = {
      chatBox: container.querySelector(SELECTORS.CHAT_BOX),
      messageInput: container.querySelector(SELECTORS.MESSAGE_INPUT),
      sendButton: container.querySelector(SELECTORS.SEND_BUTTON),
    };

    if (!elements.chatBox || !elements.messageInput || !elements.sendButton) {
      console.error("Chat UI elements not found for", container);
      return;
    }

    const defaultPlaceholder =
      elements.messageInput.getAttribute("placeholder") || "";
    const offlinePlaceholder = "اتصال به سرور پشتیبانی برقرار نشد.";

    const state = {
      roomId: (container.dataset.clientId || "").trim(),
      historyUrl: (container.dataset.historyUrl || "").trim(),
      isClientView: container.matches(SELECTORS.CLIENT_CHAT_CONTAINER),
      socket: app.helpers.safeSocket(),
      renderedMessages: new Set(),
    };

    if (!state.roomId) {
      console.error("Chat Error: Missing client identifier");
      return;
    }

    if (!state.historyUrl) {
      state.historyUrl = state.isClientView
        ? "/get_my_chat_history"
        : `/Admin/GetChatHistory/${state.roomId}`;
    }

    const setComposerEnabled = (isEnabled) => {
      elements.messageInput.disabled = !isEnabled;
      elements.sendButton.disabled = !isEnabled;
      if (isEnabled) {
        elements.sendButton.removeAttribute("aria-disabled");
        elements.sendButton.removeAttribute("title");
        elements.messageInput.setAttribute("placeholder", defaultPlaceholder);
      } else {
        elements.sendButton.setAttribute("aria-disabled", "true");
        elements.sendButton.setAttribute("title", offlinePlaceholder);
        elements.messageInput.setAttribute("placeholder", offlinePlaceholder);
      }
      container.classList.toggle("chat-offline", !isEnabled);
    };

    setComposerEnabled(Boolean(state.socket));

    const renderStateMessage = (className, message) => {
      elements.chatBox.innerHTML = "";
      const messageElement = document.createElement("div");
      messageElement.className = className;
      messageElement.textContent = message;
      elements.chatBox.appendChild(messageElement);
    };

    const scrollToBottom = () => {
      elements.chatBox.scrollTop = elements.chatBox.scrollHeight;
    };

    const resolveTimestamp = (value) => {
      const parsedDate = app.helpers.parseTimestamp(value) || new Date();
      return {
        iso: parsedDate.toISOString(),
        display: app.helpers.toPersianDigits(
          parsedDate.toLocaleTimeString("fa-IR", {
            hour: "2-digit",
            minute: "2-digit",
          })
        ),
      };
    };

    const appendMessage = (message, { isLocal = false } = {}) => {
      const rawText = (message?.message_text ?? message?.message ?? "").trim();
      if (!rawText) return;

      const bubble = document.createElement("div");
      bubble.classList.add("chat-message");

      const isClientMessage = isLocal
        ? state.isClientView
        : (message?.sender || "").toLowerCase() === "client";

      bubble.classList.add(isClientMessage ? "is-client" : "is-admin");

      const senderLabel = isLocal
        ? state.isClientView
          ? "شما"
          : (message?.sender || "ادمین")
        : state.isClientView
        ? isClientMessage
        ? "شما"
        : "پشتیبانی"
        : isClientMessage
        ? "کاربر"
        : (message?.sender && message.sender.toLowerCase() !== "admin"
            ? message.sender
            : "ادمین");

      const { iso, display } = resolveTimestamp(message?.timestamp);
      const senderKey = (message?.sender || (isClientMessage ? "client" : "admin")).toLowerCase();
      const signature = `${rawText}|${senderKey}|${iso}`;

      if (state.renderedMessages.has(signature)) return;
      state.renderedMessages.add(signature);

      const senderElement = document.createElement("span");
      senderElement.className = "chat-message--sender";
      senderElement.textContent = senderLabel;

      const textElement = document.createElement("p");
      textElement.className = "chat-message--text";
      textElement.textContent = rawText;
      textElement.dir = "auto";

      const metaElement = document.createElement("span");
      metaElement.className = "chat-message--meta";
      metaElement.dataset.timestamp = iso;
      metaElement.textContent = display;

      bubble.append(senderElement, textElement, metaElement);
      elements.chatBox.appendChild(bubble);
    };

    const sendMessage = () => {
      if (elements.sendButton.disabled) return;

      const messageText = elements.messageInput.value.trim();
      if (!messageText) return;

      if (!state.socket) {
        setComposerEnabled(false);
        return;
      }

      const sender = state.isClientView
        ? "client"
        : container.querySelector("#personaSelect")?.value || "Admin";

      state.socket.emit("send_message", {
        room: state.roomId,
        message: messageText,
        sender,
      });

      appendMessage(
        {
          message_text: messageText,
          timestamp: new Date().toISOString(),
          sender,
        },
        { isLocal: true }
      );

      elements.messageInput.value = "";
      elements.messageInput.focus();
      scrollToBottom();
      app.ui.initializeRelativeTime();
    };

    elements.sendButton.addEventListener("click", sendMessage);
    elements.messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });

    if (state.socket) {
      state.socket.on("connect", () => {
        setComposerEnabled(true);
        state.socket.emit("join", { room: state.roomId });
      });

      state.socket.on("disconnect", () => {
        setComposerEnabled(false);
      });

      state.socket.on("new_message", (payload) => {
        appendMessage(payload);
        scrollToBottom();
        app.ui.initializeRelativeTime();
      });
    }

    app.helpers
      .fetchJSON(state.historyUrl)
      .then((data) => {
        elements.chatBox.innerHTML = "";
        const messages = Array.isArray(data?.messages) ? data.messages : [];

        if (!messages.length) {
          renderStateMessage(
            "chat-empty-state",
            "هنوز پیامی وجود ندارد."
          );
          return;
        }

        messages.forEach((message) => appendMessage(message));
        scrollToBottom();
        app.ui.initializeRelativeTime();
      })
      .catch((error) => {
        console.error("Failed to load chat history:", error);
        renderStateMessage(
          "chat-error-state",
          "خطا در بارگذاری تاریخچه گفتگو."
        );
      });
  },

  client: {
    init() {
      this.initializeMobileMenu();
      this.initializeAccordion();
      this.initializeGallery();
      this.initializeLeagueFilter();

      const signUpForm = document.querySelector(
        airocupApp.constants.SELECTORS.SIGN_UP_FORM
      );
      if (signUpForm) this.initializeSignUpForm(signUpForm);

      const loginForm = document.querySelector(
        airocupApp.constants.SELECTORS.LOGIN_FORM
      );
      if (loginForm) airocupApp.forms.initializeLoginForm(loginForm);

      const forgotPasswordForm = document.querySelector(
        airocupApp.constants.SELECTORS.FORGOT_PASSWORD_FORM
      );
      if (forgotPasswordForm)
        airocupApp.forms.initializeForgotPasswordForm(forgotPasswordForm);

      const chatContainer = document.querySelector(
        airocupApp.constants.SELECTORS.CLIENT_CHAT_CONTAINER
      );
      if (chatContainer) airocupApp.initializeChat(chatContainer);
      this.initializeResetForm();
      this.initializeMembersPage();
      this.initializeLeagueSelector();
      this.initializeFileUploadValidation();
      this.initializePaymentPage();
    },

    initializeMobileMenu() {
      const menuBtn = document.getElementById("mobile-menu-btn");
      const mobileMenu = document.getElementById("mobile-menu");
      const mobileNavList = document.getElementById("mobile-nav-list");
      const backdrop = document.getElementById("mobile-menu-backdrop");
      const navList = document.getElementById("nav-list");
      const footer = document.querySelector(".site-footer");

      if (!menuBtn || !mobileMenu || !navList) return;

      function toggleMenu(forceOpen = null) {
        const isOpen =
          forceOpen !== null
            ? forceOpen
            : !mobileMenu.classList.contains("is-open");

        mobileMenu.classList.toggle("is-open", isOpen);
        backdrop?.classList.toggle("is-visible", isOpen);
        document.body.classList.toggle("body-no-scroll", isOpen);
        menuBtn.classList.toggle("is-active", isOpen);

        // Footer moves up when menu opens
        if (footer)
          footer.style.marginBottom = isOpen
            ? `${mobileMenu.scrollHeight}px`
            : "";

        mobileMenu.setAttribute("aria-hidden", !isOpen);
        menuBtn.setAttribute("aria-expanded", isOpen);
      }

      menuBtn.addEventListener("click", () => toggleMenu());
      backdrop?.addEventListener("click", () => toggleMenu(false));

      mobileNavList?.addEventListener("click", (event) => {
        const link = event.target.closest("a");
        if (link) toggleMenu(false);
      });

      // Move overflow items to mobile menu
      function updateMenuOverflow() {
        if (window.innerWidth < 992) {
          mobileNavList.innerHTML = "";
          navList.querySelectorAll("li").forEach((li) => {
            mobileNavList.appendChild(li.cloneNode(true));
          });
        } else {
          mobileNavList.innerHTML = "";
        }
      }

      window.addEventListener(
        "resize",
        airocupApp.helpers.debounce(updateMenuOverflow, 300)
      );
      updateMenuOverflow();
    },

    initializeAccordion() {
      const container = document.querySelector(
        airocupApp.constants.SELECTORS.ACCORDION_CONTAINER
      );
      if (!container) return;

      container.addEventListener("click", (e) => {
        const button = e.target.closest(
          airocupApp.constants.SELECTORS.ACCORDION_BUTTON
        );
        if (!button) return;

        const isExpanded = button.getAttribute("aria-expanded") === "true";

        container
          .querySelectorAll(airocupApp.constants.SELECTORS.ACCORDION_BUTTON)
          .forEach((btn) => {
            if (btn !== button) {
              btn.setAttribute("aria-expanded", "false");
              const otherContent = document.getElementById(
                btn.getAttribute("aria-controls")
              );
              if (otherContent) otherContent.style.maxHeight = null;
            }
          });

        button.setAttribute("aria-expanded", String(!isExpanded));
        const content = document.getElementById(
          button.getAttribute("aria-controls")
        );
        if (content) {
          content.style.maxHeight = isExpanded
            ? null
            : `${content.scrollHeight}px`;
        }
      });
    },

    initializeGallery() {
      const modal = document.querySelector(
        airocupApp.constants.SELECTORS.IMAGE_MODAL
      );
      if (!modal) return;

      const modalImage = modal.querySelector(
        airocupApp.constants.SELECTORS.MODAL_IMAGE
      );
      const gallery = document.querySelector(
        airocupApp.constants.SELECTORS.GALLERY_GRID
      );
      if (!gallery || !modalImage) return;

      gallery.addEventListener("click", (e) => {
        const img = e.target.closest(
          airocupApp.constants.SELECTORS.GALLERY_ITEM_IMG
        );
        if (img) {
          modalImage.src = img.src;
          airocupApp.ui.openModal(modal, img);
        }
      });
    },

    initializeSignUpForm(form) {
      const passwordInput = form.querySelector(
        airocupApp.constants.SELECTORS.PASSWORD_INPUT
      );
      const confirmInput = form.querySelector(
        airocupApp.constants.SELECTORS.CONFIRM_PASSWORD_INPUT
      );
      const validatorElement = form.querySelector(
        airocupApp.constants.SELECTORS.PASSWORD_STRENGTH_VALIDATOR
      );

      if (!passwordInput || !confirmInput || !validatorElement) return;

      passwordInput.addEventListener("input", () => {
        airocupApp.forms.validatePasswordStrength(
          passwordInput,
          validatorElement
        );
      });

      form.addEventListener("submit", (e) => {
        const isStrengthValid = airocupApp.forms.validatePasswordStrength(
          passwordInput,
          validatorElement
        );
        const isMatch = passwordInput.value === confirmInput.value;

        if (!isMatch) {
          confirmInput.classList.add(airocupApp.constants.CLASSES.INVALID);
        } else {
          confirmInput.classList.remove(airocupApp.constants.CLASSES.INVALID);
        }

        if (!isStrengthValid || !isMatch) {
          e.preventDefault();
          airocupApp.ui.createFlash(
            "error",
            "لطفا تمام موارد مربوط به رمز عبور را به درستی وارد کنید."
          );
        }
      });
    },

    initializeLeagueFilter() {
      const filterInput = document.querySelector(
        airocupApp.constants.SELECTORS.LEAGUE_FILTER_INPUT
      );
      const container = document.querySelector(
        airocupApp.constants.SELECTORS.ACCORDION_CONTAINER
      );
      if (!filterInput || !container) return;

      const noResultsMessage = container.querySelector(
        airocupApp.constants.SELECTORS.NO_RESULTS_MESSAGE
      );
      const allItems = Array.from(
        container.querySelectorAll(
          airocupApp.constants.SELECTORS.ACCORDION_ITEM
        )
      );

      filterInput.addEventListener(
        "input",
        airocupApp.helpers.debounce((e) => {
          const searchTerm = e.target.value.toLowerCase().trim();
          let visibleCount = 0;

          allItems.forEach((item) => {
            const isMatch = item.textContent.toLowerCase().includes(searchTerm);
            item.style.display = isMatch ? "" : "none";
            if (isMatch) visibleCount++;
          });

          if (noResultsMessage) {
            noResultsMessage.style.display = visibleCount === 0 ? "" : "none";
          }
        })
      );
    },

    initializeMembersPage() {
      const page = document.querySelector(".members-page");
      if (!page) return;

      const addForm = page.querySelector("#addMemberForm");
      if (addForm) {
        airocupApp.formHelpers.initializeDynamicSelects(addForm);
        airocupApp.formHelpers.setupDatePicker(addForm);
      }

      const editModal = document.querySelector("#editMemberModal");
      const editForm = editModal?.querySelector("form");
      if (!editModal || !editForm) return;

      airocupApp.formHelpers.initializeDynamicSelects(editForm);

      page.addEventListener("click", (e) => {
        const editBtn = e.target.closest(
          '[data-modal-target="editMemberModal"]'
        );
        if (!editBtn) return;

        const data = editBtn.dataset;
        editForm.action = `/Team/${data.teamId}/EditMember/${data.memberId}`;

        Object.keys(data).forEach((key) => {
          const input = editForm.querySelector(`[name="${key}"]`);
          if (input) {
            if (key === "province" || key === "city") {
              input.dataset.initialValue = data[key];
            } else {
              input.value = data[key];
            }
          }
        });

        airocupApp.formHelpers.initializeDynamicSelects(editForm);

        airocupApp.ui.openModal(editModal, editBtn);
      });
    },

    initializeLeagueSelector() {
      const form = document.querySelector("#selectLeagueForm");
      if (!form) return;

      const leagueOne = form.querySelector('[name="league_one"]');
      const leagueTwo = form.querySelector('[name="league_two"]');

      const syncOptions = () => {
        Array.from(leagueTwo.options).forEach(
          (opt) => (opt.disabled = opt.value && opt.value === leagueOne.value)
        );
        Array.from(leagueOne.options).forEach(
          (opt) => (opt.disabled = opt.value && opt.value === leagueTwo.value)
        );
      };

      leagueOne.addEventListener("change", syncOptions);
      leagueTwo.addEventListener("change", syncOptions);
      syncOptions();
    },

    initializeFileUploadValidation() {
      const form = document.querySelector("#documentUploadForm");
      if (!form) return;

      const fileInput = form.querySelector('input[type="file"]');
      fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (!file) return;

        const maxSizeMB = parseInt(fileInput.dataset.maxSizeMb) || 100;
        if (file.size > maxSizeMB * 1024 * 1024) {
          airocupApp.ui.createFlash(
            "error",
            `حجم فایل نباید بیشتر از ${maxSizeMB} مگابایت باشد.`
          );
          fileInput.value = "";
        }
      });
    },

    initializePaymentPage() {
      const form = document.querySelector("#teamPaymentForm");
      if (!form) return;

      const fileInput = form.querySelector('input[type="file"][name="receipt"]');
      const fileNameDisplay = document.getElementById("filename");
      const submitButton = form.querySelector('button[type="submit"]');
      const loadingText = submitButton?.dataset.loadingText || "در حال ارسال...";

      if (fileInput && fileNameDisplay) {
        fileInput.addEventListener("change", () => {
          const file = fileInput.files[0];
          fileNameDisplay.textContent = file ? file.name : "هیچ فایلی انتخاب نشده";
          fileNameDisplay.classList.toggle("file-name-display--active", Boolean(file));
        });
      }

      form.addEventListener("submit", (event) => {
        if (form.dataset.submitting === "true") {
          event.preventDefault();
          return;
        }
        form.dataset.submitting = "true";

        if (submitButton) {
          submitButton.dataset.originalText = submitButton.innerHTML;
          submitButton.textContent = loadingText;
          submitButton.classList.add("btn--loading");
          submitButton.disabled = true;
        }
      });
    },

    initializeResetForm() {
      const form = document.querySelector("#resetPasswordForm");
      if (!form) return;

      const passwordInput = form.querySelector('input[name="new_password"]');
      const confirmInput = form.querySelector('input[name="confirm_password"]');
      const validatorElement = form.querySelector(
        airocupApp.constants.SELECTORS.PASSWORD_STRENGTH_VALIDATOR
      );

      airocupApp.forms.initializePasswordConfirmation(
        form,
        passwordInput,
        confirmInput
      );

      if (passwordInput && validatorElement) {
        passwordInput.addEventListener("input", () =>
          airocupApp.forms.validatePasswordStrength(
            passwordInput,
            validatorElement
          )
        );

        form.addEventListener("submit", (event) => {
          const isStrong = airocupApp.forms.validatePasswordStrength(
            passwordInput,
            validatorElement
          );
          if (!isStrong) {
            event.preventDefault();
            airocupApp.ui.createFlash(
              "error",
              "لطفا الزامات رمز عبور را رعایت کنید."
            );
            passwordInput.focus();
          }
        });
      }
    },


  },

  admin: {
    init() {
      this.initializeMenu();

      if (
        document.querySelector(airocupApp.constants.SELECTORS.PROVINCE_CHART)
      ) {
        this.initializeDashboardCharts();
      }

      if (
        document.querySelector(
          airocupApp.constants.SELECTORS.CLIENT_SEARCH_INPUT
        )
      ) {
        this.initializeClientSearch();
      }

      const chatContainer = document.querySelector(
        airocupApp.constants.SELECTORS.ADMIN_CHAT_CONTAINER
      );
      if (chatContainer) {
        airocupApp.initializeChat(chatContainer);
      }

      this.initializeAdminMembersPage();
    },

    initializeMenu() {
      const toggleButton = document.querySelector(
        airocupApp.constants.SELECTORS.ADMIN_HEADER_MOBILE_TOGGLE
      );
      const navigation = document.querySelector(
        airocupApp.constants.SELECTORS.ADMIN_HEADER_NAV
      );
      if (!toggleButton || !navigation) return;

      const updateState = (isOpen) => {
        navigation.classList.toggle(
          airocupApp.constants.CLASSES.IS_OPEN,
          isOpen
        );
        toggleButton.setAttribute("aria-expanded", String(isOpen));
        const icon = toggleButton.querySelector("i");
        if (icon) {
          icon.className = isOpen ? "fas fa-times" : "fas fa-bars";
        }
      };

      toggleButton.addEventListener("click", () => {
        const shouldOpen = !navigation.classList.contains(
          airocupApp.constants.CLASSES.IS_OPEN
        );
        updateState(shouldOpen);
      });

      navigation.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => updateState(false));
      });

      window.addEventListener("resize", () => {
        if (window.innerWidth > 1100) {
          updateState(false);
        }
      });
    },

    initializeAdminMembersPage() {
      const page = document.querySelector(".admin-edit-team-page");
      if (!page) return;

      const teamId = page.dataset.teamId;
      const addForm = page.querySelector("#adminAddMemberForm");
      if (addForm) {
        airocupApp.formHelpers.initializeDynamicSelects(addForm);
        airocupApp.formHelpers.setupDatePicker(addForm);
      }

      const editModal = document.querySelector("#editMemberModal");
      const editForm = editModal?.querySelector("form");
      if (!editModal || !editForm) return;

      const assignValue = (name, value) => {
        if (!name) return;
        const field = editForm.querySelector(`[name="${name}"]`);
        if (!field) return;

        if (name === "province" || name === "city") {
          field.dataset.initialValue = value;
        } else {
          field.value = value;
        }
      };

      airocupApp.formHelpers.initializeDynamicSelects(editForm);
      airocupApp.formHelpers.setupDatePicker(editForm);

      page.addEventListener("click", (e) => {
        const editBtn = e.target.closest(
          '[data-modal-target="editMemberModal"]'
        );
        if (!editBtn) return;

        const data = editBtn.dataset;
        if (teamId && data.memberId) {
          editForm.action = `/Admin/Team/${teamId}/EditMember/${data.memberId}`;
        }

        assignValue("name", data.name || "");
        assignValue("national_id", data.nationalId || "");
        assignValue("role", data.role || "");
        assignValue("province", data.province || "");
        assignValue("city", data.city || "");

        const [year, month, day] = (data.birthDate || "0-0-0").split("-");
        assignValue("birth_year", year);
        assignValue("birth_month", month);
        assignValue("birth_day", day);

        airocupApp.formHelpers.initializeDynamicSelects(editForm);
        airocupApp.formHelpers.setupDatePicker(editForm);

        airocupApp.ui.openModal(editModal, editBtn);
      });
    },

    async initializeDashboardCharts() {
      const provinceCanvas = document.querySelector(
        airocupApp.constants.SELECTORS.PROVINCE_CHART
      );
      const cityCanvas = document.querySelector(
        airocupApp.constants.SELECTORS.CITY_CHART
      );

      const createChart = (canvas, chartData, type, label, indexAxis = "x") => {
        if (!canvas) return;
        const colors = [
          "#3182ce",
          "#2b6cb0",
          "#2c7a7b",
          "#2d3748",
          "#805ad5",
          "#b7791f",
        ];
        new Chart(canvas.getContext("2d"), {
          type,
          data: {
            labels: chartData.labels,
            datasets: [
              { label, data: chartData.data, backgroundColor: colors },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis,
            plugins: { legend: { display: type !== "bar" } },
          },
        });
      };

      try {
        if (provinceCanvas) {
          const endpoint =
            provinceCanvas.dataset.endpoint ||
            "/API/admin/ProvinceDistribution";
          const data = await airocupApp.helpers.fetchJSON(endpoint);
          createChart(provinceCanvas, data, "doughnut", "توزیع استانی");
        }
        if (cityCanvas) {
          const endpoint =
            cityCanvas.dataset.endpoint || "/API/AdminCityDistribution";
          const data = await airocupApp.helpers.fetchJSON(endpoint);
          createChart(cityCanvas, data, "bar", "تعداد شرکت‌کنندگان", "y");
        }
      } catch (error) {
        console.error("Failed to load chart data:", error);
        airocupApp.ui.createFlash("error", "خطا در بارگذاری داده‌های نمودار.");
      }
    },

    initializeClientSearch() {
      const searchInput = document.querySelector(
        airocupApp.constants.SELECTORS.CLIENT_SEARCH_INPUT
      );
      const tableBody = document.querySelector(
        airocupApp.constants.SELECTORS.CLIENTS_TABLE_BODY
      );
      if (!searchInput || !tableBody) return;

      const tableRows = Array.from(tableBody.querySelectorAll("tr"));
      const noResultsMessage = document.querySelector(
        airocupApp.constants.SELECTORS.NO_RESULTS_MESSAGE
      );

      searchInput.addEventListener(
        "input",
        airocupApp.helpers.debounce((e) => {
          const searchTerm = e.target.value.toLowerCase().trim();
          let visibleCount = 0;
          tableRows.forEach((row) => {
            const isMatch = row.textContent.toLowerCase().includes(searchTerm);
            row.style.display = isMatch ? "" : "none";
            if (isMatch) visibleCount++;
          });
          if (noResultsMessage) {
            noResultsMessage.style.display =
              visibleCount === 0 ? "table-row" : "none";
          }
        })
      );
    },

    // This function should be placed inside the main airocupApp object,
    // alongside helpers, ui, and forms.


  },

  init() {
    this.ui.init();
    this.forms.init();

    if (
      document.body.classList.contains(
        this.constants.SELECTORS.ADMIN_BODY.substring(1)
      )
    ) {
      this.admin.init();
    } else {
      this.client.init();
    }
  },
};

// Expose the main application object for inline scripts that rely on it.
window.airocupApp = airocupApp;

document.addEventListener("DOMContentLoaded", () => {
  try {
    airocupApp.init();
  } catch (error) {
    console.error("Failed to initialize Airocup app:", error);
  }
});
