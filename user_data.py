import json
import os
from typing import TypedDict

import platformdirs


class UserData(TypedDict):
    data_version: int
    username: str
    uuid: str
    token: str


dirs = platformdirs.PlatformDirs("muncher")
DATA_FILE = "data.json"
DATA_PATH = dirs.user_data_path / DATA_FILE
user_data: None | UserData = None


try:
    with open(DATA_PATH) as f:
        as_json = json.load(f)
        user_data = UserData(**as_json)
        print("Loaded user data for: ", user_data["username"])
except FileNotFoundError:
    print("user data not found")


def save(new_data: UserData):
    global user_data
    user_data = new_data
    os.makedirs(dirs.user_data_path, exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(new_data, f)
