import os
import socket
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ==============================================================================
# CẤU HÌNH STREAMLIT
# ==============================================================================

st.set_page_config(
    page_title="Nhôm Hoàng Gia - Cổng nhôm cao cấp",
    page_icon="🏠",
    layout="wide"
)

# ==============================================================================
# KẾT NỐI AIVEN MYSQL
# ==============================================================================

# Khuyến nghị: Ưu tiên lấy cấu hình từ st.secrets nếu triển khai web (Streamlit Cloud)
# Nếu không tìm thấy secrets, sẽ fallback về giá trị cấu hình trực tiếp bên dưới.

try:
    DB_USER = st.secrets["mysql"]["user"]
    DB_PASSWORD = st.secrets["mysql"]["password"]
    DB_HOST = st.secrets["mysql"]["host"]
    DB_PORT = st.secrets["mysql"]["port"]
    DB_NAME = st.secrets["mysql"]["database"]
except Exception:
    # Cấu hình trực tiếp trên máy local (Lưu ý: Thay đổi password nếu đổi trên Aiven)
    DB_USER = "avnadmin" # sửa lại user
    DB_PASSWORD = "AVNS_1JPNssDgmO_BqXf9Rmf" # sửa lại password
    DB_HOST = "mysql-25a34fbe-ngctruc5-4830.e.aivencloud.com" # sửa lại host
    DB_PORT = 26716 # sửa lại port
    DB_NAME = "defaultdb"

# ------------------------------------------------------------------
# Làm sạch dữ liệu kết nối
# ------------------------------------------------------------------

DB_USER = str(DB_USER).strip()
DB_PASSWORD = str(DB_PASSWORD).strip()
DB_HOST = str(DB_HOST).strip()
DB_NAME = str(DB_NAME).strip()
DB_PORT = int(DB_PORT)

# ==============================================================================
# DEBUG KẾT NỐI
# ==============================================================================

with st.expander("🔧 Kiểm tra kết nối Aiven", expanded=False):
    st.write("**HOST:**", repr(DB_HOST))
    st.write("**PORT:**", repr(DB_PORT))
    st.write("**DATABASE:**", repr(DB_NAME))
    st.write("**USER:**", repr(DB_USER))

    if DB_HOST != DB_HOST.strip():
        st.error("HOST đang có khoảng trắng ở đầu hoặc cuối. Đã tự động loại bỏ.")
    else:
        st.success("HOST không có khoảng trắng.")

    if st.button("🔍 Kiểm tra DNS Aiven"):
        try:
            ip_address = socket.gethostbyname(DB_HOST)
            st.success(f"DNS OK - Host Aiven trỏ tới IP: {ip_address}")
        except Exception as e:
            st.error(f"DNS ERROR: Không phân giải được hostname Aiven.\n\n{e}")

# ==============================================================================
# TẠO DATABASE URL
# ==============================================================================

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

# ==============================================================================
# DATABASE ENGINE
# ==============================================================================

@st.cache_resource
def get_db_engine():
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 15},
        pool_size=5,
        max_overflow=5,
    )
    return engine

# ==============================================================================
# KIỂM TRA KẾT NỐI MYSQL
# ==============================================================================

def test_database_connection():
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return True, "Kết nối Aiven MySQL thành công!"
    except Exception as e:
        return False, str(e)

# ==============================================================================
# TẠO BẢNG ORDERS
# ==============================================================================

def init_db():
    engine = get_db_engine()
    create_table_query = """
    CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        created_at DATETIME NOT NULL,
        customer_name VARCHAR(100) NOT NULL,
        phone VARCHAR(30) NOT NULL,
        construction_type VARCHAR(100) NULL,
        category VARCHAR(100) NULL,
        paint_color VARCHAR(100) NULL,
        price_package VARCHAR(100) NULL,
        item_name VARCHAR(150) NOT NULL,
        width_m DECIMAL(8,2) NULL,
        height_m DECIMAL(8,2) NULL,
        quantity INT NOT NULL,
        unit_price DECIMAL(12,2) NOT NULL,
        total_price DECIMAL(12, 2) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with engine.begin() as conn:
        conn.exec_driver_sql(create_table_query)

# ==============================================================================
# KHỞI TẠO DATABASE
# ==============================================================================

db_connected = False
try:
    init_db()
    db_connected = True
except Exception as e:
    db_connected = False
    st.error("❌ Không thể kết nối Aiven MySQL.")
    st.code(str(e), language="text")
    st.warning("Kiểm tra lại HOST, PORT, USER, PASSWORD và DATABASE trong Aiven.")

# ==============================================================================
# DANH MỤC NHÔM HOÀNG GIA

loai_cong_trinh = [
    "Nhà hiện đại", "Nhà cổ điển", "Nhà tân cổ điển",
    "Nhà thờ", "Nhà chùa", "Nhà tổ", "Biệt thự",
    "Nhà phố", "Nhà vườn", "Công trình khác",
]

mau_son = [
    "Đồng giả cổ", "Mạ vàng", "Xám khói", "Màu đen",
    "Đen điểm vàng", "Xám phối vàng", "Nâu giả đồng",
    "Trắng kem", "Màu theo yêu cầu",
]

hang_muc = [
    "Cổng", "Lan can", "Hàng rào", "Cột",
    "Chông rào", "Hạng mục khác",
]

don_gia = {
    "7 triệu": 7000000,
    "7,5 triệu": 7500000,
    "8 triệu": 8000000,
    "8,5 triệu": 8500000,
    "9 triệu": 9000000,
    "9,5 triệu": 9500000,
    "10 triệu": 10000000,
}

# SESSION STATE
# ==============================================================================

if "order_dict" not in st.session_state:
    st.session_state.order_dict = {}

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ==============================================================================
# HÀM ĐỌC LỊCH SỬ TỪ MYSQL
# ==============================================================================

def load_history_from_db():
    try:
        engine = get_db_engine()
        df = pd.read_sql(
            text(
                """
                SELECT
                    id,
                    created_at,
                    customer_name,
                    phone,
                    construction_type,
                    category,
                    paint_color,
                    price_package,
                    item_name,
                    width_m,
                    height_m,
                    quantity,
                    unit_price,
                    total_price
                FROM orders
                ORDER BY created_at DESC
                """
            ),
            engine
        )

        if not df.empty:
            df.rename(
                columns={
                    "id": "ID",
                    "created_at": "Thời gian",
                    "customer_name": "Khách hàng",
                    "phone": "Số điện thoại",
                    "construction_type": "Loại công trình",
                    "category": "Hạng mục",
                    "paint_color": "Màu sơn",
                    "price_package": "Gói giá",
                    "item_name": "Sản phẩm",
                    "width_m": "Rộng (m)",
                    "height_m": "Cao (m)",
                    "quantity": "Số lượng",
                    "unit_price": "Đơn giá",
                    "total_price": "Thành tiền",
                },
                inplace=True
            )
        return df
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu từ Aiven: {e}")
        return pd.DataFrame()

# ==============================================================================
# SIDEBAR
# ==============================================================================

st.sidebar.title("🏠 NHÔM HOÀNG GIA")
page = st.sidebar.radio("📋 Chọn trang hệ thống", ["🏠 Sản phẩm & Đặt hàng", "🔑 Admin"])

# ==============================================================================
# TRANG ORDER
# ==============================================================================

if page == "🏠 Sản phẩm & Đặt hàng":
    st.title("🏠 NHÔM HOÀNG GIA")
    st.caption("Cổng nhôm • Lan can • Hàng rào • Cột • Chông rào • Hạng mục khác")

    if db_connected:
        st.success("🟢 Aiven MySQL: ĐÃ KẾT NỐI")
    else:
        st.error("🔴 Aiven MySQL: CHƯA KẾT NỐI")

    st.markdown("---")
    st.subheader("✨ Tư vấn và đặt sản phẩm")

    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.subheader("👤 Thông tin khách hàng")
        customer_name = st.text_input("Họ và tên", placeholder="Nhập họ tên")
        phone = st.text_input("Số điện thoại", placeholder="Nhập số điện thoại")

        st.subheader("🏡 Loại công trình")
        loai_nha = st.selectbox("Phong cách / loại nhà", loai_cong_trinh)

        st.subheader("🧱 Sản phẩm")
        hang_muc_chon = st.selectbox("Hạng mục", hang_muc)

        st.subheader("🎨 Màu sơn")
        mau_son_chon = st.selectbox("Màu sơn", mau_son)

        st.subheader("💰 Đơn giá")
        goi_gia = st.selectbox("Chọn mức giá tham khảo", list(don_gia.keys()))
        price = don_gia[goi_gia]

        st.info(
            "Mức giá tham khảo từ 7.000.000 đến 10.000.000 VNĐ. "
            "Giá thực tế có thể thay đổi theo mẫu, kích thước, màu sơn "
            "và yêu cầu gia công."
        )

        st.subheader("📏 Kích thước")
        width_m = st.number_input("Chiều rộng (m)", min_value=0.3, max_value=20.0, value=3.0, step=0.1)
        height_m = st.number_input("Chiều cao (m)", min_value=0.5, max_value=10.0, value=2.5, step=0.1)
        quantity = st.number_input("Số lượng", min_value=1, step=1, value=1)

        product_name = f"{hang_muc_chon} - {mau_son_chon} - {loai_nha}"

        st.markdown(f"### {product_name}")
        st.write(f"**Đơn giá tham khảo:** {price:,.0f} VNĐ")
        st.write(f"**Kích thước:** {width_m:.1f}m × {height_m:.1f}m")

        if st.button("➕ Thêm vào đơn hàng", use_container_width=True):
            if not customer_name.strip() or not phone.strip():
                st.warning("Vui lòng nhập họ tên và số điện thoại.")
            else:
                key = f"{loai_nha}_{hang_muc_chon}_{mau_son_chon}_{goi_gia}_{width_m}_{height_m}"
                st.session_state.order_dict[key] = {
                    "Khách hàng": customer_name,
                    "Số điện thoại": phone,
                    "Loại công trình": loai_nha,
                    "Hạng mục": hang_muc_chon,
                    "Màu sơn": mau_son_chon,
                    "Gói giá": goi_gia,
                    "Sản phẩm": product_name,
                    "Chiều rộng (m)": width_m,
                    "Chiều cao (m)": height_m,
                    "Đơn giá": price,
                    "Số lượng": quantity,
                    "Thành tiền": price * quantity,
                }
                st.success("Đã thêm sản phẩm vào đơn hàng!")
                st.rerun()

    with col2:
        st.subheader("🛒 Đơn hàng hiện tại")

        if st.session_state.order_dict:
            df = pd.DataFrame.from_dict(st.session_state.order_dict, orient="index")
            st.dataframe(
                df[
                    [
                        "Khách hàng", "Loại công trình", "Hạng mục",
                        "Màu sơn", "Sản phẩm", "Chiều rộng (m)",
                        "Chiều cao (m)", "Đơn giá", "Số lượng", "Thành tiền"
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            tam_tinh = df["Thành tiền"].sum()
            st.metric("💰 Tổng giá trị đơn hàng", f"{tam_tinh:,.0f} VNĐ")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("📩 Gửi đơn hàng", use_container_width=True):
                    if not db_connected:
                        st.error("Không thể lưu đơn vì Aiven MySQL chưa kết nối.")
                    else:
                        try:
                            now_time = datetime.now()
                            records = []
                            for row in st.session_state.order_dict.values():
                                records.append({
                                    "created_at": now_time,
                                    "customer_name": row["Khách hàng"],
                                    "phone": row["Số điện thoại"],
                                    "construction_type": row["Loại công trình"],
                                    "category": row["Hạng mục"],
                                    "paint_color": row["Màu sơn"],
                                    "price_package": row["Gói giá"],
                                    "item_name": row["Sản phẩm"],
                                    "width_m": row["Chiều rộng (m)"],
                                    "height_m": row["Chiều cao (m)"],
                                    "quantity": row["Số lượng"],
                                    "unit_price": row["Đơn giá"],
                                    "total_price": row["Thành tiền"],
                                })
                            pd.DataFrame(records).to_sql(
                                "orders", get_db_engine(), if_exists="append", index=False
                            )
                            st.success("✅ Gửi đơn hàng thành công!")
                            st.session_state.order_dict = {}
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi lưu đơn hàng: {e}")

            with c2:
                if st.button("🗑️ Xóa đơn", use_container_width=True):
                    st.session_state.order_dict = {}
                    st.rerun()
        else:
            st.info("🛒 Chưa có sản phẩm trong đơn hàng.")

    st.markdown("---")
    st.subheader("📐 Kích thước tham khảo")
    sizes = pd.DataFrame([
        ["Cổng 1 cánh", "0,9 – 1,2m", "2,0 – 2,5m"],
        ["Cổng 2 cánh", "2,8 – 3,6m", "2,2 – 3,0m"],
        ["Cổng 4 cánh", "3,6 – 5,0m", "2,2 – 3,2m"],
        ["Hàng rào / lan can", "Theo thực tế", "Theo thực tế"],
    ], columns=["Hạng mục", "Chiều rộng", "Chiều cao"])
    st.dataframe(sizes, use_container_width=True, hide_index=True)

# TRANG ADMIN
# ==============================================================================

elif page == "🔑 Admin":
    st.title("🔑 Quản trị - Nhôm Hoàng Gia")

    # --------------------------------------------------------------
    # LOGIN ADMIN
    # --------------------------------------------------------------
    if not st.session_state.admin_logged_in:
        with st.form("admin_login_form"):
            password = st.text_input(
                "🔐 Nhập mật khẩu quản trị", type="password"
            )
            login_submitted = st.form_submit_button("🔑 Đăng nhập")

            if login_submitted:
                if password == "123456":
                    st.session_state.admin_logged_in = True
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("❌ Mật khẩu không chính xác!")

        st.warning("Vui lòng nhập mật khẩu quản trị.")
        st.stop()

    # --------------------------------------------------------------
    # ADMIN ĐÃ ĐĂNG NHẬP
    # --------------------------------------------------------------
    col_header_title, col_header_btn = st.columns([4, 1])

    with col_header_title:
        st.success("🟢 Xác thực quyền Quản trị viên thành công!")

    with col_header_btn:
        if st.button("🔒 Đăng xuất"):
            st.session_state.admin_logged_in = False
            st.rerun()

    # --------------------------------------------------------------
    # TABS ADMIN
    # --------------------------------------------------------------
    tab1, tab2, tab3 = st.tabs([
        "📋 Danh mục sản phẩm",
        "💰 Doanh thu & Nhật ký giao dịch",
        "📊 Thống kê & Phân tích",
    ])

    # TAB 1 - MENU
    with tab1:
        st.subheader("🚪 Danh mục sản phẩm - Nhôm Hoàng Gia")
        st.markdown("**Loại công trình:** " + " • ".join(loai_cong_trinh))
        st.markdown("**Màu sơn:** " + " • ".join(mau_son))
        st.markdown("**Hạng mục:** " + " • ".join(hang_muc))
        df_price = pd.DataFrame(
            [[k, v] for k, v in don_gia.items()],
            columns=["Mức giá", "Đơn giá (VNĐ)"]
        )
        st.dataframe(
            df_price.style.format({"Đơn giá (VNĐ)": "{:,.0f} VNĐ"}),
            use_container_width=True,
            hide_index=True
        )

    # TAB 2 - DOANH THU
    with tab2:
        st.subheader("💰 Doanh thu & Hóa đơn thực tế")
        df_history = load_history_from_db()

        if not df_history.empty:
            tong_doanh_thu = df_history["Thành tiền"].sum()
            tong_mon = df_history["Số lượng"].sum()

            col_met1, col_met2 = st.columns(2)
            with col_met1:
                st.metric("💰 Tổng doanh thu", f"{tong_doanh_thu:,.0f} VNĐ")
            with col_met2:
                st.metric("🍽️ Số lượng sản phẩm đã phục vụ", f"{tong_mon} bộ")

            st.markdown("---")

            st.subheader("📅 Doanh thu theo ngày")
            df_history["Ngày"] = pd.to_datetime(df_history["Thời gian"]).dt.date
            df_daily_revenue = (
                df_history.groupby("Ngày")["Thành tiền"]
                .sum()
                .reset_index()
            )
            df_daily_revenue.columns = ["Ngày", "Doanh thu (VNĐ)"]

            col_chart_day, col_table_day = st.columns([1.5, 1])
            with col_chart_day:
                st.bar_chart(
                    df_daily_revenue.set_index("Ngày")["Doanh thu (VNĐ)"]
                )

            with col_table_day:
                st.dataframe(
                    df_daily_revenue.style.format(
                        {"Doanh thu (VNĐ)": "{:,.0f} VNĐ"}
                    ),
                    use_container_width=True,
                    hide_index=True
                )

            st.markdown("---")

            st.subheader("📋 Chi tiết lịch sử thanh toán thực tế")
            st.dataframe(
                df_history[["ID", "Thời gian", "Khách hàng", "Số điện thoại", "Loại công trình",
                   "Hạng mục", "Màu sơn", "Gói giá", "Sản phẩm", "Rộng (m)", "Cao (m)",
                   "Số lượng", "Đơn giá", "Thành tiền"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Hệ thống chưa ghi nhận giao dịch nào.")

    # TAB 3 - PHÂN TÍCH
    with tab3:
        st.subheader("📊 Thống kê & Phân tích bán hàng REAL-TIME")
        df_anal = load_history_from_db()

        if not df_anal.empty:
            df_anal["Thời gian"] = pd.to_datetime(df_anal["Thời gian"])
            df_anal["Giờ"] = df_anal["Thời gian"].dt.hour
            df_anal["Tháng-Năm"] = df_anal["Thời gian"].dt.strftime("%m/%Y")

            # Món bán chạy
            product_quantity = df_anal.groupby("Sản phẩm")["Số lượng"].sum()
            best_seller = product_quantity.idxmax()
            best_seller_qty = product_quantity.max()

            # Khung giờ vàng
            hourly_sales = df_anal.groupby("Giờ")["Số lượng"].sum()
            best_hour = hourly_sales.idxmax()
            best_hour_qty = hourly_sales.max()

            # Tháng doanh thu cao nhất
            monthly_revenue = df_anal.groupby("Tháng-Năm")["Thành tiền"].sum()
            best_month = monthly_revenue.idxmax()
            best_month_rev = monthly_revenue.max()

            # KPI
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            with col_kpi1:
                st.info("🏆 MÓN BÁN CHẠY NHẤT")
                st.metric(label=best_seller, value=f"{best_seller_qty} bộ")

            with col_kpi2:
                st.warning("⚡ KHUNG GIỜ BÁN NHIỀU NHẤT")
                st.metric(
                    label=f"{best_hour:02d}:00 - {(best_hour + 1) % 24:02d}:00",
                    value=f"{best_hour_qty} phần"
                )

            with col_kpi3:
                st.success("📅 THÁNG DOANH THU CAO NHẤT")
                st.metric(label=f"Tháng {best_month}", value=f"{best_month_rev:,.0f} VNĐ")

            st.markdown("---")

            # Phân tích theo món
            st.subheader("🚪 Doanh thu & số lượng từng sản phẩm")
            summary_mon = (
                df_anal.groupby("Sản phẩm")
                .agg(
                    Số_lượng_bán=("Số lượng", "sum"),
                    Doanh_thu=("Thành tiền", "sum")
                )
                .reset_index()
                .sort_values(by="Số_lượng_bán", ascending=False)
            )

            col_chart1, col_table1 = st.columns([1.5, 1])
            with col_chart1:
                st.bar_chart(summary_mon.set_index("Tên món")["Số_lượng_bán"])

            with col_table1:
                st.dataframe(
                    summary_mon.style.format({"Doanh_thu": "{:,.0f} VNĐ"}),
                    use_container_width=True,
                    hide_index=True
                )

            st.markdown("---")

            # Phân tích theo giờ
            st.subheader("📦 Số lượng sản phẩm bán theo giờ")
            summary_gio = (
                df_anal.groupby("Giờ")
                .agg(
                    Số_lượng_sản_phẩm=("Số lượng", "sum"),
                    Doanh_thu=("Thành tiền", "sum")
                )
                .reset_index()
            )

            all_hours = pd.DataFrame({"Giờ": range(24)})
            summary_gio = pd.merge(all_hours, summary_gio, on="Giờ", how="left").fillna(0)

            col_chart2, col_info2 = st.columns([1.5, 1])
            with col_chart2:
                st.bar_chart(summary_gio.set_index("Giờ")["Số_lượng_sản_phẩm"])

            with col_info2:
                st.write(f"**Khung giờ bán nhiều nhất:** {best_hour:02d}:00 - {(best_hour + 1) % 24:02d}:00")
                st.write(f"**Số lượng:** {best_hour_qty} bộ")
                st.dataframe(
                    summary_gio[summary_gio["Số_lượng_sản_phẩm"] > 0].style.format(
                        {"Doanh_thu": "{:,.0f} VNĐ"}
                    ),
                    use_container_width=True,
                    hide_index=True
                )

            st.markdown("---")

            # Phân tích theo tháng
            st.subheader("📅 Doanh thu bán hàng theo tháng")
            df_anal["Tháng_Số"] = df_anal["Thời gian"].dt.month
            summary_thang = (
                df_anal.groupby(["Tháng_Số", "Tháng-Năm"])
                .agg(
                    Số_lượng_bán=("Số lượng", "sum"),
                    Doanh_thu=("Thành tiền", "sum")
                )
                .reset_index()
                .sort_values("Tháng_Số")
            )

            col_chart3, col_table3 = st.columns([1.5, 1])
            with col_chart3:
                st.bar_chart(summary_thang.set_index("Tháng-Năm")["Doanh_thu"])

            with col_table3:
                st.dataframe(
                    summary_thang[["Tháng-Năm", "Số_lượng_bán", "Doanh_thu"]].style.format(
                        {"Doanh_thu": "{:,.0f} VNĐ"}
                    ),
                    use_container_width=True,
                    hide_index=True
                )

        else:
            st.info("Chưa có dữ liệu giao dịch để thống kê.")
            
