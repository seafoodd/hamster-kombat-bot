import base64
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

SYNC_URL = "https://api.hamsterkombat.io/clicker/sync"
TAP_URL = "https://api.hamsterkombat.io/clicker/tap"
CLAIM_DAILY_CIPHER_URL = "https://api.hamsterkombat.io/clicker/claim-daily-cipher"
CLAIM_DAILY_COMBO_URL = "https://api.hamsterkombat.io/clicker/claim-daily-combo"
UPGRADES_FOR_BUY_URL = "https://api.hamsterkombat.io/clicker/upgrades-for-buy"
BUY_UPGRADE_URL = "https://api.hamsterkombat.io/clicker/buy-upgrade"
CONFIG_URL = "https://api.hamsterkombat.io/clicker/config"
DAILY_COMBO_URL = "https://api21.datavibe.top/api/GetCombo"
CHECK_TASK_URL = "https://api.hamsterkombat.io/clicker/check-task"

DONE_MESSAGE = "DONE!"
ERROR_MESSAGE = "ERROR!"

PROFIT_TO_PRICE_RATIO = float(os.getenv('PROFIT_TO_PRICE_RATIO'))
WELCOME_SCREEN = os.getenv('WELCOME_SCREEN') == 'True'
SLEEP_TIME = int(os.getenv('SLEEP_TIME'))
MINIMUM_BALANCE = float(os.getenv('MINIMUM_BALANCE'))

AUTH_TOKENS = []

available_taps = 6500
earn_per_tap = 1


def read_tokens_from_file(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f]


def do_all_taps_for_user(auth_token) -> None:
    headers = {
        "Authorization": auth_token,
    }

    response = requests.post(SYNC_URL, headers=headers)

    if response.status_code == 200:
        data = response.json()
        available_taps = data["clickerUser"]["availableTaps"]
        earn_per_tap = data["clickerUser"]["earnPerTap"]
    else:
        print(ERROR_MESSAGE, response.status_code)
        return

    # define the data for the second request
    data = {
        "count": available_taps // earn_per_tap,
        "availableTaps": available_taps,
        "timestamp": int(time.time())
    }

    # send the tap requests
    requests.post(TAP_URL, headers=headers, json=data)
    print(DONE_MESSAGE)


def get_user_balance(auth_token) -> float:
    headers = {
        "Authorization": auth_token,
    }
    response = requests.post(SYNC_URL, headers=headers)
    if response.status_code == 200:
        data = response.json()
        balance = data["clickerUser"]["balanceCoins"]
        return balance
    else:
        print("Error:", response.status_code)
        return 0


def decode_cipher(cipher: str) -> str:
    encoded = cipher[:3] + cipher[4:]
    return base64.b64decode(encoded).decode('utf-8')


def get_cipher_for_user(auth_token) -> None:
    response = requests.post(CONFIG_URL, headers={"Authorization": auth_token})
    if response.status_code == 200:
        data = response.json()
        if data["dailyCipher"]["isClaimed"]:
            print("ALREADY CLAIMED!")
            return

        cipher = decode_cipher(data["dailyCipher"]["cipher"])
        response = requests.post(CLAIM_DAILY_CIPHER_URL,
                                 headers={"Authorization": auth_token}, json={'cipher': cipher})
        print(DONE_MESSAGE if response.status_code == 200 else ERROR_MESSAGE)

    else:
        print("Error:", response.status_code)


def is_card_valid(card, balance, data):
    upgrade = next((upgrade for upgrade in data["upgradesForBuy"] if upgrade["id"] == card), None)

    if not upgrade or upgrade['isAvailable'] or upgrade['condition']["_type"] != 'ByUpgrade':
        return False

    condition_card = {'level': upgrade['condition']["level"], 'id': upgrade['condition']["upgradeId"]}
    condition_upgrade = next(
        (upgrade for upgrade in data["upgradesForBuy"] if upgrade["id"] == condition_card['id']), None)
    if not condition_upgrade:
        return False

    levels_needed = condition_card['level'] - condition_upgrade['level']
    if condition_upgrade['price'] * 1.07 ** levels_needed > balance:
        return False

    return True


def buy_card(auth_token, card, balance, data):
    upgrade = next((upgrade for upgrade in data["upgradesForBuy"] if upgrade["id"] == card), None)
    condition_card = {'level': upgrade['condition']["level"], 'id': upgrade['condition']["upgradeId"]}
    condition_upgrade = next(
        (upgrade for upgrade in data["upgradesForBuy"] if upgrade["id"] == condition_card['id']), None)

    levels_needed = condition_card['level'] - condition_upgrade['level']
    for _ in range(levels_needed + 1):
        balance -= condition_upgrade['price']
        buy_upgrade_by_id(auth_token, condition_card['id'])

    return balance - upgrade["price"]


def get_daily_combo_for_user(auth_token) -> None:
    response = requests.post(UPGRADES_FOR_BUY_URL, headers={"Authorization": auth_token})
    data = response.json()
    has_daily_combo = data["dailyCombo"]["isClaimed"]
    if has_daily_combo:
        print("ALREADY CLAIMED!")
        return

    combo_cards = requests.post(DAILY_COMBO_URL).json()["combo"]
    taken_combo_cards = [card for card in data["dailyCombo"]["upgradeIds"]]
    cards_to_buy = [card for card in combo_cards if card not in taken_combo_cards]

    balance = get_user_balance(auth_token)
    for card in cards_to_buy:
        if is_card_valid(card, balance, data):
            balance = buy_card(auth_token, card, balance, data)

    if len(data["dailyCombo"]["upgradeIds"]) == 3:
        response = requests.post(CLAIM_DAILY_COMBO_URL, headers={"Authorization": auth_token})
        if response.status_code == 200:
            print(DONE_MESSAGE)
        else:
            print(ERROR_MESSAGE, response.status_code)


def buy_upgrade_by_id(auth_token, upgrade_id) -> None:
    requests.post(BUY_UPGRADE_URL, headers={"Authorization": auth_token}, json={
        "upgradeId": upgrade_id,
        "timestamp": int(time.time())
    })
    print("Bought upgrade with ID:", upgrade_id)


def is_upgrade_valid(upgrade, balance):
    price = upgrade["price"]
    profit_per_hour = upgrade["profitPerHour"]
    is_available = upgrade["isAvailable"]
    is_expired = upgrade["isExpired"]

    if 'totalCooldownSeconds' in upgrade and upgrade["cooldownSeconds"] > 0:
        return False

    if not is_available or is_expired:
        return False

    if profit_per_hour <= 0 or price / profit_per_hour > PROFIT_TO_PRICE_RATIO:
        return False

    if balance - price <= MINIMUM_BALANCE:
        return False

    return True


def buy_upgrades_for_user(auth_token) -> None:
    balance = get_user_balance(auth_token)
    if balance < MINIMUM_BALANCE:
        print("INSUFFICIENT BALANCE!")
        return

    # Initialize a flag to track if an upgrade was bought in the last iteration
    upgrade_bought = True

    # Continue looping as long as an upgrade is being bought
    while upgrade_bought:
        upgrade_bought = False  # Reset the flag at the start of each iteration

        response = requests.post(UPGRADES_FOR_BUY_URL, headers={"Authorization": auth_token})
        if response.status_code != 200:
            print(ERROR_MESSAGE, response.status_code)
            return

        data = response.json()
        upgrade_objects = data["upgradesForBuy"]

        for upgrade in upgrade_objects:
            if is_upgrade_valid(upgrade, balance):
                buy_upgrade_by_id(auth_token, upgrade['id'])
                balance -= upgrade["price"]
                upgrade_bought = True  # Set the flag to True if an upgrade was bought
                break  # Break the loop as soon as an upgrade is bought

    print(DONE_MESSAGE)


def get_streak_for_user(auth_token) -> None:
    requests.post(CHECK_TASK_URL, headers={"Authorization": auth_token}, json={"taskId": "streak_days"})
    print(DONE_MESSAGE)


def main():
    while True:
        for auth_token in AUTH_TOKENS:
            # /clicker/sync
            data = requests.post(SYNC_URL,
                                 headers={"Authorization": auth_token}).json()
            # write all the useful info about user
            print(f'''
            {"-" * 30}
            # User ID: {data["clickerUser"]["id"]:<17} #
            # Balance: {int(data["clickerUser"]["balanceCoins"]):<17} #
            # Available Taps: {data["clickerUser"]["availableTaps"]:<10} #
            {"-" * 30}
            ''')

            print("Tapping... ", end='', flush=True)
            do_all_taps_for_user(auth_token)

            print("Getting Streak... ", end='', flush=True)
            get_streak_for_user(auth_token)

            print("Claiming Daily Combo... ", end='', flush=True)
            get_daily_combo_for_user(auth_token)

            print("Claiming Daily Cipher... ", end='', flush=True)
            get_cipher_for_user(auth_token)

            print("Buying upgrades... ", end='', flush=True)
            buy_upgrades_for_user(auth_token)

            print("-" * 50)

        print(f"Waiting for {SLEEP_TIME} seconds...")
        print("-" * 50)
        time.sleep(SLEEP_TIME)


def set_auth_tokens():
    global AUTH_TOKENS
    AUTH_TOKENS = read_tokens_from_file("tokens.txt")
    for i, auth_token in enumerate(AUTH_TOKENS):
        # if auth token doesn't start with "Bearer" add it
        if not auth_token.startswith("Bearer"):
            auth_token = auth_token.replace(" ", "")
            AUTH_TOKENS[i] = f"Bearer {auth_token}"
            auth_token = AUTH_TOKENS[i]
        response = requests.post(SYNC_URL, headers={"Authorization": auth_token})
        if response.status_code != 200:
            print(f"Invalid auth token at line {i + 1} in .env file! Token ends with {auth_token[-10:]}")
            exit()


if __name__ == "__main__":
    set_auth_tokens()

    if not WELCOME_SCREEN:
        main()

    print("""
     _   _                     _              _   __                _           _    ______       _   
    | | | |                   | |            | | / /               | |         | |   | ___ \     | |  
    | |_| | __ _ _ __ ___  ___| |_ ___ _ __  | |/ /  ___  _ __ ___ | |__   __ _| |_  | |_/ / ___ | |_ 
    |  _  |/ _` | '_ ` _ \/ __| __/ _ \ '__| |    \ / _ \| '_ ` _ \| '_ \ / _` | __| | ___ \/ _ \| __|
    | | | | (_| | | | | | \__ \ ||  __/ |    | |\  \ (_) | | | | | | |_) | (_| | |_  | |_/ / (_) | |_ 
    \_| |_/\__,_|_| |_| |_|___/\__\___|_|    \_| \_/\___/|_| |_| |_|_.__/ \__,_|\__| \____/ \___/ \__|
       
       
       
    Select one of the following options:
    
    1. Run the script
    2. Exit                                                                                               
    """)

    # Select the option
    option = input("Enter the option: ")
    if option == "1":
        print("\n")
        print("-" * 50)
        main()
    elif option == "2":
        exit()
    else:
        print("Invalid option!")
        exit()
