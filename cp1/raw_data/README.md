# Raw data

Thư mục này chứa dữ liệu nguồn được lấy trực tiếp từ dataset, trước khi parse,
normalize, lọc `WARN` hoặc tính metric. Không chỉnh sửa hay ghi đè các file đã
được đặt trong thư mục này.

## Cấu trúc đề xuất

```text
raw_data/
└── rcaeval/
    ├── cases.parquet
    └── cases/
        └── <case_id>/
            ├── logs.parquet
            ├── traces.parquet
            └── root_cause.txt
```

Không phải case nào cũng có đủ ba file. Cấu trúc của từng case nên được giữ
giống với repository RCAEval trên Hugging Face để có thể truy ngược nguồn dữ
liệu và tái lập thí nghiệm.

## Một số case mẫu nên giữ để quan sát

| Case | Mục đích quan sát |
|---|---|
| `re3ss_carts_f3_4` | Cảnh báo duplicate ở mức `WARN` |
| `re2ss_carts_cpu_1` | Cảnh báo Zipkin xuất hiện ở cả normal và faulty window |
| `re2tt_ts-route-service_mem_1` | Cảnh báo MongoDB xuất hiện trên nhiều service |

## Phân biệt raw data và artifact

- `raw_data`: file tải trực tiếp từ nguồn, không qua biến đổi.
- `artifacts`: CSV thống kê, report text, bảng kết quả và output sinh bởi code.
- `src`: code dùng để tải, parse và phân tích dữ liệu.

Dữ liệu RCAEval đầy đủ có dung lượng lớn. Chỉ nên commit README, manifest và
sample nhỏ khi thật sự cần; dữ liệu đầy đủ nên được tải lại bằng pipeline.
