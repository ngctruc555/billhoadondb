import os
import socket
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ==============================================================================
# NHÔM HOÀNG GIA - TRANG BÁN CỔNG NHÔM
# ==============================================================================

st.set_page_config(
    page_title="Nhôm Hoàng Gia - Cổng nhôm cao cấp",
    page_icon="🏠",
    layout="wide",
)


# ==============================================================================
# KẾT NỐI AIVEN MYSQL
# ==============================================================================

# Khuyến nghị: dùng st.secrets khi triển khai Streamlit Cloud.
try:
    DB_USER = st.secrets["mysql"]["user"]
    DB_PASSWORD = st.secrets["mysql"]["password"]
    DB_HOST = st.secrets["mysql"]["host"]
    DB_PORT = st.secrets["mysql"]["port"]
    DB_NAME = st.secrets["mysql"]["database"]
except Exception:
    # Chỉ dùng thông tin bên dưới nếu bạn chạy local.
    # Không nên đưa mật khẩu thật lên GitHub.
    DB_USER = "avnadmin"
    DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    DB_HOST = "mysql-25a34fbe-ngctruc5-4830.e.aivencloud.com"
    DB_PORT = 26716
    DB_NAME = "defaultdb"

DB_USER = str(DB_USER).strip()
DB_PASSWORD = str(DB_PASSWORD).strip()
DB_HOST = str(DB_HOST).strip()
DB_NAME = str(DB_NAME).strip()
DB_PORT = int(DB_PORT)


DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)


@st.cache_resource
def get_db_engine():
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 15},
        pool_size=5,
        max_overflow=5,
    )


def test_database_connection():
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).fetchone()
        return True, "Kết nối Aiven MySQL thành công!"
    except Exception as e:
        return False, str(e)


# ==============================================================================
# DATABASE
# ==============================================================================

def init_db():
    engine = get_db_engine()

    create_table_query = """
    CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        created_at DATETIME NOT NULL,
        customer_name VARCHAR(100) NOT NULL,
        phone VARCHAR(30) NOT NULL,
        item_name VARCHAR(150) NOT NULL,
        width_m DECIMAL(8,2) NULL,
        height_m DECIMAL(8,2) NULL,
        quantity INT NOT NULL,
        unit_price DECIMAL(12,2) NOT NULL,
        total_price DECIMAL(12,2) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    with engine.begin() as conn:
        conn.exec_driver_sql(create_table_query)


db_connected = False
try:
    init_db()
    db_connected = True
except Exception as e:
    st.error("❌ Không thể kết nối Aiven MySQL.")
    st.code(str(e), language="text")
    st.warning("Kiểm tra HOST, PORT, USER, PASSWORD và DATABASE trong Aiven.")


# ==============================================================================
# CSS
# ==============================================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .sub-title {
        font-size: 20px;
        color: #777;
        margin-top: 0;
    }

    .product-card {
        padding: 22px;
        border-radius: 16px;
        border: 1px solid #ddd;
        background: linear-gradient(145deg, #ffffff, #f5f5f5);
        margin-bottom: 15px;
    }

    .gold-text {
        font-weight: 800;
        font-size: 25px;
    }

    .price-text {
        font-size: 24px;
        font-weight: 800;
    }

    .info-box {
        padding: 16px;
        border-radius: 12px;
        background: #f7f7f7;
        border: 1px solid #e4e4e4;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# SẢN PHẨM
# ==============================================================================

products = {
    "Cổng nhôm xám phối vàng": {
        "category": "Cổng nhôm đúc",
        "price": 18500000,
        "description": "Cổng nhôm màu xám phối vàng, phong cách sang trọng, phù hợp nhà phố và biệt thự.",
    },
    "Cổng nhôm xám hiện đại": {
        "category": "Cổng nhôm hiện đại",
        "price": 16000000,
        "description": "Thiết kế tối giản, màu xám hiện đại, phù hợp mặt tiền nhà phố.",
    },
    "Cổng nhôm vàng cao cấp": {
        "category": "Cổng nhôm cao cấp",
        "price": 22000000,
        "description": "Mẫu cổng nhôm tạo điểm nhấn nổi bật cho biệt thự và nhà vườn.",
    },
    "Cổng nhôm 4 cánh": {
        "category": "Cổng nhôm biệt thự",
        "price": 28000000,
        "description": "Cổng 4 cánh kích thước lớn, phù hợp sân rộng và mặt tiền biệt thự.",
    },
}


# ==============================================================================
# SESSION STATE
# ==============================================================================

if "order_dict" not in st.session_state:
    st.session_state.order_dict = {}

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False


# ==============================================================================
# ĐỌC LỊCH SỬ
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
            engine,
        )

        if not df.empty:
            df.rename(
                columns={
                    "id": "ID",
                    "created_at": "Thời gian",
                    "customer_name": "Khách hàng",
                    "phone": "Số điện thoại",
                    "item_name": "Sản phẩm",
                    "width_m": "Rộng (m)",
                    "height_m": "Cao (m)",
                    "quantity": "Số lượng",
                    "unit_price": "Đơn giá",
                    "total_price": "Thành tiền",
                },
                inplace=True,
            )

        return df

    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu từ Aiven: {e}")
        return pd.DataFrame()


# ==============================================================================
# SIDEBAR
# ==============================================================================

st.sidebar.title("🏠 NHÔM HOÀNG GIA")
st.sidebar.caption("Cổng nhôm cao cấp")

page = st.sidebar.radio(
    "📋 Chọn trang",
    ["🏠 Sản phẩm & Đặt hàng", "🔑 Quản trị"],
)


# ==============================================================================
# TRANG BÁN HÀNG
# ==============================================================================

if page == "🏠 Sản phẩm & Đặt hàng":

    st.markdown(
        '<p class="main-title">🏠 NHÔM HOÀNG GIA</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-title">Cổng nhôm cao cấp • Thiết kế sang trọng • Làm theo kích thước</p>',
        unsafe_allow_html=True,
    )

    if db_connected:
        st.success("🟢 Hệ thống lưu đơn hàng: ĐÃ KẾT NỐI")
    else:
        st.error("🔴 Hệ thống lưu đơn hàng: CHƯA KẾT NỐI")

    st.markdown("---")

    st.subheader("✨ Cổng nhôm xám phối vàng")

    st.markdown(
        """
        <div class="info-box">
        <b>NHÔM HOÀNG GIA</b> nhận thiết kế và gia công cổng nhôm theo kích thước
        thực tế. Màu chủ đạo xám phối vàng, phù hợp nhà phố, biệt thự và nhà vườn.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 📐 Kích thước tham khảo")

    size_df = pd.DataFrame(
        [
            ["1 cánh", "0,9 – 1,2", "2,0 – 2,5"],
            ["2 cánh", "2,8 – 3,6", "2,2 – 3,0"],
            ["4 cánh", "3,6 – 5,0", "2,2 – 3,2"],
            ["Biệt thự / cổng lớn", "4,0 – 6,0", "2,5 – 3,5"],
        ],
        columns=["Loại cổng", "Chiều rộng (m)", "Chiều cao (m)"],
    )
    st.dataframe(size_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    col1, col2 = st.columns([1, 1.25])

    # --------------------------------------------------------------------------
    # THÔNG TIN KHÁCH + CHỌN CỔNG
    # --------------------------------------------------------------------------
    with col1:
        st.subheader("🛒 Chọn sản phẩm")

        customer_name = st.text_input(
            "👤 Họ và tên khách hàng",
            placeholder="Nhập họ tên",
        )

        phone = st.text_input(
            "📞 Số điện thoại",
            placeholder="Nhập số điện thoại",
        )

        product_name = st.selectbox(
            "🚪 Chọn mẫu cổng",
            list(products.keys()),
        )

        product = products[product_name]

        st.markdown(
            f"""
            <div class="product-card">
                <div class="gold-text">{product_name}</div>
                <p>{product["description"]}</p>
                <div class="price-text">{product["price"]:,.0f} VNĐ / bộ</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.subheader("📏 Kích thước đặt hàng")

        width_m = st.number_input(
            "↔️ Chiều rộng cổng (m)",
            min_value=0.5,
            max_value=10.0,
            value=3.0,
            step=0.1,
        )

        height_m = st.number_input(
            "↕️ Chiều cao cổng (m)",
            min_value=1.5,
            max_value=5.0,
            value=2.5,
            step=0.1,
        )

        quantity = st.number_input(
            "🔢 Số lượng bộ",
            min_value=1,
            step=1,
            value=1,
        )

        price = product["price"]

        st.write(f"**Đơn giá tham khảo:** {price:,.0f} VNĐ / bộ")

        if st.button("➕ Thêm vào đơn hàng", use_container_width=True):
            if not customer_name.strip():
                st.warning("Vui lòng nhập họ tên khách hàng.")
            elif not phone.strip():
                st.warning("Vui lòng nhập số điện thoại.")
            else:
                key = f"{product_name}_{width_m}_{height_m}"

                if key in st.session_state.order_dict:
                    st.session_state.order_dict[key]["Số lượng"] += quantity
                    st.session_state.order_dict[key]["Thành tiền"] = (
                        st.session_state.order_dict[key]["Số lượng"] * price
                    )
                else:
                    st.session_state.order_dict[key] = {
                        "Khách hàng": customer_name,
                        "Số điện thoại": phone,
                        "Sản phẩm": product_name,
                        "Chiều rộng (m)": width_m,
                        "Chiều cao (m)": height_m,
                        "Đơn giá": price,
                        "Số lượng": quantity,
                        "Thành tiền": price * quantity,
                    }

                st.success(f"Đã thêm {product_name} vào đơn hàng!")
                st.rerun()

    # --------------------------------------------------------------------------
    # GIỎ HÀNG
    # --------------------------------------------------------------------------
    with col2:
        st.subheader("🧾 Đơn hàng của khách")

        if st.session_state.order_dict:
            df = pd.DataFrame.from_dict(
                st.session_state.order_dict,
                orient="index",
            )

            st.dataframe(
                df[
                    [
                        "Khách hàng",
                        "Sản phẩm",
                        "Chiều rộng (m)",
                        "Chiều cao (m)",
                        "Đơn giá",
                        "Số lượng",
                        "Thành tiền",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            tam_tinh = df["Thành tiền"].sum()

            st.markdown("---")
            st.write(f"**Tạm tính:** {tam_tinh:,.0f} VNĐ")
            st.metric(
                "💰 Tổng giá trị đơn hàng",
                f"{tam_tinh:,.0f} VNĐ",
            )

            st.info(
                "💡 Giá trên là giá tham khảo. Giá thực tế có thể thay đổi "
                "theo kích thước, mẫu mã, phụ kiện và yêu cầu gia công."
            )

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button(
                    "📩 Gửi đơn hàng",
                    use_container_width=True,
                ):
                    if not db_connected:
                        st.error(
                            "Không thể lưu đơn vì Aiven MySQL chưa kết nối."
                        )
                    else:
                        try:
                            now_time = datetime.now()
                            records = []

                            for row in st.session_state.order_dict.values():
                                records.append(
                                    {
                                        "created_at": now_time,
                                        "customer_name": row["Khách hàng"],
                                        "phone": row["Số điện thoại"],
                                        "item_name": row["Sản phẩm"],
                                        "width_m": row["Chiều rộng (m)"],
                                        "height_m": row["Chiều cao (m)"],
                                        "quantity": row["Số lượng"],
                                        "unit_price": row["Đơn giá"],
                                        "total_price": row["Thành tiền"],
                                    }
                                )

                            engine = get_db_engine()
                            df_to_save = pd.DataFrame(records)

                            df_to_save.to_sql(
                                "orders",
                                engine,
                                if_exists="append",
                                index=False,
                            )

                            st.success(
                                "✅ Đã gửi đơn hàng thành công! "
                                "Nhôm Hoàng Gia sẽ liên hệ tư vấn."
                            )

                            st.session_state.order_dict = {}
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Lỗi lưu đơn hàng: {e}")

            with col_btn2:
                if st.button(
                    "🗑️ Xóa đơn",
                    use_container_width=True,
                ):
                    st.session_state.order_dict = {}
                    st.rerun()

        else:
            st.info(
                "🛒 Chưa có sản phẩm. Hãy chọn mẫu cổng và kích thước ở bên trái."
            )

    st.markdown("---")

    st.subheader("⭐ Vì sao chọn Nhôm Hoàng Gia?")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown("### 🎨")
        st.write("**Màu xám phối vàng**")
        st.caption("Phong cách sang trọng, nổi bật.")

    with c2:
        st.markdown("### 📐")
        st.write("**Làm theo kích thước**")
        st.caption("Thiết kế theo thực tế công trình.")

    with c3:
        st.markdown("### 🏡")
        st.write("**Nhiều kiểu nhà**")
        st.caption("Phù hợp nhà phố, biệt thự, nhà vườn.")

    with c4:
        st.markdown("### 📞")
        st.write("**Tư vấn báo giá**")
        st.caption("Liên hệ để được tư vấn mẫu và kích thước.")


# ==============================================================================
# TRANG QUẢN TRỊ
# ==============================================================================

elif page == "🔑 Quản trị":

    st.title("🔑 Quản trị bán hàng - Nhôm Hoàng Gia")

    if not st.session_state.admin_logged_in:
        with st.form("admin_login_form"):
            password = st.text_input(
                "🔐 Nhập mật khẩu quản trị",
                type="password",
            )
            login_submitted = st.form_submit_button("🔑 Đăng nhập")

            if login_submitted:
                if password == os.getenv("ADMIN_PASSWORD", "123456"):
                    st.session_state.admin_logged_in = True
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("❌ Mật khẩu không chính xác!")

        st.warning("Vui lòng nhập mật khẩu quản trị.")
        st.stop()

    col_header_title, col_header_btn = st.columns([4, 1])

    with col_header_title:
        st.success("🟢 Xác thực quyền Quản trị viên thành công!")

    with col_header_btn:
        if st.button("🔒 Đăng xuất"):
            st.session_state.admin_logged_in = False
            st.rerun()

    tab1, tab2, tab3 = st.tabs(
        [
            "🚪 Danh sách sản phẩm",
            "💰 Đơn hàng & Doanh thu",
            "📊 Thống kê",
        ]
    )

    # --------------------------------------------------------------------------
    # TAB 1
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("🚪 Sản phẩm Nhôm Hoàng Gia")

        data = []

        for product_name, product in products.items():
            data.append(
                [
                    product["category"],
                    product_name,
                    product["price"],
                    product["description"],
                ]
            )

        df_products = pd.DataFrame(
            data,
            columns=[
                "Phân loại",
                "Tên sản phẩm",
                "Đơn giá tham khảo",
                "Mô tả",
            ],
        )

        st.dataframe(
            df_products.style.format(
                {"Đơn giá tham khảo": "{:,.0f} VNĐ"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------------------------
    # TAB 2
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("💰 Đơn hàng & doanh thu")

        df_history = load_history_from_db()

        if not df_history.empty:

            tong_doanh_thu = df_history["Thành tiền"].sum()
            tong_bo = df_history["Số lượng"].sum()

            col_met1, col_met2 = st.columns(2)

            with col_met1:
                st.metric(
                    "💰 Tổng doanh thu",
                    f"{tong_doanh_thu:,.0f} VNĐ",
                )

            with col_met2:
                st.metric(
                    "🚪 Số bộ cổng đã đặt",
                    f"{tong_bo}",
                )

            st.markdown("---")

            st.subheader("📅 Doanh thu theo ngày")

            df_history["Ngày"] = pd.to_datetime(
                df_history["Thời gian"]
            ).dt.date

            df_daily_revenue = (
                df_history.groupby("Ngày")["Thành tiền"]
                .sum()
                .reset_index()
            )

            df_daily_revenue.columns = [
                "Ngày",
                "Doanh thu (VNĐ)",
            ]

            col_chart_day, col_table_day = st.columns([1.5, 1])

            with col_chart_day:
                st.bar_chart(
                    df_daily_revenue.set_index("Ngày")[
                        "Doanh thu (VNĐ)"
                    ]
                )

            with col_table_day:
                st.dataframe(
                    df_daily_revenue.style.format(
                        {"Doanh thu (VNĐ)": "{:,.0f} VNĐ"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("---")

            st.subheader("📋 Chi tiết đơn hàng")

            st.dataframe(
                df_history[
                    [
                        "ID",
                        "Thời gian",
                        "Khách hàng",
                        "Số điện thoại",
                        "Sản phẩm",
                        "Rộng (m)",
                        "Cao (m)",
                        "Số lượng",
                        "Đơn giá",
                        "Thành tiền",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info("Chưa có đơn hàng nào.")

    # --------------------------------------------------------------------------
    # TAB 3
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("📊 Thống kê bán hàng")

        df_anal = load_history_from_db()

        if not df_anal.empty:

            df_anal["Thời gian"] = pd.to_datetime(
                df_anal["Thời gian"]
            )
            df_anal["Tháng-Năm"] = df_anal["Thời gian"].dt.strftime(
                "%m/%Y"
            )

            product_quantity = (
                df_anal.groupby("Sản phẩm")["Số lượng"].sum()
            )

            best_seller = product_quantity.idxmax()
            best_seller_qty = product_quantity.max()

            monthly_revenue = (
                df_anal.groupby("Tháng-Năm")["Thành tiền"].sum()
            )

            best_month = monthly_revenue.idxmax()
            best_month_rev = monthly_revenue.max()

            col_kpi1, col_kpi2 = st.columns(2)

            with col_kpi1:
                st.info("🏆 SẢN PHẨM ĐƯỢC ĐẶT NHIỀU NHẤT")
                st.metric(
                    label=best_seller,
                    value=f"{best_seller_qty} bộ",
                )

            with col_kpi2:
                st.success("📅 THÁNG DOANH THU CAO NHẤT")
                st.metric(
                    label=f"Tháng {best_month}",
                    value=f"{best_month_rev:,.0f} VNĐ",
                )

            st.markdown("---")

            st.subheader("🚪 Số lượng từng mẫu cổng")

            summary_product = (
                df_anal.groupby("Sản phẩm")
                .agg(
                    Số_lượng_bán=("Số lượng", "sum"),
                    Doanh_thu=("Thành tiền", "sum"),
                )
                .reset_index()
                .sort_values(
                    by="Số_lượng_bán",
                    ascending=False,
                )
            )

            col_chart1, col_table1 = st.columns([1.5, 1])

            with col_chart1:
                st.bar_chart(
                    summary_product.set_index("Sản phẩm")[
                        "Số_lượng_bán"
                    ]
                )

            with col_table1:
                st.dataframe(
                    summary_product.style.format(
                        {"Doanh_thu": "{:,.0f} VNĐ"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("---")

            st.subheader("📅 Doanh thu theo tháng")

            summary_month = (
                df_anal.groupby("Tháng-Năm")
                .agg(
                    Số_lượng_bán=("Số lượng", "sum"),
                    Doanh_thu=("Thành tiền", "sum"),
                )
                .reset_index()
            )

            col_chart2, col_table2 = st.columns([1.5, 1])

            with col_chart2:
                st.bar_chart(
                    summary_month.set_index("Tháng-Năm")[
                        "Doanh_thu"
                    ]
                )

            with col_table2:
                st.dataframe(
                    summary_month.style.format(
                        {"Doanh_thu": "{:,.0f} VNĐ"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

        else:
            st.info("Chưa có dữ liệu giao dịch để thống kê.")


# ==============================================================================
# CHÂN TRANG
# ==============================================================================

st.markdown("---")
st.caption(
    "© Nhôm Hoàng Gia | Cổng nhôm cao cấp | Thiết kế và gia công theo kích thước"
)
