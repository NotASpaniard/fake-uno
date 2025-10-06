from gui import UnoGUI
import tkinter as tk


if __name__ == '__main__':
    names = ['You', 'Bot A', 'Bot B', 'Bot C']
    root = tk.Tk()
    app = UnoGUI(root, names)
    root.mainloop()