import tkinter as tk
from tkinter import messagebox, ttk
import qrcode
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import random
import os
import cv2
from pyzbar import pyzbar
import pandas as pd
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import sqlite3

# إنشاء مجلدات لتخزين الملفات
if not os.path.exists("students"):
    os.makedirs("students")
if not os.path.exists("reports"):
    os.makedirs("reports")

# إنشاء قاعدة البيانات
DATABASE_FILE = "attendance.db"

def create_database():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            time TEXT NOT NULL,
            days TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            group_name TEXT NOT NULL,
            attendance TEXT,
            evaluation TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_database()

class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font('DejaVu', '', r"C:\Users\XPS\Downloads\Amiri\DejaVuSans.ttf")
        self.add_font('Amiri', '', r"C:\Users\XPS\Downloads\Amiri\Amiri-Regular.ttf")

    def header(self):
        self.set_font('DejaVu', '', 16)
        self.cell(0, 10, "تقرير الحضور", 0, 1, 'C')

class Student:
    def __init__(self, name, phone, group):
        self.id = random.randint(10000, 99999)  # توليد ID عشوائي من 5 أرقام
        self.name = name
        self.phone = phone
        self.group = group
        self.attendance = []  # قائمة لتسجيل الحضور
        self.evaluation = {}  # قاموس لتسجيل التقييمات

    def generate_qr_code(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(str(self.id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(f"students/{self.name}_QR.png")
        messagebox.showinfo("QR Code", f"تم إنشاء QR Code للطالب {self.name} وحفظه في مجلد students.")

class Group:
    def __init__(self, name, time, days):
        self.name = name
        self.time = time
        self.days = days
        self.students = []  # قائمة الطلاب في المجموعة

    def add_student(self, student):
        self.students.append(student)
        messagebox.showinfo("إضافة طالب", f"تمت إضافة الطالب {student.name} إلى المجموعة {self.name}")

    def remove_student(self, student_id):
        for student in self.students:
            if student.id == student_id:
                self.students.remove(student)
                messagebox.showinfo("حذف طالب", f"تم حذف الطالب {student.name} من المجموعة {self.name}")
                return
        messagebox.showerror("خطأ", "الطالب غير موجود في هذه المجموعة.")

class AttendanceSystem:
    def __init__(self):
        self.groups = []
        self.students = []
        self.load_data()

    def load_data(self):
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM groups")
        groups = cursor.fetchall()
        for group in groups:
            self.groups.append(Group(group[1], group[2], group[3]))

        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        for student in students:
            new_student = Student(student[1], student[2], student[3])
            new_student.attendance = student[4].split(',') if student[4] else []
            new_student.evaluation = eval(student[5]) if student[5] else {}
            self.students.append(new_student)
        conn.close()

    def save_data(self):
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM groups")
        cursor.execute("DELETE FROM students")
        for group in self.groups:
            cursor.execute("INSERT INTO groups (name, time, days) VALUES (?, ?, ?)", (group.name, group.time, group.days))
        for student in self.students:
            cursor.execute("INSERT INTO students (name, phone, group_name, attendance, evaluation) VALUES (?, ?, ?, ?, ?)",
                           (student.name, student.phone, student.group, ','.join(student.attendance), str(student.evaluation)))
        conn.commit()
        conn.close()

    def add_group(self, name, time, days):
        if any(group.name == name for group in self.groups):
            messagebox.showerror("خطأ", "هذه المجموعة موجودة بالفعل!")
            return
        new_group = Group(name, time, days)
        self.groups.append(new_group)
        self.save_data()
        messagebox.showinfo("نجاح", f"تمت إضافة المجموعة: {name}")

    def add_student(self, name, phone, group_name):
        group = next((g for g in self.groups if g.name == group_name), None)
        if not group:
            messagebox.showerror("خطأ", "المجموعة غير موجودة!")
            return
        new_student = Student(name, phone, group_name)
        self.students.append(new_student)
        group.add_student(new_student)
        new_student.generate_qr_code()
        self.save_data()
        messagebox.showinfo("نجاح", f"تمت إضافة الطالب: {name} (ID: {new_student.id})")

    def delete_student(self, student_id):
        student = next((s for s in self.students if s.id == student_id), None)
        if not student:
            messagebox.showerror("خطأ", "الطالب غير موجود!")
            return
        self.students.remove(student)
        self.save_data()
        messagebox.showinfo("نجاح", f"تم حذف الطالب: {student.name}")

    def delete_group(self, group_name):
        group = next((g for g in self.groups if g.name == group_name), None)
        if not group:
            messagebox.showerror("خطأ", "المجموعة غير موجودة!")
            return
        self.groups.remove(group)
        self.save_data()
        messagebox.showinfo("نجاح", f"تم حذف المجموعة: {group_name}")

    def edit_student(self, student_id, new_name, new_phone, new_group):
        student = next((s for s in self.students if s.id == student_id), None)
        if not student:
            messagebox.showerror("خطأ", "الطالب غير موجود!")
            return
        student.name = new_name
        student.phone = new_phone
        student.group = new_group
        self.save_data()
        messagebox.showinfo("نجاح", f"تم تعديل بيانات الطالب: {student.name}")

    def edit_group(self, group_name, new_name, new_time, new_days):
        group = next((g for g in self.groups if g.name == group_name), None)
        if not group:
            messagebox.showerror("خطأ", "المجموعة غير موجودة!")
            return
        group.name = new_name
        group.time = new_time
        group.days = new_days
        self.save_data()
        messagebox.showinfo("نجاح", f"تم تعديل بيانات المجموعة: {group.name}")

    def record_attendance(self, student_id):
        student = next((s for s in self.students if s.id == student_id), None)
        if not student:
            messagebox.showerror("خطأ", "الطالب غير موجود!")
            return
        
        today = datetime.now().strftime("%Y-%m-%d")  # التاريخ الحالي
        group = next((g for g in self.groups if g.name == student.group), None)
        if not group:
            messagebox.showerror("خطأ", "المجموعة غير موجودة!")
            return
        
        # تحويل أيام المجموعة إلى قائمة
        group_days = group.days.split(',')
        
        # الحصول على اليوم الحالي كاسم يوم (مثل: "Saturday")
        today_name = datetime.now().strftime("%A")
        
        # تحويل اليوم الحالي إلى الاسم العربي
        days_mapping = {
            "Saturday": "السبت",
            "Sunday": "الأحد",
            "Monday": "الاثنين",
            "Tuesday": "الثلاثاء",
            "Wednesday": "الأربعاء",
            "Thursday": "الخميس",
            "Friday": "الجمعة"
        }
        today_name_arabic = days_mapping.get(today_name, today_name)
        
        # التحقق من أن اليوم الحالي موجود في أيام المجموعة
        if today_name_arabic not in group_days:
            messagebox.showerror("خطأ", f"اليوم ({today_name_arabic}) ليس من أيام المجموعة!")
            return
        
        # التحقق من أن الطالب لم يسجل حضوره مسبقًا اليوم
        if today in student.attendance:
            messagebox.showinfo("تنبيه", "تم تسجيل حضور هذا الطالب مسبقًا اليوم!")
            return
        
        # تسجيل الحضور
        student.attendance.append(today)
        self.save_data()
        messagebox.showinfo("نجاح", f"تم تسجيل حضور الطالب {student.name} بتاريخ {today}")

    def evaluate_student(self, student_id, stars, notes):
        student = next((s for s in self.students if s.id == student_id), None)
        if not student:
            messagebox.showerror("خطأ", "الطالب غير موجود!")
            return
        today = datetime.now().strftime("%Y-%m-%d")
        student.evaluation[today] = {"stars": stars, "notes": notes}
        self.save_data()
        messagebox.showinfo("نجاح", f"تم تقييم الطالب {student.name} بنجاح!")

    def generate_monthly_report(self, student_id, start_date, end_date):
        student = next((s for s in self.students if s.id == student_id), None)
        if not student:
            messagebox.showerror("خطأ", "الطالب غير موجود!")
            return

        # الحصول على أيام المجموعة
        group = next((g for g in self.groups if g.name == student.group), None)
        if not group:
            messagebox.showerror("خطأ", "المجموعة غير موجودة!")
            return

        group_days = group.days.split(',')  # أيام المجموعة (مثل ["السبت", "الأحد"])

        # إنشاء تقرير الحضور والغياب
        data = {"التاريخ": [], "اليوم": [], "الحضور": [], "التقييم": [], "الملاحظات": []}
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        current_date = start

        # تحويل الأيام الإنجليزية إلى عربية
        days_mapping = {
            "Saturday": "السبت",
            "Sunday": "الأحد",
            "Monday": "الاثنين",
            "Tuesday": "الثلاثاء",
            "Wednesday": "الأربعاء",
            "Thursday": "الخميس",
            "Friday": "الجمعة"
        }

        while current_date <= end:
            date_str = current_date.strftime("%Y-%m-%d")
            day_name = current_date.strftime("%A")  # الحصول على اسم اليوم بالإنجليزية
            day_name_arabic = days_mapping.get(day_name, day_name)  # تحويل اليوم إلى العربية

            # التحقق من أن اليوم هو أحد أيام المجموعة
            if day_name_arabic in group_days:
                data["التاريخ"].append(date_str)
                data["اليوم"].append(day_name_arabic)

                if date_str in student.attendance:
                    data["الحضور"].append("حاضر")
                    if date_str in student.evaluation:
                        data["التقييم"].append(student.evaluation[date_str]["stars"])
                        data["الملاحظات"].append(student.evaluation[date_str]["notes"])
                    else:
                        data["التقييم"].append("بدون تقييم")
                        data["الملاحظات"].append("بدون ملاحظات")
                else:
                    data["الحضور"].append("غائب")
                    data["التقييم"].append("بدون تقييم")
                    data["الملاحظات"].append("بدون ملاحظات")

            current_date += timedelta(days=1)

        # إضافة نسب الحضور والغياب
        total_days = len(data["التاريخ"])
        present_days = data["الحضور"].count("حاضر")
        absent_days = total_days - present_days
        attendance_percentage = (present_days / total_days) * 100 if total_days > 0 else 0
        absence_percentage = 100 - attendance_percentage if total_days > 0 else 0

        # إنشاء DataFrame
        df = pd.DataFrame(data)

        # حفظ التقرير كملف Excel
        with pd.ExcelWriter(f"reports/{student.name}_report.xlsx", engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='تقرير الحضور')
            workbook = writer.book
            worksheet = writer.sheets['تقرير الحضور']

            # تنسيق الخلايا
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#4CAF50',
                'border': 1,
                'font_color': 'white'
            })

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # تنسيق الخلايا بناءً على الحضور
            cell_format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
            cell_format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})

            for row_num in range(1, len(df) + 1):
                if df.iloc[row_num - 1]['الحضور'] == 'حاضر':
                    worksheet.set_row(row_num, None, cell_format_green)
                else:
                    worksheet.set_row(row_num, None, cell_format_red)

            # إضافة النسب إلى التقرير
            worksheet.write(len(df) + 2, 0, f"تقرير الحضور للطالب {student.name} (ID: {student.id})")
            worksheet.write(len(df) + 3, 0, f"نسبة الحضور: {attendance_percentage:.2f}%")
            worksheet.write(len(df) + 4, 0, f"نسبة الغياب: {absence_percentage:.2f}%")
            worksheet.write(len(df) + 5, 0, f"حضر: {present_days} مرة")
            worksheet.write(len(df) + 6, 0, f"غاب: {absent_days} مرة")

        messagebox.showinfo("تصدير Excel", f"تم تصدير التقرير كـ reports/{student.name}_report.xlsx")

    def scan_qr_code(self):
        cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            if not ret:
                messagebox.showerror("خطأ", "تعذر الوصول إلى الكاميرا!")
                break

            barcodes = pyzbar.decode(frame)
            for barcode in barcodes:
                student_id = int(barcode.data.decode("utf-8"))
                self.record_attendance(student_id)
                cap.release()
                cv2.destroyAllWindows()
                messagebox.showinfo("نجاح", f"تم تسجيل حضور الطالب {student_id}")
                return

            cv2.imshow("QR Code Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    def generate_group_report(self, group_name, start_date, end_date):
        group = next((g for g in self.groups if g.name == group_name), None)
        if not group:
            messagebox.showerror("خطأ", "المجموعة غير موجودة!")
            return

        # إنشاء تقرير الحضور والغياب
        data = {"الطالب": [], "الحضور (%)": [], "الغياب (%)": [], "الحضور (عدد)": [], "الغياب (عدد)": [], "التقييم": []}
        for student in group.students:
            total_days = len(student.attendance)
            total_possible_days = len(group.days.split(',')) * 4  # افتراض 4 أسابيع في الشهر
            attendance_percentage = (total_days / total_possible_days) * 100
            absence_percentage = 100 - attendance_percentage
            data["الطالب"].append(student.name)
            data["الحضور (%)"].append(f"{attendance_percentage:.2f}%")
            data["الغياب (%)"].append(f"{absence_percentage:.2f}%")
            data["الحضور (عدد)"].append(total_days)
            data["الغياب (عدد)"].append(total_possible_days - total_days)
            data["التقييم"].append(sum([eval["stars"] for eval in student.evaluation.values()]))

        # إنشاء DataFrame
        df = pd.DataFrame(data)

        # حفظ التقرير كملف Excel
        with pd.ExcelWriter(f"reports/{group.name}_group_report.xlsx", engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='تقرير المجموعة')
            workbook = writer.book
            worksheet = writer.sheets['تقرير المجموعة']

            # تنسيق الخلايا
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#4CAF50',
                'border': 1,
                'font_color': 'white'
            })

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # تنسيق الخلايا بناءً على نسبة الحضور
            cell_format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
            cell_format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})

            for row_num in range(1, len(df) + 1):
                if float(df.iloc[row_num - 1]['الحضور (%)'].strip('%')) >= 50:
                    worksheet.set_row(row_num, None, cell_format_green)
                else:
                    worksheet.set_row(row_num, None, cell_format_red)

            # إضافة النسب إلى التقرير
            worksheet.write(len(df) + 2, 0, "تقرير المجموعة")

        messagebox.showinfo("تصدير Excel", f"تم تصدير التقرير كـ reports/{group.name}_group_report.xlsx")

    def export_students_list(self):
        data = {"الطالب": [], "ID": [], "التقييم": []}
        for student in self.students:
            data["الطالب"].append(student.name)
            data["ID"].append(student.id)
            data["التقييم"].append(sum([eval["stars"] for eval in student.evaluation.values()]))

        df = pd.DataFrame(data)

        # حفظ التقرير كملف Excel
        with pd.ExcelWriter("reports/students_list.xlsx", engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='قائمة الطلاب')
            workbook = writer.book
            worksheet = writer.sheets['قائمة الطلاب']

            # تنسيق الخلايا
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#4CAF50',
                'border': 1,
                'font_color': 'white'
            })

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

        messagebox.showinfo("تصدير Excel", "تم تصدير قائمة الطلاب كـ reports/students_list.xlsx")

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("بافلي هاني - نظام إدارة الحضور")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")
        self.system = AttendanceSystem()

        # إنشاء واجهة المستخدم
        self.create_main_menu()

    def create_main_menu(self):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # الأزرار الرئيسية
        btn_add_group = tk.Button(self.root, text="إضافة مجموعة", font=("DejaVu", 16), bg="#4CAF50", fg="white", command=self.add_group_page)
        btn_add_group.pack(pady=10)

        btn_add_student = tk.Button(self.root, text="إضافة طالب", font=("DejaVu", 16), bg="#2196F3", fg="white", command=self.add_student_page)
        btn_add_student.pack(pady=10)

        btn_manage_groups = tk.Button(self.root, text="إدارة المجموعات", font=("DejaVu", 16), bg="#FF9800", fg="white", command=self.manage_groups_page)
        btn_manage_groups.pack(pady=10)

        btn_manage_students = tk.Button(self.root, text="إدارة الطلاب", font=("DejaVu", 16), bg="#9C27B0", fg="white", command=self.manage_students_page)
        btn_manage_students.pack(pady=10)

        btn_record_attendance = tk.Button(self.root, text="تسجيل الحضور", font=("DejaVu", 16), bg="#FF9800", fg="white", command=self.record_attendance_page)
        btn_record_attendance.pack(pady=10)

        btn_generate_report = tk.Button(self.root, text="عرض التقرير الشهري", font=("DejaVu", 16), bg="#9C27B0", fg="white", command=self.generate_report_page)
        btn_generate_report.pack(pady=10)

        btn_group_report = tk.Button(self.root, text="تقرير المجموعة", font=("DejaVu", 16), bg="#607D8B", fg="white", command=self.group_report_page)
        btn_group_report.pack(pady=10)

        btn_how_to_use = tk.Button(self.root, text="طريقة استخدام البرنامج", font=("DejaVu", 16), bg="#FF5722", fg="white", command=self.how_to_use_page)
        btn_how_to_use.pack(pady=10)

        btn_exit = tk.Button(self.root, text="الخروج", font=("DejaVu", 16), bg="#F44336", fg="white", command=self.root.quit)
        btn_exit.pack(pady=10)

    def add_group_page(self):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.create_main_menu)
        btn_back.pack(pady=10)

        # حقول إدخال البيانات
        lbl_name = tk.Label(self.root, text="اسم المجموعة:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_name.pack(pady=5)
        self.entry_name = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_name.pack(pady=5)

        lbl_time = tk.Label(self.root, text="وقت المجموعة:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_time.pack(pady=5)
        self.entry_time = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_time.pack(pady=5)

        lbl_days = tk.Label(self.root, text="أيام المجموعة:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_days.pack(pady=5)

        # قائمة منسدلة تدعم اختيار أكثر من يوم
        self.days_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE, font=("DejaVu", 14), height=7)
        days = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        for day in days:
            self.days_listbox.insert(tk.END, day)
        self.days_listbox.pack(pady=5)

        btn_add = tk.Button(self.root, text="إضافة", font=("DejaVu", 14), bg="#4CAF50", fg="white", command=self.save_group)
        btn_add.pack(pady=10)

    def save_group(self):
        name = self.entry_name.get()
        time = self.entry_time.get()
        selected_days = [self.days_listbox.get(i) for i in self.days_listbox.curselection()]  # الحصول على الأيام المختارة
        days = ",".join(selected_days)  # تحويل القائمة إلى سلسلة نصية مفصولة بفواصل

        if not name or not time or not days:
            messagebox.showerror("خطأ", "يجب ملء جميع الحقول!")
            return
        self.system.add_group(name, time, days)
        self.create_main_menu()

    def add_student_page(self):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.create_main_menu)
        btn_back.pack(pady=10)

        # حقول إدخال البيانات
        lbl_name = tk.Label(self.root, text="اسم الطالب:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_name.pack(pady=5)
        self.entry_student_name = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_student_name.pack(pady=5)

        lbl_phone = tk.Label(self.root, text="رقم الهاتف:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_phone.pack(pady=5)
        self.entry_phone = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_phone.pack(pady=5)

        lbl_group = tk.Label(self.root, text="اسم المجموعة:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_group.pack(pady=5)
        self.group_var = tk.StringVar()
        self.group_dropdown = ttk.Combobox(self.root, textvariable=self.group_var, font=("DejaVu", 14))
        self.group_dropdown['values'] = [group.name for group in self.system.groups]
        self.group_dropdown.pack(pady=5)

        btn_add = tk.Button(self.root, text="إضافة", font=("DejaVu", 14), bg="#4CAF50", fg="white", command=self.save_student)
        btn_add.pack(pady=10)

    def save_student(self):
        name = self.entry_student_name.get()
        phone = self.entry_phone.get()
        group = self.group_var.get()
        if not name or not phone or not group:
            messagebox.showerror("خطأ", "يجب ملء جميع الحقول!")
            return
        self.system.add_student(name, phone, group)
        self.create_main_menu()

    def manage_groups_page(self):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.create_main_menu)
        btn_back.pack(pady=10)

        # عرض المجموعات
        lbl_groups = tk.Label(self.root, text="المجموعات:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_groups.pack(pady=5)

        for group in self.system.groups:
            frame = tk.Frame(self.root, bg="#f0f0f0")
            frame.pack(pady=5)

            lbl_group = tk.Label(frame, text=f"المجموعة: {group.name} (الوقت: {group.time}, الأيام: {group.days})", font=("DejaVu", 12), bg="#f0f0f0")
            lbl_group.pack(side=tk.LEFT)

            btn_edit = tk.Button(frame, text="تعديل", font=("DejaVu", 12), bg="#FFC107", fg="white", command=lambda g=group.name: self.edit_group_page(g))
            btn_edit.pack(side=tk.LEFT, padx=5)

            btn_delete = tk.Button(frame, text="حذف", font=("DejaVu", 12), bg="#F44336", fg="white", command=lambda g=group.name: self.delete_group(g))
            btn_delete.pack(side=tk.LEFT)

    def edit_group_page(self, group_name):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.manage_groups_page)
        btn_back.pack(pady=10)

        # حقول إدخال البيانات
        lbl_name = tk.Label(self.root, text="اسم المجموعة:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_name.pack(pady=5)
        self.entry_name = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_name.insert(0, group_name)
        self.entry_name.pack(pady=5)

        lbl_time = tk.Label(self.root, text="وقت المجموعة:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_time.pack(pady=5)
        self.entry_time = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_time.pack(pady=5)

        lbl_days = tk.Label(self.root, text="أيام المجموعة:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_days.pack(pady=5)

        # قائمة منسدلة تدعم اختيار أكثر من يوم
        self.days_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE, font=("DejaVu", 14), height=7)
        days = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        for day in days:
            self.days_listbox.insert(tk.END, day)
        self.days_listbox.pack(pady=5)

        btn_save = tk.Button(self.root, text="حفظ التعديلات", font=("DejaVu", 14), bg="#4CAF50", fg="white", command=lambda: self.save_group_edit(group_name))
        btn_save.pack(pady=10)

    def save_group_edit(self, old_name):
        new_name = self.entry_name.get()
        new_time = self.entry_time.get()
        selected_days = [self.days_listbox.get(i) for i in self.days_listbox.curselection()]  # الحصول على الأيام المختارة
        new_days = ",".join(selected_days)  # تحويل القائمة إلى سلسلة نصية مفصولة بفواصل

        if not new_name or not new_time or not new_days:
            messagebox.showerror("خطأ", "يجب ملء جميع الحقول!")
            return
        self.system.edit_group(old_name, new_name, new_time, new_days)
        self.manage_groups_page()

    def delete_group(self, group_name):
        self.system.delete_group(group_name)
        self.manage_groups_page()

    def manage_students_page(self):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.create_main_menu)
        btn_back.pack(pady=10)

        # عرض الطلاب
        lbl_students = tk.Label(self.root, text="الطلاب:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_students.pack(pady=5)

        for student in self.system.students:
            frame = tk.Frame(self.root, bg="#f0f0f0")
            frame.pack(pady=5)

            lbl_student = tk.Label(frame, text=f"الطالب: {student.name} (ID: {student.id}, المجموعة: {student.group})", font=("DejaVu", 12), bg="#f0f0f0")
            lbl_student.pack(side=tk.LEFT)

            btn_edit = tk.Button(frame, text="تعديل", font=("DejaVu", 12), bg="#FFC107", fg="white", command=lambda s=student.id: self.edit_student_page(s))
            btn_edit.pack(side=tk.LEFT, padx=5)

            btn_evaluate = tk.Button(frame, text="تقييم", font=("DejaVu", 12), bg="#4CAF50", fg="white", command=lambda s=student.id: self.evaluate_student_page(s))
            btn_evaluate.pack(side=tk.LEFT, padx=5)

            btn_delete = tk.Button(frame, text="حذف", font=("DejaVu", 12), bg="#F44336", fg="white", command=lambda s=student.id: self.delete_student(s))
            btn_delete.pack(side=tk.LEFT)

        btn_export = tk.Button(self.root, text="تنزيل قائمة الطلاب", font=("DejaVu", 14), bg="#2196F3", fg="white", command=self.system.export_students_list)
        btn_export.pack(pady=10)

    def edit_student_page(self, student_id):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.manage_students_page)
        btn_back.pack(pady=10)

        # حقول إدخال البيانات
        student = next((s for s in self.system.students if s.id == student_id), None)
        if not student:
            messagebox.showerror("خطأ", "الطالب غير موجود!")
            return

        lbl_name = tk.Label(self.root, text="اسم الطالب:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_name.pack(pady=5)
        self.entry_student_name = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_student_name.insert(0, student.name)
        self.entry_student_name.pack(pady=5)

        lbl_phone = tk.Label(self.root, text="رقم الهاتف:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_phone.pack(pady=5)
        self.entry_phone = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_phone.insert(0, student.phone)
        self.entry_phone.pack(pady=5)

        lbl_group = tk.Label(self.root, text="اسم المجموعة:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_group.pack(pady=5)
        self.group_var = tk.StringVar()
        self.group_dropdown = ttk.Combobox(self.root, textvariable=self.group_var, font=("DejaVu", 14))
        self.group_dropdown['values'] = [group.name for group in self.system.groups]
        self.group_dropdown.set(student.group)
        self.group_dropdown.pack(pady=5)

        btn_save = tk.Button(self.root, text="حفظ التعديلات", font=("DejaVu", 14), bg="#4CAF50", fg="white", command=lambda: self.save_student_edit(student_id))
        btn_save.pack(pady=10)

    def save_student_edit(self, student_id):
        new_name = self.entry_student_name.get()
        new_phone = self.entry_phone.get()
        new_group = self.group_var.get()
        if not new_name or not new_phone or not new_group:
            messagebox.showerror("خطأ", "يجب ملء جميع الحقول!")
            return
        self.system.edit_student(student_id, new_name, new_phone, new_group)
        self.manage_students_page()

    def evaluate_student_page(self, student_id):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.manage_students_page)
        btn_back.pack(pady=10)

        # حقول إدخال البيانات
        student = next((s for s in self.system.students if s.id == student_id), None)
        if not student:
            messagebox.showerror("خطأ", "الطالب غير موجود!")
            return

        lbl_stars = tk.Label(self.root, text="عدد النجوم (1-3):", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_stars.pack(pady=5)
        self.entry_stars = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_stars.pack(pady=5)

        lbl_notes = tk.Label(self.root, text="ملاحظات:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_notes.pack(pady=5)
        self.entry_notes = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_notes.pack(pady=5)

        btn_save = tk.Button(self.root, text="حفظ التقييم", font=("DejaVu", 14), bg="#4CAF50", fg="white", command=lambda: self.save_evaluation(student_id))
        btn_save.pack(pady=10)

    def save_evaluation(self, student_id):
        stars = self.entry_stars.get()
        notes = self.entry_notes.get()
        if not stars or not notes:
            messagebox.showerror("خطأ", "يجب ملء جميع الحقول!")
            return
        if not stars.isdigit() or int(stars) < 1 or int(stars) > 3:
            messagebox.showerror("خطأ", "عدد النجوم يجب أن يكون بين 1 و 3!")
            return
        self.system.evaluate_student(student_id, int(stars), notes)
        self.manage_students_page()

    def delete_student(self, student_id):
        self.system.delete_student(student_id)
        self.manage_students_page()

    def record_attendance_page(self):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.create_main_menu)
        btn_back.pack(pady=10)

        # خيارات تسجيل الحضور
        btn_scan_qr = tk.Button(self.root, text="مسح QR Code", font=("DejaVu", 14), bg="#FF9800", fg="white", command=self.system.scan_qr_code)
        btn_scan_qr.pack(pady=10)

        lbl_id = tk.Label(self.root, text="ID الطالب:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_id.pack(pady=5)
        self.entry_student_id = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_student_id.pack(pady=5)

        btn_record = tk.Button(self.root, text="تسجيل الحضور", font=("DejaVu", 14), bg="#4CAF50", fg="white", command=self.record_attendance)
        btn_record.pack(pady=10)

    def record_attendance(self):
        student_id = self.entry_student_id.get()
        if not student_id:
            messagebox.showerror("خطأ", "يجب إدخال ID الطالب!")
            return
        self.system.record_attendance(int(student_id))
        self.create_main_menu()

    def generate_report_page(self):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.create_main_menu)
        btn_back.pack(pady=10)

        # حقول إدخال البيانات
        lbl_id = tk.Label(self.root, text="ID الطالب:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_id.pack(pady=5)
        self.entry_report_id = tk.Entry(self.root, font=("DejaVu", 14))
        self.entry_report_id.pack(pady=5)

        lbl_start = tk.Label(self.root, text="تاريخ البداية (YYYY-MM-DD):", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_start.pack(pady=5)
        self.entry_start_date = DateEntry(self.root, font=("DejaVu", 14), date_pattern="yyyy-mm-dd")
        self.entry_start_date.pack(pady=5)

        lbl_end = tk.Label(self.root, text="تاريخ النهاية (YYYY-MM-DD):", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_end.pack(pady=5)
        self.entry_end_date = DateEntry(self.root, font=("DejaVu", 14), date_pattern="yyyy-mm-dd")
        self.entry_end_date.pack(pady=5)

        btn_generate = tk.Button(self.root, text="عرض التقرير", font=("DejaVu", 14), bg="#4CAF50", fg="white", command=self.generate_report)
        btn_generate.pack(pady=10)

        btn_export_excel = tk.Button(self.root, text="تصدير Excel", font=("DejaVu", 14), bg="#2196F3", fg="white", command=self.export_excel)
        btn_export_excel.pack(pady=10)

    def generate_report(self):
        student_id = self.entry_report_id.get()
        start_date = self.entry_start_date.get()
        end_date = self.entry_end_date.get()
        if not student_id or not start_date or not end_date:
            messagebox.showerror("خطأ", "يجب ملء جميع الحقول!")
            return
        self.system.generate_monthly_report(int(student_id), start_date, end_date)

    def export_excel(self):
        student_id = self.entry_report_id.get()
        start_date = self.entry_start_date.get()
        end_date = self.entry_end_date.get()
        if not student_id or not start_date or not end_date:
            messagebox.showerror("خطأ", "يجب ملء جميع الحقول!")
            return
        self.system.export_report_excel(int(student_id), start_date, end_date)

    def group_report_page(self):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.create_main_menu)
        btn_back.pack(pady=10)

        # حقول إدخال البيانات
        lbl_group = tk.Label(self.root, text="اسم المجموعة:", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_group.pack(pady=5)
        self.group_var = tk.StringVar()
        self.group_dropdown = ttk.Combobox(self.root, textvariable=self.group_var, font=("DejaVu", 14))
        self.group_dropdown['values'] = [group.name for group in self.system.groups]
        self.group_dropdown.pack(pady=5)

        lbl_start = tk.Label(self.root, text="تاريخ البداية (YYYY-MM-DD):", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_start.pack(pady=5)
        self.entry_start_date = DateEntry(self.root, font=("DejaVu", 14), date_pattern="yyyy-mm-dd")
        self.entry_start_date.pack(pady=5)

        lbl_end = tk.Label(self.root, text="تاريخ النهاية (YYYY-MM-DD):", font=("DejaVu", 14), bg="#f0f0f0")
        lbl_end.pack(pady=5)
        self.entry_end_date = DateEntry(self.root, font=("DejaVu", 14), date_pattern="yyyy-mm-dd")
        self.entry_end_date.pack(pady=5)

        btn_generate = tk.Button(self.root, text="عرض التقرير", font=("DejaVu", 14), bg="#4CAF50", fg="white", command=self.generate_group_report)
        btn_generate.pack(pady=10)

        btn_export_excel = tk.Button(self.root, text="تصدير Excel", font=("DejaVu", 14), bg="#2196F3", fg="white", command=self.export_group_report_excel)
        btn_export_excel.pack(pady=10)

    def generate_group_report(self):
        group_name = self.group_var.get()
        start_date = self.entry_start_date.get()
        end_date = self.entry_end_date.get()
        if not group_name or not start_date or not end_date:
            messagebox.showerror("خطأ", "يجب ملء جميع الحقول!")
            return
        self.system.generate_group_report(group_name, start_date, end_date)

    def export_group_report_excel(self):
        group_name = self.group_var.get()
        start_date = self.entry_start_date.get()
        end_date = self.entry_end_date.get()
        if not group_name or not start_date or not end_date:
            messagebox.showerror("خطأ", "يجب ملء جميع الحقول!")
            return
        self.system.export_group_report_excel(group_name, start_date, end_date)

    def how_to_use_page(self):
        # تنظيف الشاشة
        for widget in self.root.winfo_children():
            widget.destroy()

        # العودة للقائمة الرئيسية
        btn_back = tk.Button(self.root, text="رجوع", font=("DejaVu", 14), bg="#607D8B", fg="white", command=self.create_main_menu)
        btn_back.pack(pady=10)

        # نص طريقة الاستخدام
        instructions = """
        طريقة استخدام البرنامج:
        1. إضافة مجموعة: قم بإضافة مجموعة جديدة مع تحديد الوقت والأيام.
        2. إضافة طالب: قم بإضافة طالب جديد واختيار المجموعة المناسبة.
        3. تسجيل الحضور: استخدم الكاميرا لمسح QR Code الطالب أو أدخل ID يدويًا.
        4. إدارة الطلاب: يمكنك تعديل أو حذف الطلاب وإضافة تقييمات لهم.
        5. عرض التقارير: قم بإنشاء تقارير الحضور الشهرية أو تقارير المجموعات.
        6. تصدير البيانات: قم بتصدير قائمة الطلاب أو التقارير كملفات Excel.

        مع تحيات،
        المبرمج
        Pavly Hany
        """
        lbl_instructions = tk.Label(self.root, text=instructions, font=("DejaVu", 14), bg="#f0f0f0", justify=tk.LEFT)
        lbl_instructions.pack(pady=20)

        # إضافة توقيع مميز
        signature = tk.Label(self.root, text="Pavly Hany", font=("DejaVu", 24, "bold"), bg="#f0f0f0", fg="#FF5722")
        signature.pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
