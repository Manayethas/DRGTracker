import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
# Database setup and table creation
def setup_database():
    conn = sqlite3.connect('members_data.db')
    c = conn.cursor()
    # Create Members table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER UNIQUE,
            username TEXT,
            rank TEXT,
            furnace_level_start INTEGER,
            power_start REAL
        )
    ''')
    # Create ChangeLog table to track updates
    c.execute('''
        CREATE TABLE IF NOT EXISTS ChangeLog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            username TEXT,
            old_furnace_level INTEGER,
            new_furnace_level INTEGER,
            old_power REAL,
            new_power REAL,
            change_date TEXT,
            FOREIGN KEY(member_id) REFERENCES Members(member_id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()
# Function to insert a new member into the Members table
def insert_member(member_id, username, rank, furnace_level, power_start):
    try:
        conn = sqlite3.connect('members_data.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO Members (member_id, username, rank, furnace_level_start, power_start)
            VALUES (?, ?, ?, ?, ?)
        ''', (member_id, username, rank, furnace_level, power_start))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", f"Member '{username}' added successfully!")
        refresh_member_list()
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", f"Member ID '{member_id}' already exists.")
# Function to remove a member from the Members table
def remove_member(member_id):
    conn = sqlite3.connect('members_data.db')
    c = conn.cursor()
    # Check if member exists
    c.execute('SELECT username FROM Members WHERE member_id = ?', (member_id,))
    result = c.fetchone()
    if result:
        username = result[0]
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete member '{username}'?")
        if confirm:
            c.execute('DELETE FROM Members WHERE member_id = ?', (member_id,))
            # Optionally, remove related change logs
            c.execute('DELETE FROM ChangeLog WHERE member_id = ?', (member_id,))
            conn.commit()
            messagebox.showinfo("Success", f"Member '{username}' removed successfully!")
            refresh_member_list()
    else:
        messagebox.showerror("Error", f"No member found with ID '{member_id}'.")
    conn.close()
# Function to update a member's furnace level and power level
def update_member(member_id, new_furnace_level, new_power):
    conn = sqlite3.connect('members_data.db')
    c = conn.cursor()
    # Get the old values before updating
    c.execute('SELECT username, furnace_level_start, power_start FROM Members WHERE member_id = ?', (member_id,))
    result = c.fetchone()
    if result:
        username, old_furnace_level, old_power = result
        # Insert the change into the ChangeLog
        change_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO ChangeLog (member_id, username, old_furnace_level, new_furnace_level, old_power, new_power, change_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (member_id, username, old_furnace_level, new_furnace_level, old_power, new_power, change_date))
        # Update the Members table
        c.execute('''
            UPDATE Members
            SET furnace_level_start = ?, power_start = ?
            WHERE member_id = ?
        ''', (new_furnace_level, new_power, member_id))
        conn.commit()
        messagebox.showinfo("Success", f"Member '{username}' updated successfully!")
        refresh_member_list()
    else:
        messagebox.showerror("Error", f"No member found with ID '{member_id}'.")
    conn.close()
# Function to generate a report of all changes in the ChangeLog
def generate_change_report():
    conn = sqlite3.connect('members_data.db')
    c = conn.cursor()
    # Fetch change log
    c.execute('SELECT * FROM ChangeLog ORDER BY change_date DESC')
    changes = c.fetchall()
    # Display report in a new window
    report_window = tk.Toplevel(root)
    report_window.title("Change Report")
    columns = ("ID", "Member ID", "Username", "Old Furnace", "New Furnace", "Old Power", "New Power", "Date")
    tree = ttk.Treeview(report_window, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    tree.pack(fill=tk.BOTH, expand=True)
    for change in changes:
        tree.insert('', tk.END, values=change)
    conn.close()
# Function to fetch and display existing members in the Treeview
def refresh_member_list():
    for item in tree_members.get_children():
        tree_members.delete(item)
    conn = sqlite3.connect('members_data.db')
    c = conn.cursor()
    c.execute('SELECT member_id, username, rank, furnace_level_start, power_start FROM Members ORDER BY username ASC')
    members = c.fetchall()
    for member in members:
        tree_members.insert('', tk.END, values=member)
    conn.close()
# GUI setup for adding and removing members
def add_member_gui():
    member_id = entry_id.get().strip()
    username = entry_username.get().strip()
    rank = entry_rank.get().strip()
    furnace_level = entry_furnace.get().strip()
    power_level = entry_power.get().strip()
    # Input validation
    if not (member_id and username and rank and furnace_level and power_level):
        messagebox.showerror("Error", "All fields are required.")
        return
    try:
        member_id = int(member_id)
        furnace_level = int(furnace_level)
        power_level = float(power_level.replace('M', '').replace(',', ''))
    except ValueError:
        messagebox.showerror("Error", "Please enter valid numeric values for Member ID, Furnace Level, and Power Level.")
        return
    # Insert into the database
    insert_member(member_id, username, rank, furnace_level, power_level)
    # Clear the input fields
    entry_id.delete(0, tk.END)
    entry_username.delete(0, tk.END)
    entry_rank.delete(0, tk.END)
    entry_furnace.delete(0, tk.END)
    entry_power.delete(0, tk.END)
def delete_selected_member():
    selected_item = tree_members.selection()
    if not selected_item:
        messagebox.showerror("Error", "No member selected.")
        return
    member = tree_members.item(selected_item)
    member_id = member['values'][0]
    remove_member(member_id)
# Setup the database when the program runs
setup_database()
# Create the main window for the GUI
root = tk.Tk()
root.title("Member Data Management")
root.geometry("800x600")
# Frame for adding members
frame_add = tk.LabelFrame(root, text="Add New Member", padx=10, pady=10)
frame_add.pack(fill="x", padx=10, pady=5)
# Create form fields for adding members
tk.Label(frame_add, text="Member ID").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
tk.Label(frame_add, text="Username").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
tk.Label(frame_add, text="Rank").grid(row=2, column=0, padx=5, pady=5, sticky=tk.E)
tk.Label(frame_add, text="Furnace Level").grid(row=3, column=0, padx=5, pady=5, sticky=tk.E)
tk.Label(frame_add, text="Power Level (e.g., 16400000)").grid(row=4, column=0, padx=5, pady=5, sticky=tk.E)
entry_id = tk.Entry(frame_add)
entry_username = tk.Entry(frame_add)
entry_rank = tk.Entry(frame_add)
entry_furnace = tk.Entry(frame_add)
entry_power = tk.Entry(frame_add)
entry_id.grid(row=0, column=1, padx=5, pady=5)
entry_username.grid(row=1, column=1, padx=5, pady=5)
entry_rank.grid(row=2, column=1, padx=5, pady=5)
entry_furnace.grid(row=3, column=1, padx=5, pady=5)
entry_power.grid(row=4, column=1, padx=5, pady=5)
# Add button to submit the form
btn_add = tk.Button(frame_add, text="Add Member", command=add_member_gui)
btn_add.grid(row=5, column=0, columnspan=2, pady=10)
# Frame for member list and actions
frame_list = tk.LabelFrame(root, text="Existing Members", padx=10, pady=10)
frame_list.pack(fill="both", expand=True, padx=10, pady=5)
# Treeview to display members
columns = ("Member ID", "Username", "Rank", "Furnace Level", "Power Level")
tree_members = ttk.Treeview(frame_list, columns=columns, show='headings')
for col in columns:
    tree_members.heading(col, text=col)
    tree_members.column(col, width=150)
tree_members.pack(fill="both", expand=True, side=tk.LEFT)
# Scrollbar for the Treeview
scrollbar = ttk.Scrollbar(frame_list, orient=tk.VERTICAL, command=tree_members.yview)
tree_members.configure(yscroll=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
# Frame for action buttons
frame_actions = tk.Frame(root, padx=10, pady=10)
frame_actions.pack(fill="x", padx=10, pady=5)
# Button to delete selected member
btn_delete = tk.Button(frame_actions, text="Delete Selected Member", command=delete_selected_member, bg="red", fg="white")
btn_delete.pack(side=tk.LEFT, padx=5)
# Button to generate change report
btn_report = tk.Button(frame_actions, text="Generate Change Report", command=generate_change_report)
btn_report.pack(side=tk.LEFT, padx=5)
# Initial population of the member list
refresh_member_list()
# Run the GUI
root.mainloop()
