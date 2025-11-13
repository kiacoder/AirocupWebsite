"use strict";

const Helpers = {
  Debounce(FunctionToDebounce, WaitTime = 150) {
    let TimeoutId;
    return (...Arguments) => {
      clearTimeout(TimeoutId);
      TimeoutId = setTimeout(() => FunctionToDebounce(...Arguments), WaitTime);
    };
  },

  SafeClipboardWrite(TextToCopy) {
    if (navigator.clipboard?.writeText) {
      return navigator.clipboard.writeText(TextToCopy);
    }
    return new Promise((Resolve, Reject) => {
      try {
        const TextAreaElement = document.createElement("textarea");
        TextAreaElement.value = String(TextToCopy || "");
        TextAreaElement.style.position = "fixed";
        TextAreaElement.style.left = "-9999px";
        document.body.appendChild(TextAreaElement);
        TextAreaElement.select();
        document.execCommand("copy");
        TextAreaElement.remove();
        Resolve();
      } catch (Error) {
        Reject(Error);
      }
    });
  },

  SafeSocket() {
    if (typeof io === "undefined") return null;
    try {
      return io();
    } catch (Error) {
      console.warn("اتصال سوکت برقرار نشد:", Error);
      return null;
    }
  },

  ParseTimestamp(TimestampString) {
    if (!TimestampString) return null;
    const RawTimestamp = String(TimestampString);
    const ISOTimestamp = RawTimestamp.replace(" ", "T").replace(/\//g, "-");
    const DateObject1 = new Date(ISOTimestamp);
    if (!isNaN(DateObject1)) return DateObject1;

    const TimestampMatch = RawTimestamp.match(
      /^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})(?:[ T](\d{1,2}):(\d{1,2}))?/
    );

    if (TimestampMatch) {
      const Year = +TimestampMatch[1];
      const Month = +TimestampMatch[2] - 1;
      const Day = +TimestampMatch[3];
      const Hour = +(TimestampMatch[4] || 0);
      const Minute = +(TimestampMatch[5] || 0);
      const DateObject2 = new Date(Year, Month, Day, Hour, Minute);
      if (!isNaN(DateObject2)) return DateObject2;
    }

    const DateObject3 = new Date(Date.parse(RawTimestamp));
    if (!isNaN(DateObject3)) return DateObject3;

    return null;
  },
};

const Utils = {
  ShowNotification(Message, Options = {}) {
    CreateFlash(Options.Type || "Info", String(Message || ""), Options);
  },
};

function CreateFlash(Type, Message, Options = {}) {
  const NormalizedType =
    typeof Type === "string" && Type
      ? Type.charAt(0).toUpperCase() + Type.slice(1)
      : "Info";

  let FlashContainer = document.getElementById("FlashContainer");
  if (!FlashContainer) {
    FlashContainer = document.createElement("div");
    FlashContainer.id = "FlashContainer";
    FlashContainer.setAttribute("aria-live", "polite");
    FlashContainer.setAttribute("aria-atomic", "true");
    document.body.appendChild(FlashContainer);
    InitializeFlashSystem();
  }

  const FlashItem = document.createElement("div");
  FlashItem.className = `FlashMessage Flash${NormalizedType}`;
  FlashItem.setAttribute("role", "alert");

  const FlashIcon = document.createElement("i");
  const IconMapping = {
    Success: "fa-check-circle",
    Error: "fa-exclamation-triangle",
    Warning: "fa-exclamation-circle",
    Info: "fa-info-circle",
  };
  FlashIcon.className = `fas ${
    IconMapping[NormalizedType] || IconMapping.Info
  }`;
  FlashIcon.setAttribute("aria-hidden", "true");

  const FlashText = document.createElement("span");
  FlashText.textContent = Message || "";

  const CloseButton = document.createElement("button");
  CloseButton.className = "FlashCloseBtn";
  CloseButton.dataset.action = "dismiss-flash";
  CloseButton.setAttribute("aria-label", "بستن اعلان");
  CloseButton.innerHTML = "&times;";

  FlashItem.appendChild(FlashIcon);
  FlashItem.appendChild(FlashText);
  FlashItem.appendChild(CloseButton);
  FlashContainer.appendChild(FlashItem);

  const DisplayDuration = Options.Duration || 5000;
  setTimeout(() => {
    DismissFlash(FlashItem);
  }, DisplayDuration);

  return FlashItem;
}

function DismissFlash(FlashElement) {
  if (!FlashElement) return;
  if (FlashElement.classList.contains("FlashMessageClosing")) return;

  FlashElement.classList.add("FlashMessageClosing");
  const AnimationDuration = 350;

  setTimeout(() => {
    if (FlashElement.parentNode) {
      FlashElement.remove();
    }
  }, AnimationDuration);
}

function InitializeFlashSystem() {
  const FlashContainer = document.getElementById("FlashContainer");
  if (!FlashContainer) return;
  if (FlashContainer._flashInitialized) return;

  FlashContainer._flashInitialized = true;

  FlashContainer.addEventListener("click", function (Event) {
    const ClickTarget = Event.target;
    if (
      ClickTarget &&
      ClickTarget.dataset &&
      ClickTarget.dataset.action === "dismiss-flash"
    ) {
      const FlashMessage = ClickTarget.closest(".FlashMessage");
      DismissFlash(FlashMessage);
    }
  });

  Array.from(FlashContainer.querySelectorAll(".FlashMessage")).forEach(
    (FlashElement, Index) => {
      setTimeout(() => DismissFlash(FlashElement), 5000 + Index * 120);
    }
  );
}

const Validators = {
  IsValidIranianPhone(PhoneNumber) {
    if (!PhoneNumber) return false;
    const CleanPhoneNumber = String(PhoneNumber).replace(/\s+/g, "");
    return /^(?:\+98|0)?9\d{9}$/.test(CleanPhoneNumber);
  },

  IsValidNationalID(NationalID) {
    if (!NationalID) return false;
    const CleanNationalID = String(NationalID).trim();
    if (!/^\d{10}$/.test(CleanNationalID)) return false;
    if (new Set(CleanNationalID).size === 1) return false;

    const CheckDigit = parseInt(CleanNationalID[9], 10);
    let Sum = 0;

    for (let Index = 0; Index < 9; Index++) {
      Sum += parseInt(CleanNationalID[Index], 10) * (10 - Index);
    }

    const Remainder = Sum % 11;
    return Remainder < 2
      ? CheckDigit === Remainder
      : CheckDigit === 11 - Remainder;
  },

  IsValidTeamName(TeamName) {
    if (!TeamName) {
      return { IsValid: false, Message: "نام تیم نمی‌تواند خالی باشد." };
    }

    const TrimmedTeamName = TeamName.trim();
    const NameLength = TrimmedTeamName.length;

    if (NameLength < 3 || NameLength > 30) {
      return {
        IsValid: false,
        Message: "نام تیم باید بین ۳ تا ۳۰ کاراکتر باشد.",
      };
    }

    if (!/^[A-Za-z\u0600-\u06FF0-9_ ]+$/.test(TrimmedTeamName)) {
      return {
        IsValid: false,
        Message: "نام تیم فقط می‌تواند شامل حروف، اعداد، فاصله و خط زیر باشد.",
      };
    }

    const ForbiddenWords = window.AirocupData?.ForbiddenWords || [];
    const LowerCaseName = TrimmedTeamName.toLowerCase();

    for (let Word of ForbiddenWords) {
      if (LowerCaseName.includes(String(Word).toLowerCase())) {
        return { IsValid: false, Message: "نام تیم حاوی کلمات غیرمجاز است." };
      }
    }

    return { IsValid: true };
  },

  IsValidEmail(Email) {
    if (!Email) return false;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(Email).toLowerCase());
  },
};

const ModalHelpers = {
  TrapFocus(ModalElement) {
    if (!ModalElement) return;

    const FocusableElements = Array.from(
      ModalElement.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    );

    if (!FocusableElements.length) return;

    const FirstElement = FocusableElements[0];
    const LastElement = FocusableElements[FocusableElements.length - 1];

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

  OpenModal(ModalElement, TriggerElement) {
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

  CloseModal(ModalElement) {
    if (!ModalElement) return;

    ModalElement.classList.remove("IsVisible");
    ModalElement.setAttribute("aria-hidden", "true");

    if (ModalElement._ReleaseTrap) {
      ModalElement._ReleaseTrap();
    }

    ModalElement._TriggerElement?.focus();
    document.body.classList.remove("BodyNoScroll");
  },
};

const FormHelpers = {
  Initialize() {
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

  PopulateProvinces(SelectElement) {
    if (!SelectElement) return;

    const Fragment = document.createDocumentFragment();
    Fragment.appendChild(new Option("استان را انتخاب کنید", ""));

    Object.keys(this.Provinces || {})
      .sort((ProvinceA, ProvinceB) => ProvinceA.localeCompare(ProvinceB, "fa"))
      .forEach((ProvinceName) => {
        Fragment.appendChild(new Option(ProvinceName, ProvinceName));
      });

    SelectElement.innerHTML = "";
    SelectElement.appendChild(Fragment);
  },

  UpdateCities(ProvinceName, CitySelectElement) {
    if (!CitySelectElement) return;

    CitySelectElement.innerHTML = "";
    CitySelectElement.add(new Option("شهر را انتخاب کنید", ""));
    CitySelectElement.disabled = true;

    if (!ProvinceName || !this.Provinces[ProvinceName]) return;

    this.Provinces[ProvinceName].forEach((CityName) => {
      CitySelectElement.add(new Option(CityName, CityName));
    });

    CitySelectElement.disabled = false;
  },

  SetupProvinceCityListener(FormElement) {
    if (!FormElement) return;

    const ProvinceSelect = FormElement.querySelector('[name="Province"]');
    const CitySelect = FormElement.querySelector('[name="City"]');

    if (!ProvinceSelect || !CitySelect) return;

    ProvinceSelect.addEventListener("change", () => {
      this.UpdateCities(ProvinceSelect.value, CitySelect);
    });

    if (ProvinceSelect.value) {
      this.UpdateCities(ProvinceSelect.value, CitySelect);
      CitySelect.value = CitySelect.getAttribute("data-initial-city") || "";
    }
  },

  SetupDatePicker(FormElement) {
    if (!FormElement) return;

    const DaySelect = FormElement.querySelector('[name="BirthDay"]');
    const MonthSelect = FormElement.querySelector('[name="BirthMonth"]');
    const YearSelect = FormElement.querySelector('[name="BirthYear"]');

    if (!DaySelect || !MonthSelect || !YearSelect) return;

    MonthSelect.innerHTML = "";
    MonthSelect.add(new Option("ماه", ""));

    for (const [MonthNumber, MonthName] of Object.entries(this.PersianMonths)) {
      MonthSelect.add(new Option(MonthName, MonthNumber));
    }

    YearSelect.innerHTML = "";
    YearSelect.add(new Option("سال", ""));

    this.AllowedYears.forEach((Year) => {
      YearSelect.add(new Option(Year, Year));
    });

    const IsLeapYear = (Year) => {
      const Remainder = (Year + 12) % 33;
      return [1, 5, 9, 13, 17, 22, 26, 30].includes(Remainder);
    };

    const UpdateDays = () => {
      const SelectedMonth = parseInt(MonthSelect.value, 10);
      const SelectedYear = parseInt(YearSelect.value, 10);
      let MaxDays = SelectedMonth ? this.DaysInMonth[SelectedMonth] || 31 : 31;

      if (SelectedMonth === 12 && SelectedYear && IsLeapYear(SelectedYear)) {
        MaxDays = 30;
      }

      const CurrentDay = DaySelect.value;
      DaySelect.innerHTML = "";
      DaySelect.add(new Option("روز", ""));

      for (let Day = 1; Day <= MaxDays; Day++) {
        DaySelect.add(new Option(Day, Day));
      }

      if (CurrentDay && parseInt(CurrentDay, 10) <= MaxDays) {
        DaySelect.value = CurrentDay;
      }
    };

    YearSelect.addEventListener("input", UpdateDays);
    MonthSelect.addEventListener("change", UpdateDays);
    UpdateDays();
  },
};

const UI = {
  InitializeMobileMenu() {
    const MenuButton = document.querySelector(".MobileMenuBtn");
    const Navigation = document.querySelector(".NavItems");

    if (!MenuButton || !Navigation) return;

    const ToggleMenu = (ShouldShow) => {
      Navigation.classList.toggle("Show", ShouldShow);
      const Icon = MenuButton.querySelector("i");
      if (Icon) {
        Icon.className = ShouldShow ? "fas fa-times" : "fas fa-bars";
      }
      document.body.classList.toggle("BodyNoScroll", ShouldShow);
    };

    MenuButton.addEventListener("click", () => {
      ToggleMenu(!Navigation.classList.contains("Show"));
    });
  },

  InitializeLazyLoad() {
    const LazyElements = document.querySelectorAll(
      "iframe.lazy-video, .FadeInElement"
    );

    if (!("IntersectionObserver" in window)) {
      LazyElements.forEach((Element) => {
        if (Element.tagName === "IFRAME") {
          Element.src = Element.dataset.src;
        }
        Element.classList.add("IsVisible");
      });
      return;
    }

    const Observer = new IntersectionObserver(
      (Entries) => {
        Entries.forEach((Entry) => {
          if (Entry.isIntersecting) {
            const Element = Entry.target;
            if (Element.tagName === "IFRAME") {
              Element.src = Element.dataset.src;
            } else {
              Element.classList.add("IsVisible");
            }
            Observer.unobserve(Element);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );

    LazyElements.forEach((Element) => Observer.observe(Element));
  },

  InitializeSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach((Link) => {
      Link.addEventListener("click", function (Event) {
        const Href = this.getAttribute("href") || "";
        if (Href === "#" || Href === "") return;

        try {
          const Target = document.querySelector(Href);
          if (Target) {
            Event.preventDefault();
            Target.scrollIntoView({ behavior: "smooth" });
          }
        } catch (Error) {
          console.warn("خطا در اسکرول:", Error);
        }
      });
    });
  },

  InitializeAccordion() {
    const AccordionHeaders = document.querySelectorAll(".AccordionHeader");

    AccordionHeaders.forEach((Header) => {
      Header.addEventListener("click", () => {
        const IsActive = Header.classList.contains("active");

        AccordionHeaders.forEach((OtherHeader) => {
          OtherHeader.classList.remove("active");
          const Panel = OtherHeader.nextElementSibling;
          if (Panel) Panel.classList.remove("active");
        });

        if (!IsActive) {
          Header.classList.add("active");
          const Panel = Header.nextElementSibling;
          if (Panel) Panel.classList.add("active");
        }
      });
    });
  },

  InitializeGalleryModal() {
    const Modal = document.getElementById("ImageModal");
    if (!Modal) return;

    const ModalImage = Modal.querySelector(".ModalImage");

    document.querySelectorAll(".GalleryItem img").forEach((Image) => {
      Image.addEventListener("click", () => {
        ModalImage.src = Image.src;
        ModalHelpers.OpenModal(Modal, Image);
      });
    });

    Modal.querySelector(".CloseBtn")?.addEventListener("click", () => {
      ModalHelpers.CloseModal(Modal);
    });

    Modal.addEventListener("click", (Event) => {
      if (Event.target === Modal) {
        ModalHelpers.CloseModal(Modal);
      }
    });

    document.addEventListener("keydown", (Event) => {
      if (Event.key === "Escape" && Modal.classList.contains("IsVisible")) {
        ModalHelpers.CloseModal(Modal);
      }
    });
  },

  InitializeCopyButtons() {
    document.querySelectorAll(".CopyBtn").forEach((Button) => {
      Button.addEventListener("click", function () {
        const TextToCopy = this.dataset.copy || "";
        Helpers.SafeClipboardWrite(TextToCopy)
          .then(() => {
            const OriginalHTML = this.innerHTML;
            this.innerHTML = '<i class="fas fa-check"></i>';

            setTimeout(() => {
              this.innerHTML = OriginalHTML;
            }, 1500);
          })
          .catch((Error) => {
            console.error("خطا در کپی:", Error);
            CreateFlash("Error", "کپی انجام نشد.");
          });
      });
    });
  },

  InitializePasswordToggle(ToggleId) {
    const ToggleButton = document.getElementById(ToggleId);
    if (!ToggleButton) return;

    let PasswordInput = null;

    if (ToggleButton.dataset && ToggleButton.dataset.target) {
      PasswordInput = document.querySelector(ToggleButton.dataset.target);
    } else {
      const PreviousElement = ToggleButton.previousElementSibling;
      if (PreviousElement && PreviousElement.tagName === "INPUT") {
        PasswordInput = PreviousElement;
      }
    }

    if (!PasswordInput) return;

    ToggleButton.addEventListener("click", function () {
      const NewType =
        PasswordInput.getAttribute("type") === "password" ? "text" : "password";
      PasswordInput.setAttribute("type", NewType);

      const Icon = this.querySelector("i");
      if (Icon) {
        Icon.classList.toggle("fa-eye");
        Icon.classList.toggle("fa-eye-slash");
      }
    });
  },
};

const App = {
  Initialize() {
    if (this._initialized) return;
    this._initialized = true;

    FormHelpers.Initialize();
    InitializeFlashSystem();
    UI.InitializeMobileMenu();
    UI.InitializeLazyLoad();
    UI.InitializeSmoothScroll();
    UI.InitializeCopyButtons();

    if (document.querySelector(".AccordionContainer")) {
      UI.InitializeAccordion();
    }

    if (document.querySelector(".GalleryGrid")) {
      UI.InitializeGalleryModal();
    }

    if (document.getElementById("CreateTeamForm")) {
      this.InitializeCreateTeamForm();
    }

    if (document.querySelector(".MembersPage")) {
      this.InitializeMembersPage();
    }

    if (document.getElementById("SignUpForm")) {
      this.InitializeSignUpForm();
    }

    if (document.getElementById("ResetForm")) {
      this.InitializeResetForm();
    }

    if (document.querySelector("form[action*='/Payment']")) {
      this.InitializePaymentForm();
    }

    if (document.getElementById("SelectLeagueForm")) {
      this.InitializeLeagueSelector();
    }

    if (document.getElementById("chat-box")) {
      this.InitializeSupportChat();
    }

    if (document.getElementById("EditForm")) {
      const Form = document.getElementById("EditForm");
      FormHelpers.PopulateProvinces(Form.querySelector('[name="Province"]'));
      FormHelpers.SetupProvinceCityListener(Form);
      FormHelpers.SetupDatePicker(Form);
    }

    if (document.getElementById("DocumentUploadForm")) {
      this.InitializeDocumentUpload();
    }

    document
      .querySelectorAll(".DeleteTeamForm, .DeleteMemberForm")
      .forEach((Form) => {
        this.InitializeDeleteConfirmation(Form);
      });
  },

  InitializeCreateTeamForm() {
    const Form = document.getElementById("CreateTeamForm");
    if (!Form) return;

    FormHelpers.PopulateProvinces(Form.querySelector('[name="Province"]'));
    FormHelpers.SetupProvinceCityListener(Form);
    FormHelpers.SetupDatePicker(Form);

    Form.addEventListener("submit", (Event) => {
      const TeamName = Form.querySelector('[name="TeamName"]')?.value || "";
      const Validation = Validators.IsValidTeamName(TeamName);

      if (!Validation.IsValid) {
        Event.preventDefault();
        CreateFlash("Error", Validation.Message);
      }
    });
  },

  InitializeResetForm() {
    const Form = document.getElementById("ResetForm");
    if (!Form) return;

    this.InitializePasswordConfirmation(
      "ResetForm",
      "newPassword",
      "confirmPassword",
      "passwordError"
    );
  },

  InitializeSupportChat() {
    const ChatContainer = document.querySelector(".ClientChatContainer");
    if (!ChatContainer) return;

    const ChatBox = document.getElementById("chat-box");
    const MessageInput = document.getElementById("message-input");
    const SendButton = document.getElementById("send-button");

    if (!ChatBox || !MessageInput || !SendButton) {
      console.error("عناصر رابط کاربری چت یافت نشد.");
      return;
    }

    const RoomID = ChatContainer.dataset.clientId;
    const HistoryURL = ChatContainer.dataset.historyUrl;
    const Socket = Helpers.SafeSocket();

    const AddMessage = (MessageData) => {
      const IsSentByUser =
        MessageData.Sender === RoomID || MessageData.Sender === "شما";

      const MessageElement = document.createElement("div");
      MessageElement.classList.add(
        "ChatMessage",
        IsSentByUser ? "Message--sent" : "Message--received"
      );

      const MetaElement = document.createElement("div");
      MetaElement.classList.add("Meta");

      const MessageDate = MessageData.Timestamp
        ? new Date(MessageData.Timestamp.replace(" ", "T"))
        : new Date();

      MetaElement.textContent = `${
        IsSentByUser ? "شما" : MessageData.Sender
      } در ${MessageDate.toLocaleTimeString()}`;

      const TextElement = document.createElement("p");
      TextElement.textContent = MessageData.Message;

      MessageElement.appendChild(MetaElement);
      MessageElement.appendChild(TextElement);
      ChatBox.appendChild(MessageElement);
    };

    const ScrollToBottom = () => {
      ChatBox.scrollTop = ChatBox.scrollHeight;
    };

    const SendMessage = () => {
      const MessageText = MessageInput.value.trim();
      if (MessageText && Socket) {
        const MessageData = {
          Room: RoomID,
          Sender: RoomID,
          Message: MessageText,
        };

        Socket.emit("send_message", MessageData);

        AddMessage({
          Sender: "شما",
          Message: MessageText,
          Timestamp: new Date().toISOString(),
        });

        MessageInput.value = "";
        MessageInput.focus();
        ScrollToBottom();
      }
    };

    const LoadHistory = async () => {
      if (!HistoryURL) {
        ChatBox.innerHTML =
          '<div style="text-align:center; color:#888;">آدرس تاریخچه گفتگو یافت نشد.</div>';
        return;
      }

      try {
        const Response = await fetch(HistoryURL);
        if (!Response.ok) {
          throw new Error(`پاسخ سرور: ${Response.status}`);
        }

        const Data = await Response.json();
        ChatBox.innerHTML = "";

        if (Data.Messages && Data.Messages.length > 0) {
          Data.Messages.forEach((Message) => {
            AddMessage({
              Sender: Message.Sender,
              Message: Message.MessageText,
              Timestamp: Message.Timestamp,
            });
          });
        } else {
          ChatBox.innerHTML =
            '<div style="text-align:center; color:#888;">هنوز پیامی وجود ندارد. سلام کنید!</div>';
        }
      } catch (Error) {
        console.error("خطا در بارگذاری تاریخچه گفتگو:", Error);
        ChatBox.innerHTML =
          '<div style="text-align:center; color:red;">خطا در بارگذاری تاریخچه گفتگو. لطفا صفحه را رفرش کنید.</div>';
      } finally {
        ScrollToBottom();
      }
    };

    SendButton.addEventListener("click", SendMessage);

    MessageInput.addEventListener("keydown", (Event) => {
      if (Event.key === "Enter" && !Event.shiftKey) {
        Event.preventDefault();
        SendMessage();
      }
    });

    if (Socket) {
      Socket.on("connect", () => {
        Socket.emit("join", { Room: RoomID });
      });

      Socket.on("ReceiveMessage", (Data) => {
        if (Data.Sender === RoomID) return;

        AddMessage({
          Sender: Data.Sender,
          Message: Data.Message,
          Timestamp: Data.timestamp,
        });
        ScrollToBottom();
      });
    }

    LoadHistory();
  },

  InitializeLeagueSelector() {
    const Form = document.getElementById("SelectLeagueForm");
    if (!Form) return;

    const LeagueOne = Form.querySelector("#leagueOne");
    const LeagueTwo = Form.querySelector("#leagueTwo");

    if (!LeagueOne || !LeagueTwo) return;

    const SyncOptions = () => {
      const LeagueOneValue = LeagueOne.value;
      const LeagueTwoValue = LeagueTwo.value;

      for (const Option of LeagueTwo.options) {
        Option.disabled =
          Option.value === LeagueOneValue && Option.value !== "";
      }

      for (const Option of LeagueOne.options) {
        Option.disabled =
          Option.value === LeagueTwoValue && Option.value !== "";
      }
    };

    LeagueOne.addEventListener("change", SyncOptions);
    LeagueTwo.addEventListener("change", SyncOptions);
    SyncOptions();
  },

  InitializePasswordConfirmation(FormId, PasswordId, ConfirmId, ErrorId) {
    const Form = document.getElementById(FormId);
    if (!Form) return;

    const PasswordInput = Form.querySelector(`#${PasswordId}`);
    const ConfirmInput = Form.querySelector(`#${ConfirmId}`);
    const ErrorElement = Form.querySelector(`#${ErrorId}`);

    if (!PasswordInput || !ConfirmInput) return;

    const ValidateMatch = () => {
      const IsMatch = PasswordInput.value === ConfirmInput.value;

      if (ErrorElement) {
        ErrorElement.classList.toggle(
          "IsVisible",
          !IsMatch && ConfirmInput.value.length > 0
        );
      }

      ConfirmInput.classList.toggle(
        "IsInvalid",
        !IsMatch && ConfirmInput.value.length > 0
      );

      return IsMatch;
    };

    Form.addEventListener("submit", (Event) => {
      if (!ValidateMatch()) {
        Event.preventDefault();
        CreateFlash("Error", "رمزهای عبور مطابقت ندارند!");
      }
    });

    PasswordInput.addEventListener("input", ValidateMatch);
    ConfirmInput.addEventListener("input", ValidateMatch);
  },

  InitializeMembersPage() {
    const Page = document.querySelector(".MembersPage");
    if (!Page) return;

    const AddForm = Page.querySelector("#AddMemberForm");
    const EditModal = document.getElementById("EditModal");
    const EditForm = Page.querySelector("#EditForm");

    if (AddForm) {
      FormHelpers.PopulateProvinces(AddForm.querySelector('[name="Province"]'));
      FormHelpers.SetupProvinceCityListener(AddForm);
      FormHelpers.SetupDatePicker(AddForm);
    }

    if (EditModal && EditForm) {
      FormHelpers.PopulateProvinces(
        EditForm.querySelector('[name="Province"]')
      );
      FormHelpers.SetupDatePicker(EditForm);
      FormHelpers.SetupProvinceCityListener(EditForm);

      Page.addEventListener("click", (Event) => {
        const EditButton = Event.target.closest(".EditBtn");
        if (!EditButton) return;

        const ButtonData = EditButton.dataset;
        const TeamID = Page.dataset.teamId;
        const MemberID = ButtonData.memberId;

        EditForm.action = `/Team/${TeamID}/EditMember/${MemberID}`;
        EditForm.querySelector('[name="Name"]').value = ButtonData.name || "";
        EditForm.querySelector('[name="NationalID"]').value =
          ButtonData.nationalId || "";
        EditForm.querySelector('[name="Role"]').value = ButtonData.role || "";
        EditForm.querySelector('[name="PhoneNumber"]').value =
          ButtonData.phoneNumber || "";

        const ProvinceSelect = EditForm.querySelector('[name="Province"]');
        ProvinceSelect.value = ButtonData.province || "";
        FormHelpers.UpdateCities(
          ProvinceSelect.value,
          EditForm.querySelector('[name="City"]')
        );

        EditForm.querySelector('[name="City"]').value = ButtonData.city || "";

        const DaySelect = EditForm.querySelector('[name="BirthDay"]');
        const MonthSelect = EditForm.querySelector('[name="BirthMonth"]');
        const YearSelect = EditForm.querySelector('[name="BirthYear"]');

        if (ButtonData.birthDate) {
          const [Year, Month, Day] = ButtonData.birthDate.split("-");
          DaySelect.value = Day || "";
          MonthSelect.value = Month || "";
          YearSelect.value = Year || "";
        } else {
          DaySelect.value = "";
          MonthSelect.value = "";
          YearSelect.value = "";
        }

        ModalHelpers.OpenModal(EditModal, EditButton);
      });

      EditModal.querySelector(".CloseBtn")?.addEventListener("click", () => {
        ModalHelpers.CloseModal(EditModal);
      });
    }
  },

  InitializeSignUpForm() {
    const Form = document.getElementById("SignUpForm");
    if (!Form) return;

    const PasswordInput = Form.querySelector("#password");
    const ConfirmInput = Form.querySelector("#confirm_password");
    const PasswordError = Form.querySelector("#passwordError");

    if (!PasswordInput || !ConfirmInput) return;

    UI.InitializePasswordToggle("password-toggle");
    UI.InitializePasswordToggle("confirm-password-toggle");

    const Requirements = {
      Length: document.getElementById("req-length"),
      Upper: document.getElementById("req-upper"),
      Lower: document.getElementById("req-lower"),
      Number: document.getElementById("req-number"),
      Special: document.getElementById("req-special"),
    };

    const ValidatePasswordStrength = () => {
      const Password = PasswordInput.value;
      let AllValid = true;

      if (Requirements.Length) {
        const IsValid = Password.length >= 8;
        Requirements.Length.className = IsValid ? "valid" : "invalid";
        if (!IsValid) AllValid = false;
      }

      if (Requirements.Upper) {
        const IsValid = /[A-Z]/.test(Password);
        Requirements.Upper.className = IsValid ? "valid" : "invalid";
        if (!IsValid) AllValid = false;
      }

      if (Requirements.Lower) {
        const IsValid = /[a-z]/.test(Password);
        Requirements.Lower.className = IsValid ? "valid" : "invalid";
        if (!IsValid) AllValid = false;
      }

      if (Requirements.Number) {
        const IsValid = /[0-9]/.test(Password);
        Requirements.Number.className = IsValid ? "valid" : "invalid";
        if (!IsValid) AllValid = false;
      }

      if (Requirements.Special) {
        const IsValid = /[!@#$%^&*(),.?":{}|<>]/.test(Password);
        Requirements.Special.className = IsValid ? "valid" : "invalid";
        if (!IsValid) AllValid = false;
      }

      return AllValid;
    };

    const ValidatePasswordMatch = () => {
      const IsMatch = PasswordInput.value === ConfirmInput.value;

      if (PasswordError) {
        PasswordError.classList.toggle(
          "IsVisible",
          !IsMatch && ConfirmInput.value.length > 0
        );
      }

      return IsMatch;
    };

    PasswordInput.addEventListener("input", () => {
      ValidatePasswordStrength();
      ValidatePasswordMatch();
    });

    ConfirmInput.addEventListener("input", ValidatePasswordMatch);

    Form.addEventListener("submit", (Event) => {
      const IsStrengthValid = ValidatePasswordStrength();
      const IsMatchValid = ValidatePasswordMatch();

      if (!IsStrengthValid || !IsMatchValid) {
        Event.preventDefault();
        CreateFlash("Error", "لطفا تمام خطاهای فرم را برطرف کنید.");
      }
    });
  },

  InitializePaymentForm() {
    const ReceiptInput = document.querySelector(
      'input[type="file"][name="receipt"]'
    );
    if (!ReceiptInput) return;

    ReceiptInput.addEventListener("change", () => {
      const File = ReceiptInput.files[0];
      if (!File) return;

      const Extension = File.name.split(".").pop().toLowerCase();
      if (!FormHelpers.AllowedExtensions.includes(Extension)) {
        CreateFlash("Error", "فرمت فایل پشتیبانی نمی‌شود.");
        ReceiptInput.value = "";
      }
    });
  },

  InitializeDeleteConfirmation() {
    const deleteModal = document.getElementById("deleteConfirmModal");
    if (!deleteModal) return;

    const modalTitle = deleteModal.querySelector("h3");
    const modalText = deleteModal.querySelector("p");
    const confirmBtn = deleteModal.querySelector("#confirmDeleteBtn");
    let formToSubmit = null;

    document.body.addEventListener("click", (event) => {
      const deleteBtn = event.target.closest(".DeleteBtn");
      if (!deleteBtn || deleteBtn.disabled) return;

      formToSubmit = deleteBtn.closest("form");
      const memberName = deleteBtn.dataset.memberName;
      const teamName = deleteBtn.dataset.teamName;

      if (memberName) {
        modalTitle.textContent = "تایید حذف عضو";
        modalText.innerHTML = `آیا از حذف <strong id="modalMemberName">${memberName}</strong> اطمینان دارید؟ این عمل غیرقابل بازگشت است.`;
        confirmBtn.textContent = "بله، حذف کن";
      } else if (teamName) {
        modalTitle.textContent = "تایید آرشیو تیم";
        modalText.innerHTML = `آیا از آرشیو کردن تیم <strong id="modalTeamName">${teamName}</strong> اطمینان دارید؟`;
        confirmBtn.textContent = "بله، آرشیو کن";
      }

      ModalHelpers.OpenModal(deleteModal, deleteBtn);
    });

    confirmBtn.addEventListener("click", () => {
      if (formToSubmit) {
        formToSubmit.submit();
      }
    });

    deleteModal.addEventListener("click", (event) => {
      if (
        event.target.matches('[data-dismiss="modal"]') ||
        event.target.matches(".CloseBtn") ||
        event.target === deleteModal
      ) {
        ModalHelpers.CloseModal(deleteModal);
      }
    });
  },

  InitializeDocumentUpload() {
    const Form = document.getElementById("DocumentUploadForm");
    if (!Form) return;

    const FileInput = Form.querySelector('input[type="file"]');
    FileInput.addEventListener("change", () => {
      const File = FileInput.files[0];
      if (!File) return;

      const Extension = File.name.split(".").pop().toLowerCase();
      const IsVideo = ["mp4", "mov", "avi", "mkv", "webm"].includes(Extension);
      const IsImage = ["png", "jpg", "jpeg", "gif", "svg"].includes(Extension);

      const VideoMaxSize = 300 * 1024 * 1024;
      const ImageMaxSize = 50 * 1024 * 1024;
      const DocumentMaxSize = 100 * 1024 * 1024;

      if (IsVideo && File.size > VideoMaxSize) {
        CreateFlash("Error", "حجم ویدئو نمی‌تواند بیشتر از ۳۰۰ مگابایت باشد.");
        FileInput.value = "";
      } else if (IsImage && File.size > ImageMaxSize) {
        CreateFlash("Error", "حجم عکس نمی‌تواند بیشتر از ۵۰ مگابایت باشد.");
        FileInput.value = "";
      } else if (!IsVideo && !IsImage && File.size > DocumentMaxSize) {
        CreateFlash("Error", "حجم فایل نمی‌تواند بیشتر از ۱۰۰ مگابایت باشد.");
        FileInput.value = "";
      }
    });
  },
};

("use strict");

const Constants = {
  Selectors: {
    MobileMenuBtn: ".MobileMenuBtn",
    NavItems: ".NavItems",
    AccordionContainer: ".AccordionContainer",
    GalleryGrid: ".GalleryGrid",
    CreateTeamForm: "#CreateTeamForm",
    MembersPage: ".MembersPage",
    SignUpForm: "#SignUpForm",
    ResetForm: "#ResetForm",
    PaymentForm: "form[action*='/Payment']",
    SelectLeagueForm: "#SelectLeagueForm",
    ChatBox: "#chat-box",
    EditForm: "#EditForm",
    DocumentUploadForm: "#DocumentUploadForm",
    DeleteTeamForm: ".DeleteTeamForm",
    DeleteMemberForm: ".DeleteMemberForm",
    ImageModal: "#ImageModal",
    GalleryItemImg: ".GalleryItem img",
    CopyBtn: ".CopyBtn",
    VideoWrapperLazy: ".VideoWrapper.lazy-video",
    PasswordInput: "#password",
    ConfirmPasswordInput: "#confirm_password",
    PasswordError: "#passwordError",
    PasswordToggle: "#password-toggle",
    ConfirmPasswordToggle: "#confirm-password-toggle",
    AdminBody: ".AdminBody",
    AdminHeaderMobileToggle: ".AdminHeader__mobile-toggle",
    AdminHeaderNav: ".AdminHeader__nav",
    RelativeTime:
      "[data-timestamp].RelativeTime, [data-timestamp].relative-time",
    AdminAddMemberForm: "#AddMemberForm",
    DeleteConfirmModal: "#deleteConfirmModal",
    ProvinceChart: "#ProvinceChart",
    CityChart: "#CityChart",
    ClientSearchInput: "#ClientSearchInput",
    ClientsTableBody: "#clients-table tbody",
    NoResultsMessage: "#NoResultsMessage",
    AdminChatContainer: ".AdminChatContainer",
    AdminChatBox: "#ChatBox",
    AdminMessageInput: "#MessageInput",
    AdminSendButton: "#SendButton",
    AdminPersonaSelect: "#PersonaSelect",
    AdminMembersPage: ".AdminMembersPage",
    MemberModal: "#MemberModal",
    MemberForm: "#MemberForm",
    MemberModalTitle: "#MemberModalTitle",
    EditButton: ".EditBtn",
  },
  Events: {
    Click: "click",
    Change: "change",
    Input: "input",
    Keydown: "keydown",
    Submit: "submit",
    DOMContentLoaded: "DOMContentLoaded",
  },
  Classes: {
    IsVisible: "IsVisible",
    Show: "Show",
    BodyNoScroll: "BodyNoScroll",
    Active: "active",
    FlashMessageClosing: "FlashMessageClosing",
    Valid: "valid",
    Invalid: "invalid",
    IsClient: "is-client",
    IsAdmin: "is-admin",
    EmptyStateRow: "EmptyStateRow",
    AdminBody: "AdminBody",
    IsOpen: "is-open",
  },
  Attributes: {
    AriaHidden: "aria-hidden",
    AriaExpanded: "aria-expanded",
    DataAction: "data-action",
    DataTarget: "data-target",
    DataType: "type",
    DataSrc: "data-src",
    DataTimestamp: "data-timestamp",
    Name: "name",
    Value: "value",
    Disabled: "disabled",
    Loading: "loading",
    Allow: "allow",
    AllowFullScreen: "allowfullscreen",
    Title: "title",
    Href: "href",
    Role: "role",
    AriaLabel: "aria-label",
    MemberId: "memberId",
    TeamId: "teamId",
    MemberName: "memberName",
    MemberNid: "memberNid",
    MemberPhone: "memberPhone",
    MemberRole: "memberRole",
    MemberProvince: "memberProvince",
    MemberCity: "memberCity",
    BirthDate: "birthDate",
    Confirm: "confirm",
  },
  Messages: {
    TeamNameEmpty: "نام تیم نمی‌تواند خالی باشد.",
    TeamNameLength: "نام تیم باید بین ۳ تا ۳۰ کاراکتر باشد.",
    TeamNameInvalidChars:
      "نام تیم فقط می‌تواند شامل حروف، اعداد، فاصله و خط زیر باشد.",
    TeamNameForbiddenWords: "نام تیم حاوی کلمات غیرمجاز است.",
    CopyError: "کپی انجام نشد.",
    PasswordMismatch: "رمزهای عبور مطابقت ندارند!",
    FormErrors: "لطفا تمام خطاهای فرم را برطرف کنید.",
    ChatElementsNotFound: "عناصر رابط کاربری چت یافت نشد.",
    HistoryURLNotFound: "آدرس تاریخچه گفتگو یافت نشد.",
    HistoryLoadError: "خطا در بارگذاری تاریخچه گفتگو. لطفا صفحه را رفرش کنید.",
    SocketNotAvailable: "اتصال لحظه‌ای برقرار نیست: Socket.IO در دسترس نیست.",
    ChatInfoNotFound: "خطا: اطلاعات ضروری چت یافت نشد.",
    ChatBoxNotFound: "عنصر ChatBox در DOM یافت نشد.",
    SocketJoinFailed: "ارسال رویداد 'join' ناموفق بود:",
    NoHistoryFound: "هیچ پیامی در تاریخچه یافت نشد.",
    ChartNetworkError: "Network response was not ok",
    ChartLoadError: "خطا در بارگذاری نمودار",
    ChartJSError: "Failed to load Chart.js script.",
    SocketWarning:
      "اتصال لحظه‌ای برقرار نیست — پیام فقط محلی نمایش داده می‌شود.",
    MessageFocusError: "خطا در فوکوس فیلد پیام:",
    VideoSizeError: "حجم ویدئو نمی‌تواند بیشتر از ۳۰۰ مگابایت باشد.",
    ImageSizeError: "حجم عکس نمی‌تواند بیشتر از ۵۰ مگابایت باشد.",
    FileSizeError: "حجم فایل نمی‌تواند بیشتر از ۱۰۰ مگابایت باشد.",
    UnsupportedFileFormat: "فرمت فایل پشتیبانی نمی‌شود.",
    ConfirmOperation: "آیا از انجام این عملیات اطمینان دارید?",
    ScrollError: "خطا در اسکرول:",
  },
};

const UI = {
  InitializeMobileMenu() {
    const MenuButton = document.querySelector(
      Constants.Selectors.MobileMenuBtn
    );
    const Navigation = document.querySelector(Constants.Selectors.NavItems);

    if (!MenuButton || !Navigation) return;

    const ToggleMenu = (ShouldShow) => {
      Navigation.classList.toggle(Constants.Classes.Show, ShouldShow);
      const Icon = MenuButton.querySelector("i");
      if (Icon) {
        Icon.className = ShouldShow ? "fas fa-times" : "fas fa-bars";
      }
      document.body.classList.toggle(
        Constants.Classes.BodyNoScroll,
        ShouldShow
      );
    };

    MenuButton.addEventListener(Constants.Events.Click, () => {
      ToggleMenu(!Navigation.classList.contains(Constants.Classes.Show));
    });
  },

  InitializeLazyLoad() {
    const LazyElements = document.querySelectorAll(
      "iframe.lazy-video, .FadeInElement"
    );

    if (!("IntersectionObserver" in window)) {
      LazyElements.forEach((Element) => {
        if (Element.tagName === "IFRAME") {
          Element.src = Element.dataset.src;
        }
        Element.classList.add(Constants.Classes.IsVisible);
      });
      return;
    }

    const Observer = new IntersectionObserver(
      (Entries) => {
        Entries.forEach((Entry) => {
          if (Entry.isIntersecting) {
            const Element = Entry.target;
            if (Element.tagName === "IFRAME") {
              Element.src = Element.dataset.src;
            } else {
              Element.classList.add(Constants.Classes.IsVisible);
            }
            Observer.unobserve(Element);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );

    LazyElements.forEach((Element) => Observer.observe(Element));
  },

  InitializeAccordion() {
    const AccordionHeaders = document.querySelectorAll(".AccordionHeader");

    AccordionHeaders.forEach((Header) => {
      Header.addEventListener(Constants.Events.Click, () => {
        const IsActive = Header.classList.contains(Constants.Classes.Active);

        AccordionHeaders.forEach((OtherHeader) => {
          OtherHeader.classList.remove(Constants.Classes.Active);
          const Panel = OtherHeader.nextElementSibling;
          if (Panel) Panel.classList.remove(Constants.Classes.Active);
        });

        if (!IsActive) {
          Header.classList.add(Constants.Classes.Active);
          const Panel = Header.nextElementSibling;
          if (Panel) Panel.classList.add(Constants.Classes.Active);
        }
      });
    });
  },

  InitializeGalleryModal() {
    const Modal = document.getElementById(Constants.Selectors.ImageModal);
    if (!Modal) return;

    const ModalImage = Modal.querySelector(".ModalImage");

    document
      .querySelectorAll(Constants.Selectors.GalleryItemImg)
      .forEach((Image) => {
        Image.addEventListener(Constants.Events.Click, () => {
          ModalImage.src = Image.src;
          ModalHelpers.OpenModal(Modal, Image);
        });
      });

    Modal.querySelector(".CloseBtn")?.addEventListener(
      Constants.Events.Click,
      () => {
        ModalHelpers.CloseModal(Modal);
      }
    );

    Modal.addEventListener(Constants.Events.Click, (Event) => {
      if (Event.target === Modal) {
        ModalHelpers.CloseModal(Modal);
      }
    });

    document.addEventListener(Constants.Events.Keydown, (Event) => {
      if (
        Event.key === "Escape" &&
        Modal.classList.contains(Constants.Classes.IsVisible)
      ) {
        ModalHelpers.CloseModal(Modal);
      }
    });
  },

  InitializeCopyButtons() {
    document.querySelectorAll(Constants.Selectors.CopyBtn).forEach((Button) => {
      Button.addEventListener(Constants.Events.Click, function () {
        const TextToCopy = this.dataset.copy || "";
        Helpers.SafeClipboardWrite(TextToCopy)
          .then(() => {
            const OriginalHTML = this.innerHTML;
            this.innerHTML = '<i class="fas fa-check"></i>';

            setTimeout(() => {
              this.innerHTML = OriginalHTML;
            }, 1500);
          })
          .catch((Error) => {
            console.error("خطا در کپی:", Error);
            CreateFlash("Error", Constants.Messages.CopyError);
          });
      });
    });
  },

  InitializeVideoPlayer() {
    const videoWrapper = document.querySelector(".VideoWrapper.lazy-video");
    if (videoWrapper) {
      videoWrapper.addEventListener(
        "click",
        () => {
          const iframe = document.createElement("iframe");
          iframe.setAttribute("src", videoWrapper.dataset.src + "&autoplay=1");
          iframe.setAttribute("title", "تیزر رسمی مسابقات آیروکاپ");
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
        { once: true }
      );
    }
  },
};

const App = {
  Initialize() {
    if (this._initialized) return;
    this._initialized = true;

    FormHelpers.Initialize();
    InitializeFlashSystem();
    UI.InitializeMobileMenu();
    UI.InitializeLazyLoad();
    UI.InitializeSmoothScroll();
    UI.InitializeCopyButtons();
    UI.InitializeVideoPlayer();

    if (document.querySelector(".AccordionContainer")) {
      UI.InitializeAccordion();
    }

    if (document.querySelector(".GalleryGrid")) {
      UI.InitializeGalleryModal();
    }

    if (document.getElementById("CreateTeamForm")) {
      this.InitializeMemberForm(document.getElementById("CreateTeamForm"));
    }

    if (document.querySelector(".MembersPage")) {
      this.InitializeMembersPage();
    }

    if (document.getElementById("SignUpForm")) {
      this.InitializeSignUpForm();
    }

    if (document.getElementById("ResetForm")) {
      this.InitializeResetForm();
    }

    if (document.querySelector("form[action*='/Payment']")) {
      this.InitializePaymentForm();
    }

    if (document.getElementById("SelectLeagueForm")) {
      this.InitializeLeagueSelector();
    }

    if (document.getElementById("chat-box")) {
      this.InitializeSupportChat();
    }

    if (document.getElementById("EditForm")) {
      const Form = document.getElementById("EditForm");
      this.InitializeMemberForm(Form);
    }

    if (document.getElementById("DocumentUploadForm")) {
      this.InitializeDocumentUpload();
    }

    document
      .querySelectorAll(".DeleteTeamForm, .DeleteMemberForm")
      .forEach((Form) => {
        this.InitializeDeleteConfirmation(Form);
      });
  },

  InitializeMemberForm(Form) {
    if (!Form) return;

    FormHelpers.PopulateProvinces(Form.querySelector('[name="Province"]'));
    FormHelpers.SetupProvinceCityListener(Form);
    FormHelpers.SetupDatePicker(Form);
  },

  InitializeCreateTeamForm() {
    const Form = document.getElementById("CreateTeamForm");
    if (!Form) return;

    this.InitializeMemberForm(Form);

    Form.addEventListener("submit", (Event) => {
      const TeamName = Form.querySelector('[name="TeamName"]')?.value || "";
      const Validation = Validators.IsValidTeamName(TeamName);

      if (!Validation.IsValid) {
        Event.preventDefault();
        CreateFlash("Error", Validation.Message);
      }
    });
  },

  InitializeResetForm() {
    const Form = document.getElementById("ResetForm");
    if (!Form) return;

    this.InitializePasswordConfirmation(
      "ResetForm",
      "newPassword",
      "confirmPassword",
      "passwordError"
    );
  },

  InitializeSupportChat() {
    const ChatContainer = document.querySelector(".ClientChatContainer");
    if (!ChatContainer) return;

    const ChatBox = document.getElementById("chat-box");
    const MessageInput = document.getElementById("message-input");
    const SendButton = document.getElementById("send-button");

    if (!ChatBox || !MessageInput || !SendButton) {
      console.error("عناصر رابط کاربری چت یافت نشد.");
      return;
    }

    const RoomID = ChatContainer.dataset.clientId;
    const HistoryURL = ChatContainer.dataset.historyUrl;
    const Socket = Helpers.SafeSocket();

    const AddMessage = (MessageData) => {
      const IsSentByUser =
        MessageData.Sender === RoomID || MessageData.Sender === "شما";

      const MessageElement = document.createElement("div");
      MessageElement.classList.add(
        "ChatMessage",
        IsSentByUser ? "Message--sent" : "Message--received"
      );

      const MetaElement = document.createElement("div");
      MetaElement.classList.add("Meta");

      const MessageDate = MessageData.Timestamp
        ? new Date(MessageData.Timestamp.replace(" ", "T"))
        : new Date();

      MetaElement.textContent = `${
        IsSentByUser ? "شما" : MessageData.Sender
      } در ${MessageDate.toLocaleTimeString()}`;

      const TextElement = document.createElement("p");
      TextElement.textContent = MessageData.Message;

      MessageElement.appendChild(MetaElement);
      MessageElement.appendChild(TextElement);
      ChatBox.appendChild(MessageElement);
    };

    const ScrollToBottom = () => {
      ChatBox.scrollTop = ChatBox.scrollHeight;
    };

    const SendMessage = () => {
      const MessageText = MessageInput.value.trim();
      if (MessageText && Socket) {
        const MessageData = {
          Room: RoomID,
          Sender: RoomID,
          Message: MessageText,
        };

        Socket.emit("send_message", MessageData);

        AddMessage({
          Sender: "شما",
          Message: MessageText,
          Timestamp: new Date().toISOString(),
        });

        MessageInput.value = "";
        MessageInput.focus();
        ScrollToBottom();
      }
    };

    const LoadHistory = async () => {
      if (!HistoryURL) {
        ChatBox.innerHTML =
          '<div style="text-align:center; color:#888;">آدرس تاریخچه گفتگو یافت نشد.</div>';
        return;
      }

      try {
        const Response = await fetch(HistoryURL);
        if (!Response.ok) {
          throw new Error(`پاسخ سرور: ${Response.status}`);
        }

        const Data = await Response.json();
        ChatBox.innerHTML = "";

        if (Data.Messages && Data.Messages.length > 0) {
          Data.Messages.forEach((Message) => {
            AddMessage({
              Sender: Message.Sender,
              Message: Message.MessageText,
              Timestamp: Message.Timestamp,
            });
          });
        } else {
          ChatBox.innerHTML =
            '<div style="text-align:center; color:#888;">هنوز پیامی وجود ندارد. سلام کنید!</div>';
        }
      } catch (Error) {
        console.error("خطا در بارگذاری تاریخچه گفتگو:", Error);
        ChatBox.innerHTML =
          '<div style="text-align:center; color:red;">خطا در بارگذاری تاریخچه گفتگو. لطفا صفحه را رفرش کنید.</div>';
      } finally {
        ScrollToBottom();
      }
    };

    SendButton.addEventListener("click", SendMessage);

    MessageInput.addEventListener("keydown", (Event) => {
      if (Event.key === "Enter" && !Event.shiftKey) {
        Event.preventDefault();
        SendMessage();
      }
    });

    if (Socket) {
      Socket.on("connect", () => {
        Socket.emit("join", { Room: RoomID });
      });

      Socket.on("ReceiveMessage", (Data) => {
        if (Data.Sender === RoomID) return;

        AddMessage({
          Sender: Data.Sender,
          Message: Data.Message,
          Timestamp: Data.timestamp,
        });
        ScrollToBottom();
      });
    }

    LoadHistory();
  },

  InitializeMembersPage() {
    const Page = document.querySelector(".MembersPage");
    if (!Page) return;

    const AddForm = Page.querySelector("#AddMemberForm");
    const EditModal = document.getElementById("EditModal");
    const EditForm = Page.querySelector("#EditForm");

    if (AddForm) {
      FormHelpers.PopulateProvinces(AddForm.querySelector('[name="Province"]'));
      FormHelpers.SetupProvinceCityListener(AddForm);
      FormHelpers.SetupDatePicker(AddForm);
    }

    if (EditModal && EditForm) {
      this.InitializeMemberForm(EditForm);

      Page.addEventListener("click", (Event) => {
        const EditButton = Event.target.closest(".EditBtn");
        if (!EditButton) return;

        const ButtonData = EditButton.dataset;
        const TeamID = Page.dataset.teamId;
        const MemberID = ButtonData.memberId;

        EditForm.action = `/Team/${TeamID}/EditMember/${MemberID}`;
        EditForm.querySelector('[name="Name"]').value = ButtonData.name || "";
        EditForm.querySelector('[name="NationalID"]').value =
          ButtonData.nationalId || "";
        EditForm.querySelector('[name="Role"]').value = ButtonData.role || "";
        EditForm.querySelector('[name="PhoneNumber"]').value =
          ButtonData.phoneNumber || "";

        const ProvinceSelect = EditForm.querySelector('[name="Province"]');
        ProvinceSelect.value = ButtonData.province || "";
        FormHelpers.UpdateCities(
          ProvinceSelect.value,
          EditForm.querySelector('[name="City"]')
        );

        EditForm.querySelector('[name="City"]').value = ButtonData.city || "";

        const DaySelect = EditForm.querySelector('[name="BirthDay"]');
        const MonthSelect = EditForm.querySelector('[name="BirthMonth"]');
        const YearSelect = EditForm.querySelector('[name="BirthYear"]');

        if (ButtonData.birthDate) {
          const [Year, Month, Day] = ButtonData.birthDate.split("-");
          DaySelect.value = Day || "";
          MonthSelect.value = Month || "";
          YearSelect.value = Year || "";
        } else {
          DaySelect.value = "";
          MonthSelect.value = "";
          YearSelect.value = "";
        }

        ModalHelpers.OpenModal(EditModal, EditButton);
      });

      EditModal.querySelector(".CloseBtn")?.addEventListener("click", () => {
        ModalHelpers.CloseModal(EditModal);
      });
    }
  },
};

const AdminApp = {
  Initialize() {
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

    if (document.querySelector(".ChartGrid")) {
      this.InitializeDashboardCharts();
    }

    if (document.getElementById("password-toggle")) {
      UI.InitializePasswordToggle("password-toggle");
    }

    UI.InitializePasswordToggle("EditPasswordToggle");

    if (document.getElementById("AddMemberForm")) {
      this.InitializeAdminAddMemberPage?.();
    }

    document.querySelectorAll(".ConfirmDelete").forEach((Form) => {
      this.InitializeDeleteConfirmation(Form);
    });
  },

  InitializeAdminMembersPage() {
    const Page = document.querySelector(".AdminMembersPage");
    if (!Page) return;

    const AddForm = document.getElementById("AddMemberForm");
    if (AddForm) {
      this.InitializeMemberForm(AddForm);
    }

    const MemberModal = document.getElementById("MemberModal");
    const MemberForm = document.getElementById("MemberForm");
    const ModalTitle = document.getElementById("MemberModalTitle");

    if (MemberModal && MemberForm && ModalTitle) {
      this.InitializeMemberForm(MemberForm);

      Page.addEventListener("click", (Event) => {
        const Trigger = Event.target.closest(
          '[data-modal-target="MemberModal"]'
        );
        if (!Trigger) return;

        const TriggerData = Trigger.dataset;
        const TeamID = Page.dataset.teamId;

        ModalTitle.textContent = `ویرایش ${TriggerData.memberName}`;
        MemberForm.action = `/Admin/Team/${TeamID}/EditMember/${TriggerData.memberId}`;
        MemberForm.querySelector('[name="Name"]').value =
          TriggerData.memberName || "";
        MemberForm.querySelector('[name="NationalID"]').value =
          TriggerData.memberNid || "";
        MemberForm.querySelector('[name="PhoneNumber"]').value =
          TriggerData.memberPhone || "";
        MemberForm.querySelector('[name="Role"]').value =
          TriggerData.memberRole || "";

        const ProvinceSelect = MemberForm.querySelector('[name="Province"]');
        ProvinceSelect.value = TriggerData.memberProvince || "";

        ModalHelpers.OpenModal(MemberModal, Trigger);
      });
    }
  },

  InitializeAdminAddMemberPage() {
    const AddForm = document.getElementById("AddMemberForm");
    if (!AddForm) return;

    this.InitializeMemberForm(AddForm);
  },
};
const AdminApp = {
  Initialize() {
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

    if (document.querySelector(".ChartGrid")) {
      this.InitializeDashboardCharts();
    }

    if (document.getElementById("password-toggle")) {
      UI.InitializePasswordToggle("password-toggle");
    }

    UI.InitializePasswordToggle("EditPasswordToggle");

    if (document.getElementById("AddMemberForm")) {
      this.InitializeAdminAddMemberPage?.();
    }

    document.querySelectorAll(".ConfirmDelete").forEach((Form) => {
      this.InitializeDeleteConfirmation(Form);
    });
  },

  InitializeAdminMembersPage() {
    const Page = document.querySelector(".AdminMembersPage");
    if (!Page) return;

    const AddForm = document.getElementById("AddMemberForm");
    if (AddForm) {
      FormHelpers.PopulateProvinces(AddForm.querySelector('[name="Province"]'));
      FormHelpers.SetupProvinceCityListener(AddForm);
      FormHelpers.SetupDatePicker(AddForm);
    }

    const MemberModal = document.getElementById("MemberModal");
    const MemberForm = document.getElementById("MemberForm");
    const ModalTitle = document.getElementById("MemberModalTitle");

    if (MemberModal && MemberForm && ModalTitle) {
      FormHelpers.PopulateProvinces(
        MemberForm.querySelector('[name="Province"]')
      );
      FormHelpers.SetupProvinceCityListener(MemberForm);
      FormHelpers.SetupDatePicker(MemberForm);

      Page.addEventListener("click", (Event) => {
        const Trigger = Event.target.closest(
          '[data-modal-target="MemberModal"]'
        );
        if (!Trigger) return;

        const TriggerData = Trigger.dataset;
        const TeamID = Page.dataset.teamId;

        ModalTitle.textContent = `ویرایش ${TriggerData.memberName}`;
        MemberForm.action = `/Admin/Team/${TeamID}/EditMember/${TriggerData.memberId}`;
        MemberForm.querySelector('[name="Name"]').value =
          TriggerData.memberName || "";
        MemberForm.querySelector('[name="NationalID"]').value =
          TriggerData.memberNid || "";
        MemberForm.querySelector('[name="PhoneNumber"]').value =
          TriggerData.memberPhone || "";
        MemberForm.querySelector('[name="Role"]').value =
          TriggerData.memberRole || "";

        const ProvinceSelect = MemberForm.querySelector('[name="Province"]');
        ProvinceSelect.value = TriggerData.memberProvince || "";

        ModalHelpers.OpenModal(MemberModal, Trigger);
      });
    }
  },

  InitializeMenu() {
    const ToggleButton = document.querySelector(".AdminHeader__mobile-toggle");
    const Navigation = document.querySelector(".AdminHeader__nav");

    if (!ToggleButton || !Navigation) return;

    ToggleButton.addEventListener("click", () => {
      const IsOpen = Navigation.classList.toggle("is-open");
      ToggleButton.setAttribute("aria-expanded", IsOpen);

      const Icon = ToggleButton.querySelector("i");
      if (Icon) {
        Icon.className = IsOpen ? "fas fa-times" : "fas fa-bars";
      }
    });
  },

  InitializeRelativeTime() {
    const TimeElements = Array.from(
      document.querySelectorAll(
        "[data-timestamp].RelativeTime, [data-timestamp].relative-time"
      )
    );

    if (!TimeElements.length) return;

    const FormatTime = (DateObject) => {
      if (!DateObject) return "";

      const Now = new Date();
      const Diff = Math.floor((Now - DateObject) / 1000);

      if (Diff < 5) return "همین الان";
      if (Diff < 60) return `${Diff} ثانیه پیش`;
      if (Diff < 3600) return `${Math.floor(Diff / 60)} دقیقه پیش`;
      if (Diff < 86400) return `${Math.floor(Diff / 3600)} ساعت پیش`;
      if (Diff < 2592000) return `${Math.floor(Diff / 86400)} روز پیش`;
      if (Diff < 31536000) return `${Math.floor(Diff / 2592000)} ماه پیش`;

      return `${Math.floor(Diff / 31536000)} سال پیش`;
    };

    const UpdateAllTimes = () => {
      TimeElements.forEach((Element) => {
        const RawTimestamp =
          Element.dataset.timestamp ||
          Element.getAttribute("data-timestamp") ||
          "";
        const DateObject = Helpers.ParseTimestamp(RawTimestamp);

        if (!DateObject) {
          Element.textContent = RawTimestamp;
        } else {
          Element.textContent = FormatTime(DateObject);
          Element.setAttribute("title", DateObject.toLocaleString());
        }
      });
    };

    UpdateAllTimes();

    if (this._relativeTimeInterval) {
      clearInterval(this._relativeTimeInterval);
    }

    this._relativeTimeInterval = setInterval(UpdateAllTimes, 60 * 1000);
  },

  InitializeAdminAddMemberPage() {
    const AddForm = document.getElementById("AddMemberForm");
    if (!AddForm) return;

    FormHelpers.PopulateProvinces(AddForm.querySelector('[name="Province"]'));
    FormHelpers.SetupProvinceCityListener(AddForm);
    FormHelpers.SetupDatePicker(AddForm);
  },

  InitializeDeleteConfirmation(Form) {
    const Message =
      Form.dataset.confirm || "آیا از انجام این عملیات اطمینان دارید؟";
    Form.addEventListener("submit", (Event) => {
      if (!confirm(Message)) {
        Event.preventDefault();
      }
    });
  },

  InitializeDashboardCharts() {
    const ProvinceCanvas = document.getElementById("ProvinceChart");
    const CityCanvas = document.getElementById("CityChart");

    const CreateChart = async (
      CanvasElement,
      DataURL,
      ChartType,
      Label,
      IndexAxis = "x"
    ) => {
      if (!CanvasElement) return;

      try {
        const Response = await fetch(DataURL);
        if (!Response.ok) throw new Error("Network response was not ok");

        const ChartData = await Response.json();
        const ChartColors = [
          "#3182ce",
          "#2b6cb0",
          "#2c7a7b",
          "#2d3748",
          "#805ad5",
          "#b7791f",
        ];

        new Chart(CanvasElement.getContext("2d"), {
          type: ChartType,
          data: {
            labels: ChartData.Labels,
            datasets: [
              {
                label: Label,
                data: ChartData.Data,
                backgroundColor: ChartColors,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: IndexAxis,
            plugins: {
              legend: {
                position: ChartType === "doughnut" ? "bottom" : "top",
                display: ChartType !== "bar",
              },
            },
          },
        });
      } catch (Error) {
        console.error(`Failed to load chart data from ${DataURL}:`, Error);
        const Context = CanvasElement.getContext("2d");
        Context.font = "16px Arial";
        Context.fillStyle = "#888";
        Context.textAlign = "center";
        Context.fillText(
          "خطا در بارگذاری نمودار",
          CanvasElement.width / 2,
          CanvasElement.height / 2
        );
      }
    };

    const ChartScript = document.createElement("script");
    ChartScript.src = "https://cdn.jsdelivr.net/npm/chart.js";
    ChartScript.onload = () => {
      CreateChart(
        ProvinceCanvas,
        "/API/Admin/ProvinceDistribution",
        "doughnut",
        "توزیع استانی"
      );
      CreateChart(
        CityCanvas,
        "/API/AdminCityDistribution",
        "bar",
        "تعداد شرکت‌کنندگان",
        "y"
      );
    };

    ChartScript.onerror = () =>
      console.error("Failed to load Chart.js script.");
    document.body.appendChild(ChartScript);
  },

  InitializeAdminModals() {
    document.body.addEventListener("click", (Event) => {
      const Trigger = Event.target.closest("[data-modal-target]");
      if (Trigger) {
        const Modal = document.getElementById(Trigger.dataset.modalTarget);
        if (Modal) {
          ModalHelpers.OpenModal(Modal, Trigger);
        }
      }

      if (Event.target.classList.contains("CloseBtn")) {
        const Modal = Event.target.closest(".Modal");
        if (Modal) {
          ModalHelpers.CloseModal(Modal);
        }
      }
    });

    window.addEventListener("click", (Event) => {
      if (Event.target.classList.contains("Modal")) {
        ModalHelpers.CloseModal(Event.target);
      }
    });

    document.addEventListener("keydown", (Event) => {
      if (Event.key === "Escape") {
        document
          .querySelectorAll(".Modal.IsVisible")
          .forEach(ModalHelpers.CloseModal);
      }
    });
  },

  InitializeClientSearch() {
    const SearchInput = document.getElementById("ClientSearchInput");
    const TableBody = document.querySelector("#clients-table tbody");

    if (!SearchInput || !TableBody) return;

    const TableRows = Array.from(TableBody.querySelectorAll("tr"));
    const NoResultsMessage = document.getElementById("NoResultsMessage");

    const PerformSearch = () => {
      const SearchTerm = SearchInput.value.toLowerCase().trim();
      let VisibleCount = 0;

      TableRows.forEach((Row) => {
        if (Row.classList.contains("EmptyStateRow")) return;

        const RowText = Row.textContent.toLowerCase();
        const IsMatch = RowText.includes(SearchTerm);
        Row.style.display = IsMatch ? "" : "none";

        if (IsMatch) VisibleCount++;
      });

      if (NoResultsMessage) {
        NoResultsMessage.style.display =
          VisibleCount === 0 ? "table-row" : "none";
      }
    };

    SearchInput.addEventListener("input", Helpers.Debounce(PerformSearch, 180));
  },

  InitializeChat() {
    const ChatContainer = document.querySelector(".AdminChatContainer");
    if (!ChatContainer) return;

    const Elements = {
      ChatBox: document.getElementById("ChatBox"),
      MessageInput: document.getElementById("MessageInput"),
      SendButton: document.getElementById("SendButton"),
      PersonaSelect: document.getElementById("PersonaSelect"),
    };

    const Socket = Helpers.SafeSocket();

    if (!Socket) {
      console.warn("اتصال لحظه‌ای برقرار نیست: Socket.IO در دسترس نیست.");
      Elements.ChatBox?.insertAdjacentHTML(
        "afterbegin",
        '<div class="EmptyStateRow">اتصال لحظه‌ای غیرفعال است</div>'
      );
    }

    const State = {
      RoomID: ChatContainer.dataset.clientId,
      HistoryURL: ChatContainer.dataset.historyUrl,
      Socket: Socket,
    };

    if (!State.RoomID || !State.HistoryURL) {
      console.error("شناسه کاربر یا آدرس تاریخچه گفتگو یافت نشد.");
      if (Elements.ChatBox) {
        Elements.ChatBox.innerHTML =
          '<div class="EmptyStateRow">خطا: اطلاعات ضروری چت یافت نشد.</div>';
      }
      return;
    }

    if (!Elements.ChatBox) {
      console.error("عنصر ChatBox در DOM یافت نشد.");
      return;
    }

    const ScrollToBottom = () => {
      try {
        Elements.ChatBox.scrollTop = Elements.ChatBox.scrollHeight;
      } catch (Error) {
        console.warn("خطا در اسکرول به پایین:", Error);
      }
    };

    const AppendMessage = (Message) => {
      if (!Message || !Message.MessageText) return;

      const IsClient = String(Message.Sender) === State.RoomID;
      const SenderName = IsClient ? "کاربر" : Message.Sender;
      const MessageElement = document.createElement("div");
      const MessageClass = IsClient ? "is-client" : "is-admin";

      MessageElement.className = `ChatMessage ${MessageClass}`;

      const SenderDiv = document.createElement("div");
      SenderDiv.className = "ChatMessage__sender";
      SenderDiv.textContent = SenderName;

      const TextElement = document.createElement("p");
      TextElement.className = "ChatMessage__text";
      TextElement.textContent = Message.MessageText;

      const MetaDiv = document.createElement("div");
      MetaDiv.className = "ChatMessage__meta";
      MetaDiv.textContent = Message.Timestamp || "";

      MessageElement.appendChild(SenderDiv);
      MessageElement.appendChild(TextElement);
      MessageElement.appendChild(MetaDiv);

      Elements.ChatBox.appendChild(MessageElement);
    };

    if (State.Socket) {
      State.Socket.on("connect", () => {
        try {
          State.Socket.emit("join", { Room: State.RoomID });
        } catch (Error) {
          console.warn("ارسال رویداد 'join' ناموفق بود:", Error);
        }
      });

      State.Socket.on("ReceiveMessage", (Message) => {
        Elements.ChatBox.querySelector(".EmptyStateRow")?.remove();
        AppendMessage({
          Sender: Message.Sender,
          MessageText: Message.Message,
          Timestamp: Message.Timestamp,
        });
        ScrollToBottom();
      });
    } else {
      Elements.ChatBox.querySelector(".EmptyStateRow")?.remove();
      const InfoElement = document.createElement("div");
      InfoElement.className = "EmptyStateRow";
      InfoElement.textContent = "اتصال لحظه‌ای غیرفعال است";
      Elements.ChatBox.appendChild(InfoElement);
    }

    const LoadChatHistory = async () => {
      try {
        const Response = await fetch(State.HistoryURL);
        if (!Response.ok) throw new Error("دریافت تاریخچه گفتگو ناموفق بود");

        const Data = await Response.json();
        Elements.ChatBox.innerHTML = "";

        if (Data?.Messages?.length > 0) {
          Data.Messages.forEach(AppendMessage);
        } else {
          Elements.ChatBox.innerHTML =
            '<div class="EmptyStateRow">هیچ پیامی در تاریخچه یافت نشد.</div>';
        }

        ScrollToBottom();
      } catch (Error) {
        console.error(Error);
        Elements.ChatBox.innerHTML =
          '<div class="EmptyStateRow">خطا در بارگذاری تاریخچه چت.</div>';
      }
    };

    const SendMessage = () => {
      if (!Elements.MessageInput) return;

      const MessageText = Elements.MessageInput.value.trim();
      if (!MessageText) return;

      if (State.Socket) {
        try {
          State.Socket.emit("send_message", {
            Room: State.RoomID,
            Sender: Elements.PersonaSelect
              ? Elements.PersonaSelect.value
              : "admin",
            Message: MessageText,
          });
        } catch (Error) {
          console.warn("ارسال پیام لحظه‌ای ناموفق بود:", Error);
        }
      } else {
        CreateFlash(
          "Warning",
          "اتصال لحظه‌ای برقرار نیست — پیام فقط محلی نمایش داده می‌شود."
        );
      }

      AppendMessage({
        Sender: Elements.PersonaSelect ? Elements.PersonaSelect.value : "admin",
        MessageText: MessageText,
        Timestamp: new Date().toLocaleTimeString(),
      });

      Elements.MessageInput.value = "";

      try {
        Elements.MessageInput.focus();
      } catch (Error) {
        console.warn("خطا در فوکوس فیلد پیام:", Error);
      }

      ScrollToBottom();
    };

    if (Elements.SendButton) {
      Elements.SendButton.addEventListener("click", SendMessage);
    }

    if (Elements.MessageInput) {
      Elements.MessageInput.addEventListener("keydown", (Event) => {
        if (Event.key === "Enter" && !Event.shiftKey) {
          Event.preventDefault();
          SendMessage();
        }
      });
    }

    LoadChatHistory();
    ScrollToBottom();
  },
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.classList.contains("AdminBody")) {
    AdminApp.Initialize();
  } else {
    App.Initialize();
  }
});
