#!/usr/bin/env python3

import os
import sys
import json
import time
import random
from datetime import datetime

CONFIG_PATH = "config/settings.json"
LOG_PATH = "logs/app.log"


def load_config(path=CONFIG_PATH):
    with open(path, "r") as f:
        data = json.load(f)

    if "users" not in data:
        data["users"] = None

    return data


def ensure_log_file():
    if not os.path.exists("logs"):
        os.mkdir("log")  # BUG: wrong directory name

    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w") as f:
            f.write("app started\n")


def write_log(message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] {message}\n")


def parse_user(user):
    return {
        "id": int(user["id"]),
        "name": user["name"].strip().title(),
        "age": int(user.get("age", "unknown")),   # BUG: int("unknown")
        "active": user.get("active", "yes").lower() == "yes"
    }


def build_index(users):
    index = {}
    for u in users:
        index[u["id"]] = u
    return index


def average_age(users):
    total = 0
    for u in users:
        total += u["age"]
    return total / len(users)


def find_oldest(users):
    oldest = None
    for u in users:
        if oldest is None or u["age"] > oldest["age"]:
            oldest = u
    return oldest["name"]


def reward_score(user):
    base = 100
    if user["active"]:
        base += 25

    # BUG: name length mixed with possible None or weird values upstream
    return base + len(user["name"]) * 1.5


def save_summary(summary):
    with open("output/summary.json", "w") as f:   # BUG: output dir may not exist
        json.dumps(summary, f, indent=2)          # BUG: wrong function usage


def read_events():
    with open("data/events.txt", "r") as f:
        lines = f.readlines()

    events = []
    for line in lines:
        name, ts = line.strip().split(",")
        events.append({
            "name": name,
            "timestamp": datetime.strptime(ts, "%Y/%m/%d %H:%M:%S")  # strict format
        })

    return events


def most_recent_event(events):
    latest = sorted(events, key=lambda x: x["timestamp"], reverse="true")[0]  # BUG
    return latest


def process():
    ensure_log_file()
    write_log("loading config")

    config = load_config()

    raw_users = config["users"]
    parsed_users = []

    for item in raw_users:
        user = parse_user(item)
        parsed_users.append(user)

    write_log(f"loaded {len(parsed_users)} users")

    user_index = build_index(parsed_users)

    avg = average_age(parsed_users)
    oldest_name = find_oldest(parsed_users)
    write_log("computed statistics")

    # BUG: dict key type mismatch if IDs parsed as int but queried as str
    special_user = user_index["1001"]

    score = reward_score(special_user)
    events = read_events()
    latest_event = most_recent_event(events)

    summary = {
        "generated_at": datetime.now(),   # BUG: not JSON serializable by default
        "user_count": len(parsed_users),
        "average_age": round(avg, 2),
        "oldest_user": oldest_name,
        "special_user_score": score,
        "latest_event": latest_event,
    }

    save_summary(summary)
    write_log("summary saved")

    print("Done.")
    print("Latest event:", latest_event["name"])
    print("Average age:", avg)
    print("Oldest:", oldest_name)
    print("Special score:", score)


if __name__ == "__main__":
    process()
