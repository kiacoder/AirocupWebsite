import os
import pandas as pd
import sqlite3
import bcrypt
import jdatetime
from sqlalchemy.orm import Session
from contextlib import closing
import re

# --- Make sure you have added the SQLAlchemy models to Data.py before running! ---
try:
    from New.Database import (
        Base,
        Engine,
        Client,
        Team,
        Member,
        Path,
        GetDataBaseSession,
    )
except ImportError as e:
    print("❌ CRITICAL ERROR: Could not import from Data.py.")
    print(
        "Please ensure you have added the SQLAlchemy model definitions to your Data.py file."
    )
    print(f"Details: {e}")
    exit()

# --- Configuration ---
OLD_DATA_DIR = os.path.join(Path.StaticDir, "DataBase", "OLD")
DB_SOURCES = [
    os.path.join(Path.DatabaseDir, "Airocup.db"),
    os.path.join(OLD_DATA_DIR, "Airocup_ChatGPT.db"),
    os.path.join(OLD_DATA_DIR, "Airocup old.db"),
    os.path.join(OLD_DATA_DIR, "Airocup_notfixed.db"),
]
FINAL_DB_PATH = Path.DataBase

COLUMN_MAP = {
    "email": "Email",
    "user_email": "Email",
    "EmailAddress": "Email",
    "phone": "PhoneNumber",
    "phone_number": "PhoneNumber",
    "mobile": "PhoneNumber",
    "password": "Password",
    "pass": "Password",
    "name": "Name",
    "team_name": "TeamName",
}


def hash_password(password):
    if not password or not isinstance(password, str):
        password = "DefaultPassword@123"
    if password.startswith("$2b$"):
        return password
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def sanitize_phone(phone):
    if not phone or not isinstance(phone, str):
        return None
    return re.sub(r"\D", "", phone)


def process_data():
    all_clients_df = pd.DataFrame()
    all_teams_df = pd.DataFrame()
    all_members_df = pd.DataFrame()

    print("--- 1. EXTRACTING DATA ---")
    for db_path in DB_SOURCES:
        if not os.path.exists(db_path):
            print(f"⚠️  Warning: Database file not found, skipping: {db_path}")
            continue

        print(f"Reading from: {os.path.basename(db_path)}")
        try:
            with sqlite3.connect(db_path) as conn:
                if pd.read_sql_query(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='Clients'",
                    conn,
                ).empty:
                    print("   - No 'Clients' table found, skipping.")
                    continue

                clients = pd.read_sql_query("SELECT * FROM Clients", conn)
                teams = pd.read_sql_query("SELECT * FROM Teams", conn)
                members = pd.read_sql_query("SELECT * FROM Members", conn)

                if not clients.empty:
                    clients["OldClientID"] = clients["ClientID"]
                    all_clients_df = pd.concat(
                        [all_clients_df, clients], ignore_index=True
                    )

                if not teams.empty:
                    teams["OldTeamID"] = teams["TeamID"]
                    teams["SourceDB"] = db_path
                    all_teams_df = pd.concat([all_teams_df, teams], ignore_index=True)

                if not members.empty:
                    members["SourceDB"] = db_path
                    all_members_df = pd.concat(
                        [all_members_df, members], ignore_index=True
                    )
        except Exception as e:
            print(f"❌ Error reading {os.path.basename(db_path)}: {e}")

    print("\n--- 2. TRANSFORMING & CLEANING DATA ---")

    print("Processing Clients...")
    all_clients_df.rename(columns=COLUMN_MAP, inplace=True)
    if "Email" in all_clients_df.columns:
        all_clients_df["Email"] = all_clients_df["Email"].str.lower().str.strip()
    if "PhoneNumber" in all_clients_df.columns:
        all_clients_df["PhoneNumber"] = all_clients_df["PhoneNumber"].apply(
            sanitize_phone
        )

    all_clients_df.dropna(subset=["Email", "PhoneNumber"], inplace=True)
    all_clients_df.drop_duplicates(subset=["Email"], keep="first", inplace=True)
    all_clients_df.drop_duplicates(subset=["PhoneNumber"], keep="first", inplace=True)

    all_clients_df["Password"] = all_clients_df.get(
        "Password", pd.Series(dtype="str")
    ).apply(hash_password)
    all_clients_df["IsActive"] = 1
    all_clients_df["IsPhoneVerified"] = 1
    if "RegistrationDate" not in all_clients_df.columns:
        all_clients_df["RegistrationDate"] = jdatetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    print(f"Found {len(all_clients_df)} unique clients.")

    print("Processing Teams...")
    all_teams_df.rename(columns=COLUMN_MAP, inplace=True)
    all_teams_df.drop_duplicates(subset=["TeamName"], keep="first", inplace=True)
    all_teams_df["IsActive"] = 1
    if "TeamRegistrationDate" not in all_teams_df.columns:
        all_teams_df["TeamRegistrationDate"] = jdatetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    print(f"Found {len(all_teams_df)} unique teams.")

    print("Processing Members...")
    all_members_df.rename(columns=COLUMN_MAP, inplace=True)
    all_members_df["Status"] = "فعال"
    all_members_df["IsActive"] = 1
    all_members_df.dropna(subset=["TeamID", "NationalID"], inplace=True)
    all_members_df.drop_duplicates(
        subset=["TeamID", "NationalID", "SourceDB"], keep="first", inplace=True
    )
    print(f"Found {len(all_members_df)} unique member entries.")

    print("\n--- 3. LOADING DATA INTO NEW DATABASE ---")
    if os.path.exists(FINAL_DB_PATH):
        os.remove(FINAL_DB_PATH)
        print("Removed old final database.")

    Base.metadata.create_all(Engine)
    print("Created new database with a clean schema.")

    with closing(GetDataBaseSession()) as db_session:
        client_records = all_clients_df.to_dict("records")
        new_clients = []
        for record in client_records:
            valid_data = {
                key: value
                for key, value in record.items()
                if key in Client.__table__.columns
            }
            valid_data.pop("ClientID", None)  # <<< FINAL FIX
            new_clients.append(Client(**valid_data))

        db_session.add_all(new_clients)
        db_session.commit()
        print(f"✅ Loaded {len(new_clients)} clients.")

        print("Re-mapping foreign keys...")
        client_id_map = {
            old_id: new_client.ClientID
            for old_id, new_client in zip(all_clients_df["OldClientID"], new_clients)
        }

        all_teams_df["NewClientID"] = all_teams_df["ClientID"].map(client_id_map)
        all_teams_df.dropna(subset=["NewClientID"], inplace=True)
        all_teams_df["ClientID"] = all_teams_df["NewClientID"].astype(int)

        team_records = all_teams_df.to_dict("records")
        new_teams = []
        for record in team_records:
            valid_data = {
                key: value
                for key, value in record.items()
                if key in Team.__table__.columns
            }
            valid_data.pop("TeamID", None)  # <<< FINAL FIX
            new_teams.append(Team(**valid_data))

        db_session.add_all(new_teams)
        db_session.commit()
        print(f"✅ Loaded {len(new_teams)} teams.")

        team_id_map = {}
        for old_team_info, new_team in zip(team_records, new_teams):
            key = (old_team_info["SourceDB"], old_team_info["OldTeamID"])
            team_id_map[key] = new_team.TeamID

        all_members_df["NewTeamID"] = all_members_df.apply(
            lambda row: team_id_map.get((row.get("SourceDB"), row.get("TeamID"))),
            axis=1,
        )
        all_members_df.dropna(subset=["NewTeamID"], inplace=True)
        all_members_df["TeamID"] = all_members_df["NewTeamID"].astype(int)

        member_records = all_members_df.to_dict("records")
        new_members = []
        for record in member_records:
            valid_data = {
                key: value
                for key, value in record.items()
                if key in Member.__table__.columns
            }
            valid_data.pop("MemberID", None)  # <<< FINAL FIX
            new_members.append(Member(**valid_data))

        db_session.add_all(new_members)
        db_session.commit()
        print(f"✅ Loaded {len(new_members)} members.")

    print("\n--- MIGRATION COMPLETE ---")
    print(f"🎉 Final database created at: {FINAL_DB_PATH}")


if __name__ == "__main__":
    process_data()
