from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, State, dcc, html, no_update
from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
REQUIRED_COLUMNS = {"date", "revenue", "orders", "customers", "cost"}


def env_user(username_key: str, password_key: str, role: str):
    username = os.getenv(username_key, "")
    password = os.getenv(password_key, "")
    if not username or not password:
        return None
    return {"username": username, "password_hash": generate_password_hash(password), "role": role}


USERS = {
    u["username"]: u
    for u in (
        env_user("ADMIN_USERNAME", "ADMIN_PASSWORD", "admin"),
        env_user("VIEWER_USERNAME", "VIEWER_PASSWORD", "viewer"),
    )
    if u
}


def load_data() -> pd.DataFrame:
    source = os.getenv("DATA_SOURCE", "csv").lower()
    if source == "database":
        from sqlalchemy import create_engine, text

        url = os.getenv("DATABASE_URL", "")
        table = os.getenv("DATABASE_TABLE", "executive_metrics")
        if not url:
            raise RuntimeError("DATA_SOURCE=database requires DATABASE_URL")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            raise RuntimeError("DATABASE_TABLE must be a simple table name")
        with create_engine(url, pool_pre_ping=True).connect() as connection:
            frame = pd.read_sql(text(f'SELECT date, revenue, orders, customers, cost FROM "{table}"'), connection)
    elif source == "csv":
        csv_path = Path(os.getenv("CSV_PATH", "data/sample.csv"))
        if not csv_path.is_absolute():
            csv_path = BASE_DIR / csv_path
        frame = pd.read_csv(csv_path)
    else:
        raise RuntimeError("DATA_SOURCE must be csv or database")

    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Data is missing required columns: {', '.join(sorted(missing))}")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in REQUIRED_COLUMNS - {"date"}:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=list(REQUIRED_COLUMNS)).sort_values("date")
    return frame


def money(value: float) -> str:
    return f"฿{value:,.0f}"


def make_card(label: str, value: str, note: str, color: str):
    return html.Div(
        [html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"), html.Div(note, className="kpi-note")],
        className="kpi-card",
        style={"borderTop": f"4px solid {color}"},
    )


server = Flask(__name__)
server.secret_key = os.getenv("SECRET_KEY", "")
server.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


@server.get("/login")
def login_page():
    if session.get("username") in USERS:
        return redirect("/")
    return """<!doctype html><html lang='th'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>เข้าสู่ระบบ | Executive Dashboard</title><link rel='stylesheet' href='/assets/style.css'>
    <main class='login-shell'><form class='login-card' method='post' action='/login'>
    <div class='eyebrow'>BUSINESS INTELLIGENCE</div><h1>เข้าสู่ระบบ</h1><p>Executive Dashboard</p>
    <label>ชื่อผู้ใช้<input name='username' autocomplete='username' required></label>
    <label>รหัสผ่าน<input name='password' type='password' autocomplete='current-password' required></label>
    <button class='primary-button' type='submit'>เข้าสู่ระบบ</button>
    <div class='login-error'>{{ERROR}}</div></form></main></html>""".replace("{{ERROR}}", "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง" if request.args.get("error") else "")


@server.post("/login")
def login():
    user = USERS.get(request.form.get("username", ""))
    if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
        session.clear()
        session["username"] = user["username"]
        session["role"] = user["role"]
        return redirect("/")
    return redirect(url_for("login_page", error="1"))


@server.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@server.get("/admin")
def admin_page():
    if session.get("role") != "admin":
        return "ไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    source = os.getenv("DATA_SOURCE", "csv").lower()
    return f"""<!doctype html><html lang='th'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>ตั้งค่าระบบ | Executive Dashboard</title><link rel='stylesheet' href='/assets/style.css'>
    <main class='login-shell'><section class='login-card'><div class='eyebrow'>ADMIN</div><h1>ตั้งค่าระบบ</h1>
    <p>บัญชีผู้ดูแลระบบเท่านั้น</p><div class='admin-info'><b>แหล่งข้อมูล</b><br>{source}</div>
    <p>เปลี่ยนแหล่งข้อมูลและบัญชีผู้ใช้ผ่านไฟล์ .env จากนั้นเริ่มแอปใหม่</p>
    <a class='logout-link' href='/'>กลับหน้า Dashboard</a></section></main></html>"""


@server.before_request
def require_login():
    if request.endpoint in {"login_page", "login", "static"} or request.path.startswith("/assets/"):
        return None
    if session.get("username") not in USERS:
        return redirect(url_for("login_page"))
    return None


app = Dash(__name__, server=server, title="Executive Dashboard", update_title=None)
app.layout = html.Div(
    [
        html.Header(
            [
                html.Div([html.Div("BUSINESS INTELLIGENCE", className="eyebrow"), html.H1("ภาพรวมธุรกิจ", className="page-title"), html.Div("Executive Dashboard", className="subtitle")]),
                html.Div([html.Div(id="user-label", className="user-label"), html.A("ตั้งค่าระบบ", href="/admin", id="admin-link", className="logout-link"), html.A("ออกจากระบบ", href="/logout", className="logout-link")], className="user-menu"),
            ], className="topbar"),
        html.Main(
            [
                html.Div([html.Label("ช่วงวันที่", htmlFor="date-range"), dcc.DatePickerRange(id="date-range", display_format="DD/MM/YYYY", minimum_n=None, maximum_n=None, start_date_placeholder_text="วันเริ่มต้น", end_date_placeholder_text="วันสิ้นสุด")], className="filter-card"),
                html.Div(id="kpi-row", className="kpi-grid"),
                html.Div([html.Div([html.H2("รายได้ตามช่วงเวลา"), html.P("แสดงยอดขาย ต้นทุน และกำไรขั้นต้น", className="section-note")]), dcc.Graph(id="trend-chart", config={"displayModeBar": False}, className="chart")], className="panel"),
                html.Div(id="data-note", className="data-note"),
            ], className="content"),
        dcc.Location(id="location"),
    ], className="app-shell")


@app.callback(Output("user-label", "children"), Output("admin-link", "style"), Input("location", "pathname"))
def show_user(_):
    username = session.get("username", "")
    role = session.get("role", "viewer")
    return f"{username} · {'ผู้ดูแลระบบ' if role == 'admin' else 'ผู้บริหาร'}", ({"display": "inline"} if role == "admin" else {"display": "none"})


@app.callback(Output("date-range", "min_date_allowed"), Output("date-range", "max_date_allowed"), Output("date-range", "start_date"), Output("date-range", "end_date"), Input("location", "pathname"))
def initialize_dates(_):
    df = load_data()
    if df.empty:
        return None, None, None, None
    return df.date.min().date(), df.date.max().date(), df.date.min().date(), df.date.max().date()


@app.callback(Output("kpi-row", "children"), Output("trend-chart", "figure"), Output("data-note", "children"), Input("date-range", "start_date"), Input("date-range", "end_date"))
def update_dashboard(start_date, end_date):
    df = load_data()
    if start_date:
        df = df[df.date >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df.date < pd.to_datetime(end_date) + pd.Timedelta(days=1)]
    if df.empty:
        return [make_card("รายได้", "—", "ไม่มีข้อมูลในช่วงที่เลือก", "#2563eb")], px.line(title="ไม่มีข้อมูลในช่วงวันที่นี้"), ""
    revenue = df.revenue.sum()
    cost = df.cost.sum()
    orders = int(df.orders.sum())
    customers = int(df.customers.sum())
    profit = revenue - cost
    margin = (profit / revenue * 100) if revenue else 0
    cards = [
        make_card("รายได้รวม", money(revenue), f"{len(df):,} รายการข้อมูล", "#2563eb"),
        make_card("กำไรขั้นต้น", money(profit), f"อัตรากำไร {margin:.1f}%", "#0f9f6e"),
        make_card("คำสั่งซื้อ", f"{orders:,}", "รวมในช่วงเวลาที่เลือก", "#7c3aed"),
        make_card("ลูกค้า", f"{customers:,}", "รวมในช่วงเวลาที่เลือก", "#e08b19"),
    ]
    trend = df.set_index("date")[["revenue", "cost"]].resample("MS").sum().reset_index().melt(id_vars="date", var_name="ประเภท", value_name="จำนวนเงิน")
    trend["ประเภท"] = trend["ประเภท"].map({"revenue": "รายได้", "cost": "ต้นทุน"})
    fig = px.line(trend, x="date", y="จำนวนเงิน", color="ประเภท", markers=True, color_discrete_map={"รายได้": "#2563eb", "ต้นทุน": "#f59e0b"})
    fig.update_layout(margin=dict(l=8, r=8, t=18, b=8), legend_title_text="", hovermode="x unified", paper_bgcolor="white", plot_bgcolor="white", font=dict(family="Segoe UI, sans-serif", color="#334155"), yaxis=dict(tickprefix="฿", separatethousands=True, gridcolor="#eef2f7", title=""), xaxis=dict(title="", gridcolor="#fff"))
    return cards, fig, f"ข้อมูลตั้งแต่ {df.date.min():%d/%m/%Y} ถึง {df.date.max():%d/%m/%Y} · อัปเดตเมื่อเปิดหรือเปลี่ยนตัวกรอง"


if __name__ == "__main__":
    if not server.secret_key or server.secret_key == "change-this-to-a-long-random-secret":
        raise RuntimeError("Set a unique SECRET_KEY in your .env before starting the app")
    if not USERS or os.getenv("ADMIN_PASSWORD", "").startswith("change-this") or os.getenv("VIEWER_PASSWORD", "").startswith("change-this"):
        raise RuntimeError("Set non-default admin and viewer credentials in your .env")
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8050")), debug=False)
