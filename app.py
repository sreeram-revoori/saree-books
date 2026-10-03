"""Saree Business Books — a simple bookkeeping app backed by a spreadsheet.

The books live in a Google Sheet when one is configured (see DEPLOY.md), otherwise
in saree_books.xlsx next to this file.
"""
import hmac
from datetime import date

import pandas as pd
import streamlit as st

import books as xs
import fx
import storage

st.set_page_config(page_title="Saree Books", page_icon="🧵", layout="wide")

SYMBOL = {"INR": "₹", "USD": "$"}
PAYMENT_MODES = ["Cash", "Zelle", "UPI", "Bank Transfer", "Card", "Credit (pay later)"]
EXPENSE_CATEGORIES = [
    "Shipping / Courier", "Customs / Duty", "Packaging", "Rent", "Travel",
    "Advertising", "Tailoring / Fall-Pico", "Bank Charges", "Other",
]


def check_password() -> None:
    """If an app_password is set in the secrets, ask for it once per visit."""
    password = storage.secrets().get("app_password")
    if not password or st.session_state.get("signed_in"):
        return
    st.title("🧵 Saree Books")
    entered = st.text_input("Password", type="password")
    if entered and hmac.compare_digest(entered, str(password)):
        st.session_state.signed_in = True
        st.rerun()
    elif entered:
        st.error("That password isn't right.")
    st.stop()


check_password()


def money(v: float, sym: str) -> str:
    return f"-{sym}{-v:,.2f}" if v < 0 else f"{sym}{v:,.2f}"


@st.cache_resource(show_spinner="Opening your books…")
def get_store():
    return storage.open_store()


def load_fresh() -> dict[str, pd.DataFrame]:
    return xs.compute(get_store().read())


def get_data() -> dict[str, pd.DataFrame]:
    if "sheets" not in st.session_state:
        st.session_state.sheets = load_fresh()
    return st.session_state.sheets


def add_rows(sheet: str, rows):
    """A change that appends rows to one sheet."""
    new = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    return lambda d: {**d, sheet: pd.concat([d[sheet], new], ignore_index=True)}


def persist(change, message: str) -> None:
    """Apply `change` to the latest saved books and save them.

    Starting from what is saved (not what this screen loaded earlier) means an
    entry made meanwhile on another phone or computer is not overwritten.
    """
    try:
        with st.spinner("Saving…"):
            fresh = load_fresh()
            sheets = xs.compute(change({k: fresh[k] for k in xs.INPUT_SHEETS}))
            get_store().write(sheets)
    except PermissionError:
        st.error("Could not save — please close saree_books.xlsx in Excel and try again.")
        return
    except Exception as exc:
        st.error(f"Could not save — nothing was changed. Please try again. ({exc})")
        return
    st.session_state.sheets = sheets
    st.session_state.flash = message
    st.session_state.n = st.session_state.get("n", 0) + 1  # fresh, empty entry form
    st.rerun()


@st.cache_data(ttl=3600, show_spinner="Getting today's exchange rate…")
def online_rate(on: date):
    return fx.usd_to_inr(on)


def rate_input(on: date, key: str) -> float:
    """Exchange-rate box, pre-filled from the internet for that date where possible."""
    fetched = online_rate(on)
    fallback = xs.last_rate(get_data())
    default = fetched[0] if fetched else (fallback or 0.0)
    rate = st.number_input(
        "Exchange rate (₹ for $1)", min_value=0.0, value=round(float(default), 2), step=0.1,
        format="%.2f", key=f"{key}_{on}_{default}",
    )
    if fetched:
        st.caption(f"Filled in automatically ({fetched[1]}). Change it if you got a different rate.")
    elif fallback:
        st.caption("Couldn't get the rate online — showing the last rate you used. Please check it.")
    else:
        st.caption("Couldn't get the rate online — please type it in.")
    return rate


def md(text: str) -> str:
    """Stop Streamlit reading '$…$' in messages as a maths formula."""
    return text.replace("$", "\\$")


def other(cur: str) -> str:
    return "USD" if cur == "INR" else "INR"


def both(amount: float, cur: str, rate: float) -> str:
    """'$120.00 (≈ ₹10,000.00)'."""
    alt = other(cur)
    return f"{money(amount, SYMBOL[cur])} (≈ {money(xs.convert(amount, cur, rate, alt), SYMBOL[alt])})"


data = get_data()
purchases, sales, expenses = data["Purchases"], data["Sales"], data["Expenses"]
stock = data["Stock"]
n = st.session_state.setdefault("n", 0)
store = get_store()

st.sidebar.title("🧵 Saree Books")
page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "New Sale", "New Purchase", "New Expense", "Stock", "Pending Payments", "View / Edit Records"],
)
st.sidebar.divider()
show_in = st.sidebar.radio("Show totals in", ["USD", "INR"], format_func=lambda c: f"{SYMBOL[c]} {c}", horizontal=True)
S = SYMBOL[show_in]
st.sidebar.divider()
if isinstance(store, storage.SheetsStore):
    st.sidebar.caption(f"Books kept in your [Google Sheet]({store.url})")
else:
    st.sidebar.caption(f"Books kept in `{store.WORKBOOK.name}` on this computer")
if st.sidebar.button("🔄 Reload", help="Use this after editing the spreadsheet directly"):
    st.session_state.pop("sheets", None)
    st.rerun()
st.sidebar.download_button(
    "⬇️ Download Excel copy", xs.xlsx_bytes(data), file_name=f"saree_books_{date.today()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

if msg := st.session_state.pop("flash", None):
    st.success(md(msg))


# ---------------- Dashboard ----------------
if page == "Dashboard":
    st.title("Dashboard")
    today = date.today()
    this_month = today.strftime("%Y-%m")
    month_sales = sales[pd.to_datetime(sales["Date"]).dt.strftime("%Y-%m") == this_month]
    general = xs.general_expenses(expenses)
    month_exp = general[pd.to_datetime(general["Date"]).dt.strftime("%Y-%m") == this_month]

    st.subheader(f"This month ({today:%B %Y})")
    c = st.columns(4)
    c[0].metric("Sales", money(month_sales[f"Total {S}"].sum(), S))
    c[1].metric("Gross profit", money(month_sales[f"Profit {S}"].sum(), S))
    c[2].metric("Other expenses", money(month_exp[f"Amount {S}"].sum(), S),
                 help="Expenses not added to the cost of particular sarees")
    c[3].metric("Net profit", money(month_sales[f"Profit {S}"].sum() - month_exp[f"Amount {S}"].sum(), S))

    st.subheader("Overall")
    c = st.columns(4)
    c[0].metric("Sarees in stock", f"{int(stock['In Stock'].clip(lower=0).sum()) if not stock.empty else 0}")
    c[1].metric("Stock value (at cost)", money(stock[f"Stock Value {S}"].sum() if not stock.empty else 0, S))
    c[2].metric("Money to collect", money(sales[f"Balance Due {S}"].clip(lower=0).sum(), S))
    c[3].metric("Total sales to date", money(sales[f"Total {S}"].sum(), S))

    summary = data["Monthly Summary"]
    if not summary.empty:
        st.subheader("Month by month")
        cols = [f"{m} {S}" for m in xs.SUMMARY_METRICS]
        view = summary[["Month"] + cols].rename(columns=lambda c: c.removesuffix(f" {S}"))
        st.bar_chart(view.set_index("Month")[["Sales", "Net Profit"]], stack=False)
        st.dataframe(view, hide_index=True, use_container_width=True)

    low = stock[(stock["In Stock"] > 0) & (stock["In Stock"] <= 2)] if not stock.empty else stock
    if not low.empty:
        st.subheader("Running low (2 or fewer left)")
        st.dataframe(low[["Saree Code", "Description", "In Stock"]], hide_index=True)

    pending_cost = sales[sales[xs.PURCHASED] == "No"]
    if not pending_cost.empty:
        codes = ", ".join(sorted(pending_cost["Saree Code"].unique()))
        st.warning(f"{len(pending_cost)} sale(s) are for sarees whose purchase isn't entered yet ({codes}). "
                   "Their profit is counted as 0 until you add those purchases under **New Purchase**.")

    if purchases.empty and sales.empty:
        st.info("Welcome! Start by adding a **New Purchase** (the sarees you bought), then record sales as they happen.")


# ---------------- New Sale ----------------
elif page == "New Sale":
    st.title("Record a sale")
    designs = stock.set_index("Saree Code")
    avail = designs[designs["In Stock"] > 0]
    NOT_LISTED = "\0not-listed"
    labels = {code: f"{code} — {r['Description']} ({int(r['In Stock'])} left)" for code, r in avail.iterrows()}
    labels[NOT_LISTED] = "➕ A saree not in stock yet (purchase not entered)"

    c1, c2, c3 = st.columns(3)
    d = c1.date_input("Date", date.today(), format="DD/MM/YYYY", key=f"s_date{n}")
    bill = c2.text_input("Bill No", xs.next_bill_no(sales), key=f"s_bill{n}")
    mode = c3.selectbox("Payment mode", PAYMENT_MODES, key=f"s_mode{n}")
    c1, c2 = st.columns(2)
    customer = c1.text_input("Customer name", key=f"s_cust{n}")
    phone = c2.text_input("Phone", key=f"s_phone{n}")
    c1, c2 = st.columns(2)
    cur = c1.selectbox("Sold in", xs.CURRENCIES, index=1, format_func=lambda c: f"{SYMBOL[c]} {c}", key=f"s_cur{n}")
    with c2:
        rate = rate_input(d, f"s_rate{n}")
    sym = SYMBOL[cur]

    code = st.selectbox("Saree", list(labels), format_func=labels.get, key=f"s_code{n}")
    if code == NOT_LISTED:
        c1, c2 = st.columns([1, 2])
        code = c1.text_input("Saree Code", key=f"s_newcode{n}", placeholder="KAN-001",
                             help="Use this same code when you enter the purchase later").strip().upper()
        desc = c2.text_input("Description", key=f"s_newdesc{n}", placeholder="e.g. Kanjivaram silk, red")
        left = None  # no stock check — the purchase isn't entered yet
    else:
        desc, left = avail.loc[code, "Description"], int(avail.loc[code, "In Stock"])
    known_cost = code in designs.index and designs.loc[code, "Qty Bought"] > 0
    cost_here = designs.loc[code, f"Avg Landed Cost {sym}"] if known_cost else None
    if known_cost:
        st.caption(md(f"Your cost for this saree: {money(cost_here, sym)} per piece (including shipping & customs)"))
    elif code:
        st.caption("Its cost isn't known yet — the profit on this sale will show once you enter the "
                   f"purchase with code **{code}** (New Purchase).")
    c1, c2, c3 = st.columns(3)
    qty = c1.number_input("Qty", min_value=1, value=1, step=1, key=f"s_qty{n}")
    price = c2.number_input(f"Price per piece ({sym})", min_value=0.0, step=5.0 if cur == "USD" else 100.0, key=f"s_price{n}")
    discount = c3.number_input(f"Discount ({sym})", min_value=0.0, step=1.0, key=f"s_disc{n}")
    total = qty * price - discount
    paid_full = st.checkbox("Paid in full", value=mode != "Credit (pay later)", key=f"s_full{n}_{mode}")
    paid = total if paid_full else st.number_input(f"Amount paid now ({sym})", min_value=0.0, step=1.0, key=f"s_paid{n}")
    notes = st.text_input("Notes", key=f"s_notes{n}")

    if price > 0 and rate > 0:
        profit = money(total - qty * cost_here, sym) if cost_here is not None else "shown after the purchase is entered"
        st.info(md(f"**Total: {both(total, cur, rate)}** · Profit on this sale: {profit}"
                   + (f" · Still to collect: {money(total - paid, sym)}" if total - paid > 0 else "")))

    if st.button("Save sale", type="primary"):
        if not code:
            st.error("Please enter a Saree Code.")
        elif price <= 0:
            st.error("Please enter the selling price.")
        elif rate <= 0:
            st.error("Please enter the exchange rate.")
        elif left is not None and qty > left:
            st.error(f"Only {left} of {code} in stock. If you sold more than you've entered, "
                     "choose \"A saree not in stock yet\" and type the code.")
        else:
            row = {
                "Date": d, "Bill No": bill, "Customer": customer, "Phone": phone,
                "Saree Code": code, "Description": desc, "Qty": qty,
                "Currency": cur, xs.RATE: rate, "Price per Piece": price, "Discount": discount,
                "Amount Paid": paid, "Payment Mode": mode, "Notes": notes,
            }
            persist(add_rows("Sales", [row]), f"Sale {bill} saved — {both(total, cur, rate)}")


# ---------------- New Purchase ----------------
elif page == "New Purchase":
    st.title("Record a purchase")
    st.caption(
        "Add every design you bought in this lot, one per line. Give each design a short "
        "**Saree Code** (e.g. KAN-001) and re-use the same code when you buy it again, so stock adds up."
    )
    c1, c2, c3 = st.columns(3)
    d = c1.date_input("Date", date.today(), format="DD/MM/YYYY", key=f"p_date{n}")
    supplier = c2.text_input("Supplier", key=f"p_sup{n}")
    invoice = c3.text_input("Supplier invoice no", key=f"p_inv{n}")
    c1, c2 = st.columns(2)
    cur = c1.selectbox("Paid in", xs.CURRENCIES, format_func=lambda c: f"{SYMBOL[c]} {c}", key=f"p_cur{n}")
    with c2:
        rate = rate_input(d, f"p_rate{n}")
    sym = SYMBOL[cur]

    known = stock.set_index("Saree Code")["Description"]
    waiting = stock[stock["Qty Bought"] == 0]
    if not waiting.empty:
        st.warning("Sold but purchase not entered yet: " + ", ".join(
            f"**{r['Saree Code']}** ({int(r['Qty Sold'])} sold)" for _, r in waiting.iterrows())
            + ". Use the same codes here so their cost and profit fill in.")
    if not known.empty:
        with st.expander(f"Saree codes already used ({len(known)})"):
            st.dataframe(known.reset_index(), hide_index=True)

    BULK, OWN, MIX = "One bulk price for the whole lot", "Each design has its own price", "Some have their own price, the rest share a bulk price"
    pricing = st.radio("How were these sarees priced?", [BULK, OWN, MIX], key=f"p_pricing{n}")
    n_designs = st.number_input("How many different designs in this lot?", min_value=1, max_value=50,
                                value=1, step=1, key=f"p_ndesigns{n}")

    st.markdown("**Sarees in this lot**")
    if pricing == MIX:
        st.caption("Leave *Own price* at 0 for sarees that are part of the bulk price.")
    rows = []
    for i in range(int(n_designs)):
        cols = st.columns([1.2, 2.2, 1.4, 0.8] + ([1.3] if pricing != BULK else []))
        lab = "visible" if i == 0 else "collapsed"
        code = cols[0].text_input("Saree Code", key=f"p_code{n}_{i}", label_visibility=lab, placeholder="KAN-001")
        code = code.strip().upper()
        desc = cols[1].text_input("Description", key=f"p_desc{n}_{i}", label_visibility=lab,
                                  placeholder=known.get(code, "e.g. Kanjivaram silk, red"))
        fabric = cols[2].text_input("Fabric / Type", key=f"p_fab{n}_{i}", label_visibility=lab)
        qty = cols[3].number_input("Qty", min_value=0, value=1, step=1, key=f"p_qty{n}_{i}", label_visibility=lab)
        own = 0.0
        if pricing != BULK:
            own = cols[4].number_input(f"Own price ({sym})", min_value=0.0, step=100.0,
                                       key=f"p_own{n}_{i}", label_visibility=lab)
        if code and qty > 0:
            rows.append({"Saree Code": code, "Description": desc or known.get(code, ""),
                         "Fabric / Type": fabric, "Colour": "", "Qty": qty, "Own Price": own or None})
    items = pd.DataFrame(rows, columns=["Saree Code", "Description", "Fabric / Type", "Colour", "Qty", "Own Price"])
    own = pd.to_numeric(items["Own Price"], errors="coerce")
    bulk_qty = int(items.loc[~(own > 0), "Qty"].sum())

    c1, c2, c3 = st.columns(3)
    bulk_price = 0.0
    if pricing != OWN:
        bulk_price = c1.number_input(
            f"Bulk price for the lot ({sym}) — total", min_value=0.0, step=100.0, key=f"p_bulk{n}",
            help="The one price you paid for all the sarees that don't have their own price",
        )
    elif bulk_qty:
        st.warning("Please enter an own price for every design.")
    ship = c2.number_input("Shipping + customs for the whole lot", min_value=0.0, step=10.0, key=f"p_ship{n}",
                           help="Freight, courier, customs duty, clearing — spread over every piece")
    ship_cur = c3.selectbox("Shipping paid in", xs.CURRENCIES, index=xs.CURRENCIES.index(cur),
                            format_func=lambda c: f"{SYMBOL[c]} {c}", key=f"p_shipcur{n}_{cur}")
    notes = st.text_input("Notes", key=f"p_notes{n}")

    ship_in_cur = xs.convert(ship, ship_cur, rate, cur)
    lot = xs.split_lot(items, bulk_price if bulk_qty else 0, ship_in_cur) if not items.empty else items

    if not lot.empty:
        st.markdown("**Cost per piece for this lot**")
        alt = other(cur)
        preview = lot[["Saree Code", "Description", "Qty", "Pricing", "Cost per Piece", "Landed Cost per Piece"]].copy()
        preview[f"Landed ({SYMBOL[alt]})"] = xs.convert(preview["Landed Cost per Piece"], cur, rate, alt).round(2)
        preview = preview.rename(columns={
            "Cost per Piece": f"Price ({sym})", "Landed Cost per Piece": f"Landed incl. shipping ({sym})"})
        st.dataframe(preview, hide_index=True, use_container_width=True)
        lot_total = (lot["Qty"] * lot["Cost per Piece"]).sum() + ship_in_cur
        st.info(md(f"**{int(lot['Qty'].sum())} sarees · lot total {both(lot_total, cur, rate)}**"))

    if st.button("Save purchase", type="primary"):
        if lot.empty:
            st.error("Add at least one saree with a code and quantity.")
        elif rate <= 0:
            st.error("Please enter the exchange rate.")
        elif bulk_qty and bulk_price <= 0:
            st.error(f"{bulk_qty} sarees have no own price — enter the bulk lot price, or give them their own price.")
        else:
            rows = lot.assign(
                Date=d, Supplier=supplier, **{"Invoice No": invoice, "Currency": cur, xs.RATE: rate, "Notes": notes}
            ).drop(columns=["Own Price", "Landed Cost per Piece"])
            persist(add_rows("Purchases", rows), f"Saved {int(lot['Qty'].sum())} sarees ({len(lot)} designs) from {supplier or 'this lot'}")


# ---------------- New Expense ----------------
elif page == "New Expense":
    st.title("Record an expense")
    c1, c2 = st.columns(2)
    d = c1.date_input("Date", date.today(), format="DD/MM/YYYY", key=f"e_date{n}")
    cat = c2.selectbox("Category", EXPENSE_CATEGORIES, key=f"e_cat{n}")
    c1, c2, c3 = st.columns(3)
    cur = c1.selectbox("Paid in", xs.CURRENCIES, format_func=lambda c: f"{SYMBOL[c]} {c}", key=f"e_cur{n}")
    amount = c2.number_input(f"Amount ({SYMBOL[cur]})", min_value=0.0, step=10.0, key=f"e_amt{n}")
    with c3:
        rate = rate_input(d, f"e_rate{n}")
    c1, c2 = st.columns(2)
    desc = c1.text_input("Description", key=f"e_desc{n}")
    mode = c2.selectbox("Payment mode", PAYMENT_MODES[:-1], key=f"e_mode{n}")

    has_purchase = stock[stock["Qty Bought"] > 0]
    codes = has_purchase["Saree Code"].tolist()
    names = dict(zip(has_purchase["Saree Code"], has_purchase["Description"]))
    linked = st.multiselect(
        "For particular sarees? (optional)", codes, key=f"e_codes{n}",
        format_func=lambda c: f"{c} — {names.get(c, '')}",
        placeholder="Leave empty for a general business expense",
        help="e.g. tailoring or fall-pico for one design, or courier for a few designs",
    )
    if linked:
        bought = stock.set_index("Saree Code")["Qty Bought"]
        pieces = int(bought[linked].sum())
        st.info(md(
            f"This will be added to the cost of {', '.join(linked)} — spread over the {pieces} "
            f"piece{'s' if pieces != 1 else ''} bought"
            + (f" (about {money(amount / pieces, SYMBOL[cur])} each)." if amount and pieces else ".")
            + " It won't count again as a general expense."
        ))
    notes = st.text_input("Notes", key=f"e_notes{n}")
    if st.button("Save expense", type="primary"):
        if amount <= 0:
            st.error("Please enter the amount.")
        elif rate <= 0:
            st.error("Please enter the exchange rate.")
        else:
            row = {"Date": d, "Category": cat, "Description": desc, "Saree Code": ", ".join(linked),
                   "Currency": cur, xs.RATE: rate, "Amount": amount, "Payment Mode": mode, "Notes": notes}
            where = f" and added to the cost of {', '.join(linked)}" if linked else ""
            persist(add_rows("Expenses", [row]), f"Expense of {both(amount, cur, rate)} saved{where}")


# ---------------- Stock ----------------
elif page == "Stock":
    st.title("Stock")
    if stock.empty:
        st.info("No purchases recorded yet.")
    else:
        show_all = st.toggle("Show sold-out designs too", value=False)
        view = stock if show_all else stock[stock["In Stock"] != 0]
        if (stock["In Stock"] < 0).any():
            st.caption("A negative *In Stock* means more was sold than purchases entered — "
                       "add the missing purchase with that Saree Code.")
        search = st.text_input("Search", placeholder="Code, description or fabric")
        if search:
            mask = view.apply(lambda r: search.lower() in " ".join(map(str, r.values)).lower(), axis=1)
            view = view[mask]
        c = st.columns(2)
        c[0].metric("Pieces in stock", int(view["In Stock"].clip(lower=0).sum()))
        c[1].metric("Value at cost", money(view[f"Stock Value {S}"].sum(), S))
        cols = ["Saree Code", "Description", "Fabric / Type", "Qty Bought", "Qty Sold", "In Stock",
                f"Extra Costs {S}", f"Avg Landed Cost {S}", f"Stock Value {S}"]
        st.dataframe(view[cols], hide_index=True, use_container_width=True)


# ---------------- Pending Payments ----------------
elif page == "Pending Payments":
    st.title("Pending payments")
    due = sales[sales["Balance Due"] > 0]
    if due.empty:
        st.success("Nothing pending — everyone has paid! 🎉")
    else:
        st.metric("Total to collect", money(due[f"Balance Due {S}"].sum(), S))
        st.dataframe(
            due[["Date", "Bill No", "Customer", "Phone", "Currency", "Total Amount", "Amount Paid", "Balance Due"]],
            hide_index=True, use_container_width=True,
        )
        st.subheader("Record a payment received")
        opts = {
            i: f"{r['Bill No']} — {r['Customer']} (due {money(r['Balance Due'], SYMBOL[r['Currency']])})"
            for i, r in due.iterrows()
        }
        idx = st.selectbox("Bill", list(opts), format_func=opts.get, key=f"pay_bill{n}")
        pay_sym = SYMBOL[due.loc[idx, "Currency"]]
        amt = st.number_input(f"Amount received ({pay_sym})", min_value=0.0, step=1.0, key=f"pay_amt{n}")
        if st.button("Save payment", type="primary") and amt > 0:
            bill = due.loc[idx, "Bill No"]

            def add_payment(d, bill=bill, amt=amt):
                s = d["Sales"].copy()
                open_rows = s.index[(s["Bill No"] == bill) & (s["Amount Paid"] < s["Qty"] * s["Price per Piece"] - s["Discount"])]
                s.loc[open_rows[:1], "Amount Paid"] += amt
                return {**d, "Sales": s}

            persist(add_payment, f"Payment of {money(amt, pay_sym)} recorded")


# ---------------- View / Edit ----------------
elif page == "View / Edit Records":
    st.title("View / edit records")
    st.caption(
        "Click a cell to fix a mistake. To delete a row, tick the box on its left and press the "
        "delete key (or the bin icon). Grey columns are calculated automatically. Press **Save changes** when done."
    )
    sheet = st.radio("Sheet", ["Sales", "Purchases", "Expenses"], horizontal=True)
    edited = st.data_editor(
        data[sheet], num_rows="dynamic", hide_index=True, use_container_width=True,
        disabled=xs.COMPUTED[sheet], key=f"edit_{sheet}{n}",
        column_config={
            "Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Currency": st.column_config.SelectboxColumn(options=xs.CURRENCIES),
        },
    )
    if st.button("Save changes", type="primary"):
        persist(lambda d: {**d, sheet: edited}, f"{sheet} updated")
