### Site Parsing for hh.ru with Telegram Bot Integration

## Features

* Scrapes the hh.ru website for job listings.
* Controls the parser via a Telegram bot.
* Saves the results to a CSV file.

## Installation

1. Clone the repository from `https://github.com/mvrogozov/hh_parser` and navigate into the directory:

    ```bash
    git clone git@github.com:mvrogozov/hh_parser.git
    cd hh_parser
    ```

2. Set up and activate a virtual environment:

    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

3. Install the necessary dependencies from `requirements.txt`:

    ```bash
    python3 -m pip install --upgrade pip
    pip install -r requirements/requirements.txt
    ```

4. Create a `.env` file and add your Telegram bot token:

    ```env
    TG_TOKEN = 'your-telegram-bot-token'
    ```

5. Run the project:

    ```bash
    python3 job_parser.py
    ```

### Docker Deployment Option

1. Copy the `job_parser` directory to your server.
2. In the `Dockerfile`, replace `xxxxxxxxxx` in the line `ENV TG_TOKEN=xxxxxxxxxx` with your Telegram bot token.
3. Build the Docker image:

    ```bash
    sudo docker build .
    ```

4. Run the Docker container:

    ```bash
    sudo docker run <container_id>
    ```

5. Send the `/help` command in Telegram to see the bot's command list.

### Required Environment Variables

* `TG_TOKEN` - Your Telegram bot token
