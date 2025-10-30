"use strict";
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
    const IsLeapYearFunction = (Year) =>
      [1, 5, 9, 13, 17, 22, 26, 30].includes(Year % 33);
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
      (EntriesList) => {
        EntriesList.forEach((Entry) => {
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
        const TargetElement = document.querySelector(this.getAttribute("href"));
        if (TargetElement) {
          Event.preventDefault();
          TargetElement.scrollIntoView({ behavior: "smooth" });
        }
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
          OtherHeaderElement.nextElementSibling.classList.remove("active");
        });
        if (!IsActive) {
          HeaderElement.classList.add("active");
          HeaderElement.nextElementSibling.classList.add("active");
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
        const CopyValue = this.dataset.copy;
        navigator.clipboard
          .writeText(CopyValue)
          .then(() => {
            const OriginalIconHtml = this.innerHTML;
            this.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
              this.innerHTML = OriginalIconHtml;
            }, 1500);
          })
          .catch((Error) => console.error("Failed to copy:", Error));
      });
    });
  },
  InitializePasswordToggle: function (ToggleId) {
    const ToggleElement = document.getElementById(ToggleId);
    if (!ToggleElement) return;
    const InputElement = ToggleElement.previousElementSibling;
    if (!InputElement || InputElement.tagName !== "INPUT") return;
    ToggleElement.addEventListener("click", function () {
      const InputType =
        InputElement.getAttribute("type") === "password" ? "text" : "password";
      InputElement.setAttribute("type", InputType);
      this.querySelector("i").classList.toggle("fa-eye");
      this.querySelector("i").classList.toggle("fa-eye-slash");
    });
  },
};

const App = {
  Initialize: function () {
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
    if (document.getElementById("ChatBox")) this.InitializeSupportChat();
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
    const ChatBoxElement = document.getElementById("ChatBox");
    if (!ChatBoxElement) return;
    const MessageInputElement = document.getElementById("MessageInput");
    const SendButtonElement = document.getElementById("SendButton");
    const RoomName = window.AirocupData?.ClientID || null;
    const SenderID = window.AirocupData?.ClientID || "User";
    const AdministratorPersonas = window.AirocupData?.AdminPersonas || [];
    if (!RoomName) {
      console.error("Chat Room ID not found.");
      return;
    }
    const SocketIO = io();
    const ScrollToBottom = () => {
      ChatBoxElement.scrollTop = ChatBoxElement.scrollHeight;
    };
    const AddMessageToBox = ({ Sender, Message, Timestamp }) => {
      ChatBoxElement.querySelector(".ChatPlaceholder")?.remove();
      const MessageDiv = document.createElement("div");
      const MessageClass = AdministratorPersonas.includes(Sender)
        ? "AdminMessage"
        : "ClientMessage";
      MessageDiv.className = `Message ${MessageClass}`;
      const CleanMessage = Message.replace(/</g, "&lt;").replace(/>/g, "&gt;");
      MessageDiv.innerHTML = `
              <div class="MessageSender">${Sender}</div>
              <p>${CleanMessage}</p>
              <div class="MessageMeta">${Timestamp}</div>
            `;
      ChatBoxElement.appendChild(MessageDiv);
      ScrollToBottom();
    };
    SocketIO.on("connect", () => {
      SocketIO.emit("join", { Room: RoomName });
    });
    SocketIO.on("ReceiveMessage", (Data) => {
      AddMessageToBox(Data);
    });
    const SendMessage = () => {
      const MessageText = MessageInputElement.value.trim();
      if (MessageText) {
        const MessageData = {
          Room: RoomName,
          Sender: SenderID,
          Message: MessageText,
        };
        SocketIO.emit("send_message", MessageData);
        const CurrentDate = new Date();
        const TemporaryTimestamp = `${CurrentDate.getHours()}:${String(
          CurrentDate.getMinutes()
        ).padStart(2, "0")}`;
        AddMessageToBox({
          Sender: "شما",
          Message: MessageText,
          Timestamp: TemporaryTimestamp,
        });
        MessageInputElement.value = "";
        MessageInputElement.focus();
      }
    };
    SendButtonElement.addEventListener("click", SendMessage);
    MessageInputElement.addEventListener("keydown", (Event) => {
      if (Event.key === "Enter") SendMessage();
    });
    ScrollToBottom();
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
        ProvinceSelectElement.dispatchEvent(new Event("change"));
        setTimeout(() => {
          EditFormElement.querySelector('[name="City"]').value =
            DataSet.city || "";
        }, 100);
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
        ProvinceSelectElement.dispatchEvent(new Event("change"));
        setTimeout(() => {
          MemberFormElement.querySelector('[name="City"]').value =
            DataSet.memberCity || "";
        }, 100);
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
      const ProvinceData = JSON.parse(
        ChartGridElement.dataset.provinceData || "{}"
      );
      const CityData = JSON.parse(ChartGridElement.dataset.cityData || "{}");
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
      if (ContextProvince && ProvinceData.Labels) {
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
      if (ContextCity && CityData.Labels) {
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
    const TableRowsList = TableBodyElement.querySelectorAll("tr");
    const NoResultsMessageElement = document.getElementById("NoResultsMessage");
    SearchInputElement.addEventListener("keyup", () => {
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
    });
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
    const StateDictionary = {
      RoomID: ChatContainerElement.dataset.clientId,
      HistoryURL: ChatContainerElement.dataset.historyUrl,
      SocketIO: io(),
    };
    if (!StateDictionary.RoomID || !StateDictionary.HistoryURL) {
      console.error("Chat client ID or history URL is missing.");
      ElementsDictionary.ChatBox.innerHTML =
        '<div class="EmptyStateRow">خطا: اطلاعات ضروری چت یافت نشد.</div>';
      return;
    }
    const ScrollToBottomFunction = () => {
      ElementsDictionary.ChatBox.scrollTop =
        ElementsDictionary.ChatBox.scrollHeight;
    };
    const AppendMessageFunction = (MessageObject) => {
      if (!MessageObject || !MessageObject.MessageText) return;
      const IsClientBoolean =
        String(MessageObject.Sender) === StateDictionary.RoomID;
      const SenderName = IsClientBoolean ? "کاربر" : MessageObject.Sender;
      const MessageElement = document.createElement("div");
      const MessageClass = IsClientBoolean ? "is-client" : "is-admin";
      MessageElement.className = `ChatMessage ${MessageClass}`;
      const SanitizedMessage = MessageObject.MessageText.replace(
        /</g,
        "&lt;"
      ).replace(/>/g, "&gt;");
      MessageElement.innerHTML = `
              <div class="ChatMessage__sender">${SenderName}</div>
              <p class="ChatMessage__text">${SanitizedMessage}</p>
              <div class="ChatMessage__meta">${
                MessageObject.Timestamp || ""
              }</div>
            `;
      ElementsDictionary.ChatBox.appendChild(MessageElement);
    };
    const LoadChatHistoryFunction = async () => {
      try {
        const Response = await fetch(StateDictionary.HistoryURL);
        if (!Response.ok) throw new Error("Failed to fetch history");
        const Data = await Response.json();
        ElementsDictionary.ChatBox.innerHTML = "";
        if (Data?.Messages?.length > 0)
          Data.Messages.forEach(AppendMessageFunction);
        else
          ElementsDictionary.ChatBox.innerHTML =
            '<div class="EmptyStateRow">هیچ پیامی در تاریخچه یافت نشد.</div>';
        ScrollToBottomFunction();
      } catch (Error) {
        console.error(Error);
        ElementsDictionary.ChatBox.innerHTML =
          '<div class="EmptyStateRow">خطا در بارگذاری تاریخچه چت.</div>';
      }
    };
    const SendMessageFunction = () => {
      const MessageText = ElementsDictionary.MessageInput.value.trim();
      if (!MessageText) return;
      StateDictionary.SocketIO.emit("send_message", {
        Room: StateDictionary.RoomID,
        Sender: ElementsDictionary.PersonaSelect.value,
        Message: MessageText,
      });
      ElementsDictionary.MessageInput.value = "";
      ElementsDictionary.MessageInput.focus();
    };
    StateDictionary.SocketIO.on("connect", () =>
      StateDictionary.SocketIO.emit("join", { Room: StateDictionary.RoomID })
    );
    StateDictionary.SocketIO.on("ReceiveMessage", (MessageReceived) => {
      ElementsDictionary.ChatBox.querySelector(".EmptyStateRow")?.remove();
      AppendMessageFunction({
        Sender: MessageReceived.Sender,
        MessageText: MessageReceived.Message,
        Timestamp: MessageReceived.Timestamp,
      });
      ScrollToBottomFunction();
    });
    ElementsDictionary.SendButton.addEventListener(
      "click",
      SendMessageFunction
    );
    ElementsDictionary.MessageInput.addEventListener("keydown", (Event) => {
      if (Event.key === "Enter" && !Event.shiftKey) {
        Event.preventDefault();
        SendMessageFunction();
      }
    });
    LoadChatHistoryFunction();
    ScrollToBottomFunction();
  },
  InitializeRelativeTime: function () {
    const TimeElementsList = document.querySelectorAll(".RelativeTime");
    if (TimeElementsList.length === 0) return;
    const FormatRelativeTimeFunction = (Timestamp) => {
      if (!Timestamp) return "";
      const MessageDate = new Date(
        Timestamp.replace(" ", "T").replace(/\//g, "-")
      );
      const CurrentDate = new Date();
      const SecondsValue = Math.round((CurrentDate - MessageDate) / 1000);
      if (isNaN(SecondsValue)) return Timestamp;
      if (SecondsValue < 60) return "لحظاتی پیش";
      const MinutesValue = Math.round(SecondsValue / 60);
      if (MinutesValue < 60) return `${MinutesValue} دقیقه پیش`;
      const HoursValue = Math.round(MinutesValue / 60);
      if (HoursValue < 24) return `${HoursValue} ساعت پیش`;
      const DaysValue = Math.round(HoursValue / 24);
      if (DaysValue === 1) return "دیروز";
      if (DaysValue < 30) return `${DaysValue} روز پیش`;
      return MessageDate.toLocaleDateString("fa-IR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    };
    TimeElementsList.forEach((Element) => {
      const Timestamp = Element.dataset.timestamp;
      if (Timestamp) {
        Element.textContent = FormatRelativeTimeFunction(Timestamp);
        Element.setAttribute("title", Timestamp);
      }
    });
  },
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.classList.contains("AdminBody")) AdminApp.Initialize();
  else App.Initialize();
});
