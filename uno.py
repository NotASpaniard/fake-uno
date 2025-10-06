from gui import UnoGUI
import tkinter as tk


if __name__ == '__main__':
    names = ['You', 'Thành', 'Đức Anh ', 'Vũ']
    root = tk.Tk()
    app = UnoGUI(root, names)
    root.mainloop()