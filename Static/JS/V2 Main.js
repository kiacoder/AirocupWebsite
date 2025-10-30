"use strict";
const Helpers = {
  debounce(fn, wait = 150) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), wait);
    };
  },

  safeClipboardWrite(text) {
    if (navigator.clipboard?.writeText)
      return navigator.clipboard.writeText(text);
    return new Promise((resolve, reject) => {
      try {
        const ta = document.createElement("textarea");
        ta.value = String(text || "");
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
        resolve();
      } catch (e) {
        reject(e);
      }
    });
  },

  safeSocket() {
    if (typeof io === "undefined") return null;
    try {
      return io();
    } catch (e) {
      console.warn("اتصال سوکت برقرار نشد:", e);
      return null;
    }
  },

  parseTimestamp(ts) {
    if (!ts) return null;
    const raw = String(ts);
    const iso = raw.replace(" ", "T").replace(/\//g, "-");
    const d1 = new Date(iso);
    if (!isNaN(d1)) return d1;
    const m = raw.match(
      /^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})(?:[ T](\d{1,2}):(\d{1,2}))?/
    );
    if (m) {
      const y = +m[1],
        mo = +m[2] - 1,
        day = +m[3],
        hh = +(m[4] || 0),
        mm = +(m[5] || 0);
      const d2 = new Date(y, mo, day, hh, mm);
      if (!isNaN(d2)) return d2;
    }
    const d3 = new Date(Date.parse(raw));
    if (!isNaN(d3)) return d3;
    return null;
  },
};
const Utils = {
  ShowNotification: function (Message, Options = {}) {
    CreateFlash(Options.Type || "Info", String(Message || ""), Options);
  },
};

function CreateFlash(Type, Message, Options = {}) {
  const NormalizedType =
    typeof Type === "string" && Type
      ? Type.charAt(0).toUpperCase() + Type.slice(1)
      : "Info";
  let Container = document.getElementById("FlashContainer");
  if (!Container) {
    Container = document.createElement("div");
    Container.id = "FlashContainer";
    Container.setAttribute("aria-live", "polite");
    Container.setAttribute("aria-atomic", "true");
    document.body.appendChild(Container);
    InitializeFlashSystem();
  }
  const Item = document.createElement("div");
  Item.className = `FlashMessage Flash${NormalizedType}`;
  Item.setAttribute("role", "alert");
  const Icon = document.createElement("i");
  const IconMap = {
    Success: "fa-check-circle",
    Error: "fa-exclamation-triangle",
    Warning: "fa-exclamation-circle",
    Info: "fa-info-circle",
  };
  Icon.className = `fas ${IconMap[NormalizedType] || IconMap.Info}`;
  Icon.setAttribute("aria-hidden", "true");
  const Text = document.createElement("span");
  Text.textContent = Message || "";
  const Btn = document.createElement("button");
  Btn.className = "FlashCloseBtn";
  Btn.dataset.action = "dismiss-flash";
  Btn.setAttribute("aria-label", "بستن اعلان");
  Btn.innerHTML = "&times;";
  Item.appendChild(Icon);
  Item.appendChild(Text);
  Item.appendChild(Btn);
  Container.appendChild(Item);
  const Duration = Options.Duration || 5000;
  setTimeout(() => {
    DismissFlash(Item);
  }, Duration);
  return Item;
}

function DismissFlash(FlashElement) {
  if (!FlashElement) return;
  if (FlashElement.classList.contains("FlashMessageClosing")) return;
  FlashElement.classList.add("FlashMessageClosing");
  const Duration = 350;
  setTimeout(() => {
    if (FlashElement.parentNode) FlashElement.remove();
  }, Duration);
}

function InitializeFlashSystem() {
  const Container = document.getElementById("FlashContainer");
  if (!Container) return;
  if (Container._flashInit) return;
  Container._flashInit = true;

  Container.addEventListener("click", function (e) {
    const Target = e.target;
    if (Target && Target.dataset && Target.dataset.action === "dismiss-flash") {
      const Flash = Target.closest(".FlashMessage");
      DismissFlash(Flash);
    }
  });
  Array.from(Container.querySelectorAll(".FlashMessage")).forEach((el, idx) => {
    setTimeout(() => DismissFlash(el), 5000 + idx * 120);
  });
}

const Validators = {
  IsValidIranianPhone: function (PhoneNumber) {
    if (!PhoneNumber) return false;
    const StringValue = String(PhoneNumber).replace(/\s+/g, "");
    return /^(?:\+98|0)?9\d{9}$/.test(StringValue);
  },
  IsValidNationalID: function (NationalID) {
    if (!NationalID) return false;
    const StringValue = String(NationalID).trim();
    if (!/^\d{10}$/.test(StringValue)) return false;
    if (new Set(StringValue).size === 1) return false;
    const CheckDigit = parseInt(StringValue[9], 10);
    let SumValue = 0;
    for (let Index = 0; Index < 9; Index++) {
      SumValue += parseInt(StringValue[Index], 10) * (10 - Index);
    }
    const RemainderValue = SumValue % 11;
    return RemainderValue < 2
      ? CheckDigit === RemainderValue
      : CheckDigit === 11 - RemainderValue;
  },
  IsValidTeamName: function (TeamName) {
    if (!TeamName)
      return { IsOK: false, Message: "نام تیم نمی‌تواند خالی باشد." };
    const Length = TeamName.trim().length;
    if (Length < 3 || Length > 30)
      return { IsOK: false, Message: "نام تیم باید بین ۳ تا ۳۰ کاراکتر باشد." };
    if (!/^[A-Za-z\u0600-\u06FF0-9_ ]+$/.test(TeamName)) {
      return {
        IsOK: false,
        Message: "نام تیم فقط می‌تواند شامل حروف، اعداد، فاصله و خط زیر باشد.",
      };
    }
    const ForbiddenWords = window.AirocupData?.ForbiddenWords || [];
    const LowercaseName = TeamName.toLowerCase();
    for (let Word of ForbiddenWords) {
      if (LowercaseName.includes(String(Word).toLowerCase()))
        return { IsOK: false, Message: "نام تیم حاوی کلمات غیرمجاز است." };
    }
    return { IsOK: true };
  },
  IsValidEmail: function (Email) {
    if (!Email) return false;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(Email).toLowerCase());
  },
};

const ModalHelpers = {
  TrapFocus: function (ModalElement) {
    if (!ModalElement) return;
    const FocusableList = Array.from(
      ModalElement.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    );
    if (!FocusableList.length) return;
    const FirstElement = FocusableList[0];
    const LastElement = FocusableList[FocusableList.length - 1];
    const KeyHandler = (KeyboardEvent) => {
      if (KeyboardEvent.key !== "Tab") return;
      if (KeyboardEvent.shiftKey && document.activeElement === FirstElement) {
        KeyboardEvent.preventDefault();
        LastElement.focus();
      } else if (
        !KeyboardEvent.shiftKey &&
        document.activeElement === LastElement
      ) {
        KeyboardEvent.preventDefault();
        FirstElement.focus();
      }
    };
    ModalElement.addEventListener("keydown", KeyHandler);
    return () => ModalElement.removeEventListener("keydown", KeyHandler);
  },
  OpenModal: function (ModalElement, TriggerElement) {
    if (!ModalElement) return;
    ModalElement.classList.add("IsVisible");
    ModalElement.setAttribute("aria-hidden", "false");
    ModalElement._TriggerElement = TriggerElement || document.activeElement;
    ModalElement.querySelector("button, a, input")?.focus();
    if (ModalElement._ReleaseTrap) {
      ModalElement._ReleaseTrap();
    }
    ModalElement._ReleaseTrap = this.TrapFocus(ModalElement);
    document.body.classList.add("BodyNoScroll");
  },

  CloseModal: function (ModalElement) {
    if (!ModalElement) return;
    ModalElement.classList.remove("IsVisible");
    ModalElement.setAttribute("aria-hidden", "true");
    if (ModalElement._ReleaseTrap) ModalElement._ReleaseTrap();
    ModalElement._TriggerElement?.focus();
    document.body.classList.remove("BodyNoScroll");
  },
};

const FormHelpers = {
  Initialize: function () {
    if (this._initialized) return;
    this._initialized = true;
    this.AirocupData = window.AirocupData || {};
    this.DaysInMonth = this.AirocupData.DaysInMonth || {};
    this.Provinces = this.AirocupData.Provinces || {};
    this.AllowedYears = this.AirocupData.AllowedYears || [];
    this.PersianMonths = this.AirocupData.PersianMonths || {};
    this.AllowedExtensions = this.AirocupData.AllowedExtensions || [
      "png",
      "jpg",
      "jpeg",
      "gif",
      "pdf",
      "docx",
    ];
  },
  PopulateProvinces: function (SelectElement) {
    if (!SelectElement) return;
    const FragmentElement = document.createDocumentFragment();
    FragmentElement.appendChild(new Option("استان را انتخاب کنید", ""));
    Object.keys(this.Provinces || {})
      .sort((A, B) => A.localeCompare(B, "fa"))
      .forEach((ProvinceName) =>
        FragmentElement.appendChild(new Option(ProvinceName, ProvinceName))
      );
    SelectElement.innerHTML = "";
    SelectElement.appendChild(FragmentElement);
  },
  UpdateCities: function (ProvinceName, CitySelectElement) {
    if (!CitySelectElement) return;
    CitySelectElement.innerHTML = "";
    CitySelectElement.add(new Option("شهر را انتخاب کنید", ""));
    CitySelectElement.disabled = true;
    if (!ProvinceName || !this.Provinces[ProvinceName]) return;
    this.Provinces[ProvinceName].forEach((CityName) =>
      CitySelectElement.add(new Option(CityName, CityName))
    );
    CitySelectElement.disabled = false;
  },
  SetupProvinceCityListener: function (FormElement) {
    if (!FormElement) return;
    const ProvinceSelectElement =
      FormElement.querySelector('[name="Province"]');
    const CitySelectElement = FormElement.querySelector('[name="City"]');
    if (!ProvinceSelectElement || !CitySelectElement) return;
    ProvinceSelectElement.addEventListener("change", () =>
      this.UpdateCities(ProvinceSelectElement.value, CitySelectElement)
    );
    if (ProvinceSelectElement.value) {
      this.UpdateCities(ProvinceSelectElement.value, CitySelectElement);
      CitySelectElement.value =
        CitySelectElement.getAttribute("data-initial-city") || "";
    }
  },
  SetupDatePicker: function (FormElement) {
    if (!FormElement) return;
    const DayElement = FormElement.querySelector('[name="BirthDay"]');
    const MonthElement = FormElement.querySelector('[name="BirthMonth"]');
    const YearElement = FormElement.querySelector('[name="BirthYear"]');
    if (!DayElement || !MonthElement || !YearElement) return;
    MonthElement.innerHTML = "";
    MonthElement.add(new Option("ماه", ""));
    for (const [MonthNumber, MonthName] of Object.entries(this.PersianMonths)) {
      MonthElement.add(new Option(MonthName, MonthNumber));
    }
    YearElement.innerHTML = "";
    YearElement.add(new Option("سال", ""));
    this.AllowedYears.forEach((Year) =>
      YearElement.add(new Option(Year, Year))
    );
    const IsLeapYearFunction = (Year) => {
      const remainder = (Year + 12) % 33;
      return [1, 5, 9, 13, 17, 22, 26, 30].includes(remainder);
    };

    const UpdateDaysFunction = () => {
      const MonthValue = parseInt(MonthElement.value, 10);
      const YearValue = parseInt(YearElement.value, 10);
      let MaxDays = MonthValue ? this.DaysInMonth[MonthValue] || 31 : 31;
      if (MonthValue === 12 && YearValue && IsLeapYearFunction(YearValue))
        MaxDays = 30;
      const CurrentDayValue = DayElement.value;
      DayElement.innerHTML = "";
      DayElement.add(new Option("روز", ""));
      for (let DayIndex = 1; DayIndex <= MaxDays; DayIndex++)
        DayElement.add(new Option(DayIndex, DayIndex));
      if (CurrentDayValue && parseInt(CurrentDayValue, 10) <= MaxDays)
        DayElement.value = CurrentDayValue;
    };
    YearElement.addEventListener("input", UpdateDaysFunction);
    MonthElement.addEventListener("change", UpdateDaysFunction);
    UpdateDaysFunction();
  },
};

const UI = {
  InitializeMobileMenu: function () {
    const ButtonElement = document.querySelector(".MobileMenuBtn");
    const NavElement = document.querySelector(".NavItems");
    if (!ButtonElement || !NavElement) return;
    const ToggleFunction = (ShouldShow) => {
      NavElement.classList.toggle("Show", ShouldShow);
      const Icon = ButtonElement.querySelector("i");
      if (Icon) Icon.className = ShouldShow ? "fas fa-times" : "fas fa-bars";
      document.body.classList.toggle("BodyNoScroll", ShouldShow);
    };
    ButtonElement.addEventListener("click", () =>
      ToggleFunction(!NavElement.classList.contains("Show"))
    );
  },
  InitializeLazyLoad: function () {
    const LazyElements = document.querySelectorAll(
      "iframe.lazy-video, .FadeInElement"
    );
    if (!("IntersectionObserver" in window)) {
      LazyElements.forEach((Element) => {
        if (Element.tagName === "IFRAME") Element.src = Element.dataset.src;
        Element.classList.add("IsVisible");
      });
      return;
    }
    const Observer = new IntersectionObserver(
      (Entries) => {
        Entries.forEach((Entry) => {
          if (Entry.isIntersecting) {
            const Element = Entry.target;
            if (Element.tagName === "IFRAME") Element.src = Element.dataset.src;
            else Element.classList.add("IsVisible");
            Observer.unobserve(Element);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );
    LazyElements.forEach((Element) => Observer.observe(Element));
  },
  InitializeSmoothScroll: function () {
    document.querySelectorAll('a[href^="#"]').forEach((LinkElement) => {
      LinkElement.addEventListener("click", function (Event) {
        const href = this.getAttribute("href") || "";
        if (href === "#" || href === "") return;
        try {
          const TargetElement = document.querySelector(href);
          if (TargetElement) {
            Event.preventDefault();
            TargetElement.scrollIntoView({ behavior: "smooth" });
          }
        } catch (e) {}
      });
    });
  },

  InitializeAccordion: function () {
    const HeadersList = document.querySelectorAll(".AccordionHeader");
    HeadersList.forEach((HeaderElement) => {
      HeaderElement.addEventListener("click", () => {
        const IsActive = HeaderElement.classList.contains("active");
        HeadersList.forEach((OtherHeaderElement) => {
          OtherHeaderElement.classList.remove("active");
          const panel = OtherHeaderElement.nextElementSibling;
          if (panel) panel.classList.remove("active");
        });
        if (!IsActive) {
          HeaderElement.classList.add("active");
          const panel = HeaderElement.nextElementSibling;
          if (panel) panel.classList.add("active");
        }
      });
    });
  },
  InitializeGalleryModal: function () {
    const ModalElement = document.getElementById("ImageModal");
    if (!ModalElement) return;
    const ModalImageElement = ModalElement.querySelector(".ModalImage");
    document.querySelectorAll(".GalleryItem img").forEach((ImageElement) => {
      ImageElement.addEventListener("click", () => {
        ModalImageElement.src = ImageElement.src;
        ModalHelpers.OpenModal(ModalElement, ImageElement);
      });
    });
    ModalElement.querySelector(".CloseBtn")?.addEventListener("click", () =>
      ModalHelpers.CloseModal(ModalElement)
    );
    ModalElement.addEventListener("click", (Event) => {
      if (Event.target === ModalElement) ModalHelpers.CloseModal(ModalElement);
    });
    document.addEventListener("keydown", (Event) => {
      if (
        Event.key === "Escape" &&
        ModalElement.classList.contains("IsVisible")
      )
        ModalHelpers.CloseModal(ModalElement);
    });
  },
  InitializeCopyButtons: function () {
    document.querySelectorAll(".CopyBtn").forEach((ButtonElement) => {
      ButtonElement.addEventListener("click", function () {
        const CopyValue = this.dataset.copy || "";
        Helpers.safeClipboardWrite(CopyValue)
          .then(() => {
            const OriginalIconHtml = this.innerHTML;
            this.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
              this.innerHTML = OriginalIconHtml;
            }, 1500);
          })
          .catch((Error) => {
            console.error("Failed to copy:", Error);
            CreateFlash("Error", "کپی انجام نشد.");
          });
      });
    });
  },

  InitializePasswordToggle: function (ToggleId) {
    const ToggleElement = document.getElementById(ToggleId);
    if (!ToggleElement) return;

    let InputElement = null;
    if (ToggleElement.dataset && ToggleElement.dataset.target) {
      InputElement = document.querySelector(ToggleElement.dataset.target);
    } else {
      const prev = ToggleElement.previousElementSibling;
      if (prev && prev.tagName === "INPUT") InputElement = prev;
    }
    if (!InputElement) return;

    ToggleElement.addEventListener("click", function () {
      const InputType =
        InputElement.getAttribute("type") === "password" ? "text" : "password";
      InputElement.setAttribute("type", InputType);
      const i = this.querySelector("i");
      if (i) {
        i.classList.toggle("fa-eye");
        i.classList.toggle("fa-eye-slash");
      }
    });
  },
};

const App = {
  Initialize: function () {
    if (this._initialized) return;
    this._initialized = true;
    FormHelpers.Initialize();
    InitializeFlashSystem();
    UI.InitializeMobileMenu();
    UI.InitializeLazyLoad();
    UI.InitializeSmoothScroll();
    UI.InitializeCopyButtons();
    if (document.querySelector(".AccordionContainer")) UI.InitializeAccordion();
    if (document.querySelector(".GalleryGrid")) UI.InitializeGalleryModal();
    if (document.getElementById("CreateTeamForm"))
      this.InitializeCreateTeamForm();
    if (document.querySelector(".MembersPage")) this.InitializeMembersPage();
    if (document.getElementById("SignUpForm")) this.InitializeSignUpForm();
    if (document.getElementById("ResetForm")) this.InitializeResetForm();
    if (document.querySelector("form[action*='/Payment']"))
      this.InitializePaymentForm();
    if (document.getElementById("SelectLeagueForm"))
      this.InitializeLeagueSelector();
    if (document.getElementById("chat-box")) this.InitializeSupportChat();
    if (document.getElementById("EditForm")) {
      const Form = document.getElementById("EditForm");
      FormHelpers.PopulateProvinces(Form.querySelector('[name="Province"]'));
      FormHelpers.SetupProvinceCityListener(Form);
      FormHelpers.SetupDatePicker(Form);
    }
    document
      .querySelectorAll(".DeleteTeamForm, .DeleteMemberForm")
      .forEach((FormElement) => this.InitializeDeleteConfirmation(FormElement));
  },
  InitializeCreateTeamForm: function () {
    const FormElement = document.getElementById("CreateTeamForm");
    if (!FormElement) return;
    FormHelpers.PopulateProvinces(
      FormElement.querySelector('[name="Province"]')
    );
    FormHelpers.SetupProvinceCityListener(FormElement);
    FormHelpers.SetupDatePicker(FormElement);
    FormElement.addEventListener("submit", (Event) => {
      const TeamName =
        FormElement.querySelector('[name="TeamName"]')?.value || "";
      const ValidationResult = Validators.IsValidTeamName(TeamName);
      if (!ValidationResult.IsOK) {
        Event.preventDefault();
        CreateFlash("Error", ValidationResult.Message);
      }
    });
  },
  InitializeResetForm: function () {
    const FormElement = document.getElementById("ResetForm");
    if (!FormElement) return;
    this.InitializePasswordConfirmation(
      "ResetForm",
      "newPassword",
      "confirmPassword",
      "passwordError"
    );
  },

  InitializeSupportChat: function () {
    const chatContainer = document.querySelector(".ClientChatContainer");
    if (!chatContainer) return;

    const chatBox = document.getElementById("chat-box");
    const messageInput = document.getElementById("message-input");
    const sendButton = document.getElementById("send-button");

    if (!chatBox || !messageInput || !sendButton) {
      console.error("عناصر رابط کاربری چت یافت نشد.");
      return;
    }

    const roomID = chatContainer.dataset.clientId;
    const historyURL = chatContainer.dataset.historyUrl;
    const socket = Helpers.safeSocket();

    const addMessage = (msgData) => {
      const isSentByUser =
        msgData.Sender === roomID || msgData.Sender === "شما";

      const messageEl = document.createElement("div");
      messageEl.classList.add(
        "ChatMessage",
        isSentByUser ? "Message--sent" : "Message--received"
      );

      const metaEl = document.createElement("div");
      metaEl.classList.add("Meta");

      const date = msgData.Timestamp
        ? new Date(msgData.Timestamp.replace(" ", "T"))
        : new Date();
      metaEl.textContent = `${
        isSentByUser ? "شما" : msgData.Sender
      } در ${date.toLocaleTimeString()}`;

      const textEl = document.createElement("p");
      textEl.textContent = msgData.Message;

      messageEl.appendChild(metaEl);
      messageEl.appendChild(textEl);
      chatBox.appendChild(messageEl);
    };

    const scrollToBottom = () => {
      chatBox.scrollTop = chatBox.scrollHeight;
    };

    const sendMessage = () => {
      const messageText = messageInput.value.trim();
      if (messageText && socket) {
        const messageData = {
          Room: roomID,
          Sender: roomID,
          Message: messageText,
        };
        socket.emit("send_message", messageData);

        addMessage({
          Sender: "شما",
          Message: messageText,
          Timestamp: new Date().toISOString(),
        });

        messageInput.value = "";
        messageInput.focus();
        scrollToBottom();
      }
    };

    const loadHistory = async () => {
      if (!historyURL) {
        chatBox.innerHTML =
          '<div style="text-align:center; color:#888;">آدرس تاریخچه گفتگو یافت نشد.</div>';
        return;
      }
      try {
        const response = await fetch(historyURL);
        if (!response.ok) {
          throw new Error(`پاسخ سرور: ${response.status}`);
        }
        const data = await response.json();

        chatBox.innerHTML = "";

        if (data.Messages && data.Messages.length > 0) {
          data.Messages.forEach((dbMessage) => {
            addMessage({
              Sender: dbMessage.Sender,
              Message: dbMessage.MessageText,
              Timestamp: dbMessage.Timestamp,
            });
          });
        } else {
          chatBox.innerHTML =
            '<div style="text-align:center; color:#888;">هنوز پیامی وجود ندارد. سلام کنید!</div>';
        }
      } catch (error) {
        console.error("خطا در بارگذاری تاریخچه گفتگو:", error);
        chatBox.innerHTML =
          '<div style="text-align:center; color:red;">خطا در بارگذاری تاریخچه گفتگو. لطفا صفحه را رفرش کنید.</div>';
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
      socket.on("connect", () => {
        socket.emit("join", { Room: roomID });
      });

      socket.on("ReceiveMessage", (data) => {
        if (data.Sender === roomID) {
          return;
        }
        addMessage({
          Sender: data.Sender,
          Message: data.Message,
          Timestamp: data.timestamp,
        });
        scrollToBottom();
      });
    }

    loadHistory();
  },

  InitializeLeagueSelector: function () {
    const FormElement = document.getElementById("SelectLeagueForm");
    if (!FormElement) return;
    const LeagueOneElement = FormElement.querySelector("#leagueOne");
    const LeagueTwoElement = FormElement.querySelector("#leagueTwo");
    if (!LeagueOneElement || !LeagueTwoElement) return;
    const SyncOptionsFunction = () => {
      const ValueOne = LeagueOneElement.value;
      const ValueTwo = LeagueTwoElement.value;
      for (const OptionElement of LeagueTwoElement.options) {
        OptionElement.disabled =
          OptionElement.value === ValueOne && OptionElement.value !== "";
      }
      for (const OptionElement of LeagueOneElement.options) {
        OptionElement.disabled =
          OptionElement.value === ValueTwo && OptionElement.value !== "";
      }
    };
    LeagueOneElement.addEventListener("change", SyncOptionsFunction);
    LeagueTwoElement.addEventListener("change", SyncOptionsFunction);
    SyncOptionsFunction();
  },
  InitializePasswordConfirmation: function (
    FormId,
    PasswordId,
    ConfirmId,
    ErrorId
  ) {
    const FormElement = document.getElementById(FormId);
    if (!FormElement) return;
    const PasswordElement = FormElement.querySelector(`#${PasswordId}`);
    const ConfirmElement = FormElement.querySelector(`#${ConfirmId}`);
    const ErrorElement = FormElement.querySelector(`#${ErrorId}`);
    if (!PasswordElement || !ConfirmElement) return;
    const ValidateMatch = () => {
      const IsMatch =
        (PasswordElement?.value || "") === (ConfirmElement?.value || "");
      if (ErrorElement) {
        ErrorElement.classList.toggle(
          "IsVisible",
          !IsMatch && ConfirmElement.value.length > 0
        );
      }
      ConfirmElement.classList.toggle(
        "IsInvalid",
        !IsMatch && ConfirmElement.value.length > 0
      );
      return IsMatch;
    };
    FormElement.addEventListener("submit", (Event) => {
      if (!ValidateMatch()) {
        Event.preventDefault();
        CreateFlash("Error", "رمزهای عبور مطابقت ندارند!");
      }
    });
    PasswordElement.addEventListener("input", ValidateMatch);
    ConfirmElement.addEventListener("input", ValidateMatch);
  },
  InitializeMembersPage: function () {
    const PageElement = document.querySelector(".MembersPage");
    if (!PageElement) return;
    const AddFormElement = PageElement.querySelector("#AddMemberForm");
    const EditModalElement = document.getElementById("EditModal");
    const EditFormElement = PageElement.querySelector("#EditForm");
    if (AddFormElement) {
      FormHelpers.PopulateProvinces(
        AddFormElement.querySelector('[name="Province"]')
      );
      FormHelpers.SetupProvinceCityListener(AddFormElement);
      FormHelpers.SetupDatePicker(AddFormElement);
    }
    if (EditModalElement && EditFormElement) {
      FormHelpers.PopulateProvinces(
        EditFormElement.querySelector('[name="Province"]')
      );
      FormHelpers.SetupDatePicker(EditFormElement);
      FormHelpers.SetupProvinceCityListener(EditFormElement);
      PageElement.addEventListener("click", (Event) => {
        const EditButtonElement = Event.target.closest(".EditBtn");
        if (!EditButtonElement) return;
        const DataSet = EditButtonElement.dataset;
        const TeamId = PageElement.dataset.teamId;
        const MemberId = DataSet.memberId;
        EditFormElement.action = `/Team/${TeamId}/EditMember/${MemberId}`;
        EditFormElement.querySelector('[name="Name"]').value =
          DataSet.name || "";
        EditFormElement.querySelector('[name="NationalID"]').value =
          DataSet.nationalId || "";
        EditFormElement.querySelector('[name="Role"]').value =
          DataSet.role || "";
        EditFormElement.querySelector('[name="PhoneNumber"]').value =
          DataSet.phoneNumber || "";
        const ProvinceSelectElement =
          EditFormElement.querySelector('[name="Province"]');
        ProvinceSelectElement.value = DataSet.province || "";
        FormHelpers.UpdateCities(
          ProvinceSelectElement.value,
          EditFormElement.querySelector('[name="City"]')
        );
        EditFormElement.querySelector('[name="City"]').value =
          DataSet.city || "";
        const DaySelect = EditFormElement.querySelector('[name="BirthDay"]');
        const MonthSelect = EditFormElement.querySelector(
          '[name="BirthMonth"]'
        );
        const YearSelect = EditFormElement.querySelector('[name="BirthYear"]');
        if (DataSet.birthDate) {
          const [Year, Month, Day] = DataSet.birthDate.split("-");
          DaySelect.value = Day || "";
          MonthSelect.value = Month || "";
          YearSelect.value = Year || "";
        } else {
          DaySelect.value = "";
          MonthSelect.value = "";
          YearSelect.value = "";
        }
        ModalHelpers.OpenModal(EditModalElement, EditButtonElement);
      });
      EditModalElement.querySelector(".CloseBtn")?.addEventListener(
        "click",
        () => ModalHelpers.CloseModal(EditModalElement)
      );
    }
  },
  InitializeSignUpForm: function () {
    const FormElement = document.getElementById("SignUpForm");
    if (!FormElement) return;
    const PasswordInputElement = FormElement.querySelector("#password");
    const ConfirmInputElement = FormElement.querySelector("#confirm_password");
    const PasswordErrorElement = FormElement.querySelector("#passwordError");
    if (!PasswordInputElement || !ConfirmInputElement) return;
    UI.InitializePasswordToggle("password-toggle");
    UI.InitializePasswordToggle("confirm-password-toggle");
    const RequirementsDictionary = {
      LengthRequirement: document.getElementById("req-length"),
      UpperRequirement: document.getElementById("req-upper"),
      LowercaseRequirement: document.getElementById("req-lower"),
      NumberRequirement: document.getElementById("req-number"),
      SpecialRequirement: document.getElementById("req-special"),
    };
    const ValidatePasswordStrengthFunction = () => {
      const Value = PasswordInputElement.value;
      let AllValid = true;
      if (RequirementsDictionary.LengthRequirement) {
        const Valid = Value.length >= 8;
        RequirementsDictionary.LengthRequirement.className = Valid
          ? "valid"
          : "invalid";
        if (!Valid) AllValid = false;
      }
      if (RequirementsDictionary.UpperRequirement) {
        const Valid = /[A-Z]/.test(Value);
        RequirementsDictionary.UpperRequirement.className = Valid
          ? "valid"
          : "invalid";
        if (!Valid) AllValid = false;
      }
      if (RequirementsDictionary.LowercaseRequirement) {
        const Valid = /[a-z]/.test(Value);
        RequirementsDictionary.LowercaseRequirement.className = Valid
          ? "valid"
          : "invalid";
        if (!Valid) AllValid = false;
      }
      if (RequirementsDictionary.NumberRequirement) {
        const Valid = /[0-9]/.test(Value);
        RequirementsDictionary.NumberRequirement.className = Valid
          ? "valid"
          : "invalid";
        if (!Valid) AllValid = false;
      }
      if (RequirementsDictionary.SpecialRequirement) {
        const Valid = /[!@#$%^&*(),.?":{}|<>]/.test(Value);
        RequirementsDictionary.SpecialRequirement.className = Valid
          ? "valid"
          : "invalid";
        if (!Valid) AllValid = false;
      }
      return AllValid;
    };
    const ValidatePasswordMatchFunction = () => {
      const IsMatch = PasswordInputElement.value === ConfirmInputElement.value;
      if (PasswordErrorElement) {
        PasswordErrorElement.classList.toggle(
          "IsVisible",
          !IsMatch && ConfirmInputElement.value.length > 0
        );
      }
      return IsMatch;
    };
    PasswordInputElement.addEventListener("input", () => {
      ValidatePasswordStrengthFunction();
      ValidatePasswordMatchFunction();
    });
    ConfirmInputElement.addEventListener(
      "input",
      ValidatePasswordMatchFunction
    );
    FormElement.addEventListener("submit", (Event) => {
      const IsStrengthValid = ValidatePasswordStrengthFunction();
      const IsMatchValid = ValidatePasswordMatchFunction();
      if (!IsStrengthValid || !IsMatchValid) {
        Event.preventDefault();
        CreateFlash("Error", "لطفا تمام خطاهای فرم را برطرف کنید.");
      }
    });
  },
  InitializePaymentForm: function () {
    const ReceiptInputElement = document.querySelector(
      'input[type="file"][name="receipt"]'
    );
    if (!ReceiptInputElement) return;
    ReceiptInputElement.addEventListener("change", () => {
      const FileElement = ReceiptInputElement.files[0];
      if (!FileElement) return;
      const Extension = FileElement.name.split(".").pop().toLowerCase();
      if (!FormHelpers.AllowedExtensions.includes(Extension)) {
        CreateFlash("Error", "فرمت فایل پشتیبانی نمی‌شود.");
        ReceiptInputElement.value = "";
      }
    });
  },
  InitializeDeleteConfirmation: function (FormElement) {
    FormElement.addEventListener("submit", (Event) => {
      const TeamName = FormElement.dataset.teamName || "این آیتم";
      if (!confirm(`آیا از حذف «${TeamName}» اطمینان دارید؟`)) {
        Event.preventDefault();
      }
    });
  },
};

const AdminApp = {
  Initialize: function () {
    if (this._initialized) return;
    this._initialized = true;
    this.InitializeMenu();
    this.InitializeChat();
    FormHelpers.Initialize();
    InitializeFlashSystem();
    this.InitializeRelativeTime();
    this.InitializeAdminModals();
    this.InitializeClientSearch();
    this.InitializeAdminMembersPage();
    if (document.querySelector(".ChartGrid")) this.InitializeDashboardCharts();
    if (document.getElementById("password-toggle"))
      UI.InitializePasswordToggle("password-toggle");
    UI.InitializePasswordToggle("EditPasswordToggle");
    if (document.getElementById("AddMemberForm"))
      this.InitializeAdminAddMemberPage?.();
    document
      .querySelectorAll(".ConfirmDelete")
      .forEach((FormElement) => this.InitializeDeleteConfirmation(FormElement));
  },
  InitializeAdminMembersPage: function () {
    const PageElement = document.querySelector(".AdminMembersPage");
    if (!PageElement) return;
    const AddFormElement = document.getElementById("AddMemberForm");
    if (AddFormElement) {
      FormHelpers.PopulateProvinces(
        AddFormElement.querySelector('[name="Province"]')
      );
      FormHelpers.SetupProvinceCityListener(AddFormElement);
      FormHelpers.SetupDatePicker(AddFormElement);
    }
    const MemberModalElement = document.getElementById("MemberModal");
    const MemberFormElement = document.getElementById("MemberForm");
    const ModalTitleElement = document.getElementById("MemberModalTitle");
    if (MemberModalElement && MemberFormElement && ModalTitleElement) {
      FormHelpers.PopulateProvinces(
        MemberFormElement.querySelector('[name="Province"]')
      );
      FormHelpers.SetupProvinceCityListener(MemberFormElement);
      FormHelpers.SetupDatePicker(MemberFormElement);
      PageElement.addEventListener("click", (Event) => {
        const TriggerElement = Event.target.closest(
          '[data-modal-target="MemberModal"]'
        );
        if (!TriggerElement) return;
        const DataSet = TriggerElement.dataset;
        const TeamId = PageElement.dataset.teamId;
        ModalTitleElement.textContent = `ویرایش ${DataSet.memberName}`;
        MemberFormElement.action = `/Admin/Team/${TeamId}/EditMember/${DataSet.memberId}`;
        MemberFormElement.querySelector('[name="Name"]').value =
          DataSet.memberName || "";
        MemberFormElement.querySelector('[name="NationalID"]').value =
          DataSet.memberNid || "";
        MemberFormElement.querySelector('[name="PhoneNumber"]').value =
          DataSet.memberPhone || "";
        MemberFormElement.querySelector('[name="Role"]').value =
          DataSet.memberRole || "";
        const ProvinceSelectElement =
          MemberFormElement.querySelector('[name="Province"]');
        ProvinceSelectElement.value = DataSet.memberProvince || "";
        ModalHelpers.OpenModal(MemberModalElement, TriggerElement);
      });
    }
  },
  InitializeMenu: function () {
    const ToggleButton = document.querySelector(".AdminHeader__mobile-toggle");
    const NavMenu = document.querySelector(".AdminHeader__nav");
    if (!ToggleButton || !NavMenu) return;
    ToggleButton.addEventListener("click", () => {
      const IsOpen = NavMenu.classList.toggle("is-open");
      ToggleButton.setAttribute("aria-expanded", IsOpen);
      const IconElement = ToggleButton.querySelector("i");
      if (IconElement)
        IconElement.className = IsOpen ? "fas fa-times" : "fas fa-bars";
    });
  },
  InitializeRelativeTime: function () {
    const Els = Array.from(
      document.querySelectorAll(
        "[data-timestamp].RelativeTime, [data-timestamp].relative-time"
      )
    );
    if (!Els.length) return;

    const format = (date) => {
      if (!date) return "";
      const now = new Date();
      const diff = Math.floor((now - date) / 1000);
      if (diff < 5) return "همین الان";
      if (diff < 60) return `${diff} ثانیه پیش`;
      if (diff < 3600) return `${Math.floor(diff / 60)} دقیقه پیش`;
      if (diff < 86400) return `${Math.floor(diff / 3600)} ساعت پیش`;
      if (diff < 2592000) return `${Math.floor(diff / 86400)} روز پیش`;
      if (diff < 31536000) return `${Math.floor(diff / 2592000)} ماه پیش`;
      return `${Math.floor(diff / 31536000)} سال پیش`;
    };

    const updateAll = () => {
      Els.forEach((el) => {
        const raw =
          el.dataset.timestamp || el.getAttribute("data-timestamp") || "";
        const d = Helpers.parseTimestamp(raw);
        if (!d) {
          el.textContent = raw;
        } else {
          el.textContent = format(d);
          el.setAttribute("title", d.toLocaleString());
        }
      });
    };

    updateAll();
    if (this._relativeTimeInterval) clearInterval(this._relativeTimeInterval);
    this._relativeTimeInterval = setInterval(updateAll, 60 * 1000);
  },

  InitializeAdminAddMemberPage: function () {
    const AddForm = document.getElementById("AddMemberForm");
    if (!AddForm) return;
    FormHelpers.PopulateProvinces(AddForm.querySelector('[name="Province"]'));
    FormHelpers.SetupProvinceCityListener(AddForm);
    FormHelpers.SetupDatePicker(AddForm);
  },

  InitializeDeleteConfirmation: function (FormElement) {
    const Message =
      FormElement.dataset.confirm || "آیا از انجام این عملیات اطمینان دارید؟";
    FormElement.addEventListener("submit", (Event) => {
      if (!confirm(Message)) Event.preventDefault();
    });
  },
  InitializeDashboardCharts: function () {
    const ChartGridElement = document.querySelector(".ChartGrid");
    if (!ChartGridElement) return;
    const ScriptElement = document.createElement("script");
    ScriptElement.src = "https://cdn.jsdelivr.net/npm/chart.js";
    ScriptElement.onload = () => {
      try {
        const ProvinceData = JSON.parse(
          ChartGridElement.dataset.provinceData || "{}"
        );
        const CityData = JSON.parse(ChartGridElement.dataset.cityData || "{}");
        if (typeof Chart === "undefined") {
          console.warn("Chart.js loaded but Chart is undefined.");
          return;
        }

        const ChartColorsList = [
          "#3182ce",
          "#2b6cb0",
          "#2c7a7b",
          "#2d3748",
          "#805ad5",
          "#b7791f",
        ];
        const ContextProvince = document
          .getElementById("ProvinceChart")
          ?.getContext("2d");
        if (
          ContextProvince &&
          ProvinceData.Labels &&
          Array.isArray(ProvinceData.DataPoints)
        ) {
          new Chart(ContextProvince, {
            type: "doughnut",
            data: {
              labels: ProvinceData.Labels,
              datasets: [
                {
                  data: ProvinceData.DataPoints,
                  backgroundColor: ChartColorsList,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { position: "bottom" } },
            },
          });
        }
        const ContextCity = document
          .getElementById("CityChart")
          ?.getContext("2d");
        if (
          ContextCity &&
          CityData.Labels &&
          Array.isArray(CityData.DataPoints)
        ) {
          new Chart(ContextCity, {
            type: "bar",
            data: {
              labels: CityData.Labels,
              datasets: [
                {
                  label: "تعداد شرکت کنندگان",
                  data: CityData.DataPoints,
                  backgroundColor: ChartColorsList[1],
                },
              ],
            },
            options: {
              indexAxis: "y",
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
            },
          });
        }
      } catch (e) {
        console.error("Failed to initialize charts:", e);
      }
    };
    ScriptElement.onerror = () => {
      console.error("Failed to load Chart.js script.");
    };
    document.body.appendChild(ScriptElement);
  },
  InitializeAdminModals: function () {
    document.body.addEventListener("click", (Event) => {
      const TriggerElement = Event.target.closest("[data-modal-target]");
      if (TriggerElement) {
        const ModalElement = document.getElementById(
          TriggerElement.dataset.modalTarget
        );
        if (ModalElement) ModalHelpers.OpenModal(ModalElement, TriggerElement);
      }
      if (Event.target.classList.contains("CloseBtn")) {
        const ModalElement = Event.target.closest(".Modal");
        if (ModalElement) ModalHelpers.CloseModal(ModalElement);
      }
    });
    window.addEventListener("click", (Event) => {
      if (Event.target.classList.contains("Modal"))
        ModalHelpers.CloseModal(Event.target);
    });
    document.addEventListener("keydown", (Event) => {
      if (Event.key === "Escape")
        document
          .querySelectorAll(".Modal.IsVisible")
          .forEach(ModalHelpers.CloseModal);
    });
  },
  InitializeClientSearch: function () {
    const SearchInputElement = document.getElementById("ClientSearchInput");
    const TableBodyElement = document.querySelector("#clients-table tbody");
    if (!SearchInputElement || !TableBodyElement) return;
    const TableRowsList = Array.from(TableBodyElement.querySelectorAll("tr"));
    const NoResultsMessageElement = document.getElementById("NoResultsMessage");

    const doSearch = () => {
      const SearchTerm = SearchInputElement.value.toLowerCase().trim();
      let VisibleRowsCount = 0;
      TableRowsList.forEach((RowElement) => {
        if (RowElement.classList.contains("EmptyStateRow")) return;
        const RowText = RowElement.textContent.toLowerCase();
        const IsMatch = RowText.includes(SearchTerm);
        RowElement.style.display = IsMatch ? "" : "none";
        if (IsMatch) VisibleRowsCount++;
      });
      if (NoResultsMessageElement)
        NoResultsMessageElement.style.display =
          VisibleRowsCount === 0 ? "table-row" : "none";
    };

    SearchInputElement.addEventListener(
      "input",
      Helpers.debounce(doSearch, 180)
    );
  },

  InitializeChat: function () {
    const ChatContainerElement = document.querySelector(".AdminChatContainer");
    if (!ChatContainerElement) return;

    const ElementsDictionary = {
      ChatBox: document.getElementById("ChatBox"),
      MessageInput: document.getElementById("MessageInput"),
      SendButton: document.getElementById("SendButton"),
      PersonaSelect: document.getElementById("PersonaSelect"),
    };

    const socket = Helpers.safeSocket();
    if (!socket) {
      console.warn("اتصال لحظه‌ای برقرار نیست: Socket.IO در دسترس نیست.");
      ElementsDictionary.ChatBox?.insertAdjacentHTML(
        "afterbegin",
        '<div class="EmptyStateRow">اتصال لحظه‌ای غیرفعال است</div>'
      );
    }

    const StateDictionary = {
      RoomID: ChatContainerElement.dataset.clientId,
      HistoryURL: ChatContainerElement.dataset.historyUrl,
      SocketIO: socket,
    };

    if (!StateDictionary.RoomID || !StateDictionary.HistoryURL) {
      console.error("شناسه کاربر یا آدرس تاریخچه گفتگو یافت نشد.");
      if (ElementsDictionary.ChatBox)
        ElementsDictionary.ChatBox.innerHTML =
          '<div class="EmptyStateRow">خطا: اطلاعات ضروری چت یافت نشد.</div>';
      return;
    }

    if (!ElementsDictionary.ChatBox) {
      console.error("عنصر ChatBox در DOM یافت نشد.");
      return;
    }

    const ScrollToBottomFunction = () => {
      try {
        ElementsDictionary.ChatBox.scrollTop =
          ElementsDictionary.ChatBox.scrollHeight;
      } catch (e) {}
    };

    const AppendMessageFunction = (MessageObject) => {
      if (!MessageObject || !MessageObject.MessageText) return;
      const IsClientBoolean =
        String(MessageObject.Sender) === StateDictionary.RoomID;
      const SenderName = IsClientBoolean ? "کاربر" : MessageObject.Sender;
      const MessageElement = document.createElement("div");
      const MessageClass = IsClientBoolean ? "is-client" : "is-admin";
      MessageElement.className = `ChatMessage ${MessageClass}`;

      const senderDiv = document.createElement("div");
      senderDiv.className = "ChatMessage__sender";
      senderDiv.textContent = SenderName;

      const textP = document.createElement("p");
      textP.className = "ChatMessage__text";
      textP.textContent = MessageObject.MessageText;

      const metaDiv = document.createElement("div");
      metaDiv.className = "ChatMessage__meta";
      metaDiv.textContent = MessageObject.Timestamp || "";

      MessageElement.appendChild(senderDiv);
      MessageElement.appendChild(textP);
      MessageElement.appendChild(metaDiv);

      ElementsDictionary.ChatBox.appendChild(MessageElement);
    };

    if (StateDictionary.SocketIO) {
      StateDictionary.SocketIO.on("connect", () => {
        try {
          StateDictionary.SocketIO.emit("join", {
            Room: StateDictionary.RoomID,
          });
        } catch (e) {
          console.warn("ارسال رویداد 'join' ناموفق بود:", e);
        }
      });

      StateDictionary.SocketIO.on("ReceiveMessage", (MessageReceived) => {
        ElementsDictionary.ChatBox.querySelector(".EmptyStateRow")?.remove();
        AppendMessageFunction({
          Sender: MessageReceived.Sender,
          MessageText: MessageReceived.Message,
          Timestamp: MessageReceived.Timestamp,
        });
        ScrollToBottomFunction();
      });
    } else {
      ElementsDictionary.ChatBox.querySelector(".EmptyStateRow")?.remove();
      const info = document.createElement("div");
      info.className = "EmptyStateRow";
      info.textContent = "اتصال لحظه‌ای غیرفعال است";
      ElementsDictionary.ChatBox.appendChild(info);
    }

    const LoadChatHistoryFunction = async () => {
      try {
        const Response = await fetch(StateDictionary.HistoryURL);
        if (!Response.ok) throw new Error("دریافت تاریخچه گفتگو ناموفق بود");
        const Data = await Response.json();
        ElementsDictionary.ChatBox.innerHTML = "";
        if (Data?.Messages?.length > 0) {
          Data.Messages.forEach(AppendMessageFunction);
        } else {
          ElementsDictionary.ChatBox.innerHTML =
            '<div class="EmptyStateRow">هیچ پیامی در تاریخچه یافت نشد.</div>';
        }
        ScrollToBottomFunction();
      } catch (Error) {
        console.error(Error);
        ElementsDictionary.ChatBox.innerHTML =
          '<div class="EmptyStateRow">خطا در بارگذاری تاریخچه چت.</div>';
      }
    };

    const SendMessageFunction = () => {
      if (!ElementsDictionary.MessageInput) return;
      const MessageText = ElementsDictionary.MessageInput.value.trim();
      if (!MessageText) return;

      if (StateDictionary.SocketIO) {
        try {
          StateDictionary.SocketIO.emit("send_message", {
            Room: StateDictionary.RoomID,
            Sender: ElementsDictionary.PersonaSelect
              ? ElementsDictionary.PersonaSelect.value
              : "admin",
            Message: MessageText,
          });
        } catch (e) {
          console.warn("ارسال پیام لحظه‌ای ناموفق بود:", e);
        }
      } else {
        CreateFlash(
          "Warning",
          "اتصال لحظه‌ای برقرار نیست — پیام فقط محلی نمایش داده می‌شود."
        );
      }
      AppendMessageFunction({
        Sender: ElementsDictionary.PersonaSelect
          ? ElementsDictionary.PersonaSelect.value
          : "admin",
        MessageText: MessageText,
        Timestamp: new Date().toLocaleTimeString(),
      });

      ElementsDictionary.MessageInput.value = "";
      try {
        ElementsDictionary.MessageInput.focus();
      } catch (e) {}
      ScrollToBottomFunction();
    };
    if (ElementsDictionary.SendButton) {
      ElementsDictionary.SendButton.addEventListener(
        "click",
        SendMessageFunction
      );
    }
    if (ElementsDictionary.MessageInput) {
      ElementsDictionary.MessageInput.addEventListener("keydown", (Event) => {
        if (Event.key === "Enter" && !Event.shiftKey) {
          Event.preventDefault();
          SendMessageFunction();
        }
      });
    }
    LoadChatHistoryFunction();
    ScrollToBottomFunction();
  },
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.classList.contains("AdminBody")) AdminApp.Initialize();
  else App.Initialize();
});
