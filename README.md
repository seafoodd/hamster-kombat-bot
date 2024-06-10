# Hamster Kombat Bot

This bot is designed to automate coin farming in Hamster Kombat. It is written in Python and uses Bearer tokens to authenticate with the game's API.

## Features

The bot can perform the following tasks:

- Perform all available taps for a user
- Check and claim daily cipher and combo rewards
- Buy upgrades based on certain conditions
- Maintain a streak for a user

## [Settings](https://github.com/seafoodd/hamster-kombat-bot/blob/main/.env-example)
| Setting | Description |
| --- | --- |
| `WELCOME_SCREEN` | Whether to show the welcome screen or not |
| `PROFIT_TO_PRICE_RATIO` | The profit to price ratio for upgrades (play around with this value) |
| `SLEEP_TIME` | Time to sleep between each cycle of tasks |
| `MINIMUM_BALANCE` | Minimum balance to maintain |


## Installation

1. Clone this repository to your local machine.
    ```bash
    git clone https://github.com/seafoodd/hamster-kombat-bot.git
    cd hamster-kombat-bot
   
2. Install the required Python libraries by running 
    ```bash
    pip install -r requirements.txt

3. Create a `.env` file in the root directory of the project, based on the provided `.env-example` file. Fill in the appropriate values for your game account.
    ```bash
    # Linux
    cp .env-example .env
   
    # Windows
    copy .env-example .env
    ```

4. Create a `tokens.txt` file in the root directory of the project. This file should contain the authorization tokens for the accounts you want the bot to manage. Each token should be on a new line. You can get a token for each account from the local storage of the browser. You can use [this repo](https://github.com/mudachyo/Hamster-Kombat) to open Hamster Kombat from the browser.

## Usage

To run the bot, simply execute the `main.py` script with Python:

```bash
python main.py
```

The bot will then start performing its tasks for each account whose token is listed in the `tokens.txt` file. It will continue to do so indefinitely, with a pause between each cycle of tasks as defined by the `SLEEP_TIME` environment variable.

## Note

This bot is intended for educational purposes only. Use it responsibly and at your own risk.
