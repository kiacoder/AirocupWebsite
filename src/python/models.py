"""ORM models for the application using SQLAlchemy."""

from __future__ import annotations

import enum
import datetime
from typing import Optional

from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    Mapped,
    mapped_column,
)
from sqlalchemy import (
    String,
    ForeignKey,
    TEXT,
    Enum as sql_alchemy_enum,
    DateTime,
    Boolean,
    Index,
    Date,
    text,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class LabeledEnum(enum.Enum):
    """Enum base class with an additional label attribute for display."""

    label: str

    def __new__(cls, value, label):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj


class EntityStatus(LabeledEnum):
    """Enumeration for the status of entities (e.g., client, فeam)."""

    ACTIVE = ("active", "فعال")
    INACTIVE = ("inactive", "غیرفعال")
    WITHDRAWN = ("withdrawn", "منصرف شده")


class MemberRole(LabeledEnum):
    """Enumeration for the role of a team member."""

    LEADER = ("leader", "سرپرست")
    COACH = ("coach", "مربی")
    MEMBER = ("member", "عضو")


class PaymentStatus(LabeledEnum):
    """Enumeration for the status of a payment."""

    PENDING = ("pending", "در حال بررسی")
    APPROVED = ("approved", "تایید شده")
    REJECTED = ("rejected", "رد شده")


class Client(Base):
    """Represents a registered user account (client)."""

    __tablename__ = "clients"
    __table_args__ = (
        Index("clients_status_email_idx", "status", "email"),
        Index("clients_phone_status_idx", "phone_number", "status"),
    )
    client_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    phone_number: Mapped[str] = mapped_column(String(11), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_date: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    status: Mapped[EntityStatus] = mapped_column(
        sql_alchemy_enum(EntityStatus),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verification_code: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )
    verification_code_timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )

    teams = relationship(
        "Team",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    payments = relationship(
        "Payment",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    history_logs = relationship(
        "HistoryLog",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    chat_messages = relationship(
        "ChatMessage",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    team_documents = relationship(
        "TeamDocument",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    @property
    def ClientID(self) -> int:
        return self.client_id

    @property
    def Email(self) -> str:
        return self.email

    @property
    def PhoneNumber(self) -> str:
        return self.phone_number

    @property
    def RegistrationDate(self) -> datetime.datetime:
        return self.registration_date


class League(Base):
    """Represents a competition league that a team can join."""

    __tablename__ = "leagues"
    league_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    icon: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)


class Team(Base):
    """Represents a team of members, owned by a client."""

    __tablename__ = "teams"
    __table_args__ = (
        Index("teams_client_status_idx", "client_id", "status"),
        Index("teams_status_registration_idx", "status", "team_registration_date"),
    )
    team_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.client_id"),
        nullable=False,
        index=True,
    )
    team_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    league_one_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("leagues.league_id"), nullable=True
    )
    league_two_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("leagues.league_id"), nullable=True
    )
    education_level: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    team_registration_date: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    average_age: Mapped[int] = mapped_column(default=0)
    average_provinces: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[EntityStatus] = mapped_column(
        sql_alchemy_enum(EntityStatus),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    unpaid_members_count: Mapped[int] = mapped_column(default=0)

    client = relationship("Client", back_populates="teams")
    members = relationship(
        "Member",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    payments = relationship(
        "Payment",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    documents = relationship(
        "TeamDocument",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    league_one = relationship(
        "League",
        foreign_keys=[league_one_id],
    )
    league_two = relationship(
        "League",
        foreign_keys=[league_two_id],
    )


class Payment(Base):
    """Represents a payment transaction for a team."""

    __tablename__ = "payments"
    __table_args__ = (
        Index("payments_status_upload_idx", "status", "upload_date"),
        Index("payments_team_status_idx", "team_id", "status"),
    )

    payment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.team_id"), nullable=False, index=True
    )
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.client_id"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(nullable=False)
    members_paid_for: Mapped[int] = mapped_column(nullable=False)
    receipt_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    paid_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    upload_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        sql_alchemy_enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    team = relationship("Team", back_populates="payments")
    client = relationship("Client", back_populates="payments")


class Member(Base):
    """Represents an individual member belonging to a team."""

    __tablename__ = "members"

    member_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.team_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    national_id: Mapped[str] = mapped_column(String(10), nullable=False)
    role: Mapped[MemberRole] = mapped_column(
        sql_alchemy_enum(MemberRole),
        nullable=False,
    )
    status: Mapped[EntityStatus] = mapped_column(
        sql_alchemy_enum(EntityStatus),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.city_id"), nullable=False, index=True
    )

    team = relationship("Team", back_populates="members")
    city = relationship("City", back_populates="members")

    __table_args__ = (
        Index(
            "one_leader_per_team_idx",
            "team_id",
            unique=True,
            sqlite_where=text(f"role = '{MemberRole.LEADER.value}'"),
        ),
        Index("members_team_status_idx", "team_id", "status"),
    )


class Province(Base):
    """Represents a province in Iran."""

    __tablename__ = "provinces"
    province_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    cities = relationship(
        "City",
        back_populates="province",
        cascade="all, delete-orphan",
    )


class City(Base):
    """Represents a city within a province."""

    __tablename__ = "cities"
    city_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    province_id: Mapped[int] = mapped_column(
        ForeignKey("provinces.province_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    province = relationship("Province", back_populates="cities")
    members = relationship("Member", back_populates="city")


class LoginAttempt(Base):
    """Logs a single login attempt for security monitoring."""

    __tablename__ = "login_attempts"
    attempt_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False)


class News(Base):
    """Represents a news article to be displayed on the site."""

    __tablename__ = "news"
    news_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publish_date: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    template_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class HistoryLog(Base):
    """Logs significant actions performed by clients or admins."""

    __tablename__ = "history_logs"
    log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.client_id"), nullable=False, index=True
    )
    admin_involved: Mapped[bool] = mapped_column(Boolean, default=False)
    action: Mapped[str] = mapped_column(TEXT, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    client = relationship("Client", back_populates="history_logs")


class PasswordReset(Base):
    """Stores tokens for password reset requests."""

    __tablename__ = "password_resets"
    reset_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )


class ChatMessage(Base):
    """Represents a single message in the admin-client chat."""

    __tablename__ = "chat_messages"
    message_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.client_id"), nullable=False, index=True
    )
    message_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    sender: Mapped[str] = mapped_column(String(20), nullable=False)
    client = relationship("Client", back_populates="chat_messages")


class TeamDocument(Base):
    """Stores metadata about documents uploaded for a team."""

    __tablename__ = "team_documents"

    document_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.team_id"), nullable=False, index=True
    )
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.client_id"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    upload_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    team = relationship("Team", back_populates="documents")
    client = relationship("Client", back_populates="team_documents")