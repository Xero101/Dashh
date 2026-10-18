# Executive Dashboard (Dash + Python)

ตัวอย่างเว็บ Dashboard สำหรับผู้บริหาร ใช้ Plotly Dash และ Flask มี KPI cards, ตัวกรองวันที่, กราฟแนวโน้ม และบัญชีผู้ใช้ 2 บทบาท (admin / viewer) ข้อมูลเริ่มต้นอ่านจาก CSV และเลือกเปลี่ยนเป็นฐานข้อมูล SQL ได้

## เริ่มใช้งานบน Windows

1. ติดตั้ง Python 3.10 ขึ้นไป
2. เปิด PowerShell ในโฟลเดอร์นี้ แล้วรัน:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

3. แก้ `.env` ตั้ง `SECRET_KEY` และเปลี่ยนรหัสผ่านของ `admin` และ `executive` ให้เป็นรหัสผ่านของคุณเอง
4. เริ่มเว็บ:

```powershell
python app.py
```

5. เปิด `http://127.0.0.1:8050/login`

ผู้ใช้จาก `.env` ที่กำหนดบทบาท `admin` หรือ `viewer` จะเข้าสู่ Dashboard ได้ ทั้งสองบทบาทดู KPI ได้ แต่เฉพาะ admin เท่านั้นที่เข้า `/admin` เพื่อดูหน้าตั้งค่าระบบได้; viewer จะได้รับการปฏิเสธการเข้าถึงหน้านั้น การเปลี่ยนบัญชีผู้ใช้และแหล่งข้อมูลทำผ่าน `.env` บนเซิร์ฟเวอร์ ไม่ได้ผ่านหน้าเว็บ

## รูปแบบข้อมูล CSV

ไฟล์ CSV ต้องมีคอลัมน์ `date,revenue,orders,customers,cost` ตัวอย่างอยู่ที่ `data/sample.csv` กำหนดไฟล์ด้วย `CSV_PATH` ใน `.env` ได้ วันที่ควรอยู่ในรูปแบบที่ pandas อ่านได้ เช่น `2026-06-30` จำนวนเงินเป็นตัวเลขหน่วยบาท

## เปลี่ยนไปอ่านจากฐานข้อมูล

ตั้งค่าใน `.env`:

```dotenv
DATA_SOURCE=database
DATABASE_URL=postgresql+psycopg://dashboard_user:password@db-host:5432/company
DATABASE_TABLE=executive_metrics
```

ตารางต้องมีคอลัมน์ `date,revenue,orders,customers,cost` และสิทธิ์ของบัญชีฐานข้อมูลควรเป็นแบบอ่านอย่างเดียว ตัวอย่าง URL ของ PostgreSQL ใช้ไดรเวอร์ `psycopg` ซึ่งติดตั้งจาก `requirements.txt` ไว้แล้ว รองรับ URL รูปแบบ SQLAlchemy สำหรับฐานข้อมูลอื่นเมื่อเพิ่มไดรเวอร์ที่เหมาะสม

## ก่อนเปิดใช้จริงบนเซิร์ฟเวอร์

- อย่าใช้ค่า secret หรือรหัสผ่านตัวอย่าง และเก็บ `.env` เป็นความลับ
- ให้ reverse proxy เช่น Nginx หรือ Caddy จัดการ HTTPS และส่งทราฟฟิกเข้าแอป
- ตั้งค่า secure session cookie ใน `app.py` หลังเปิด HTTPS โดยเพิ่ม `SESSION_COOKIE_SECURE=True` ใน `server.config.update`
- ใช้ WSGI server สำหรับ production เช่น Gunicorn บน Linux (มี Dockerfile ให้); อย่าเปิด Flask development server สู่สาธารณะ
- สำรองฐานข้อมูลและจำกัดการเชื่อมต่อฐานข้อมูล/เว็บตามเครือข่ายที่จำเป็น
- ข้อมูลตัวอย่างเป็นข้อมูลสมมติ ควรตรวจสอบนิยาม KPI และสูตรกำไรกับทีมธุรกิจก่อนใช้รายงานจริง

## โครงสร้าง

```text
executive-dash/
  app.py
  requirements.txt
  .env.example
  assets/style.css
  data/sample.csv
  Dockerfile
```

## Docker

คัดลอก `.env.example` เป็น `.env`, เปลี่ยน secret และรหัสผ่าน แล้วสร้าง/เริ่ม container:

```sh
docker build -t executive-dash .
docker run --env-file .env -p 8050:8050 executive-dash
```

สำหรับ CSV ที่ต้องแก้จาก host ให้ mount ไฟล์หรือโฟลเดอร์ `data` เข้า container และตั้ง `CSV_PATH` ให้ตรงกับตำแหน่งที่ mount
