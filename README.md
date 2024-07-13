# Charlotte-RPIcordBot

"""
Charlotte-RPIcordBot is a Discord bot designed to enhance the experience of users in the Rensselaer Polytechnic Institute (RPI) community. It offers various features such as role customization, command analytics, and email verification.

## Features

- **Role Customization**: Allows users to customize their Discord role colors and names through interactive modals.
- **Command Analytics**: Logs command usage and sets user context in Sentry for better monitoring and debugging.
- **Email Verification**: Verifies users' student status through email, ensuring only authorized users can access certain features.
- **Reaction Roles**: Provides dorm and class year roles with emojis and descriptions for easy role management.
- **Miscellaneous Commands**: Includes fun and useful commands like ping, TicTacToe, and more.

## Getting Started

### Prerequisites

- Python 3.8+
- Discord API Token
- Google API Credentials for Gmail
- PostgreSQL or SQLite database

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/Charlotte-RPIcordBot.git
    cd Charlotte-RPIcordBot
    ```

2. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

3. Set up environment variables:
    ```sh
    cp .env.example .env
    # Edit the .env file with your credentials
    ```

4. Initialize the database:
    ```sh
    python -c "from core.database import initialize_db; initialize_db()"
    ```

### Running the Bot

Start the bot by running:
```
python main.py
```
"""