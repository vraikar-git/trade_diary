# Trade Diary
A simple web app to log trades and analyze key metrics.
Most available trading journals are too complex to use and cannot be customized to fit individual needs. They are often hosted on Third-party cloud services.
This App was mainly developed to be simple, self-hosted and customizable.

This app is built using Dash for UI and SQLite for Persistence. It can be run locally on your machine or hosted on cloud.

## Features
1. **Logging**
    - Supports multiple entries and exits.
    - Tag Set-up, Entry/Exit Reasons, Notes.
    - Charges, Fees and Commissions etc are calculated while exiting trades (calculations are based on National Stock Exchange).
2. **Analysis**
    - Monthly/Quarterly/Yearly summaries of key trading metrics - R Multiples, Avg win/loss, Win Rate, Adjusted RR, RR Etc
    - Set-up wise performance analysis.
3. **Import Old Trades**


### ToDo
- Fetch Current Price from Yahoo Finance and display current position status.
- Add New Tab for Statement/Account Balance.
- Add Equity Curve and Charts to display metrics.
