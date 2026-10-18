from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html, dash_table
from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
REQUIRED_COLUMNS = {"plan_year", "task", "department", "owner", "start_date", "due_date", "progress", "status", "note"}
VALID_STATUSES = {"ยังไม่เริ่ม", "กำลังดำเนินการ", "เสร็จแล้ว", "ล่าช้า"}


def env_user(username_key: str, password_key: str, role: str):
    username, password = os.getenv(username_key, ""), os.getenv(password_key, "")
    return {"username": username, "password_hash": generate_password_hash(password), "role": role} if username and password else None


USERS = {u["username"]: u for u in (env_user("ADMIN_USERNAME", "ADMIN_PASSWORD", "admin"), env_user("VIEWER_USERNAME", "VIEWER_PASSWORD", "viewer")) if u}


def load_data() -> pd.DataFrame:
    if os.getenv("DATA_SOURCE", "csv").lower() == "database":
        from sqlalchemy import create_engine, text
        url, table = os.getenv("DATABASE_URL", ""), os.getenv("DATABASE_TABLE", "annual_plan_tasks")
        if not url:
            raise RuntimeError("DATA_SOURCE=database requires DATABASE_URL")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            raise RuntimeError("DATABASE_TABLE must be a simple table name")
        query = f'SELECT plan_year, task, department, owner, start_date, due_date, progress, status, note FROM "{table}"'
        with create_engine(url, pool_pre_ping=True).connect() as connection:
            df = pd.read_sql(text(query), connection)
    else:
        path = Path(os.getenv("CSV_PATH", "data/sample.csv"))
        if not path.is_absolute():
            path = BASE_DIR / path
        df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"ข้อมูลขาดคอลัมน์: {', '.join(sorted(missing))}")
    df = df.copy()
    df["plan_year"] = pd.to_numeric(df["plan_year"], errors="coerce")
    df["progress"] = pd.to_numeric(df["progress"], errors="coerce").clip(0, 100)
    for col in ("start_date", "due_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df = df.dropna(subset=["plan_year", "task", "department", "owner", "due_date", "progress"])
    df["plan_year"] = df["plan_year"].astype(int)
    df["status"] = df["status"].fillna("ยังไม่เริ่ม")
    df["note"] = df["note"].fillna("")
    return df.sort_values(["due_date", "department", "task"])


server = Flask(__name__)
server.secret_key = os.getenv("SECRET_KEY", "")
server.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


@server.get("/login")
def login_page():
    if session.get("username") in USERS:
        return redirect("/")
    error = "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง" if request.args.get("error") else ""
    return f"""<!doctype html><html lang='th'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>เข้าสู่ระบบ</title><link rel='stylesheet' href='/assets/style.css'><main class='login-shell'><form class='login-card' method='post' action='/login'><div class='eyebrow'>ANNUAL PLAN TRACKER</div><h1>เข้าสู่ระบบ</h1><p>ติดตามแผนปฏิบัติงานประจำปี</p><label>ชื่อผู้ใช้<input name='username' autocomplete='username' required></label><label>รหัสผ่าน<input name='password' type='password' autocomplete='current-password' required></label><button class='primary-button' type='submit'>เข้าสู่ระบบ</button><div class='login-error'>{error}</div></form></main></html>"""


@server.post("/login")
def login():
    user = USERS.get(request.form.get("username", ""))
    if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
        session.clear()
        session["username"], session["role"] = user["username"], user["role"]
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
    return f"<!doctype html><html lang='th'><meta charset='utf-8'><link rel='stylesheet' href='/assets/style.css'><main class='login-shell'><section class='login-card'><div class='eyebrow'>ADMIN</div><h1>ตั้งค่าระบบ</h1><p>บัญชีผู้ดูแลระบบ · แหล่งข้อมูล: {source}</p><p>เปลี่ยนแหล่งข้อมูลและบัญชีผู้ใช้ผ่านไฟล์ .env แล้วเริ่มแอปใหม่</p><a href='/'>กลับหน้า Dashboard</a></section></main></html>"


@server.before_request
def require_login():
    if request.endpoint in {"login_page", "login", "static"} or request.path.startswith("/assets/"):
        return None
    if session.get("username") not in USERS:
        return redirect(url_for("login_page"))


def card(label, value, hint, color):
    return html.Div([html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"), html.Div(hint, className="kpi-note")], className="kpi-card", style={"borderTop": f"4px solid {color}"})


app = Dash(__name__, server=server, title="ติดตามแผนปฏิบัติงาน", update_title=None)
app.layout = html.Div([
    html.Header([html.Div([html.Div("ANNUAL PLAN TRACKER", className="eyebrow"), html.H1("ติดตามแผนปฏิบัติงานประจำปี", className="page-title"), html.Div("ภาพรวมความคืบหน้า ผู้รับผิดชอบ และกำหนดส่ง", className="subtitle")]), html.Div([html.Div(id="user-label", className="user-label"), html.A("ตั้งค่าระบบ", href="/admin", id="admin-link", className="logout-link"), html.A("ออกจากระบบ", href="/logout", className="logout-link")], className="user-menu")], className="topbar"),
    html.Main([
        html.Div([html.Div([html.Label("ปีแผน", htmlFor="plan-year"), dcc.Dropdown(id="plan-year", clearable=False, className="select-control")]), html.Div([html.Label("แผนก", htmlFor="department"), dcc.Dropdown(id="department", clearable=False, className="select-control")])], className="filters-row"),
        html.Div(id="kpi-row", className="kpi-grid"),
        html.Div([html.Div([html.H2("ความคืบหน้าตามแผนก"), html.P("ค่าเฉลี่ยความคืบหน้าของหัวข้องานในแต่ละแผนก", className="section-note")]), dcc.Graph(id="department-chart", config={"displayModeBar": False})], className="panel"),
        html.Div([html.Div([html.H2("รายการตามแผนปฏิบัติงาน"), html.P("ติดตามผู้ดำเนินการ กำหนดส่ง และสถานะของแต่ละหัวข้อ", className="section-note")]), html.Div(id="task-table")], className="panel table-panel"),
        html.Div(id="data-note", className="data-note")
    ], className="content"), dcc.Location(id="location")
], className="app-shell")


@app.callback(Output("user-label", "children"), Output("admin-link", "style"), Input("location", "pathname"))
def show_user(_):
    role = session.get("role", "viewer")
    return f"{session.get('username', '')} · {'ผู้ดูแลระบบ' if role == 'admin' else 'ผู้บริหาร'}", ({"display": "inline"} if role == "admin" else {"display": "none"})


@app.callback(Output("plan-year", "options"), Output("plan-year", "value"), Output("department", "options"), Output("department", "value"), Input("location", "pathname"))
def initialize_filters(_):
    df = load_data()
    years = sorted(df.plan_year.unique(), reverse=True)
    depts = sorted(df.department.unique())
    return ([{"label": str(y), "value": int(y)} for y in years], int(years[0]) if years else None,
            [{"label": "ทุกแผนก", "value": "ทั้งหมด"}] + [{"label": d, "value": d} for d in depts], "ทั้งหมด")


@app.callback(Output("kpi-row", "children"), Output("department-chart", "figure"), Output("task-table", "children"), Output("data-note", "children"), Input("plan-year", "value"), Input("department", "value"))
def update_dashboard(year, department):
    df = load_data()
    if year is not None:
        df = df[df.plan_year == int(year)]
    if department and department != "ทั้งหมด":
        df = df[df.department == department]
    if df.empty:
        return [card("หัวข้องาน", "0", "ไม่พบข้อมูล", "#2563eb")], px.bar(title="ไม่มีข้อมูล"), html.Div("ไม่มีรายการตามตัวกรอง", className="empty-state"), ""
    today = pd.Timestamp.now().normalize()
    total = len(df)
    done = int((df.status == "เสร็จแล้ว").sum())
    late = int(((df.due_date < today) & (df.progress < 100)).sum())
    avg = df.progress.mean()
    cards = [card("หัวข้องานทั้งหมด", f"{total:,}", f"เสร็จแล้ว {done:,} หัวข้อ", "#2563eb"), card("ความคืบหน้าเฉลี่ย", f"{avg:.0f}%", "เฉลี่ยทุกหัวข้องาน", "#0f9f6e"), card("เสร็จแล้ว", f"{done:,}", f"จากทั้งหมด {total:,} หัวข้อ", "#7c3aed"), card("เกินกำหนด", f"{late:,}", "ยังไม่เสร็จและเลยกำหนด", "#dc4545")]
    by_dept = df.groupby("department", as_index=False).progress.mean().sort_values("progress")
    fig = px.bar(by_dept, x="progress", y="department", orientation="h", text=by_dept.progress.map(lambda v: f"{v:.0f}%"), range_x=[0, 100], color_discrete_sequence=["#2563eb"])
    fig.update_layout(margin=dict(l=10, r=24, t=14, b=8), paper_bgcolor="white", plot_bgcolor="white", font=dict(family="Segoe UI, sans-serif", color="#334155"), xaxis=dict(title="ความคืบหน้า (%)", gridcolor="#eef2f7", ticksuffix="%"), yaxis=dict(title="", gridcolor="#fff"), showlegend=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    table = df.copy()
    table["due_date"] = table.due_date.dt.strftime("%d/%m/%Y")
    table["start_date"] = table.start_date.dt.strftime("%d/%m/%Y")
    table["progress"] = table.progress.map(lambda v: f"{v:.0f}%")
    table = table.rename(columns={"task": "หัวข้องาน", "department": "แผนก", "owner": "ผู้ดำเนินการ", "start_date": "วันเริ่ม", "due_date": "กำหนดเสร็จ", "progress": "ความคืบหน้า", "status": "สถานะ", "note": "หมายเหตุ"})
    columns = ["หัวข้องาน", "แผนก", "ผู้ดำเนินการ", "วันเริ่ม", "กำหนดเสร็จ", "ความคืบหน้า", "สถานะ", "หมายเหตุ"]
    grid = dash_table.DataTable(data=table[columns].to_dict("records"), columns=[{"name": c, "id": c} for c in columns], page_size=12, sort_action="native", filter_action="native", style_table={"overflowX": "auto"}, style_cell={"fontFamily": "Segoe UI, sans-serif", "fontSize": 13, "padding": "12px", "textAlign": "left", "whiteSpace": "normal", "height": "auto", "minWidth": "100px", "maxWidth": "320px"}, style_header={"backgroundColor": "#f5f8fc", "fontWeight": 700, "color": "#45536b", "border": "0", "borderBottom": "1px solid #e7edf4"}, style_data={"border": "0", "borderBottom": "1px solid #eef2f7", "color": "#334155"})
    note = f"แผนปี {year} · แสดง {total:,} หัวข้อ · ค่าเกินกำหนดคำนวณจากวันที่กำหนดเสร็จและความคืบหน้าต่ำกว่า 100%"
    return cards, fig, grid, note


if __name__ == "__main__":
    if not server.secret_key or server.secret_key == "change-this-to-a-long-random-secret":
        raise RuntimeError("Set a unique SECRET_KEY in your .env before starting the app")
    if not USERS or os.getenv("ADMIN_PASSWORD", "").startswith("change-this") or os.getenv("VIEWER_PASSWORD", "").startswith("change-this"):
        raise RuntimeError("Set non-default admin and viewer credentials in your .env")
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8050")), debug=False)
