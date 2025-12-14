import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.collections import LineCollection
import pandas as pd
import numpy as np
import os
from datetime import datetime
import calendar

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Get the app data path
app_data = os.environ.get('LOCALAPPDATA')
if app_data is None:
    messagebox.showerror("Error", "LOCALAPPDATA environment variable not found.")
    exit(1)

folder = os.path.join(app_data, '💲NovaFoundry')
os.makedirs(folder, exist_ok=True)
csv_path = os.path.join(folder, 'transactions.csv')

# Load or initialize DataFrame
if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        df['Balance'] = df['Amount'].cumsum()
        df.to_csv(csv_path, index=False)
else:
    df = pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Balance'])

# Function to select date
def select_date(entry):
    cal_dialog = ctk.CTkToplevel(root)
    cal_dialog.title("Select Date")
    cal_dialog.geometry("300x300")
    cal_dialog.attributes('-topmost', True)

    current_year = datetime.now().year
    current_month = datetime.now().month

    year_var = ctk.StringVar(value=str(current_year))
    month_var = ctk.StringVar(value=str(current_month))

    ctk.CTkLabel(cal_dialog, text="Year:").pack(pady=5)
    year_combo = ctk.CTkComboBox(cal_dialog, values=[str(y) for y in range(current_year - 10, current_year + 10)], variable=year_var)
    year_combo.pack(pady=5)

    ctk.CTkLabel(cal_dialog, text="Month:").pack(pady=5)
    month_combo = ctk.CTkComboBox(cal_dialog, values=[str(m) for m in range(1, 13)], variable=month_var)
    month_combo.pack(pady=5)

    days_frame = ctk.CTkFrame(cal_dialog)
    days_frame.pack(pady=5)

    def update_days(*args):
        try:
            year = int(year_var.get())
            month = int(month_var.get())
        except ValueError:
            return

        for widget in days_frame.winfo_children():
            widget.destroy()

        cal = calendar.monthcalendar(year, month)

        weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for i, day in enumerate(weekdays):
            ctk.CTkLabel(days_frame, text=day, width=4).grid(row=0, column=i, padx=2)

        row = 1
        for week in cal:
            for i, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(days_frame, text=' ', width=4).grid(row=row, column=i, padx=2)
                else:
                    btn = ctk.CTkButton(days_frame, text=str(day), width=40,
                                        command=lambda d=day, y=year, m=month: set_date(y, m, d))
                    btn.grid(row=row, column=i, padx=2, pady=2)
            row += 1

    def set_date(y, m, d):
        entry.delete(0, 'end')
        entry.insert(0, f"{y}-{m:02d}-{d:02d}")
        cal_dialog.destroy()

    update_days()
    year_var.trace_add('write', update_days)
    month_var.trace_add('write', update_days)

# Function to add transaction
def add_transaction(is_income=True):
    dialog = ctk.CTkToplevel(root)
    dialog.title("Add Transaction")
    dialog.geometry("300x300")
    dialog.configure(fg_color='#1a1a1a')
    dialog.attributes('-topmost', True)

    ctk.CTkLabel(dialog, text="Date (YYYY-MM-DD):").pack(pady=10)
    date_entry = ctk.CTkEntry(dialog)
    date_entry.pack(pady=5)

    ctk.CTkButton(dialog, text="Select Date", command=lambda: select_date(date_entry)).pack(pady=5)

    ctk.CTkLabel(dialog, text="Description:").pack(pady=10)
    desc_entry = ctk.CTkEntry(dialog)
    desc_entry.pack(pady=5)

    ctk.CTkLabel(dialog, text="Amount:").pack(pady=10)
    amount_entry = ctk.CTkEntry(dialog)
    amount_entry.pack(pady=5)

    def submit():
        try:
            date_str = date_entry.get()
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
            
            amount = float(amount_entry.get())
            if not is_income:
                amount = -amount
            desc = desc_entry.get() or ("Income" if is_income else "Spending")
            
            new_row = {'Date': date, 'Description': desc, 'Amount': amount, 'Balance': 0}  # Balance temp
            global df
            new_df = pd.DataFrame([new_row])
            if df.empty:
                df = new_df
            else:
                df = pd.concat([df, new_df], ignore_index=True)
            
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date').reset_index(drop=True)
            df['Balance'] = df['Amount'].cumsum()
            
            df.to_csv(csv_path, index=False)
            update_ui()
            dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    ctk.CTkButton(dialog, text="Submit", command=submit).pack(pady=10)

# Function to reset data
def reset_data():
    if messagebox.askyesno("Confirm", "Are you sure you want to reset all transactions?"):
        global df
        df = pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Balance'])
        if os.path.exists(csv_path):
            os.remove(csv_path)
        update_ui()

# Function to export
def export_data():
    file = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx"), ("OpenDocument Spreadsheet", "*.ods")]
    )
    if file:
        try:
            if file.endswith('.csv'):
                df.to_csv(file, index=False)
            elif file.endswith('.xlsx'):
                df.to_excel(file, index=False)
            elif file.endswith('.ods'):
                # Note: Requires odfpy installed (pip install odfpy)
                df.to_excel(file, index=False, engine='odf')
            messagebox.showinfo("Success", "Export successful.")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {str(e)}")

# Function to scroll x
def scroll_x(*args):
    if args[0] == 'scroll':
        units = float(args[1])
        type_ = args[2] if len(args) > 2 else 'units'
        if type_ == 'pages':
            delta = units * 0.9
        else:
            delta = units * 0.1
        low, high = scrollbar_graph.get()
        size = high - low
        new_low = low + delta * size
        new_low = max(0, min(new_low, 1 - size))
        scrollbar_graph.set(new_low, new_low + size)
    elif args[0] == 'moveto':
        new_low = float(args[1])
        size = scrollbar_graph.get()[1] - scrollbar_graph.get()[0]
        new_low = max(0, min(new_low, 1 - size))
        scrollbar_graph.set(new_low, new_low + size)
    update_lim()

# Function to update lim
def update_lim():
    low, high = scrollbar_graph.get()
    xmin, xmax = full_xlim
    width = xmax - xmin
    ax.set_xlim(xmin + low * width, xmin + high * width)
    canvas.draw_idle()

full_xlim = None

# Function to update UI
def update_ui():
    global full_xlim
    for item in tree.get_children():
        tree.delete(item)
    if df.empty:
        tree.insert('', 'end', values=("No transactions yet", "", "", "", "", "", ""))
    else:
        for idx, row in df.iterrows():
            tag = 'even' if idx % 2 == 0 else 'odd'
            tree.insert('', 'end', values=(str(row['Date']), '│', row['Description'], '│', f"{row['Amount']:.2f}", '│', f"{row['Balance']:.2f}"), tags=(tag,))
    
    ax.clear()
    ax.set_facecolor('#1a1a1a')
    if not df.empty:
        dates = df['Date'].to_numpy()
        balances = df['Balance'].to_numpy()
        dates_num = mdates.date2num(dates)
        last_x = dates_num.max()
        full_min = dates_num.min()

        if len(balances) > 1:
            deltas = np.diff(balances)
            points = np.column_stack([dates_num, balances]).reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)

            max_abs = np.max(np.abs(deltas))
            norm = Normalize(-max_abs, max_abs)
            cmap = plt.colormaps.get_cmap('RdYlGn')

            lc = LineCollection(segments, cmap=cmap, norm=norm)
            lc.set_array(deltas)
            lc.set_linewidth(2)
            ax.add_collection(lc)

            # Predictions
            x = dates_num
            y = balances
            coef = np.polyfit(x, y, 1)
            future_x = np.arange(last_x + 1, last_x + 31)
            pred_y = np.polyval(coef, future_x)
            ax.plot(np.concatenate((np.array([last_x]), future_x)), np.concatenate((np.array([y[-1]]), pred_y)), color='grey', linestyle='--')
            full_max = future_x.max()
        else:
            ax.plot(dates_num, balances, color='white')
            full_max = last_x

        full_xlim = (full_min, full_max)
        data_range = last_x - full_min
        visible_days = min(30, data_range)
        if visible_days > 0:
            initial_left = last_x - visible_days
            initial_right = last_x
            low = max(0, (initial_left - full_min) / (full_max - full_min))
            high = min(1, (initial_right - full_min) / (full_max - full_min))
            ax.set_xlim(initial_left, initial_right)
            scrollbar_graph.set(low, high)
        else:
            ax.set_xlim(full_min - 0.5, full_max + 0.5)
            scrollbar_graph.set(0, 1)

        # Gradient shading for positive
        cmap_green = LinearSegmentedColormap.from_list('green_fade', [(0,1,0,0), (0,1,0,0.3)])
        poly_pos = ax.fill_between(dates_num, balances, 0, where=(balances >= 0), lw=0, color='none')
        for path in poly_pos.get_paths():
            verts = path.vertices
            xmin, xmax = verts[:,0].min(), verts[:,0].max()
            ymin, ymax = 0, verts[:,1].max()
            grad = ax.imshow(np.linspace(0,1,256).reshape(-1,1), cmap=cmap_green, aspect='auto', extent=[xmin, xmax, ymin, ymax], origin='lower')
            grad.set_clip_path(path, transform=ax.transData)

        # Gradient shading for negative
        cmap_red = LinearSegmentedColormap.from_list('red_fade', [(1,0,0,0.3), (1,0,0,0)])
        poly_neg = ax.fill_between(dates_num, balances, 0, where=(balances <= 0), lw=0, color='none')
        for path in poly_neg.get_paths():
            verts = path.vertices
            xmin, xmax = verts[:,0].min(), verts[:,0].max()
            ymin, ymax = verts[:,1].min(), 0
            grad = ax.imshow(np.linspace(0,1,256).reshape(-1,1), cmap=cmap_red, aspect='auto', extent=[xmin, xmax, ymin, ymax], origin='lower')
            grad.set_clip_path(path, transform=ax.transData)

        ax.set_xlabel('Date', color='white')
        ax.set_ylabel('Balance', color='white')
        ax.tick_params(colors='white')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        for spine in ax.spines.values():
            spine.set_edgecolor('white')
        fig.autofmt_xdate()
    else:
        ax.text(0.5, 0.5, 'No data yet', horizontalalignment='center', verticalalignment='center', color='white', fontsize=12)
        scrollbar_graph.set(0, 1)
    canvas.draw()

# On closing
def on_closing():
    try:
        for seq in root.tk.eval('after info').split():
            root.after_cancel(seq)
    except:
        pass
    root.destroy()

# Main window
root = ctk.CTk()
root.title("Financial Tracker")
root.after(200, lambda: root.state('zoomed'))
root.configure(fg_color='#1a1a1a')
root.protocol("WM_DELETE_WINDOW", on_closing)

# Button frame
button_frame = ctk.CTkFrame(root, fg_color='#1a1a1a', corner_radius=20)
button_frame.pack(fill='x', padx=20, pady=20)

ctk.CTkButton(button_frame, text="Add Income", command=lambda: add_transaction(True), corner_radius=32, font=('Arial', 14)).pack(side='left', padx=10)
ctk.CTkButton(button_frame, text="Add Spending", command=lambda: add_transaction(False), corner_radius=32, font=('Arial', 14)).pack(side='left', padx=10)
ctk.CTkButton(button_frame, text="Export", command=export_data, corner_radius=32, font=('Arial', 14)).pack(side='left', padx=10)
ctk.CTkButton(button_frame, text="Reset", command=reset_data, corner_radius=32, font=('Arial', 14)).pack(side='left', padx=10)

# Transactions frame
trans_frame = ctk.CTkFrame(root, fg_color='#1a1a1a', corner_radius=20)
trans_frame.pack(fill='both', expand=True, padx=20, pady=10, side='top')
trans_frame.grid_rowconfigure(0, weight=1)
trans_frame.grid_columnconfigure(0, weight=1)

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview", background="#1a1a1a", foreground="white", fieldbackground="#1a1a1a", bordercolor="grey", borderwidth=1, lightcolor="grey", darkcolor="grey")
style.map("Treeview", background=[('selected', 'grey')])
style.configure("Treeview.Heading", background="#2a2a2a", foreground="white", relief="flat")
style.map("Treeview.Heading", background=[('active', "#3a3a3a")])
style.configure('even.Treeview', background='#242424')
style.configure('odd.Treeview', background='#1a1a1a')

tree = ttk.Treeview(trans_frame, columns=('Date', 'sep1', 'Description', 'sep2', 'Amount', 'sep3', 'Balance'), show='headings', height=10)
tree.heading('Date', text='Date')
tree.heading('sep1', text='')
tree.heading('Description', text='Description')
tree.heading('sep2', text='')
tree.heading('Amount', text='Amount')
tree.heading('sep3', text='')
tree.heading('Balance', text='Balance')
tree.column('Date', width=200, anchor='center')
tree.column('sep1', width=2, anchor='center', stretch=False)
tree.column('Description', width=300, anchor='center')
tree.column('sep2', width=2, anchor='center', stretch=False)
tree.column('Amount', width=100, anchor='center')
tree.column('sep3', width=2, anchor='center', stretch=False)
tree.column('Balance', width=100, anchor='center')
tree.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

scrollbar = ctk.CTkScrollbar(trans_frame, command=tree.yview)
scrollbar.grid(row=0, column=1, sticky='ns')

tree.configure(yscrollcommand=scrollbar.set)

# Graph frame
graph_frame = ctk.CTkFrame(root, fg_color='#1a1a1a', corner_radius=20)
graph_frame.pack(fill='both', expand=True, padx=20, pady=10, side='top')

fig, ax = plt.subplots(figsize=(8, 3), facecolor='#1a1a1a')
ax.set_facecolor('#1a1a1a')
canvas = FigureCanvasTkAgg(fig, master=graph_frame)
canvas.get_tk_widget().pack(fill='both', expand=True)

scrollbar_graph = ctk.CTkScrollbar(graph_frame, orientation='horizontal', command=scroll_x)
scrollbar_graph.pack(fill='x')

# Initial update
update_ui()

root.mainloop()