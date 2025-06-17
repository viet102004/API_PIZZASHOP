
-- Bảng NguoiDung
CREATE TABLE NguoiDung (
    ma_nguoi_dung BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    so_dien_thoai VARCHAR(15) UNIQUE,
    mat_khau VARCHAR(255) NOT NULL,
    vai_tro VARCHAR(50) NOT NULL CHECK (vai_tro IN ('khach_hang', 'quan_tri_vien', 'bep', 'giao_hang', 'ho_tro', 'nhan_vien_cua_hang')),
    ho_ten VARCHAR(100),
    anh_dai_dien VARCHAR(255),
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    ngay_cap_nhat DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    hoat_dong BOOLEAN DEFAULT TRUE
);

-- Bảng HoSoKhachHang
CREATE TABLE HoSoKhachHang (
    ma_ho_so BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT UNIQUE NOT NULL,
    dia_chi VARCHAR(255),
    ngay_sinh DATE,
    cai_dat_thong_bao TEXT,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng TaiKhoan
CREATE TABLE TaiKhoan (
    ma_tai_khoan BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT UNIQUE NOT NULL,
    so_du DECIMAL(15, 2) DEFAULT 0.00,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng GiaoDich
CREATE TABLE GiaoDich (
    ma_giao_dich BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    loai_giao_dich VARCHAR(50) NOT NULL,
    so_tien DECIMAL(15, 2) NOT NULL,
    trang_thai VARCHAR(50) NOT NULL CHECK (trang_thai IN ('cho_xu_ly', 'hoan_thanh', 'that_bai')),
    phuong_thuc_thanh_toan VARCHAR(50),
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng DanhMuc - Phân loại sản phẩm chính
CREATE TABLE DanhMuc (
    ma_danh_muc BIGINT AUTO_INCREMENT PRIMARY KEY,
    ten_danh_muc VARCHAR(50) NOT NULL, 
    hinh_anh VARCHAR(255),
    mo_ta TEXT,
    thu_tu_hien_thi INT DEFAULT 0,
    hoat_dong BOOLEAN DEFAULT TRUE
);

-- Bảng LoaiTuyChon - Định nghĩa các loại tùy chọn có thể có
CREATE TABLE LoaiTuyChon (
    ma_loai_tuy_chon BIGINT AUTO_INCREMENT PRIMARY KEY,
    ten_loai VARCHAR(50) NOT NULL,
    mo_ta VARCHAR(255),
    loai_lua_chon ENUM('single', 'multiple') DEFAULT 'single',
    bat_buoc BOOLEAN DEFAULT FALSE
);

-- Bảng SanPham
CREATE TABLE SanPham (
    ma_san_pham BIGINT AUTO_INCREMENT PRIMARY KEY,
    ten_san_pham VARCHAR(100) NOT NULL,
    hinh_anh VARCHAR(255),
    mo_ta TEXT,
    gia_co_ban DECIMAL(10, 2) NOT NULL,
    hien_thi BOOLEAN DEFAULT TRUE,
    ma_danh_muc BIGINT,
    loai_san_pham VARCHAR(50), 
    moi BOOLEAN DEFAULT FALSE,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    ngay_cap_nhat DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_danh_muc) REFERENCES DanhMuc(ma_danh_muc) ON DELETE SET NULL
);

-- Bảng HinhAnhSanPham
CREATE TABLE HinhAnhSanPham (
    ma_hinh_anh BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_san_pham BIGINT NOT NULL,
    url_hinh_anh VARCHAR(255) NOT NULL,
    thu_tu INT DEFAULT 0,
    FOREIGN KEY (ma_san_pham) REFERENCES SanPham(ma_san_pham) ON DELETE CASCADE
);

-- Bảng TuyChonSanPham - Liên kết sản phẩm với các loại tùy chọn
CREATE TABLE TuyChonSanPham (
    ma_tuy_chon_san_pham BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_san_pham BIGINT NOT NULL,
    ma_loai_tuy_chon BIGINT NOT NULL,
    FOREIGN KEY (ma_san_pham) REFERENCES SanPham(ma_san_pham) ON DELETE CASCADE,
    FOREIGN KEY (ma_loai_tuy_chon) REFERENCES LoaiTuyChon(ma_loai_tuy_chon) ON DELETE CASCADE
);

-- Bảng GiaTriTuyChon - Các giá trị cụ thể cho từng loại tùy chọn
CREATE TABLE GiaTriTuyChon (
    ma_gia_tri BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_loai_tuy_chon BIGINT NOT NULL,
    ten_gia_tri VARCHAR(100) NOT NULL,
    gia_them DECIMAL(10, 2) DEFAULT 0.00,
    mo_ta VARCHAR(255),
    thu_tu_hien_thi INT DEFAULT 0,
    hoat_dong BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (ma_loai_tuy_chon) REFERENCES LoaiTuyChon(ma_loai_tuy_chon) ON DELETE CASCADE
);

-- Bảng Combo - Hoạt động như một sản phẩm (Tạo trước để tham chiếu)
CREATE TABLE Combo (
    ma_combo BIGINT AUTO_INCREMENT PRIMARY KEY,
    ten_combo VARCHAR(100) NOT NULL,
    mo_ta TEXT,
    hinh_anh VARCHAR(255),
    gia_ban DECIMAL(10, 2) NOT NULL, -- Giá bán combo (thay vì giá giảm)
    gia_goc DECIMAL(10, 2) NOT NULL, -- Tổng giá gốc các sản phẩm trong combo
    ngay_bat_dau DATE NOT NULL,
    ngay_ket_thuc DATE NOT NULL,
    so_luong_ban INT DEFAULT 0, -- Số lượng combo đã bán
    moi BOOLEAN DEFAULT FALSE, -- Combo mới
    noi_bat BOOLEAN DEFAULT FALSE, -- Combo nổi bật
    hoat_dong BOOLEAN DEFAULT TRUE,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    ngay_cap_nhat DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Bảng ChiTietCombo - Chi tiết các sản phẩm trong combo
CREATE TABLE ChiTietCombo (
    ma_chi_tiet_combo BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_combo BIGINT NOT NULL,
    ma_san_pham BIGINT NOT NULL,
    so_luong INT NOT NULL, -- Số lượng sản phẩm trong combo
    ten_san_pham VARCHAR(100) NOT NULL,
    gia_san_pham DECIMAL(10, 2) NOT NULL, -- Giá sản phẩm tại thời điểm tạo combo
    co_the_thay_the BOOLEAN DEFAULT FALSE, -- Có thể thay thế sản phẩm khác cùng loại không
    FOREIGN KEY (ma_combo) REFERENCES Combo(ma_combo) ON DELETE CASCADE,
    FOREIGN KEY (ma_san_pham) REFERENCES SanPham(ma_san_pham) ON DELETE CASCADE
);

-- Bảng GioHang
CREATE TABLE GioHang (
    ma_gio_hang BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng MatHangGioHang - Cải thiện để hỗ trợ combo
CREATE TABLE MatHangGioHang (
    ma_mat_hang_gio_hang BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_gio_hang BIGINT NOT NULL,
    ma_san_pham BIGINT, -- NULL nếu là combo
    ma_combo BIGINT, -- NULL nếu là sản phẩm đơn lẻ
    loai_mat_hang VARCHAR(20), CHECK (loai_mat_hang IN ('san_pham', 'combo')) NOT NULL,
    so_luong INT NOT NULL,
    gia_san_pham DECIMAL(10, 2) NOT NULL, -- Giá sản phẩm/combo tại thời điểm thêm vào giỏ
    ghi_chu TEXT, -- Ghi chú đặc biệt
    FOREIGN KEY (ma_gio_hang) REFERENCES GioHang(ma_gio_hang) ON DELETE CASCADE,
    FOREIGN KEY (ma_san_pham) REFERENCES SanPham(ma_san_pham) ON DELETE CASCADE,
    FOREIGN KEY (ma_combo) REFERENCES Combo(ma_combo) ON DELETE CASCADE,
    CHECK ((ma_san_pham IS NOT NULL AND ma_combo IS NULL AND loai_mat_hang = 'san_pham') OR (ma_san_pham IS NULL AND ma_combo IS NOT NULL AND loai_mat_hang = 'combo'))
);


CREATE TABLE ChiTietComboGioHang (
    ma_chi_tiet BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_mat_hang_gio_hang BIGINT NOT NULL,
    ma_chi_tiet_combo BIGINT NOT NULL, 
    FOREIGN KEY (ma_mat_hang_gio_hang) REFERENCES MatHangGioHang(ma_mat_hang_gio_hang) ON DELETE CASCADE,
    FOREIGN KEY (ma_chi_tiet_combo) REFERENCES ChiTietCombo(ma_chi_tiet_combo) ON DELETE CASCADE
);


CREATE TABLE TuyChonComboGioHang (
    ma_tuy_chon_combo_gio_hang BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_chi_tiet_combo_gio_hang BIGINT NOT NULL,
    ma_gia_tri BIGINT NOT NULL,
    gia_them DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (ma_chi_tiet_combo_gio_hang) REFERENCES ChiTietComboGioHang(ma_chi_tiet) ON DELETE CASCADE,
    FOREIGN KEY (ma_gia_tri) REFERENCES GiaTriTuyChon(ma_gia_tri) ON DELETE CASCADE
);

-- Bảng ChiTietTuyChonGioHang - Lưu các tùy chọn đã chọn cho từng mặt hàng trong giỏ
CREATE TABLE ChiTietTuyChonGioHang (
    ma_chi_tiet BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_mat_hang_gio_hang BIGINT NOT NULL,
    ma_gia_tri BIGINT NOT NULL,
    gia_them DECIMAL(10, 2) NOT NULL, -- Giá tăng thêm tại thời điểm chọn
    FOREIGN KEY (ma_mat_hang_gio_hang) REFERENCES MatHangGioHang(ma_mat_hang_gio_hang) ON DELETE CASCADE,
    FOREIGN KEY (ma_gia_tri) REFERENCES GiaTriTuyChon(ma_gia_tri) ON DELETE CASCADE
);

-- Bảng ThongTinCuaHang
CREATE TABLE ThongTinCuaHang (
    ma_cua_hang BIGINT AUTO_INCREMENT PRIMARY KEY,
    ten_cua_hang VARCHAR(100) NOT NULL,
    dia_chi VARCHAR(255) NOT NULL,
    so_dien_thoai VARCHAR(15),
    email VARCHAR(100),
    gio_mo TIME,
    gio_dong TIME,
    hoat_dong BOOLEAN DEFAULT TRUE,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bảng MaGiamGia
CREATE TABLE MaGiamGia (
    ma_giam_gia BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_code VARCHAR(50) UNIQUE NOT NULL,
    loai_giam_gia VARCHAR(50) NOT NULL CHECK (loai_giam_gia IN ('phan_tram', 'co_dinh')),
    gia_tri_giam DECIMAL(10, 2) NOT NULL,
    ngay_bat_dau DATE NOT NULL,
    ngay_ket_thuc DATE NOT NULL,
    gia_tri_don_hang_toi_thieu DECIMAL(15, 2),
    so_lan_su_dung_toi_da INT,
    da_su_dung INT DEFAULT 0,
    hoat_dong BOOLEAN DEFAULT TRUE,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bảng HinhAnhCombo - Hình ảnh cho combo
CREATE TABLE HinhAnhCombo (
    ma_hinh_anh_combo BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_combo BIGINT NOT NULL,
    url_hinh_anh VARCHAR(255) NOT NULL,
    thu_tu INT DEFAULT 0,
    FOREIGN KEY (ma_combo) REFERENCES Combo(ma_combo) ON DELETE CASCADE
);

-- Bảng TuyChonCombo - Tùy chọn cho từng sản phẩm trong combo
CREATE TABLE TuyChonCombo (
    ma_tuy_chon_combo BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_chi_tiet_combo BIGINT NOT NULL,
    ma_loai_tuy_chon BIGINT NOT NULL,
    FOREIGN KEY (ma_chi_tiet_combo) REFERENCES ChiTietCombo(ma_chi_tiet_combo) ON DELETE CASCADE,
    FOREIGN KEY (ma_loai_tuy_chon) REFERENCES LoaiTuyChon(ma_loai_tuy_chon) ON DELETE CASCADE
);

-- Bảng DonHang
CREATE TABLE DonHang (
    ma_don_hang BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT,
    ma_cua_hang BIGINT,
    tong_tien_san_pham DECIMAL(15, 2) NOT NULL, -- Tổng tiền sản phẩm
    phi_giao_hang DECIMAL(15, 2) DEFAULT 0.00, -- Phí giao hàng
    giam_gia_ma_giam_gia DECIMAL(15, 2) DEFAULT 0.00, -- Giảm giá từ mã
    giam_gia_combo DECIMAL(15, 2) DEFAULT 0.00, -- Giảm giá từ combo
    tong_tien_cuoi_cung DECIMAL(15, 2) NOT NULL, -- Tổng tiền cuối cùng
    trang_thai VARCHAR(50) NOT NULL CHECK (trang_thai IN ('da_nhan', 'da_xac_nhan', 'cho_xu_ly', 'dang_chuan_bi', 'dang_giao', 'hoan_thanh', 'da_huy')),
    dia_chi_giao_hang VARCHAR(255) NOT NULL,
    so_dien_thoai_giao_hang VARCHAR(15),
    phuong_thuc_thanh_toan VARCHAR(50) NOT NULL,
    trang_thai_thanh_toan VARCHAR(50) NOT NULL CHECK (trang_thai_thanh_toan IN ('cho_xu_ly', 'hoan_thanh', 'that_bai')),
    ma_giam_gia BIGINT,
    ma_nhan_vien_cua_hang BIGINT,
    ma_combo BIGINT,
    ghi_chu TEXT, -- Ghi chú của khách hàng
    thoi_gian_giao_du_kien DATETIME,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    ngay_cap_nhat DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE SET NULL,
    FOREIGN KEY (ma_cua_hang) REFERENCES ThongTinCuaHang(ma_cua_hang) ON DELETE SET NULL,
    FOREIGN KEY (ma_giam_gia) REFERENCES MaGiamGia(ma_giam_gia) ON DELETE SET NULL,
    FOREIGN KEY (ma_nhan_vien_cua_hang) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE NO ACTION,
    FOREIGN KEY (ma_combo) REFERENCES Combo(ma_combo) ON DELETE SET NULL
);

-- Bảng MatHangDonHang - Cải thiện để hỗ trợ combo
CREATE TABLE MatHangDonHang (
    ma_mat_hang_don_hang BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_don_hang BIGINT NOT NULL,
    ma_san_pham BIGINT, -- NULL nếu là combo
    ma_combo BIGINT, -- NULL nếu là sản phẩm đơn lẻ
    loai_mat_hang VARCHAR(20) CHECK (loai_mat_hang IN ('san_pham', 'combo')) NOT NULL,
    so_luong INT NOT NULL,
    don_gia_co_ban DECIMAL(10, 2) NOT NULL, -- Giá cơ bản của sản phẩm/combo
    tong_gia_tuy_chon DECIMAL(10, 2) DEFAULT 0.00, -- Tổng giá các tùy chọn
    thanh_tien DECIMAL(10, 2) NOT NULL, -- Thành tiền = (don_gia_co_ban + tong_gia_tuy_chon) * so_luong
    ghi_chu TEXT, -- Ghi chú riêng cho món này
    FOREIGN KEY (ma_don_hang) REFERENCES DonHang(ma_don_hang) ON DELETE CASCADE,
    FOREIGN KEY (ma_san_pham) REFERENCES SanPham(ma_san_pham) ON DELETE CASCADE,
    FOREIGN KEY (ma_combo) REFERENCES Combo(ma_combo) ON DELETE CASCADE,
    CHECK ((ma_san_pham IS NOT NULL AND ma_combo IS NULL AND loai_mat_hang = 'san_pham') OR 
           (ma_san_pham IS NULL AND ma_combo IS NOT NULL AND loai_mat_hang = 'combo'))
);

-- Bảng ChiTietComboDonHang - Chi tiết combo trong đơn hàng
CREATE TABLE ChiTietComboDonHang (
    ma_chi_tiet BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_mat_hang_don_hang BIGINT NOT NULL,
    ma_san_pham BIGINT NOT NULL,
    ten_san_pham VARCHAR(100) NOT NULL, -- Lưu tên để tránh mất dữ liệu
    so_luong INT NOT NULL,
    don_gia DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (ma_mat_hang_don_hang) REFERENCES MatHangDonHang(ma_mat_hang_don_hang) ON DELETE CASCADE,
    FOREIGN KEY (ma_san_pham) REFERENCES SanPham(ma_san_pham) ON DELETE CASCADE
);

-- Bảng TuyChonComboDonHang - Tùy chọn cho từng sản phẩm trong combo của đơn hàng
CREATE TABLE TuyChonComboDonHang (
    ma_tuy_chon_combo_don_hang BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_chi_tiet_combo_don_hang BIGINT NOT NULL,
    ma_gia_tri BIGINT NOT NULL,
    ten_loai_tuy_chon VARCHAR(50) NOT NULL,
    ten_gia_tri VARCHAR(100) NOT NULL,
    gia_them DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (ma_chi_tiet_combo_don_hang) REFERENCES ChiTietComboDonHang(ma_chi_tiet) ON DELETE CASCADE,
    FOREIGN KEY (ma_gia_tri) REFERENCES GiaTriTuyChon(ma_gia_tri) ON DELETE CASCADE
);

-- Bảng ChiTietTuyChonDonHang - Lưu các tùy chọn đã chọn cho từng mặt hàng trong đơn hàng
CREATE TABLE ChiTietTuyChonDonHang (
    ma_chi_tiet BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_mat_hang_don_hang BIGINT NOT NULL,
    ma_gia_tri BIGINT NOT NULL,
    ten_loai_tuy_chon VARCHAR(50) NOT NULL, -- Lưu tên để tránh mất dữ liệu khi xóa
    ten_gia_tri VARCHAR(100) NOT NULL, -- Lưu tên để tránh mất dữ liệu khi xóa
    gia_them DECIMAL(10, 2) NOT NULL, -- Giá tăng thêm tại thời điểm đặt hàng
    FOREIGN KEY (ma_mat_hang_don_hang) REFERENCES MatHangDonHang(ma_mat_hang_don_hang) ON DELETE CASCADE,
    FOREIGN KEY (ma_gia_tri) REFERENCES GiaTriTuyChon(ma_gia_tri) ON DELETE CASCADE
);

-- Bảng PhanCongDonHang
CREATE TABLE PhanCongDonHang (
    ma_phan_cong BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_don_hang BIGINT NOT NULL,
    ma_nguoi_giao_hang BIGINT NOT NULL,
    ngay_phan_cong DATETIME DEFAULT CURRENT_TIMESTAMP,
    trang_thai VARCHAR(50) NOT NULL CHECK (trang_thai IN ('da_phan_cong', 'da_chap_nhan', 'da_tu_choi', 'hoan_thanh')),
    FOREIGN KEY (ma_don_hang) REFERENCES DonHang(ma_don_hang) ON DELETE CASCADE,
    FOREIGN KEY (ma_nguoi_giao_hang) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng ChuyenDonHang
CREATE TABLE ChuyenDonHang (
    ma_chuyen_don_hang BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_don_hang BIGINT NOT NULL,
    ma_nguoi_chuyen BIGINT NOT NULL,
    ma_nguoi_nhan BIGINT NOT NULL,
    loai_chuyen VARCHAR(50) NOT NULL CHECK (loai_chuyen IN ('toi_bep', 'toi_giao_hang')),
    ngay_chuyen DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_don_hang) REFERENCES DonHang(ma_don_hang) ON DELETE CASCADE,
    FOREIGN KEY (ma_nguoi_chuyen) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE,
    FOREIGN KEY (ma_nguoi_nhan) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng DanhGia
CREATE TABLE DanhGia (
    ma_danh_gia BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    ma_san_pham BIGINT NOT NULL,
    ma_don_hang BIGINT NOT NULL,
    diem_so INT CHECK (diem_so >= 1 AND diem_so <= 5),
    binh_luan TEXT,
    hinh_anh_danh_gia TEXT, -- JSON array chứa các URL hình ảnh
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE,
    FOREIGN KEY (ma_san_pham) REFERENCES SanPham(ma_san_pham) ON DELETE CASCADE,
    FOREIGN KEY (ma_don_hang) REFERENCES DonHang(ma_don_hang) ON DELETE CASCADE
);

-- Bảng SanPhamYeuThich
CREATE TABLE SanPhamYeuThich (
    ma_yeu_thich BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    ma_san_pham BIGINT NOT NULL,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE,
    FOREIGN KEY (ma_san_pham) REFERENCES SanPham(ma_san_pham) ON DELETE CASCADE,
    UNIQUE(ma_nguoi_dung, ma_san_pham) -- Tránh trùng lặp
);

-- Bảng MaGiamGiaNguoiDung
CREATE TABLE MaGiamGiaNguoiDung (
    ma_giam_gia_nguoi_dung BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    ma_giam_gia BIGINT NOT NULL,
    so_lan_su_dung INT DEFAULT 0,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE,
    FOREIGN KEY (ma_giam_gia) REFERENCES MaGiamGia(ma_giam_gia) ON DELETE CASCADE
);

-- Bảng DiemThuong
CREATE TABLE DiemThuong (
    ma_diem_thuong BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    diem INT DEFAULT 0,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng TroChuyen
CREATE TABLE TroChuyen (
    ma_tro_chuyen BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    ma_nhan_vien_ho_tro BIGINT NOT NULL,
    noi_dung TEXT NOT NULL,
    nguoi_gui VARCHAR(20) CHECK (nguoi_gui IN ('khach_hang', 'nhan_vien')),
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE,
    FOREIGN KEY (ma_nhan_vien_ho_tro) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng ThongBao
CREATE TABLE ThongBao (
    ma_thong_bao BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    loai_thong_bao VARCHAR(50) NOT NULL CHECK (loai_thong_bao IN ('email', 'sms', 'push')),
    noi_dung TEXT NOT NULL,
    trang_thai VARCHAR(50) NOT NULL CHECK (trang_thai IN ('da_gui', 'cho_gui', 'that_bai')),
    da_doc BOOLEAN DEFAULT FALSE,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng LichLamViec
CREATE TABLE LichLamViec (
    ma_lich_lam_viec BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    thoi_gian_bat_dau DATETIME NOT NULL,
    thoi_gian_ket_thuc DATETIME NOT NULL,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);

-- Bảng Banner
CREATE TABLE Banner (
    ma_banner BIGINT AUTO_INCREMENT PRIMARY KEY,
    url_hinh_anh VARCHAR(255) NOT NULL,
    ma_san_pham BIGINT,
    tieu_de VARCHAR(200),
    mo_ta VARCHAR(500),
    link_chuyen_huong VARCHAR(255),
    ngay_bat_dau DATE NOT NULL,
    ngay_ket_thuc DATE NOT NULL,
    thu_tu_hien_thi INT DEFAULT 0,
    hoat_dong BOOLEAN DEFAULT TRUE,
    ngay_tao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- SỬA: Thêm DEFAULT
    FOREIGN KEY (ma_san_pham) REFERENCES SanPham(ma_san_pham) ON DELETE SET NULL
);

-- : Bảng OTP -
CREATE TABLE OTP(
    ma_otp BIGINT AUTO_INCREMENT PRIMARY KEY,
    ma_nguoi_dung BIGINT NOT NULL,
    otp_code VARCHAR(10) NOT NULL,  -- SỬA: NVARCHAR -> VARCHAR
    loai_otp VARCHAR(50) NOT NULL CHECK (loai_otp IN ('reset_password', 'verify_email', 'verify_phone')),  -- SỬA: NVARCHAR -> VARCHAR
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,  -- SỬA: GETDATE() -> CURRENT_TIMESTAMP
    het_han DATETIME NOT NULL,
    da_su_dung BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung) ON DELETE CASCADE
);