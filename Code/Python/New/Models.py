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
    WITH_DRAWN = ("with_drawn", "منصرف شده")


class MemberRole(LabeledEnum):
    """Role of a team member."""
    LEADER = ("Leader", "سرپرست")
    COACH = ("Coach", "مربی")
    MEMBER = ("Member", "عضو")


class PaymentStatus(LabeledEnum):
    """Status of a payment."""
    PENDING = ("Pending", "در حال بررسی")
    APPROVED = ("Approved", "تایید شده")
    REJECTED = ("Rejected", "رد شده")


class Client(Base):
    """Client / account owner."""
    __tablename__ = "Clients"

    ClientID = Column(Integer, primary_key=True, autoincrement=True)
    PhoneNumber = Column(String, nullable=False, unique=True)
    Email = Column(String, nullable=False, unique=True)
    Password = Column(String, nullable=False)
    RegistrationDate = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    EducationLevel = Column(String)
    Status: Mapped[EntityStatus] = mapped_column(
        sql_alchemy_enum(EntityStatus),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    IsPhoneVerified = Column(Boolean, default=False)
    PhoneVerificationCode = Column(String)
    VerificationCodeTimestamp = Column(DateTime)

    Teams = relationship(
        "Team",
        back_populates="Client",
        cascade="all, delete-orphan",
    )
    Payments = relationship(
        "Payment",
        back_populates="Client",
        cascade="all, delete-orphan",
    )
    HistoryLogs = relationship(
        "HistoryLog",
        back_populates="Client",
        cascade="all, delete-orphan",
    )
    ChatMessages = relationship(
        "ChatMessage",
        back_populates="Client",
        cascade="all, delete-orphan",
    )
    TeamDocuments = relationship(
        "TeamDocument",
        back_populates="Client",
        cascade="all, delete-orphan",
    )


class League(Base):
    """League / competition tier."""
    __tablename__ = "Leagues"

    LeagueID = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String, nullable=False, unique=True)
    Icon = Column(String)
    Description = Column(TEXT)


class Team(Base):
    """Team entity."""
    __tablename__ = "Teams"

    TeamID = Column(Integer, primary_key=True, autoincrement=True)
    ClientID = Column(
        Integer,
        ForeignKey("Clients.ClientID"),
        nullable=False,
        index=True,
    )
    TeamName = Column(String, nullable=False, unique=True)
    LeagueOneID = Column(Integer, ForeignKey("Leagues.LeagueID"))
    LeagueTwoID = Column(Integer, ForeignKey("Leagues.LeagueID"))
    TeamRegistrationDate = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    AverageAge = Column(Integer, default=0)
    AverageProvinces = Column(String)
    Status: Mapped[EntityStatus] = mapped_column(
        sql_alchemy_enum(EntityStatus),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    UnpaidMembersCount = Column(Integer, default=0)

    Client = relationship("Client", back_populates="Teams")
    Members = relationship(
        "Member",
        back_populates="Team",
        cascade="all, delete-orphan",
    )
    Payments = relationship(
        "Payment",
        back_populates="Team",
        cascade="all, delete-orphan",
    )
    Documents = relationship(
        "TeamDocument",
        back_populates="Team",
        cascade="all, delete-orphan",
    )
    LeagueOne = relationship(
        "League",
        foreign_keys=[LeagueOneID],
    )
    LeagueTwo = relationship(
        "League",
        foreign_keys=[LeagueTwoID],
    )


class Payment(Base):
    """Payments uploaded by clients for teams."""
    __tablename__ = "Payments"

    PaymentID = Column(Integer, primary_key=True, autoincrement=True)
    TeamID = Column(
        Integer,
        ForeignKey("Teams.TeamID"),
        nullable=False,
        index=True,
    )
    ClientID = Column(
        Integer,
        ForeignKey("Clients.ClientID"),
        nullable=False,
        index=True,
    )
    Amount = Column(Integer, nullable=False)
    MembersPaidFor = Column(Integer, nullable=False)
    ReceiptFilename = Column(String, nullable=False)
    UploadDate = Column(DateTime, nullable=False)
    Status: Mapped[PaymentStatus] = mapped_column(
        sql_alchemy_enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    Team = relationship("Team", back_populates="Payments")
    Client = relationship("Client", back_populates="Payments")


class Member(Base):
    """Team member record."""
    __tablename__ = "Members"

    MemberID = Column(Integer, primary_key=True, autoincrement=True)
    TeamID = Column(
        Integer,
        ForeignKey("Teams.TeamID"),
        nullable=False,
        index=True,
    )
    Name = Column(String, nullable=False)
    BirthDate = Column(Date, nullable=False)
    NationalID = Column(String, unique=True, nullable=False)
    Role: Mapped[MemberRole] = mapped_column(
        sql_alchemy_enum(MemberRole),
        nullable=False,
    )
    Status: Mapped[EntityStatus] = mapped_column(
        sql_alchemy_enum(EntityStatus),
        default=EntityStatus.ACTIVE,
        nullable=False,
    )
    CityID = Column(Integer, ForeignKey("Cities.CityID"), nullable=False)

    Team = relationship("Team", back_populates="Members")
    City = relationship("City", back_populates="Members")

    _leader_where = f"Role = '{MemberRole.LEADER.value}'"
    __table_args__ = (
        Index(
            "one_leader_per_team_idx",
            "TeamID",
            unique=True,
            sqlite_where=_leader_where,
        ),
    )


class Province(Base):
    """Province containing cities."""
    __tablename__ = "Provinces"

    ProvinceID = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String, nullable=False, unique=True)
    Cities = relationship(
        "City",
        back_populates="Province",
        cascade="all, delete-orphan",
    )


class City(Base):
    """City inside a province."""
    __tablename__ = "Cities"

    CityID = Column(Integer, primary_key=True, autoincrement=True)
    ProvinceID = Column(
        Integer,
        ForeignKey("Provinces.ProvinceID"),
        nullable=False,
        index=True,
    )
    Name = Column(String, nullable=False)
    Province = relationship("Province", back_populates="Cities")
    Members = relationship("Member", back_populates="City")


class LoginAttempt(Base):
    """Login attempt audit."""
    __tablename__ = "LoginAttempts"

    AttemptID = Column(Integer, primary_key=True, autoincrement=True)
    Identifier = Column(String, nullable=False, index=True)
    IPAddress = Column(String, nullable=False)
    Timestamp = Column(DateTime, nullable=False, index=True)
    IsSuccess = Column(Boolean, nullable=False)


class News(Base):
    """Published news articles."""
    __tablename__ = "News"

    NewsID = Column(Integer, primary_key=True, autoincrement=True)
    Title = Column(TEXT, nullable=False)
    Content = Column(TEXT, nullable=False)
    ImagePath = Column(String)
    PublishDate = Column(DateTime, nullable=False, index=True)
    TemplatePath = Column(String)


class HistoryLog(Base):
    """History log entries."""
    __tablename__ = "HistoryLog"

    LogID = Column(Integer, primary_key=True, autoincrement=True)
    ClientID = Column(
        Integer,
        ForeignKey("Clients.ClientID"),
        nullable=False,
        index=True,
    )
    AdminInvolved = Column(Boolean, default=False)
    Action = Column(TEXT, nullable=False)
    Timestamp = Column(DateTime, nullable=False)
    Client = relationship("Client", back_populates="HistoryLogs")


class PasswordReset(Base):
    """Password reset codes."""
    __tablename__ = "PasswordResets"

    ResetID = Column(Integer, primary_key=True, autoincrement=True)
    Identifier = Column(String, nullable=False, index=True)
    IdentifierType = Column(String, nullable=False)
    Code = Column(String, nullable=False)
    Timestamp = Column(DateTime, nullable=False, index=True)


class ChatMessage(Base):
    """Chat messages stored per client."""
    __tablename__ = "ChatMessages"

    MessageID = Column(Integer, primary_key=True, autoincrement=True)
    ClientID = Column(
        Integer,
        ForeignKey("Clients.ClientID"),
        nullable=False,
        index=True,
    )
    MessageText = Column(TEXT, nullable=False)
    Timestamp = Column(DateTime, nullable=False, index=True)
    Sender = Column(String, nullable=False)
    Client = relationship("Client", back_populates="ChatMessages")


class TeamDocument(Base):
    """Uploaded documents related to teams."""
    __tablename__ = "TeamDocuments"

    DocumentID = Column(Integer, primary_key=True, autoincrement=True)
    TeamID = Column(
        Integer,
        ForeignKey("Teams.TeamID"),
        nullable=False,
        index=True,
    )
    ClientID = Column(
        Integer,
        ForeignKey("Clients.ClientID"),
        nullable=False,
        index=True,
    )
    FileName = Column(String, nullable=False)
    FileType = Column(String, nullable=False)
    UploadDate = Column(DateTime, nullable=False)
    Team = relationship("Team", back_populates="Documents")
    Client = relationship("Client", back_populates="TeamDocuments")
