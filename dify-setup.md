# Triển khai MTL Validator vào Dify Agent

## 1. Deploy API ra public

Dify cloud (dyfi.besen.vn) cần URL public để gọi API. Chọn 1 cách:

### Cách A: ngrok (test nhanh, miễn phí)

```powershell
# Tải ngrok từ https://ngrok.com và cài
ngrok http 8000
# → Copy URL dạng https://xxxx.ngrok-free.app
```

### Cách B: VPS (production)

```bash
git clone https://github.com/vothanhlam1793/check-mtl.git
cd check-mtl
pip install -r requirements.txt

# Mở port 8000 trên firewall, rồi chạy:
API_BASE_URL=http://<VPS-IP>:8000 ./run.sh
# Hoặc tự động từ Host header:
./run.sh
```

Dify import: `http://<VPS-IP>:8000/dify/openapi.json`

### Cách C: Railway / Render / Fly.io (free tier)

Push code lên GitHub → deploy tự động qua Railway/Render với Dockerfile có sẵn.

---

## 2. Đăng ký Tool trong Dify

Vào Dify → **Tools** → **Create Custom Tool** → chọn **OpenAPI / Swagger**

### Nhập URL OpenAPI spec:

```
https://your-server.com/dify/openapi.json
```

Hoặc paste nội dung file `openapi.yaml` vào tab **Import from URL / Paste**.

### Kiểm tra Tool đã import đúng:

Sau khi import, Dify sẽ hiện:
- **POST /api/v1/validate** — tool chính để validate file
- **GET /api/v1/health** — tool kiểm tra service

---

## 3. Tạo Dify Agent Workflow (có rẽ nhánh Validate / Export Word)

Vào Dify → **Studio** → **Create from blank** → chọn **Chatflow**

### Cấu trúc workflow:

```
[Start] → [Agent: Review yêu cầu] → [Condition: intent?]
                                           ├── "validate" → [validateFile] ──┐
                                           └── "export"   → [exportWordDify] ─┤
                                                                              ↓
                                                                     [Answer: Output]
```

### Bước 1: Thêm biến Conversation Variable

Vào **Variables** → thêm `intent` (kiểu text, mặc định rỗng).

### Bước 2: Node Agent (Review yêu cầu)

Cho phép user upload file và chat. Agent phân tích xem user muốn gì.

**System Prompt:**
```
Bạn là trợ lý GMS. Đọc yêu cầu của người dùng và phân loại:

- Nếu user chỉ muốn KIỂM TRA, VALIDATE, CHECK lỗi → set intent = "validate"
- Nếu user muốn XUẤT BÁO CÁO, EXPORT, WORD, BÁO CÁO THẨM ĐỊNH, THẨM ĐỊNH → set intent = "export"

QUAN TRỌNG: Luôn đọc kỹ tin nhắn của user để xác định đúng intent.
Trả lời ngắn gọn: "Đã nhận yêu cầu [validate/export]. Đang xử lý..."

Cách set intent: dùng output variable của Agent node → intent.
```

**User Prompt:**
```
{{#sys.files#}}
---
User yêu cầu: {{#sys.query#}}
```

**Output variable:** `intent` (text) → gán cho conversation variable `intent`.

### Bước 3: Node Condition (IF/ELSE)

- **IF**: `{{#conversation.intent#}}` **contains** `export` → nhánh Export Word
- **ELSE** → nhánh Validate

### Bước 4: Nhánh VALIDATE

**Node: validateFile tool**

Params:
- `file`: `{{#sys.files#}}`
- `employee_id`: `GMS`

**Node Agent (phản hồi):**

**System Prompt:**
```
Bạn là trợ lý GMS thông báo kết quả kiểm tra MTL cho nhân viên.

Đọc kết quả từ tool validateFile:
1. Đọc `messages.user_message` — copy nguyên text này gửi cho nhân viên.
2. Dựa vào `messages.status_hint`:
   - BLOCKED → yêu cầu nhân viên sửa GẤP các lỗi CRITICAL và nộp lại ngay
   - FAIL_NEED_FIX → yêu cầu sửa lỗi ERROR trước khi nộp lại
   - PASS_WITH_NOTES → thông báo đạt, nhắc nhẹ các lưu ý nếu có
   - PASS_CLEAN → khen ngợi, file hoàn hảo!
3. Nếu có lỗi, kèm gợi ý là user có thể yêu cầu xuất báo cáo thẩm định Word nếu muốn.
4. KHÔNG tự ý thay đổi nội dung user_message.
```

### Bước 5: Nhánh EXPORT WORD

**Node: exportWordDify tool**

Params:
- `file`: `{{#sys.files#}}`
- `reviewer_name`: `GMS`

**Node Agent (phản hồi):**

> **Dùng prompt từ file `prompt-export.md`** — paste toàn bộ System Prompt trong file đó.

### Bước 6: Node Answer (Output)

Nối cả 2 nhánh Agent vào **Answer** node.

### Bắt buộc bật:
- **File Upload** — cho phép người dùng gửi file .xlsx
- **Tool: validateFile** + **Tool: exportWordDify** — gắn cả 2 tool

---

## 4. Test thử

Vào Dify → **Preview / Debug**:

1. Upload file test (VD: PT10A có lỗi thiếu tên công ty)
2. Gửi tin nhắn
3. Kiểm tra response — Agent phải gọi tool, đọc `user_message`, và trả lời nhân viên

**Response mong đợi:**
```
LOI COVER:
  [CRITICAL] Cover thiếu tên công ty
  [WARNING] Cover thiếu yêu cầu chung

File `...` cần sửa 1 lỗi:
Vui long sua cac loi tren va gui lai file.
```

---

## 5. Kịch bản thực tế

### Nhân viên nộp file mới mỗi ngày:
```
Nhân viên: "Đây ạ" [gửi file MTL_PhuocThien_20260528.xlsx]

Agent: gọi validateFile → kết quả PASS_WITH_NOTES
Agent: "File đạt chuẩn ạ. Có 1 lưu ý nhỏ: [WARNING] Cover thiếu yêu cầu chung — nếu không có thì bỏ qua."
```

### Nhân viên nộp file lỗi:
```
Nhân viên: "Đây ạ" [gửi file MTL_PhuocThien_10A.xlsx]

Agent: gọi validateFile → kết quả BLOCKED
Agent: "File của anh/chị bị lỗi NGHIÊM TRỌNG:
  [CRITICAL] Cover thiếu tên công ty
  => Cách sửa: Điền tên công ty vào Cover (VD: 'Công ty TNHH...')
Vui lòng sửa và gửi lại ạ."
```

---

## 6. Endpoint tham khảo

| Endpoint | Method | Dùng cho |
|---|---|---|
| `/` | GET | Test UI (kéo thả upload) |
| `/gms-tools` | GET | GMS Tools UI |
| `/gms-tools-pro` | GET | GMS Tools PRO UI |
| `/api/v1/validate` | POST | Kiểm tra file (Dify Agent gọi) |
| `/api/v1/export-word` | POST | Xuất Word (download trực tiếp) |
| `/api/v1/export-word-pro` | POST | Xuất Word PRO (download trực tiếp) |
| `/api/v1/export-word-dify` | POST | **[DIFY]** Xuất Word + link download |
| `/api/v1/export-word-pro-dify` | POST | **[DIFY]** Xuất Word PRO + link download |
| `/api/v1/health` | GET | Dify kiểm tra tool còn sống |
| `/dify/openapi.json` | GET | Dify import tool (JSON) |
| `/dify/openapi.yaml` | GET | Dify import tool (YAML) |
| `/docs` | GET | FastAPI auto-docs |
| `/api-docs` | GET | Swagger UI (spec đầy đủ) |
| `/outputs/{file}` | GET | Tải file Word đã export |

---

## 7. Troubleshooting

| Vấn đề | Nguyên nhân | Cách sửa |
|---|---|---|
| Dify không import được tool | URL OpenAPI không public | Dùng ngrok hoặc deploy lên server public |
| File upload báo lỗi | File > 15MB | Tăng `max_upload_size` trong Dify config |
| Agent không gọi tool | Chưa gắn tool vào Agent | Vào Agent settings → Tools → thêm validateFile |
| Response tiếng Anh | System prompt chưa set tiếng Việt | Copy nguyên System Prompt ở trên |
