# telegram-api-renaper
source code to connect to the RENAPER API, look up full names to get DNI/CUIL, and an approximate IP geolocation system. I'll just leave the code here, I'm not responsible for any misuse people give it.


## 📝 Quick Configuration Guide



* **`TELEGRAM_TOKEN`** Create a bot using `@BotFather` and paste the token here.



* **`RENAPER_API_BASE`** The base URL of your RENAPER API. Example:  

  `xxxxxxxxxx` (if that's the one).



* **`STAFF_IDS`** List of Telegram IDs for the administrators. You can get your ID using `@userinfobot`.



---



## 🛠️ Installation



```bash

pip install python-telegram-bot aiohttp cuitonline
