"""Define SQLite database structure."""

# Disable style checks that are not useful for declarative models
# pylint: disable=missing-module-docstring, invalid-name
# pylint: disable=too-few-public-methods, missing-class-docstring
# pylint: disable=line-too-long, unnecessary-pass

import enum
import datetime
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    Mapped,
    mapped_column,
)
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    TEXT,
    Enum as sql_alchemy_enum,
    DateTime,
    Boolean,
    Index,
    Date,
)


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy models."""
    pass


class LabeledEnum(enum.Enum):
    """Enum with human-readable label attached to each member."""

    def __new__(cls, value, label):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj


class EntityStatus(LabeledEnum):
    """Status of entities."""
    ACTIVE = ("active", "فعال")
    INACTIVE = ("inactive", "غیرفعال")
    WITHDRAWN = ("withdrawn", "منصرف شده")


class MemberRole(LabeledEnum):
    """Role of a team member."""
    LEADER = ("leader", "سرپرست")
    COACH = ("coach", "مربی")
    MEMBER = ("member", "عضو")


class PaymentStatus(LabeledEnum):
    """Status of a payment."""
    PENDING = ("pending", "در حال بررسی")
    APPROVED = ("approved", "تایید شده")
    REJECTED = ("rejected", "رد شده")


class Client(Base):
    """Client / account owner."""
    __tablename__ = "clients"

    client_id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    registration_date = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    education_level = Column(String)
    status: Mapped[EntityStatus] = mapped_column(
        sql_alchemy_enum(EntityStatus),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    is_phone_verified = Column(Boolean, default=False)
    phone_verification_code = Column(String)
    verification_code_timestamp = Column(DateTime)

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


class League(Base):
    """League / competition tier."""
    __tablename__ = "leagues"

    league_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    icon = Column(String)
    description = Column(TEXT)


class Team(Base):
    """Team entity."""
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        Integer,
        ForeignKey("clients.client_id"),
        nullable=False,
        index=True,
    )
    team_name = Column(String, nullable=False, unique=True)
    league_one_id = Column(Integer, ForeignKey("leagues.league_id"))
    league_two_id = Column(Integer, ForeignKey("leagues.league_id"))
    team_registration_date = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    average_age = Column(Integer, default=0)
    average_provinces = Column(String)
    status: Mapped[EntityStatus] = mapped_column(
        sql_alchemy_enum(EntityStatus),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    unpaid_members_count = Column(Integer, default=0)

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
    """Payments uploaded by clients for teams."""
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(
        Integer,
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True,
    )
    client_id = Column(
        Integer,
        ForeignKey("clients.client_id"),
        nullable=False,
        index=True,
    )
    amount = Column(Integer, nullable=False)
    members_paid_for = Column(Integer, nullable=False)
    receipt_filename = Column(String, nullable=False)
    upload_date = Column(DateTime, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        sql_alchemy_enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    team = relationship("Team", back_populates="payments")
    client = relationship("Client", back_populates="payments")


class Member(Base):
    """Team member record."""
    __tablename__ = "members"

    member_id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(
        Integer,
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    birth_date = Column(Date, nullable=False)
    national_id = Column(String, unique=True, nullable=False)
    role: Mapped[MemberRole] = mapped_column(
        sql_alchemy_enum(MemberRole),
        nullable=False,
    )
    status: Mapped[EntityStatus] = mapped_column(
        sql_alchemy_enum(EntityStatus),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    city_id = Column(Integer, ForeignKey("cities.city_id"), nullable=False)

    team = relationship("Team", back_populates="members")
    city = relationship("City", back_populates="members")

    _leader_where = f"role = '{MemberRole.LEADER.value}'"
    __table_args__ = (
        Index(
            "one_leader_per_team_idx",
            "team_id",
            unique=True,
            sqlite_where=_leader_where,
        ),
    )


class Province(Base):
    """Province containing cities."""
    __tablename__ = "provinces"

    province_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    cities = relationship(
        "City",
        back_populates="province",
        cascade="all, delete-orphan",
    )


class City(Base):
    """City inside a province."""
    __tablename__ = "cities"

    city_id = Column(Integer, primary_key=True, autoincrement=True)
    province_id = Column(
        Integer,
        ForeignKey("provinces.province_id"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    province = relationship("Province", back_populates="cities")
    members = relationship("Member", back_populates="city")


class LoginAttempt(Base):
    """Login attempt audit."""
    __tablename__ = "login_attempts"

    attempt_id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    is_success = Column(Boolean, nullable=False)


class News(Base):
    """Published news articles."""
    __tablename__ = "news"

    news_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(TEXT, nullable=False)
    content = Column(TEXT, nullable=False)
    image_path = Column(String)
    publish_date = Column(DateTime, nullable=False, index=True)
    template_path = Column(String)


class HistoryLog(Base):
    """History log entries."""
    __tablename__ = "history_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        Integer,
        ForeignKey("clients.client_id"),
        nullable=False,
        index=True,
    )
    admin_involved = Column(Boolean, default=False)
    action = Column(TEXT, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    client = relationship("Client", back_populates="history_logs")


class PasswordReset(Base):
    """Password reset codes."""
    __tablename__ = "password_resets"

    reset_id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String, nullable=False, index=True)
    identifier_type = Column(String, nullable=False)
    code = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)


class ChatMessage(Base):
    """Chat messages stored per client."""
    __tablename__ = "chat_messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        Integer,
        ForeignKey("clients.client_id"),
        nullable=False,
        index=True,
    )
    message_text = Column(TEXT, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    sender = Column(String, nullable=False)
    client = relationship("Client", back_populates="chat_messages")


class TeamDocument(Base):
    """Uploaded documents related to teams."""
    __tablename__ = "team_documents"

    document_id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(
        Integer,
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True,
    )
    client_id = Column(
        Integer,
        ForeignKey("clients.client_id"),
        nullable=False,
        index=True,
    )
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    upload_date = Column(DateTime, nullable=False)
    team = relationship("Team", back_populates="documents")
    client = relationship("Client", back_populates="team_documents")
