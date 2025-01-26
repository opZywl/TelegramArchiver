**Telegram Archiver Downloader** is a free, open-source command-line tool, built with `asyncio` and the `Telethon` library, designed to extract and download data from Telegram channels, groups, and users, including media (photos, videos, documents) and other files.

## Issues

If you encounter any bugs or missing features, please let us know by opening a new [issue here](https://github.com/opZywl/TelegramArchiver/issues).

## License

This project is licensed under the GNU General Public License v3.0. This license only applies to the source code directly located in this repository. During the development and compilation process, additional source code might be used that we have not obtained the rights to. That code is not covered by the GPL.

In short, you may use, share, and modify the code, but if you do so, you must:

*   Disclose the source code of your modified work and the source code you used from this project.
*   License your modified application under the GPL.

## Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/opZywl/TelegramArchiver.git
    cd your-repo
    ```

2.  **Create a `.env` file** in the project root with the following variables:

    ```env
    API_ID=your_api_id
    API_HASH=your_api_hash
    SESSION_NAME=your_session_name
    BATCH_SIZE=20 # optional, default 5
    ```
    *   Obtain an `API_ID` and `API_HASH` from [Telegram API](https://my.telegram.org/auth).
    *   The `SESSION_NAME` is the name `Telethon` will use to save your session data.
    *   `BATCH_SIZE` is the batch size for downloads (ideal value depends on your connection, 20 is good).

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the script:**

    ```bash
    python downloder.py
    ```

## Dependencies

*   **`asyncio`:** For asynchronous operations, enabling concurrent downloads.
*   **`Telethon`:** Telegram client for Python to interact with the Telegram API.
*   **`python-dotenv`:** Loads environment variables from the `.env` file.
*   **`colorama`:** Adds colors and styles to terminal output.
*   **`tqdm`:** Displays progress bars.
*  **`hashlib`:** Used to generate file hashes for duplicate checking.

## Contributing

Contributions are welcome. Feel free to make changes to TDE's source code and submit a pull request.
