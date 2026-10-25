# application/

Use case của dataset.

- describe_dataset: trả về profile (shape, columns, head, value_counts).
- read_incident(id): đọc một incident.
- explain_incident(id): mô tả nội dung incident bằng chứng cứ.

Chỉ gọi port/entity từ domain; việc đọc file do infrastructure làm.
