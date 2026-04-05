# Vianor Car Wash Telegram Bot

This project is an asynchronous Python-based Telegram bot designed to automate the management and daily operations of the Vianor car wash business. It utilizes the `aiogram` framework, a PostgreSQL database, and the Google Sheets API to handle customer bookings, vehicle tracking, staff management, and real-time business reporting.

## Features

- **Role-Based Access Control**: Strict access levels for Super Admins, standard Admins, Workers, and regular Users.
- **Staff Management System**: Add, manage, and softly delete (deactivate) administrative staff and car wash workers directly via the Telegram interface.
- **Booking & Vehicle Tracking**: Allows users to register their cars and book time slots for different car wash services.
- **Google Sheets Integration**: Automatically synchronizes staff statuses, new clients, vehicles, and booking history to a Google Spreadsheet for live dashboard analytics.
- **Automated Logging**: Tracks security events (e.g., who added/removed staff) and sends notifications directly to Super Admins and Google Sheets.

- **Dockerized Environment**: Fully containerized using Docker and Docker Compose, optimized for deployment on VPS or Proxmox LXC containers.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine or server.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- Python 3.12+ (if running locally without Docker)
- A registered Telegram Bot token from [@BotFather](https://t.me/botfather)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/vianor-bot.git
    cd vianor-bot
    ```

2.  **Set up Google Sheets API Credentials:**
    - Go to the [Google Cloud Console](https://console.cloud.google.com/).
    - Enable the **Google Sheets API** and **Google Drive API**.
    - Create a Service Account and download the JSON key.
    - Rename the downloaded file to `credentials.json` and place it in the root directory of the project.
    - *Important:* Share your target Google Spreadsheet with the `client_email` found inside `credentials.json` with "Editor" permissions.

### Configuration

Before starting the bot, you need to configure your environment variables. 

1. Create a `.env` file in the root directory.
2. Populate it with the required configuration:

    ```env
    # .env
    BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
    BD_ENGINE="postgresql+asyncpg://postgres:password@db:5432/vianor_db"
    
    # List of Telegram IDs for Super Admins (comma-separated)
    SUPER_ADMINS="123456789,987654321"
    
    # Working hours configuration
    WORK_HOURS="09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,18:00"
    DAYS_TO_BOOK_LIMIT="7"
    
    # Name of your Google Sheet for the Dashboard
    LOG_SHEET_NAME="YOUR_GOOGLE_SHEET_NAME"
    PRICE_SHEET_NAME=Prices 
    SHEET_URL="LINK_FOR_GOOGLE_SHEET"
   
    # Advanced settings. You can leave them as basic
    FAQ_FILE_PATH=app/utils/faq_data.csv
    # limit for one car
    DAYS_TO_BOOK_LIMIT=3
    # hours
    CANCEL_TIME_LIMIT=2
    # rounded up to an hour 
    HOURS_BEFORE_BOOKING=1
    ```

## Usage

To run the bot and the database, use Docker Compose. This is the recommended method for both development and production.

```bash
docker-compose up -d --build
```

The script will perform the following actions:
1. Pull the necessary Python and PostgreSQL images.
2. Initialize the `vianor_db` database and create all required tables.
3. Automatically insert Super Admins into the database based on the `.env` configuration.
4. Launch the bot in polling mode.

To view the real-time logs:
```bash
docker-compose logs -f
```

## Project Structure

```text
.
├── app/
│   ├── db/
│   │   ├── db_setup.py          # Database models and table definitions.
│   │   └── db_requests.py       # Async SQLAlchemy CRUD operations.
│   ├── routers/
│   │   ├── admin_routers/       # Handlers for staff management (adding/removing).
│   │   └── ...                  # Other handlers for bookings and user interactions.
│   └── utils/
│       ├── csv_handler.py       # Utility functions for parsing and handling FAQ questions.
│       ├── faq_data.csv         # Static CSV storage for Frequently Asked Questions (FAQ). 
│       ├── funcs.py             # Helper functions and text generation.
│       ├── google_sheets.py     # gspread integration for Dashboard sync.
│       ├── keyboards.py         # Inline and Reply keyboard builders.
│       └── price.py             # Handlers and logic for updating service prices.
│
├── docker-compose.yml           # Docker services configuration (Bot + DB).
├── .env                         # Environment variables (Ignored by Git).
├── credentials.json             # Google Service Account key (Ignored by Git).
├── main.py                      # Application entry point and dispatcher setup.
└── README.md                    # This file.
```