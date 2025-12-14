import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.collections import LineCollection
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import webbrowser
from PIL import Image
import re 
import math

# --- Configuration ---
DATA_FOLDER = '💲NovaFoundry'
TRANS_FILE = 'transactions.csv'
RECUR_FILE = 'recurring_rules.csv'
ICON_PATH = "Icons/Pulsar_Icon.ico"
VERSION = "1.2.1"
APP_NAME = "Pulsar"
COMPANY_NAME = "Nova Foundry"
WEBSITE_URL = "https://novafoundry.ca"

# Currency Options
CURRENCIES = ["$", "¥", "€", "£", "₹", "₽", "₩"]
CURRENT_CURRENCY = "$"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Font Setup
FONT_REGULAR_FAMILY = "Be Vietnam Pro"
FONT_BOLD_FAMILY = "Be Vietnam Pro Bold"

# Get Paths
app_data = os.environ.get('LOCALAPPDATA')
if app_data is None: exit(1)
folder = os.path.join(app_data, DATA_FOLDER)
os.makedirs(folder, exist_ok=True)
trans_path = os.path.join(folder, TRANS_FILE)
recur_path = os.path.join(folder, RECUR_FILE)

# --- Data Management ---

def init_files():
    if not os.path.exists(trans_path):
        pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Type']).to_csv(trans_path, index=False)
    
    if not os.path.exists(recur_path):
        pd.DataFrame(columns=['StartDate', 'Description', 'Amount', 'Interval', 'Unit', 'EndDate']).to_csv(recur_path, index=False)

init_files()

df_static = pd.DataFrame()
df_rules = pd.DataFrame()
df_display = pd.DataFrame() 

def load_data():
    global df_static, df_rules
    try:
        df_static = pd.read_csv(trans_path)
        df_static['Date'] = pd.to_datetime(df_static['Date'])
    except:
        df_static = pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Type'])

    try:
        df_rules = pd.read_csv(recur_path)
        df_rules['StartDate'] = pd.to_datetime(df_rules['StartDate'])
        if 'EndDate' not in df_rules.columns:
            df_rules['EndDate'] = pd.NaT
        else:
            df_rules['EndDate'] = pd.to_datetime(df_rules['EndDate'])
    except:
        df_rules = pd.DataFrame(columns=['StartDate', 'Description', 'Amount', 'Interval', 'Unit', 'EndDate'])

def add_interval(start_date, interval, unit):
    """
    Helper to add an interval (float supported) to a date.
    Converts non-integer units to days if necessary.
    """
    try:
        val = float(interval)
    except:
        val = 1.0

    # If it's a clean integer, keep using standard logic for accuracy (especially months/years)
    is_int = (val % 1 == 0)
    
    if unit == 'Days':
        return start_date + timedelta(days=val)
    elif unit == 'Weeks':
        return start_date + timedelta(weeks=val)
    elif unit == 'Months':
        if is_int:
            return start_date + relativedelta(months=int(val))
        else:
            # 0.5 months -> ~15.2 days
            days = val * 30.437 
            return start_date + timedelta(days=days)
    elif unit == 'Years':
        if is_int:
            return start_date + relativedelta(years=int(val))
        else:
            days = val * 365.25
            return start_date + timedelta(days=days)
    return start_date

def generate_projection(years=1.0):
    global df_display
    load_data()
    
    generated_rows = []
    end_date = datetime.now() + timedelta(days=365 * years)
    
    if not df_rules.empty:
        for _, rule in df_rules.iterrows():
            current_date = rule['StartDate']
            rule_end = rule['EndDate'] if pd.notnull(rule['EndDate']) else end_date + timedelta(days=1)
            cutoff_date = min(end_date, rule_end)
            
            while current_date <= cutoff_date:
                generated_rows.append({
                    'Date': current_date,
                    'Description': rule['Description'],
                    'Amount': rule['Amount'],
                    'Recurring': True
                })
                
                # Use the new helper function
                current_date = add_interval(current_date, rule['Interval'], rule['Unit'])

    frames_to_concat = []
    if not df_static.empty:
        temp_static = df_static.copy()
        temp_static['Recurring'] = False
        frames_to_concat.append(temp_static)
        
    if generated_rows:
        frames_to_concat.append(pd.DataFrame(generated_rows))
        
    if frames_to_concat:
        df_display = pd.concat(frames_to_concat, ignore_index=True)
        df_display = df_display.sort_values('Date').reset_index(drop=True)
        df_display['Balance'] = df_display['Amount'].cumsum()
    else:
        df_display = pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Balance', 'Recurring'])

# --- File Operations ---

def save_static(date, desc, amount):
    new_row = pd.DataFrame([{'Date': date, 'Description': desc, 'Amount': amount, 'Type': 'Static'}])
    if os.path.exists(trans_path) and os.path.getsize(trans_path) > 0:
        new_row.to_csv(trans_path, mode='a', header=False, index=False)
    else:
        new_row.to_csv(trans_path, index=False)

def save_rule(start_date, desc, amount, interval, unit, end_date=None, index_to_overwrite=None):
    global df_rules
    new_data = {
        'StartDate': start_date, 
        'Description': desc, 
        'Amount': amount, 
        'Interval': float(interval), # Ensure stored as float/number
        'Unit': unit,
        'EndDate': end_date
    }
    
    if index_to_overwrite is not None:
        load_data()
        if 0 <= index_to_overwrite < len(df_rules):
            df_rules.loc[index_to_overwrite] = new_data
            df_rules.to_csv(recur_path, index=False)
    else:
        new_row = pd.DataFrame([new_data])
        if os.path.exists(recur_path) and os.path.getsize(recur_path) > 0:
            new_row.to_csv(recur_path, mode='a', header=False, index=False)
        else:
            new_row.to_csv(recur_path, index=False)

def delete_rule():
    sel = tree_recur.selection()
    if not sel: 
        messagebox.showinfo("Selection Required", "Please click on a recurring item to delete it.")
        return
    
    if messagebox.askyesno("Confirm Delete", "Are you sure? Past occurrences will be saved to history."):
        idx = tree_recur.index(sel[0])
        load_data()
        
        rule = df_rules.iloc[idx]
        current_date = rule['StartDate']
        now = datetime.now()
        
        rule_end = rule['EndDate'] if pd.notnull(rule['EndDate']) else now + timedelta(days=1)
        archive_limit = min(now, rule_end)
        
        while current_date <= archive_limit:
            save_static(current_date, f"{rule['Description']} (Archived)", rule['Amount'])
            current_date = add_interval(current_date, rule['Interval'], rule['Unit'])

        df_rules.drop(df_rules.index[idx], inplace=True)
        df_rules.to_csv(recur_path, index=False)
        refresh_data()

# --- Helper Functions ---

def clean_amount(amount_str):
    clean = re.sub(r'[^\d.-]', '', amount_str)
    return float(clean)

def apply_icon(window):
    if ICON_PATH and os.path.exists(ICON_PATH):
        try:
            window.after(200, lambda: window.iconbitmap(ICON_PATH))
        except:
            pass

# --- Popups ---

def open_about():
    abt = ctk.CTkToplevel(root)
    abt.title("About")
    abt.geometry("350x400")
    abt.attributes('-topmost', True)
    apply_icon(abt)
    
    if os.path.exists(ICON_PATH):
        try:
            my_image = ctk.CTkImage(light_image=Image.open(ICON_PATH), 
                                  dark_image=Image.open(ICON_PATH), 
                                  size=(100, 100))
            img_label = ctk.CTkLabel(abt, image=my_image, text="")
            img_label.pack(pady=(30, 10))
        except: pass

    ctk.CTkLabel(abt, text=APP_NAME, font=(FONT_BOLD_FAMILY, 24)).pack()
    ctk.CTkLabel(abt, text=f"Version {VERSION}", text_color="grey").pack(pady=(0, 20))
    ctk.CTkLabel(abt, text="Financial Forecasting Engine\nDesigned for Simplicity.", font=(FONT_REGULAR_FAMILY, 14)).pack(pady=10)
    ctk.CTkLabel(abt, text="Created by", font=(FONT_REGULAR_FAMILY, 12, "italic")).pack(pady=(20,0))
    link = ctk.CTkLabel(abt, text=COMPANY_NAME, font=(FONT_BOLD_FAMILY, 14), text_color="#3399ff", cursor="hand2")
    link.pack()
    link.bind("<Button-1>", lambda e: webbrowser.open(WEBSITE_URL))
    ctk.CTkButton(abt, text="Close", command=abt.destroy, fg_color="grey", width=100).pack(pady=30)

def open_transaction_dialog(is_income=True, edit_rule_idx=None):
    dialog = ctk.CTkToplevel(root)
    apply_icon(dialog)
    
    title_text = "Edit Recurring Item" if edit_rule_idx is not None else ("Add Income" if is_income else "Add Expense")
    dialog.title(title_text)
    dialog.geometry("420x680")
    dialog.attributes('-topmost', True)
    
    # Defaults
    pre_date = datetime.now()
    pre_desc = ""
    pre_amt = ""
    pre_recur = False
    pre_int = "1"
    pre_unit = "Months"
    pre_end_date = ""
    
    if edit_rule_idx is not None:
        load_data()
        if 0 <= edit_rule_idx < len(df_rules):
            row = df_rules.iloc[edit_rule_idx]
            pre_date = row['StartDate']
            pre_desc = row['Description']
            pre_amt = abs(row['Amount'])
            is_income = row['Amount'] >= 0
            pre_recur = True
            
            # Format interval nicely (remove .0 if integer)
            ival = float(row['Interval'])
            if ival.is_integer(): pre_int = str(int(ival))
            else: pre_int = str(ival)
                
            pre_unit = row['Unit']
            if pd.notnull(row['EndDate']):
                pre_end_date = row['EndDate'].strftime('%Y-%m-%d')

    # UI
    ctk.CTkLabel(dialog, text="When?", font=(FONT_BOLD_FAMILY, 14)).pack(pady=(15,5))
    
    date_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    date_frame.pack(pady=5)
    entry_date = ctk.CTkEntry(date_frame, width=120, placeholder_text="YYYY-MM-DD")
    entry_date.insert(0, pre_date.strftime('%Y-%m-%d'))
    entry_date.pack(side='left', padx=5)

    var_h = ctk.StringVar(value=f"{pre_date.hour:02d}")
    var_m = ctk.StringVar(value=f"{pre_date.minute:02d}")
    ctk.CTkComboBox(date_frame, values=[f"{x:02d}" for x in range(24)], variable=var_h, width=60).pack(side='left', padx=2)
    ctk.CTkLabel(date_frame, text=":").pack(side='left')
    ctk.CTkComboBox(date_frame, values=[f"{x:02d}" for x in range(60)], variable=var_m, width=60).pack(side='left', padx=2)

    ctk.CTkLabel(dialog, text="What is it?", font=(FONT_BOLD_FAMILY, 14)).pack(pady=(15,5))
    entry_desc = ctk.CTkEntry(dialog, placeholder_text="e.g. Netflix, Salary, Groceries")
    entry_desc.insert(0, pre_desc)
    entry_desc.pack(pady=5)
    
    ctk.CTkLabel(dialog, text=f"How much? ({CURRENT_CURRENCY})", font=(FONT_BOLD_FAMILY, 14)).pack(pady=(15,5))
    entry_amt = ctk.CTkEntry(dialog, placeholder_text="0.00")
    if pre_amt: entry_amt.insert(0, str(pre_amt))
    entry_amt.pack(pady=5)

    recur_frame = ctk.CTkFrame(dialog, border_width=1, border_color="#3a3a3a", corner_radius=10)
    recur_frame.pack(fill='x', padx=20, pady=20)
    
    var_is_recur = ctk.BooleanVar(value=pre_recur)
    
    def toggle_recur():
        state = 'normal' if var_is_recur.get() else 'disabled'
        entry_int.configure(state=state)
        combo_unit.configure(state=state)
        entry_end_date.configure(state=state)

    chk_recur = ctk.CTkCheckBox(recur_frame, text="This happens repeatedly (Recurring)", variable=var_is_recur, command=toggle_recur, font=(FONT_REGULAR_FAMILY, 12))
    chk_recur.pack(pady=15)
    if edit_rule_idx is not None: chk_recur.configure(state='disabled')

    f_int = ctk.CTkFrame(recur_frame, fg_color="transparent")
    f_int.pack(pady=(0, 5))
    ctk.CTkLabel(f_int, text="Repeats Every").pack(side='left')
    entry_int = ctk.CTkEntry(f_int, width=40)
    entry_int.insert(0, pre_int)
    entry_int.pack(side='left', padx=10)
    combo_unit = ctk.CTkComboBox(f_int, values=["Days", "Weeks", "Months", "Years"], width=100)
    combo_unit.set(pre_unit)
    combo_unit.pack(side='left')
    
    ctk.CTkLabel(recur_frame, text="End Date (Optional):", font=(FONT_REGULAR_FAMILY, 11)).pack(pady=(10,0))
    entry_end_date = ctk.CTkEntry(recur_frame, placeholder_text="YYYY-MM-DD", width=120)
    if pre_end_date: entry_end_date.insert(0, pre_end_date)
    entry_end_date.pack(pady=(5, 15))

    toggle_recur() 

    def submit():
        try:
            full_date = f"{entry_date.get()} {var_h.get()}:{var_m.get()}:00"
            if not entry_amt.get(): raise ValueError("Please enter an amount.")
            
            amt = clean_amount(entry_amt.get())
            final_amt = abs(amt) if is_income else -abs(amt)
            desc = entry_desc.get() or ("Income" if is_income else "Expense")
            
            if var_is_recur.get():
                # Allow float
                try: 
                    interval = float(entry_int.get())
                except:
                    raise ValueError("Interval must be a number (decimals allowed).")
                    
                unit = combo_unit.get()
                
                end_dt_val = None
                if entry_end_date.get().strip():
                    try: end_dt_val = pd.to_datetime(entry_end_date.get())
                    except: raise ValueError("Invalid End Date format.")

                save_rule(full_date, desc, final_amt, interval, unit, end_date=end_dt_val, index_to_overwrite=edit_rule_idx)
            else:
                save_static(full_date, desc, final_amt)
            
            refresh_data()
            dialog.destroy()
        except ValueError as ve: messagebox.showwarning("Input Error", str(ve))
        except Exception as e: messagebox.showerror("System Error", str(e))

    btn_text = "Update Item" if edit_rule_idx is not None else "Save Item"
    ctk.CTkButton(dialog, text=btn_text, command=submit, fg_color="#2cc985" if is_income else "#ff4d4d", 
                  text_color="white", corner_radius=20, font=(FONT_BOLD_FAMILY, 14)).pack(pady=10)

def edit_selected_rule():
    sel = tree_recur.selection()
    if not sel: 
        messagebox.showinfo("Selection Required", "Please click on a recurring item to edit it.")
        return
    idx = tree_recur.index(sel[0])
    open_transaction_dialog(edit_rule_idx=idx)

def reset_data():
    if messagebox.askyesno("Confirm Reset", "This will delete ALL your data including transactions and recurring items. Are you sure?"):
        try:
            if os.path.exists(trans_path): os.remove(trans_path)
            if os.path.exists(recur_path): os.remove(recur_path)
            init_files()
            refresh_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset data: {str(e)}")

# --- Main App ---

root = ctk.CTk()
root.title(APP_NAME)
root.configure(fg_color='#1a1a1a')
apply_icon(root)

def on_closing():
    try:
        plt.close('all') 
        root.quit()      
        root.destroy()   
    except: pass
    finally: sys.exit(0)

def delete_selected_history():
    sel = tree_main.selection()
    if not sel: 
        messagebox.showinfo("Selection Required", "Please click on a history item to delete it.")
        return
    
    if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected history item(s)?"):
        load_data()
        indices_to_delete = [tree_main.index(item) for item in sel]
        df_static.drop(df_static.index[indices_to_delete], inplace=True)

root.protocol("WM_DELETE_WINDOW", on_closing)
root.after(200, lambda: root.state('zoomed'))

font_reg = ctk.CTkFont(family=FONT_REGULAR_FAMILY, size=13)
font_bold = ctk.CTkFont(family=FONT_BOLD_FAMILY, size=13)
font_large = ctk.CTkFont(family=FONT_BOLD_FAMILY, size=24)

# 1. Top Control Bar
ctrl_frame = ctk.CTkFrame(root, height=60, corner_radius=20)
ctrl_frame.pack(fill='x', padx=15, pady=10)

ctk.CTkButton(ctrl_frame, text="+ Add Income", command=lambda: open_transaction_dialog(True), 
              fg_color="#2cc985", hover_color="#25a870", corner_radius=20, width=120, font=font_bold).pack(side='left', padx=10, pady=10)

ctk.CTkButton(ctrl_frame, text="+ Add Spending", command=lambda: open_transaction_dialog(False), 
              fg_color="#ff4d4d", hover_color="#cc3d3d", corner_radius=20, width=120, font=font_bold).pack(side='left', padx=10, pady=10)

ctk.CTkButton(ctrl_frame, text="Reset Data", command=reset_data, fg_color="#ff9900", hover_color="#cc7a00", corner_radius=20, width=120, font=font_bold).pack(side='left', padx=10, pady=10)

# Settings
ctk.CTkLabel(ctrl_frame, text="Currency:", font=font_bold).pack(side='left', padx=(30, 5))
curr_var = ctk.StringVar(value="$")
def change_currency(val):
    global CURRENT_CURRENCY
    CURRENT_CURRENCY = val
    refresh_data()
ctk.CTkComboBox(ctrl_frame, values=CURRENCIES, variable=curr_var, command=change_currency, width=60).pack(side='left')

ctk.CTkLabel(ctrl_frame, text="Forecast Range:", font=font_bold).pack(side='left', padx=(20, 5))
proj_var = ctk.StringVar(value="1 Year")
ctk.CTkComboBox(ctrl_frame, values=["3 Months", "6 Months", "1 Year", "2 Years", "5 Years", "10 Years"], variable=proj_var, command=lambda x: refresh_data(), width=110).pack(side='left')

ctk.CTkLabel(ctrl_frame, text="Zoom Level:", font=font_bold).pack(side='left', padx=(20, 5))
scale_var = ctk.StringVar(value="1 Year")
ctk.CTkComboBox(ctrl_frame, values=["1 Month", "6 Months", "1 Year", "2 Years", "All Time"], variable=scale_var, command=lambda x: update_graph(), width=110).pack(side='left')

ctk.CTkButton(ctrl_frame, text="About", command=open_about, fg_color="transparent", border_width=1, 
              text_color="#aaaaaa", corner_radius=20, width=80).pack(side='right', padx=10)

# 2. Prediction Dashboard
pred_frame = ctk.CTkFrame(root, corner_radius=20, fg_color="#2b2b2b")
pred_frame.pack(fill='x', padx=15, pady=(0, 10))

lbl_pred_title = ctk.CTkLabel(pred_frame, text="Financial Health Forecast", font=(FONT_REGULAR_FAMILY, 12), text_color="grey")
lbl_pred_title.pack(pady=(10, 0))
lbl_pred_main = ctk.CTkLabel(pred_frame, text="Calculating...", font=font_large)
lbl_pred_main.pack(pady=5)
lbl_pred_sub = ctk.CTkLabel(pred_frame, text="...", font=(FONT_REGULAR_FAMILY, 14), text_color="#aaaaaa")
lbl_pred_sub.pack(pady=(0, 10))

# 3. Split View
content = ctk.CTkFrame(root, corner_radius=20, fg_color="transparent")
content.pack(fill='both', expand=True, padx=10, pady=5)
content.columnconfigure(0, weight=1)
content.columnconfigure(1, weight=1)
content.rowconfigure(1, weight=1)

# Left: History
f_left = ctk.CTkFrame(content, corner_radius=15, border_color="#3a3a3a", border_width=1)
f_left.grid(row=1, column=0, sticky='nsew', padx=(0,5))
f_left.rowconfigure(1, weight=1)
f_left.columnconfigure(0, weight=1)

ctk.CTkLabel(f_left, text="History (One-Time Only)", font=(FONT_BOLD_FAMILY, 16)).grid(row=0, column=0, sticky='w', padx=15, pady=10)
tree_main = ttk.Treeview(f_left, columns=('Date', 'Desc', 'Amt'), show='headings')
tree_main.heading('Date', text='Date'); tree_main.column('Date', width=100)
tree_main.heading('Desc', text='Description'); tree_main.column('Desc', width=200)
tree_main.heading('Amt', text='Amount'); tree_main.column('Amt', width=80)
tree_main.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0,10))
sc1 = ctk.CTkScrollbar(f_left, command=tree_main.yview); sc1.grid(row=1, column=1, sticky='ns', padx=(0,10), pady=(0,10)); tree_main.configure(yscrollcommand=sc1.set)

f_l_btns = ctk.CTkFrame(f_left, fg_color="transparent")
f_l_btns.grid(row=2, column=0, sticky='ew', padx=10, pady=10)
ctk.CTkButton(f_l_btns, text="Delete Selected", command=delete_selected_history, fg_color="#bf2c2c", hover_color="#992323", height=30, corner_radius=15).pack(side='left', padx=5)

# Right: Rules
f_right = ctk.CTkFrame(content, corner_radius=15, border_color="#3a3a3a", border_width=1)
f_right.grid(row=1, column=1, sticky='nsew', padx=(5,0))
f_right.rowconfigure(1, weight=1)
f_right.columnconfigure(0, weight=1)

ctk.CTkLabel(f_right, text="Recurring Bills & Income", font=(FONT_BOLD_FAMILY, 16)).grid(row=0, column=0, sticky='w', padx=15, pady=10)
tree_recur = ttk.Treeview(f_right, columns=('Date', 'Desc', 'Amt', 'Freq'), show='headings')
tree_recur.heading('Date', text='Next/Start Date'); tree_recur.column('Date', width=100)
tree_recur.heading('Desc', text='Description'); tree_recur.column('Desc', width=150)
tree_recur.heading('Amt', text='Amount'); tree_recur.column('Amt', width=80)
tree_recur.heading('Freq', text='Repeats Every'); tree_recur.column('Freq', width=100)
tree_recur.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0,5))
sc2 = ctk.CTkScrollbar(f_right, command=tree_recur.yview); sc2.grid(row=1, column=1, sticky='ns', padx=(0,10), pady=(0,5)); tree_recur.configure(yscrollcommand=sc2.set)

f_r_btns = ctk.CTkFrame(f_right, fg_color="transparent")
f_r_btns.grid(row=2, column=0, sticky='ew', padx=10, pady=10)
ctk.CTkButton(f_r_btns, text="Edit Item", command=edit_selected_rule, height=30, corner_radius=15).pack(side='left', padx=5)
ctk.CTkButton(f_r_btns, text="Stop & Archive", command=delete_rule, fg_color="#bf2c2c", hover_color="#992323", height=30, corner_radius=15).pack(side='right', padx=5)

# 4. Graph
graph_frame = ctk.CTkFrame(root, height=280, corner_radius=20)
graph_frame.pack(fill='x', padx=15, pady=10)

fig, ax = plt.subplots(figsize=(10, 3), facecolor='#2b2b2b')
canvas = FigureCanvasTkAgg(fig, master=graph_frame)
canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=(5, 0))

# Scrollbar for Graph
graph_scrollbar = ctk.CTkScrollbar(graph_frame, orientation='horizontal', height=16)
graph_scrollbar.pack(fill='x', padx=5, pady=5)

# --- Scroll Logic ---
current_scroll_pos = 1.0 # Default to end (future)

def on_scroll_graph(*args):
    global current_scroll_pos
    if args[0] == 'moveto':
        current_scroll_pos = float(args[1])
        update_graph(preserve_scroll=True)
    elif args[0] == 'scroll':
        step = int(args[1])
        current_scroll_pos = max(0.0, min(1.0, current_scroll_pos + (step * 0.05)))
        update_graph(preserve_scroll=True)

graph_scrollbar.configure(command=on_scroll_graph)

# --- Update Logic ---

def update_prediction_ui():
    if df_display.empty:
        lbl_pred_main.configure(text="No Data Available", text_color="grey")
        return

    p_text = proj_var.get()
    if "Month" in p_text:
        months = int(p_text.split()[0])
        years = months / 12.0
    else:
        try: years = int(p_text.split()[0])
        except: years = 1
    
    now = datetime.now()
    target_date = now + timedelta(days=365*years)
    
    past_mask = df_display['Date'] <= now
    if past_mask.any(): current_bal = df_display.loc[past_mask, 'Balance'].iloc[-1]
    else: current_bal = 0.0

    future_mask = df_display['Date'] <= target_date
    if future_mask.any(): final_bal = df_display.loc[future_mask, 'Balance'].iloc[-1]
    else: final_bal = current_bal

    net_change = final_bal - current_bal
    sign = "+" if net_change >= 0 else "-"
    color = "#2cc985" if net_change >= 0 else "#ff4d4d"
    
    lbl_pred_title.configure(text=f"Forecast for the next {p_text}")
    lbl_pred_main.configure(text=f"{sign}{CURRENT_CURRENCY}{abs(net_change):,.2f}", text_color=color)
    lbl_pred_sub.configure(text=f"Projected Balance: {CURRENT_CURRENCY}{final_bal:,.2f}")

def refresh_data():
    p_text = proj_var.get()
    if "Month" in p_text:
        months = int(p_text.split()[0])
        years = months / 12.0
    else:
        try: years = int(p_text.split()[0])
        except: years = 1

    generate_projection(years)
    update_lists()
    update_prediction_ui()
    update_graph(preserve_scroll=False)

def update_lists():
    for i in tree_main.get_children(): tree_main.delete(i)
    for i in tree_recur.get_children(): tree_recur.delete(i)

    if not df_static.empty:
        # Sort for display
        hist_view = df_static.sort_values('Date', ascending=False)
        
        # FIX: Iterate with index so we can map the dataframe index to the treeview iid
        for original_idx, row in hist_view.iterrows():
            vals = (str(row['Date'].date()), row['Description'], f"{CURRENT_CURRENCY}{row['Amount']:.2f}")
            # We set 'iid' to original_idx (as string) so we can retrieve it later
            tree_main.insert('', 'end', iid=str(original_idx), values=vals)

    if not df_rules.empty:
        for _, row in df_rules.iterrows():
            try: 
                ival = float(row['Interval'])
                ival_str = str(int(ival)) if ival.is_integer() else str(ival)
            except: ival_str = str(row['Interval'])

            freq_str = f"Every {ival_str} {row['Unit']}"
            if pd.notnull(row['EndDate']):
                freq_str += f" until {row['EndDate'].date()}"
            vals = (str(row['StartDate'].date()), row['Description'], f"{CURRENT_CURRENCY}{row['Amount']:.2f}", freq_str)
            tree_recur.insert('', 'end', values=vals)

def update_graph(preserve_scroll=True):
    ax.clear()
    ax.set_facecolor('#2b2b2b')
    if df_display.empty: canvas.draw(); return

    # Total Range
    min_date = df_display['Date'].min()
    max_date = df_display['Date'].max()
    total_days = (max_date - min_date).days
    if total_days <= 0: total_days = 1

    scale = scale_var.get()
    view_days = total_days
    if scale == "1 Month": view_days = 30
    elif scale == "6 Months": view_days = 180
    elif scale == "1 Year": view_days = 365
    elif scale == "2 Years": view_days = 730
    
    visible_ratio = min(1.0, view_days / total_days)
    
    global current_scroll_pos
    if not preserve_scroll:
        now = datetime.now()
        if min_date <= now <= max_date:
            days_until_now = (now - min_date).days
            current_scroll_pos = days_until_now / total_days
        else:
            current_scroll_pos = 0.0 

    max_pos = 1.0 - visible_ratio
    current_scroll_pos = max(0.0, min(max_pos, current_scroll_pos))
    
    graph_scrollbar.set(current_scroll_pos, current_scroll_pos + visible_ratio)
    
    start_offset_days = total_days * current_scroll_pos
    view_start_date = min_date + timedelta(days=start_offset_days)
    view_end_date = view_start_date + timedelta(days=view_days)
    
    df_plot = df_display
    
    dates = df_plot['Date'].to_numpy()
    balances = df_plot['Balance'].to_numpy()
    dates_num = mdates.date2num(dates)

    points = np.column_stack([dates_num, balances]).reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    
    deltas = np.diff(balances)
    cmap = ListedColormap(['#ff3333', '#2cc985'])
    norm = BoundaryNorm([-float('inf'), 0, float('inf')], cmap.N)
    lc = LineCollection(segments, cmap=cmap, norm=norm)
    lc.set_array(deltas)
    lc.set_linewidth(2)
    ax.add_collection(lc)
    
    mask_view = (df_plot['Date'] >= view_start_date) & (df_plot['Date'] <= view_end_date)
    df_view = df_plot.loc[mask_view]
    
    if not df_view.empty:
        ax.scatter(df_view['Date'], df_view['Balance'], color='#aaaaaa', s=10, zorder=3, alpha=0.6)
        
        for idx, row in df_view.iterrows():
            ax.annotate(row['Description'], 
                        (mdates.date2num(row['Date']), row['Balance']),
                        xytext=(0, 10 if idx % 2 == 0 else -15), 
                        textcoords='offset points',
                        fontsize=7, color='#888888', ha='center',
                        arrowprops=dict(arrowstyle="-", color='#444444', lw=0.5))

    ax.axvline(x=mdates.date2num(datetime.now()), color='white', linestyle=':', linewidth=1.5, alpha=0.7)

    ax.set_xlim(mdates.date2num(view_start_date), mdates.date2num(view_end_date))
    
    mask = (df_display['Date'] >= view_start_date) & (df_display['Date'] <= view_end_date)
    visible_bals = df_display.loc[mask, 'Balance']
    if not visible_bals.empty:
        y_min, y_max = visible_bals.min(), visible_bals.max()
        margin = (y_max - y_min) * 0.1 if y_max != y_min else 100
        ax.set_ylim(y_min - margin, y_max + margin)
    else:
        ax.set_ylim(balances.min(), balances.max())

    ax.fill_between(dates_num, balances, 0, where=(balances>=0), color='#2cc985', alpha=0.1)
    ax.fill_between(dates_num, balances, 0, where=(balances<0), color='#ff3333', alpha=0.1)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.tick_params(colors='#aaaaaa', labelsize=9)
    for s in ax.spines.values(): s.set_edgecolor('#404040')
    ax.set_ylabel(f"Balance ({CURRENT_CURRENCY})", color='#aaaaaa')
    ax.grid(True, color='#404040', alpha=0.3)
    fig.autofmt_xdate()
    canvas.draw()

# Styles
s = ttk.Style()
s.theme_use('clam')
s.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0, font=font_reg, rowheight=25)
s.configure("Treeview.Heading", background="#1a1a1a", foreground="white", relief="flat", font=font_bold)
s.map("Treeview", background=[('selected', '#1f538d')])

refresh_data()
root.mainloop()