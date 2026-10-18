# Dashboard ติดตามแผนปฏิบัติงานประจำปี

เว็บ Dashboard สำหรับผู้บริหาร ติดตามความคืบหน้าของแต่ละหัวข้องาน แผนก ผู้ดำเนินการ กำหนดส่ง และหมายเหตุ มีตัวกรองปี/แผนก, KPI ภาพรวม, กราฟความคืบหน้าตามแผนก และตารางค้นหา/เรียงลำดับได้ ใช้ Dash + Plotly, รองรับ CSV หรือฐานข้อมูล SQL และล็อกอินสองบทบาท

## เริ่มบน Windows

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

แก้ `.env` เปลี่ยน `SECRET_KEY`, `ADMIN_PASSWORD`, `VIEWER_PASSWORD` จากนั้นรัน:

```powershell
python app.py
```

เปิด `http://127.0.0.1:8050/login` ผู้ดูแลระบบใช้ค่า username ใน `ADMIN_USERNAME`; ผู้บริหารใช้ `VIEWER_USERNAME` ค่าเริ่มต้นเป็น `admin` และ `executive` ตามลำดับ รหัสผ่านต้องเป็นค่าที่ตั้งเองใน `.env`

## คอลัมน์ข้อมูล

ทั้ง CSV และตาราง SQL ต้องมีคอลัมน์ดังนี้:

| คอลัมน์ | ความหมาย | ตัวอย่าง |
|---|---|---|
| `plan_year` | ปีแผน | `2026` |
| `task` | หัวข้องานตามแผน | `พัฒนาระบบบริการออนไลน์` |
| `department` | แผนก/หน่วยงาน | `เทคโนโลยีสารสนเทศ` |
| `owner` | ผู้ดำเนินการ/ผู้รับผิดชอบ | `กิตติพงษ์ ใจดี` |
| `start_date` | วันเริ่มต้น | `2026-01-05` |
| `due_date` | วันกำหนดเสร็จ | `2026-06-30` |
| `progress` | ความคืบหน้าเป็นเปอร์เซ็นต์ 0–100 | `82` |
| `status` | สถานะงาน | `กำลังดำเนินการ` |
| `note` | หมายเหตุ/อุปสรรค | `อยู่ระหว่างทดสอบระบบ` |

ตัวอย่างอยู่ใน `data/sample.csv` เปลี่ยนตำแหน่งด้วย `CSV_PATH` ใน `.env` สถานะที่แนะนำ: `ยังไม่เริ่ม`, `กำลังดำเนินการ`, `เสร็จแล้ว`, `ล่าช้า` ค่า KPI “เกินกำหนด” คำนวณจากกำหนดส่งที่ผ่านไปและความคืบหน้าต่ำกว่า 100%

## ใช้ฐานข้อมูล

```dotenv
DATA_SOURCE=database
DATABASE_URL=postgresql+psycopg://dashboard_user:password@db-host:5432/company
DATABASE_TABLE=annual_plan_tasks
```

สิทธิ์บัญชีฐานข้อมูลควรเป็นแบบอ่านอย่างเดียว Dashboard โหลดข้อมูลใหม่เมื่อมีการเปลี่ยนตัวกรอง

## ล็อกอินและสิทธิ์

ตั้งผู้ใช้ใน `.env` แยกเป็น admin และ viewer ผู้ใช้ทั้งสองบทบาทดู Dashboard ได้ แต่เฉพาะ admin เข้า `/admin` ได้ ข้อมูลบัญชีถูกเก็บใน environment ไม่ได้เพิ่มรหัสผ่านลงฐานข้อมูล

## Docker

```sh
docker build -t executive-dash .
docker run --env-file .env -p 8050:8050 executive-dash
```

ก่อนเปิดใช้งานจริง ให้ใช้รหัสผ่านและ `SECRET_KEY` ที่เดายาก เปิด HTTPS ผ่าน reverse proxy และเปิด `SESSION_COOKIE_SECURE=True` ใน `server.config.update` ของ `app.py` หลังใช้งาน HTTPS แล้ว หากแก้ข้อมูล CSV ในเครื่อง host ให้ mount โฟลเดอร์ `data` เข้า container
