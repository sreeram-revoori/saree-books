# Saree Books

A simple bookkeeping app for the saree business. Records are kept in a spreadsheet
you can always open yourself:
- in a **Google Sheet**, when set up (needed for using it online — see [DEPLOY.md](DEPLOY.md)), or
- in **saree_books.xlsx** in this folder, if no Google Sheet is set up.

The **Download Excel copy** button in the app gives you an Excel file of everything at any time.

## Starting the app
- **Mac:** double-click `Start Saree Books.command`
  (first time only: right-click → Open, then click Open, since macOS blocks unknown scripts)
- **Windows:** double-click `Start Saree Books.bat`

The first start takes a minute to set up (needs internet once). The app then
opens in your web browser. Keep the black window open while you use it; close it when done.

Needs Python 3 installed (python.org) — already there on most Macs.

## Rupees and dollars
Every purchase, sale and expense can be in ₹ or $. The exchange rate (₹ for $1) is
filled in automatically from the internet for that date — change it if your bank or
money-transfer gave a different rate. Without internet, it shows the last rate used.
The Excel file shows every amount in both ₹ and $, and the sidebar switch
"Show totals in" changes the dashboard between ₹ and $.

## Daily use
1. **New Purchase** — when sarees arrive. Give each design a short code like `KAN-001`.
   Choose how the lot was priced:
   - *One bulk price* — e.g. ₹50,000 for 20 sarees of 6 designs: enter each design and
     how many, then the one bulk price. It is shared equally per piece.
   - *Each has its own price* — enter the price per piece for every design.
   - *Mixed* — give own prices where you have them; leave 0 for the rest to share the bulk price.
   Shipping + customs for the whole lot (₹ or $) is spread over every piece, so you see
   the real (landed) cost of each saree.
2. **New Sale** — pick the saree, currency and price. It shows your cost and the profit
   before you save. If the customer pays later, untick "Paid in full".
   **Sold something before entering its purchase?** Choose *"A saree not in stock yet"*
   and type its code. The sale is saved; its profit shows as 0 (and the dashboard reminds
   you) until you add the purchase with the same code — then cost and profit fill in by themselves.
3. **New Expense** — packaging, courier, rent, etc. If an expense was for particular
   sarees (tailoring, fall-pico, courier for one lot…), pick their codes under
   *For particular sarees?* — it is added to those sarees' cost, spread over the pieces
   bought, so their profit is right. Leave it empty for general business expenses.
4. **Pending Payments** — see who owes money and record payments as they come in.
5. **Dashboard / Stock** — profit, stock on hand, low-stock items.

## The spreadsheet
Sheets: Purchases, Sales, Expenses, Stock, Monthly Summary.
- On Monthly Summary, *Purchases* includes saree-linked expenses and *Expenses* is only
  the general ones — so nothing is counted twice.
- Stock and Monthly Summary are rebuilt automatically every time the app saves.
- You *can* edit Purchases/Sales/Expenses directly in Excel — save & close Excel,
  then press **Reload** in the app.
- Excel file: every save first makes a copy in the `backups` folder (last 60 kept).
  To undo a mistake, copy a backup over `saree_books.xlsx`.
- Google Sheet: undo with File → Version history in Google Sheets, then **Reload** in the app.
