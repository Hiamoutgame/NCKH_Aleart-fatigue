#!/usr/bin/env bash
# ============================================================================== #
# Script dieu khien va khai thac LEMMA-RCA Dataset                              #
# Ho tro 2 cach dung:                                                          #
#   1. Chay CLI truc tiep: ./run_lemma.sh fetch --mode sample                  #
#   2. Chay Menu tuong tac: ./run_lemma.sh                                     #
# ============================================================================== #

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Dinh vi Python (.venv)
if [ -f "$WORKSPACE_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$WORKSPACE_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
else
    echo "[Loi] Khong tim thay Python! Vui long cai dat Python 3."
    exit 1
fi

export PYTHONPATH="$WORKSPACE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
CLI_MODULE="src.datasets.lemma_rca.interface.cli"

# Neu co tham so dong lenh -> Chuyen tiep cho CLI
if [ "$#" -gt 0 ]; then
    case "$1" in
        test)
            echo "=== CHAY KIEM THU LEMMA-RCA (PYTEST) ==="
            "$PYTHON_BIN" -m pytest "$WORKSPACE_ROOT/src/datasets/lemma_rca/tests/"
            exit $?
            ;;
        *)
            "$PYTHON_BIN" -m "$CLI_MODULE" "$@"
            exit $?
            ;;
    esac
fi

# ============================================================================== #
# Interactive Menu (Khi chay khong kem tham so)                                 #
# ============================================================================== #
clear 2>/dev/null || true
echo "========================================================================"
echo "          LEMMA-RCA DATASET MANAGER & LOG EXPLORATION TOOL              "
echo "========================================================================"
echo " Thư mục làm việc: $SCRIPT_DIR"
echo " Python interpreter: $PYTHON_BIN"
echo "------------------------------------------------------------------------"
echo " [1] Tải dữ liệu SAMPLE (~48MB via HTTP Range - Khuyến nghị)"
echo " [2] Tải toàn bộ dữ liệu FULL (~51GB từ Hugging Face)"
echo " [3] Xem kế hoạch tải (Dry Run - không tải thật)"
echo " [4] Xem Profile 4 tiêu chí bắt buộc (Shape, Columns, Head, Value Counts)"
echo " [5] Xem danh sách ca sự cố Ground Truth & Chi tiết"
echo " [6] Tìm kiếm và đọc nội dung Log thực tế (lọc theo service/level/keyword)"
echo " [7] Xuất log ra file CSV / JSON (để mở trong Excel hoặc phân tích)"
echo " [8] Chạy Unit Tests kiểm tra module (pytest)"
echo " [0] Thoát"
echo "========================================================================"
read -p "Chọn chức năng [0-8]: " choice

case "$choice" in
    1)
        echo -e "\n>>> Đang tải dữ liệu SAMPLE..."
        "$PYTHON_BIN" -m "$CLI_MODULE" fetch --mode sample
        ;;
    2)
        echo -e "\n>>> CẢNH BÁO: Chế độ FULL sẽ tải ~51GB từ Hugging Face."
        read -p "Bạn có chắc chắn muốn tải 51GB không? (y/N): " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            "$PYTHON_BIN" -m "$CLI_MODULE" fetch --mode full
        else
            echo "Đã hủy tải FULL."
        fi
        ;;
    3)
        echo -e "\n>>> Kế hoạch tải (Dry Run):"
        "$PYTHON_BIN" -m "$CLI_MODULE" fetch --mode sample --dry-run
        ;;
    4)
        echo -e "\n>>> Profile dữ liệu LEMMA-RCA:"
        "$PYTHON_BIN" -m "$CLI_MODULE" profile --limit 10000
        ;;
    5)
        echo -e "\n>>> Danh sách sự cố Ground Truth:"
        "$PYTHON_BIN" -m "$CLI_MODULE" list-incidents
        echo ""
        read -p "Nhập ID sự cố để xem chi tiết (bỏ trống để quay lại): " inc_id
        if [ -n "$inc_id" ]; then
            "$PYTHON_BIN" -m "$CLI_MODULE" show-incident --id "$inc_id"
        fi
        ;;
    6)
        echo -e "\n>>> Tra cứu Log LEMMA-RCA:"
        read -p "Lọc theo service (ví dụ: productpage, reviews, dispatch, rỗng = tất cả): " filter_svc
        read -p "Lọc theo level (DEBUG, INFO, WARN, ERROR, rỗng = tất cả): " filter_lvl
        read -p "Lọc theo từ khóa trong message (rỗng = không lọc): " filter_q
        read -p "Số dòng muốn xem (mặc định: 15): " filter_limit
        filter_limit=${filter_limit:-15}
        CMD_ARGS=(logs --limit "$filter_limit")
        [ -n "$filter_svc" ] && CMD_ARGS+=(--service "$filter_svc")
        [ -n "$filter_lvl" ] && CMD_ARGS+=(--level "$filter_lvl")
        [ -n "$filter_q" ] && CMD_ARGS+=(--query "$filter_q")
        "$PYTHON_BIN" -m "$CLI_MODULE" "${CMD_ARGS[@]}"
        ;;
    7)
        echo -e "\n>>> Xuất dữ liệu Log ra file:"
        read -p "Định dạng xuất (csv/json, mặc định: csv): " exp_fmt
        exp_fmt=${exp_fmt:-csv}
        read -p "Tên file xuất (mặc định: lemma_logs.$exp_fmt): " exp_out
        exp_out=${exp_out:-lemma_logs.$exp_fmt}
        read -p "Lọc theo level (DEBUG, INFO, WARN, ERROR, rỗng = tất cả): " exp_lvl
        read -p "Lọc theo service (rỗng = tất cả): " exp_svc
        read -p "Số dòng tối đa (rỗng = tất cả): " exp_limit
        EXP_ARGS=(export --output "$exp_out" --format "$exp_fmt")
        [ -n "$exp_lvl" ] && EXP_ARGS+=(--level "$exp_lvl")
        [ -n "$exp_svc" ] && EXP_ARGS+=(--service "$exp_svc")
        [ -n "$exp_limit" ] && EXP_ARGS+=(--limit "$exp_limit")
        "$PYTHON_BIN" -m "$CLI_MODULE" "${EXP_ARGS[@]}"
        ;;
    8)
        echo -e "\n>>> Chạy pytest:"
        "$PYTHON_BIN" -m pytest "$WORKSPACE_ROOT/src/datasets/lemma_rca/tests/"
        ;;
    0)
        echo "Tạm biệt!"
        exit 0
        ;;
    *)
        echo "Lựa chọn không hợp lệ."
        exit 1
        ;;
esac
