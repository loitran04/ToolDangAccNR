import os
import sys
import json
import threading
import asyncio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from playwright.async_api import async_playwright

# --- TỰ ĐỘNG CHUYỂN WORKING DIRECTORY VỀ THƯ MỤC CHỨA FILE SCRIPT ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

CONFIG_FILE = "config.json"
DEFAULT_ACC_FILE = "accs.txt"

CATEGORIES = [
    "Nick NRO Vip",
    "Nick NRO giá rẻ",
    "Nick Buff Đậu",
    "Nick sơ sinh có đệ"
]
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

def normalize_hanhtinh(ht_str):
    """Chuẩn hóa tên Hành tinh từ viết tắt sang chữ hiển thị trên Web"""
    val = ht_str.strip().lower()
    if val in ["nm", "namek"]:
        return "Namek"
    elif val in ["td", "trai dat", "trái đất", "traidat"]:
        return "Trái đất"
    elif val in ["xd", "xayda", "xay da"]:
        return "Xayda"
    return ht_str.strip().capitalize()

def normalize_server(sv_str):
    """Chuẩn hóa Server nếu trong file txt chỉ ghi số"""
    val = sv_str.strip().lower()
    if val.isdigit():
        return f"{val} sao"
    return sv_str.strip()

def find_account_image(images_dir, account):
    if not account or account in {".", ".."} or os.path.basename(account) != account:
        return None

    for extension in IMAGE_EXTENSIONS:
        image_path = os.path.join(images_dir, f"{account}{extension}")
        if os.path.isfile(image_path):
            return image_path
    return None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tool Auto Post Account - ShopAcc Admin")
        self.geometry("920x980")
        self.resizable(True, True)

        self.configure(bg="#F4F6F9")
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        
        self.style.configure("TFrame", background="#F4F6F9")
        self.style.configure("TLabel", background="#F4F6F9", font=("Segoe UI", 10))
        
        self.style.configure("Blue.TButton", font=("Segoe UI", 10, "bold"), background="#2980B9", foreground="white", padding=8)
        self.style.map("Blue.TButton", background=[("active", "#1F6391")])

        self.style.configure("Red.TButton", font=("Segoe UI", 9, "bold"), background="#C0392B", foreground="white", padding=6)
        self.style.map("Red.TButton", background=[("active", "#962D22")])
        
        self.acc_items = {}
        self.category_vars = {}
        
        self._build_ui()
        self._load_saved_config()

    def _build_ui(self):
        header = tk.Frame(self, bg="#4A90E2", height=50)
        header.pack(fill="x")
        title_lbl = tk.Label(
            header, 
            text="HỆ THỐNG TỰ ĐỘNG ĐĂNG ACCOUNT - SHOPACC ADMIN", 
            font=("Segoe UI", 13, "bold"), 
            fg="white", 
            bg="#4A90E2"
        )
        title_lbl.pack(pady=12)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # 1. Khung Admin Web
        login_frame = tk.LabelFrame(main_frame, text=" Thông tin tài khoản Admin Web ", font=("Segoe UI", 10, "bold"), bg="#F4F6F9", fg="#333333")
        login_frame.pack(fill="x", pady=(0, 10), ipadx=5, ipady=5)

        tk.Label(login_frame, text="Tên đăng nhập:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.txt_admin_user = ttk.Entry(login_frame, width=30)
        self.txt_admin_user.grid(row=0, column=1, padx=5, pady=3, sticky="w")

        tk.Label(login_frame, text="Mật khẩu:").grid(row=0, column=2, sticky="w", padx=(15, 5), pady=3)
        self.txt_admin_pass = ttk.Entry(login_frame, width=30, show="*")
        self.txt_admin_pass.grid(row=0, column=3, padx=5, pady=3, sticky="w")

        # 2. Khung Nguồn File & Cấu hình Đăng Bài
        config_frame = tk.LabelFrame(main_frame, text=" Cấu hình dữ liệu đăng bài ", font=("Segoe UI", 10, "bold"), bg="#F4F6F9", fg="#333333")
        config_frame.pack(fill="x", pady=(0, 10), ipadx=5, ipady=5)

        # Tiêu đề mẫu
        tk.Label(config_frame, text="Tiêu đề bài viết:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.txt_title_template = ttk.Entry(config_frame, width=60)
        self.txt_title_template.grid(row=0, column=1, padx=5, pady=3)
        tk.Label(config_frame, text="(Để trống = tự tạo tiêu đề)").grid(row=0, column=2, sticky="w", padx=3)

        # Setting Giá Bán
        tk.Label(config_frame, text="Giá bán (VNĐ):").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.txt_price = ttk.Entry(config_frame, width=20)
        self.txt_price.insert(0, "15000")
        self.txt_price.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        tk.Label(config_frame, text="(Giá mặc định đăng bài lên QLTK)").grid(row=1, column=2, sticky="w", padx=3)

        # Delay giữa các bước
        tk.Label(config_frame, text="Delay (giây/bước):").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.txt_delay = ttk.Entry(config_frame, width=20)
        self.txt_delay.insert(0, "1.5")
        self.txt_delay.grid(row=2, column=1, sticky="w", padx=5, pady=3)
        tk.Label(config_frame, text="(Tăng thời gian để quan sát kỹ hơn)").grid(row=2, column=2, sticky="w", padx=3)

        # Danh mục Checkbox (Chọn nhiều)
        tk.Label(config_frame, text="Danh mục (tick chọn):").grid(row=3, column=0, sticky="nw", padx=5, pady=3)
        
        cat_box = tk.Frame(config_frame, bg="#FFFFFF", relief="solid", bd=1)
        cat_box.grid(row=3, column=1, padx=5, pady=3, sticky="w")
        
        for cat in CATEGORIES:
            var = tk.BooleanVar(value=(cat == "Nick NRO giá rẻ"))
            chk = tk.Checkbutton(
                cat_box, 
                text=cat, 
                variable=var, 
                bg="#FFFFFF", 
                activebackground="#FFFFFF", 
                anchor="w"
            )
            chk.pack(anchor="w", padx=8, pady=2)
            self.category_vars[cat] = var

        # Mô tả
        tk.Label(config_frame, text="Mô tả bài viết:").grid(row=4, column=0, sticky="nw", padx=5, pady=3)
        self.txt_description = tk.Text(config_frame, width=60, height=3, font=("Segoe UI", 9))
        self.txt_description.grid(row=4, column=1, padx=5, pady=3)

        # Chọn thư mục ảnh theo tài khoản
        tk.Label(config_frame, text="Thư mục ảnh theo acc:").grid(row=5, column=0, sticky="w", padx=5, pady=3)
        self.txt_img_dir = ttk.Entry(config_frame, width=60)
        self.txt_img_dir.grid(row=5, column=1, padx=5, pady=3)
        ttk.Button(config_frame, text="Chọn thư mục", command=self._browse_image_folder).grid(row=5, column=2, padx=3, pady=3)

        # Chọn file accs
        tk.Label(config_frame, text="File data (accs.txt):").grid(row=6, column=0, sticky="w", padx=5, pady=3)
        self.txt_acc_path = ttk.Entry(config_frame, width=60)
        self.txt_acc_path.grid(row=6, column=1, padx=5, pady=3)
        ttk.Button(config_frame, text="Nạp file", command=self._load_acc_file).grid(row=6, column=2, padx=3, pady=3)

        # 3. Nút bấm Chức năng
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=5)

        self.btn_post = ttk.Button(
            btn_frame, 
            text="🚀 BẮT ĐẦU TỰ ĐỘNG ĐĂNG ACC", 
            style="Blue.TButton",
            command=self._start_auto_post_thread
        )
        self.btn_post.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_reset_all = ttk.Button(
            btn_frame, 
            text="🔄 Reset Toàn Bộ Data", 
            style="Red.TButton",
            command=self._reset_all_data
        )
        self.btn_reset_all.pack(side="right", fill="x")

        # 4. Treeview Danh sách Acc
        table_frame = tk.LabelFrame(main_frame, text=" Bảng Quản Lý Tiến Trình Account ", font=("Segoe UI", 10, "bold"), bg="#F4F6F9", fg="#333333")
        table_frame.pack(fill="both", expand=True, pady=(5, 5))

        columns = ("stt", "tk", "sv", "ht", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=6)
        
        self.tree.heading("stt", text="STT")
        self.tree.heading("tk", text="Tài khoản Game")
        self.tree.heading("sv", text="Server")
        self.tree.heading("ht", text="Hành tinh")
        self.tree.heading("status", text="Bước / Trạng thái hiện tại")

        self.tree.column("stt", width=45, anchor="center")
        self.tree.column("tk", width=180, anchor="w")
        self.tree.column("sv", width=80, anchor="center")
        self.tree.column("ht", width=90, anchor="center")
        self.tree.column("status", width=400, anchor="w")

        tree_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        tree_scroll.pack(side="right", fill="y", pady=5)

        # 5. Log Chi tiết
        log_frame = tk.LabelFrame(main_frame, text=" Bảng Log Chi Tiết Hệ Thống ", font=("Segoe UI", 10, "bold"), bg="#F4F6F9", fg="#333333")
        log_frame.pack(fill="both", expand=True, pady=(5, 0))

        self.log_text = tk.Text(log_frame, wrap="word", height=8, font=("Consolas", 9), bg="#1E1E1E", fg="#D4D4D4")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        log_scroll.pack(side="right", fill="y", pady=5)

    def _save_config(self, key, value):
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        
        config[key] = value
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def _load_saved_config(self):
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                self.log(f"[Cảnh báo] Không thể đọc file config: {e}")

        if "admin_user" in config:
            self.txt_admin_user.insert(0, config["admin_user"])
        if "admin_pass" in config:
            self.txt_admin_pass.insert(0, config["admin_pass"])
        if "title_template" in config:
            self.txt_title_template.insert(0, config["title_template"])
        if "price" in config:
            self.txt_price.delete(0, tk.END)
            self.txt_price.insert(0, str(config["price"]))
        if "delay_step" in config:
            self.txt_delay.delete(0, tk.END)
            self.txt_delay.insert(0, str(config["delay_step"]))
        if "selected_categories" in config:
            saved_cats = config["selected_categories"]
            for cat, var in self.category_vars.items():
                var.set(cat in saved_cats)
        if "description" in config:
            self.txt_description.insert("1.0", config["description"])

        img_dir = config.get("img_dir", "")
        if img_dir and os.path.isdir(img_dir):
            self.txt_img_dir.delete(0, tk.END)
            self.txt_img_dir.insert(0, img_dir)

        acc_path = config.get("acc_path", "")
        if acc_path and os.path.exists(acc_path):
            self.txt_acc_path.delete(0, tk.END)
            self.txt_acc_path.insert(0, acc_path)
            self._update_table_from_file(acc_path)
        elif os.path.exists(DEFAULT_ACC_FILE):
            self.txt_acc_path.delete(0, tk.END)
            self.txt_acc_path.insert(0, DEFAULT_ACC_FILE)
            self._update_table_from_file(DEFAULT_ACC_FILE)
            self._save_config("acc_path", DEFAULT_ACC_FILE)

    def _clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.acc_items.clear()

    def _reset_all_data(self):
        if messagebox.askyesno("Xác nhận Reset", "Xóa toàn bộ Cấu hình & Data?"):
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)

            self.txt_admin_user.delete(0, tk.END)
            self.txt_admin_pass.delete(0, tk.END)
            self.txt_title_template.delete(0, tk.END)
            self.txt_price.delete(0, tk.END)
            self.txt_price.insert(0, "15000")
            self.txt_delay.delete(0, tk.END)
            self.txt_delay.insert(0, "1.5")
            for cat, var in self.category_vars.items():
                var.set(cat == "Nick NRO giá rẻ")
            self.txt_description.delete("1.0", tk.END)
            self.txt_img_dir.delete(0, tk.END)
            self.txt_acc_path.delete(0, tk.END)

            self._clear_table()
            self.log_text.delete("1.0", tk.END)
            self.log("--> Đã xóa toàn bộ Data thành công!")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def update_status(self, tk_acc, status_text):
        if tk_acc in self.acc_items:
            item_id = self.acc_items[tk_acc]
            self.tree.set(item_id, column="status", value=status_text)

    def _browse_image_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa ảnh theo tên tài khoản")
        if folder:
            self.txt_img_dir.delete(0, tk.END)
            self.txt_img_dir.insert(0, folder)
            self._save_config("img_dir", folder)

    def _load_acc_file(self):
        filename = filedialog.askopenfilename(
            title="Chọn file txt chứa danh sách acc",
            filetypes=[("Text Files", "*.txt")]
        )
        if filename:
            self.txt_acc_path.delete(0, tk.END)
            self.txt_acc_path.insert(0, filename)
            self._save_config("acc_path", filename)
            self._update_table_from_file(filename)

    def _update_table_from_file(self, file_path):
        self._clear_table()
        if not os.path.exists(file_path):
            return

        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        for idx, line in enumerate(lines, start=1):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                tk_acc, mk, raw_sv, raw_ht = parts[:4]
                sv_display = normalize_server(raw_sv)
                ht_display = normalize_hanhtinh(raw_ht)
                item_id = self.tree.insert("", "end", values=(idx, tk_acc, sv_display, ht_display, "Chờ xử lý..."))
                self.acc_items[tk_acc] = item_id

    def _start_auto_post_thread(self):
        admin_user = self.txt_admin_user.get().strip()
        admin_pass = self.txt_admin_pass.get().strip()
        custom_title = self.txt_title_template.get().strip()
        price_val = self.txt_price.get().strip()
        
        try:
            delay_step = float(self.txt_delay.get().strip())
        except ValueError:
            delay_step = 1.5
            
        selected_categories = [cat for cat, var in self.category_vars.items() if var.get()]
        
        custom_desc = self.txt_description.get("1.0", tk.END).strip()
        img_dir = self.txt_img_dir.get().strip()
        acc_path = self.txt_acc_path.get().strip()

        if not admin_user or not admin_pass:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Tên đăng nhập và Mật khẩu Admin Web!")
            return

        if not price_val:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Giá bán!")
            return

        if not selected_categories:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất 1 Danh mục!")
            return

        if not img_dir or not os.path.isdir(img_dir):
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn thư mục ảnh hợp lệ!")
            return

        if not acc_path or not os.path.exists(acc_path):
            messagebox.showwarning("Cảnh báo", "Không tìm thấy file danh sách account!")
            return

        with open(acc_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        missing_images = []
        for line in lines:
            parts = [part.strip() for part in line.split("|")]
            if len(parts) >= 4 and not find_account_image(img_dir, parts[0]):
                missing_images.append(parts[0])

        if missing_images:
            missing_list = "\n".join(missing_images[:10])
            if len(missing_images) > 10:
                missing_list += f"\n... và {len(missing_images) - 10} tài khoản khác"
            messagebox.showerror(
                "Thiếu ảnh tài khoản",
                f"Không tìm thấy ảnh trùng tên cho {len(missing_images)} tài khoản:\n{missing_list}\n\n"
                "Đặt ảnh trong thư mục đã chọn với tên dạng <tên_acc>.jpg, .jpeg, .png hoặc .webp."
            )
            return

        self._save_config("img_dir", img_dir)
        self._save_config("admin_user", admin_user)
        self._save_config("admin_pass", admin_pass)
        self._save_config("title_template", custom_title)
        self._save_config("price", price_val)
        self._save_config("delay_step", delay_step)
        self._save_config("selected_categories", selected_categories)
        self._save_config("description", custom_desc)

        threading.Thread(
            target=self._run_async_task, 
            args=(self._auto_post_logic, admin_user, admin_pass, custom_title, price_val, delay_step, selected_categories, custom_desc, img_dir, acc_path), 
            daemon=True
        ).start()

    def _run_async_task(self, async_func, *args):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_func(*args))
        loop.close()

    async def _auto_post_logic(self, admin_user, admin_pass, custom_title, price_val, delay_step, selected_categories, custom_desc, img_dir, acc_path):
        self.btn_post.config(state="disabled")
        self.log("\n================ BẮT ĐẦU ĐĂNG ACC ================")

        delay_ms = int(delay_step * 1000)

        with open(acc_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--start-maximized"]
            )
            context = await browser.new_context(no_viewport=True)
            page = await context.new_page()

            # --- 1. ĐĂNG NHẬP ADMIN ---
            self.log("--> 🔑 Đang đăng nhập tài khoản Admin...")
            try:
                await page.goto("https://shopaccadmin.ngocrong.net/login")
                await page.wait_for_load_state("networkidle")

                await page.locator('input#username').fill(admin_user)
                await page.locator('input#password').fill(admin_pass)
                await page.locator('button:has-text("Đăng nhập")').click()
                
                await page.wait_for_url("**/ctv/listings**", timeout=15000)
                self.log("--> ✅ Đăng nhập Admin thành công!")
                await page.wait_for_timeout(delay_ms)
            except Exception as e:
                self.log(f"--> ❌ Đăng nhập thất bại: Kiểm tra lại tài khoản Admin! ({e})")
                messagebox.showerror("Lỗi đăng nhập", "Không thể đăng nhập vào web Admin.")
                await browser.close()
                self.btn_post.config(state="normal")
                return

            # --- 2. VÒNG LẶP ĐĂNG BÀI ---
            for idx, line in enumerate(lines):
                parts = [item.strip() for item in line.split("|")]
                if len(parts) < 4:
                    continue

                tk_acc, mk, raw_sv, raw_ht = parts[:4]
                sv = normalize_server(raw_sv)
                ht = normalize_hanhtinh(raw_ht)

                try:
                    account_img_path = find_account_image(img_dir, tk_acc)
                    if not account_img_path:
                        raise FileNotFoundError(f"Không tìm thấy ảnh cho tài khoản {tk_acc}")

                    if idx > 0:
                        self.log(f"--> 🔄 Làm mới trang chuẩn bị đăng acc tiếp theo: {tk_acc}")
                        await page.goto("https://shopaccadmin.ngocrong.net/ctv/listings")
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(delay_ms)

                    self.update_status(tk_acc, "🔄 1. Bấm 'Đăng account mới'...")
                    btn_new = page.locator('button:has-text("Đăng account mới")')
                    await btn_new.wait_for(state="visible", timeout=12000)
                    await btn_new.click()
                    await page.wait_for_timeout(delay_ms)
                    
                    await page.wait_for_selector('div.cdk-overlay-container')
                    dialog = page.locator('div.cdk-overlay-container').last

                    self.update_status(tk_acc, "🔄 2. Điền Tiêu đề, Giá, Mô tả & Form...")
                    title = custom_title if custom_title else f"Acc {ht} server {sv}"
                    
                    await dialog.locator('mat-form-field:has-text("Tiêu đề") input').first.fill(title)
                    await page.wait_for_timeout(300)
                    
                    if custom_desc:
                        desc_field = dialog.locator('mat-form-field:has-text("Mô tả") textarea').first
                        if await desc_field.count() > 0:
                            await desc_field.fill(custom_desc)
                            await page.wait_for_timeout(300)

                    # Điền Giá Bán cài đặt từ UI
                    await dialog.locator('mat-form-field:has-text("Giá bán") input').first.fill(price_val)
                    await dialog.locator('mat-form-field:has-text("Bảo hành") input').first.fill("24")
                    await dialog.locator('mat-form-field:has-text("Tài khoản game") input').first.fill(tk_acc)
                    await dialog.locator('mat-form-field:has-text("Mật khẩu game") input').first.fill(mk)
                    await page.wait_for_timeout(delay_ms)

                    self.update_status(tk_acc, f"🔄 3. Chọn Dropdown & Danh mục...")
                    await self._select_mat_option(page, "Server", sv, delay_ms)
                    await self._select_mat_option(page, "Hành tinh", ht, delay_ms)
                    await self._select_mat_option(page, "Dạng đăng ký", "Đăng ký ảo", delay_ms)
                    
                    for cat in selected_categories:
                        await self._select_mat_option(page, "Danh mục", cat, delay_ms)
                    
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(delay_ms)

                    self.update_status(tk_acc, "🔄 4. Upload ảnh...")
                    file_input = dialog.locator('input[type="file"]').first
                    await file_input.set_input_files([account_img_path])
                    await page.wait_for_timeout(delay_ms)

                    self.update_status(tk_acc, "🔄 5. Lưu bản nháp...")
                    btn_save = dialog.locator('button:has-text("Lưu bản nháp và ảnh")').first
                    await btn_save.click()
                    await page.wait_for_timeout(2000 + delay_ms)

                    btn_close = dialog.locator('button:has-text("Đóng")')
                    try:
                        if await btn_close.is_visible(timeout=2000):
                            await btn_close.click(timeout=3000)
                            await page.wait_for_timeout(delay_ms)
                    except Exception:
                        pass

                    self.update_status(tk_acc, "🔄 6. Bấm 'Đăng bán'...")
                    row = page.locator(f'tr:has-text("{tk_acc}")').first
                    if await row.count() > 0:
                        await row.scroll_into_view_if_needed()
                        btn_post_sell = row.locator('button:has-text("Đăng bán")')
                    else:
                        btn_post_sell = page.locator('tr').nth(1).locator('button:has-text("Đăng bán")')
                        await btn_post_sell.scroll_into_view_if_needed()
                    
                    await btn_post_sell.click()
                    await page.wait_for_timeout(delay_ms)

                    self.update_status(tk_acc, "✅ HOÀN THÀNH (Đã đăng bán)")
                    self.log(f"[Thành công] Đã đăng bài cho {tk_acc}")

                except Exception as e:
                    self.update_status(tk_acc, f"❌ Lỗi: {str(e)[:35]}...")
                    self.log(f"[Lỗi] {tk_acc}: {e}")

            await page.wait_for_timeout(1000)
            await browser.close()

        self.log("\n================ HOÀN THÀNH ================")
        self.btn_post.config(state="normal")

    async def _select_mat_option(self, page, label_name, option_text, delay_ms=1000):
        """Hàm chọn Dropdown chuẩn xác trong Dialog kèm delay"""
        dialog = page.locator('div.cdk-overlay-container, mat-dialog-container').last
        
        field = dialog.locator(f'mat-form-field:has-text("{label_name}")').first
        await field.click()
        await page.wait_for_timeout(300)
        
        option = page.locator(f'mat-option:has-text("{option_text}")').or_(
            page.locator(f'span.mat-option-text:has-text("{option_text}")')
        )
        if await option.count() > 0:
            await option.first.click()
        else:
            checkbox = page.locator(f'span:has-text("{option_text}")')
            if await checkbox.count() > 0:
                await checkbox.first.click()
        await page.wait_for_timeout(300)

if __name__ == "__main__":
    app = App()
    app.mainloop()