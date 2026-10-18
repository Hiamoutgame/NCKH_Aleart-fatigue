# domain/

Entity và port riêng của dataset.

- Entity: ví dụ Incident, LogEvent, Alert.
- Port: interface đọc dữ liệu (ví dụ IncidentReader) để infrastructure cài đặt.
- Không import pandas, không đọc file, không gọi mạng.
