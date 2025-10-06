import tkinter as tk
from tkinter import messagebox
import math
import random
from game import Deck, Player, COLORS


class UnoGUI:
    def __init__(self, root, player_names):
        self.root = root
        self.root.title('UNO - Round Table')
        self.width = 900
        self.height = 700
        self.canvas = tk.Canvas(root, width=self.width, height=self.height, bg='#2b2b2b')
        self.canvas.pack(fill='both', expand=True)

        # chỉnh kích cỡ cửa sổ
        self.canvas.bind('<Configure>', self.on_resize)

        # Game logic
        self.deck = Deck()
        self.players = [Player(name, is_human=(i == 0)) for i, name in enumerate(player_names)]
        for p in self.players:
            p.draw(self.deck, 7)
        self.discard_pile = [self.deck.draw()]
        self.direction = 1
        self.current = 0

        # UI
        self.center = (self.width//2, self.height//2)
        self.table_radius = 260
        self.card_width = 80
        self.card_height = 120
        self.deck_pos = (self.center[0], self.center[1] - self.table_radius - 40)
        self.discard_pos = (self.center[0] + 120, self.center[1] - self.table_radius - 40)

        # bốc bài
        self.canvas.bind('<Button-1>', self.on_click)

        # chọn lá để xem
        self.selected_index = None

        self.draw_table()
        self.root.after(500, self.ai_turn_if_needed)

    def draw_table(self):
        self.canvas.delete('all')
        # chỉnh cửa sổ
        w = max(self.canvas.winfo_width(), 200)
        h = max(self.canvas.winfo_height(), 200)
        self.width = w
        self.height = h
        self.center = (w//2, h//2)
        self.table_radius = max(100, min(w, h)//2 - 160)
        self.card_width = max(60, min(110, self.table_radius//3))
        self.card_height = int(self.card_width * 1.6)
        self.deck_pos = (self.center[0], self.center[1] - self.table_radius - 40)
        self.discard_pos = (self.center[0] + int(self.table_radius*0.25), self.center[1] - self.table_radius - 40)

        # bàn
        x, y = self.center
        self.canvas.create_oval(x - self.table_radius, y - self.table_radius,
                                x + self.table_radius, y + self.table_radius,
                                fill='#1e3b2b', outline='')

        # khu vực chơi của 4 người chơi
        n = len(self.players)
        for i, player in enumerate(self.players):
            angle = (i / n) * 2 * math.pi - math.pi/2
            px = x + math.cos(angle) * (self.table_radius + 70)
            py = y + math.sin(angle) * (self.table_radius + 40)
            # tên
            self.canvas.create_text(px, py - 30, text=player.name, fill='white', font=('Helvetica', 12, 'bold'))
            # highlight current player with yellow ring
            if i == self.current:
                self.canvas.create_oval(px - 44, py - 54, px + 44, py + 6, outline='yellow', width=3)
            # rút hoặc đếm cho AI
            if player.is_human:
                # rút
                self.draw_hand(player)
            else:
                self.canvas.create_rectangle(px - 30, py - 10, px + 30, py + 10, fill='#444', outline='white')
                self.canvas.create_text(px, py, text=str(len(player.hand)), fill='white')

        # rút lá và huỷ
        self.draw_deck()
        self.draw_discard()

        # mô tả bài
        self.draw_card_description()

    def draw_deck(self):
        x, y = self.deck_pos
        # chồng bài
        count = self.deck.count()
        for i in range(min(6, count)):
            offset = i * 1.5
            self.canvas.create_rectangle(x - self.card_width/2 + offset, y - self.card_height/2 + offset,
                                         x + self.card_width/2 + offset, y + self.card_height/2 + offset,
                                         fill='#222', outline='white', tags=('deck',))
        self.canvas.create_text(x, y + self.card_height/2 + 10, text=f'Deck: {count}', fill='white')
        # rename button near deck
        bx = x - 40
        by = y + self.card_height/2 + 30
        self.canvas.create_rectangle(bx-2, by-12, bx+82, by+12, fill='#333', outline='white', tags=('rename_btn',))
        self.canvas.create_text(bx+40, by, text='Rename', fill='white', tags=('rename_btn',))

    def draw_discard(self):
        # show the top discarded card in the center of the table
        x, y = self.center
        top = self.discard_pile[-1]
        color = self.tk_color_for(top.color)
        w = int(self.card_width * 1.2)
        h = int(self.card_height * 1.2)
        self.canvas.create_rectangle(x - w//2, y - h//2, x + w//2, y + h//2, fill=color, outline='white', width=2)
        # show only value/function
        display_text = getattr(top, 'value', str(top))
        self.canvas.create_text(x, y, text=display_text, fill='white', font=('Helvetica', 14, 'bold'))
        if top.color is not None and display_text in ('Wild', 'Wild Draw Four'):
            # show chosen color name below the card
            self.canvas.create_text(x, y + h//2 + 12, text=f'Color: {top.color}', fill='white')
        else:
            self.canvas.create_text(x, y + h//2 + 12, text='Discard', fill='white')

    def draw_hand(self, player):
        # rút bài
        margin = 20
        start_x = margin
        y = self.height - self.card_height/2 - 30
        for i, card in enumerate(player.hand):
            x = start_x + i * (self.card_width - 30)
            color = self.tk_color_for(card.color)
            tag = f'hand_{i}'
            self.canvas.create_rectangle(x - self.card_width/2, y - self.card_height/2,
                                         x + self.card_width/2, y + self.card_height/2,
                                         fill=color, outline='white', tags=(tag, 'hand'))
            # hiển thị giá trị
            value_text = getattr(card, 'value', str(card))
            self.canvas.create_text(x, y, text=value_text, fill='white', tags=(tag,))
            if self.selected_index == i:
                self.canvas.create_rectangle(x - self.card_width/2 - 4, y - self.card_height/2 - 4,
                                             x + self.card_width/2 + 4, y + self.card_height/2 + 4,
                                             outline='yellow', width=3)

    def on_resize(self, event):
        # chỉnh kích cỡ thu phóng cửa sổ
        try:
            self.width = event.width
            self.height = event.height
        except Exception:
            self.width = max(self.canvas.winfo_width(), self.width)
            self.height = max(self.canvas.winfo_height(), self.height)
        self.draw_table()

    def draw_card_description(self):
        # panel
        w = 260
        h = 140
        x = self.width - w - 20
        y = self.height - h - 20
        self.canvas.create_rectangle(x, y, x + w, y + h, fill='#111', outline='white')
        self.canvas.create_text(x + 10, y + 10, anchor='nw', text='Card Info', fill='white', font=('Helvetica', 12, 'bold'))
        if self.selected_index is not None and len(self.players[0].hand) > self.selected_index:
            c = self.players[0].hand[self.selected_index]
            self.canvas.create_text(x + 10, y + 40, anchor='nw', text=f'Name: {str(c)}', fill='white')
            desc = self.describe_card(c)
            self.canvas.create_text(x + 10, y + 70, anchor='nw', text=desc, fill='white', width=w-20)
        else:
            self.canvas.create_text(x + 10, y + 40, anchor='nw', text='Select a card to see details', fill='white')

    def tk_color_for(self, color):
        if color == 'Pink':
            return '#ff77aa'
        if color == 'Black':
            return '#222222'
        if color == 'Teal':
            return '#00b3b3'
        if color == 'Green':
            return '#22bb33'
        return '#666'

    def describe_card(self, card):
        if card.color is None:
            if card.value == 'Wild':
                return 'Wild: choose any color when played.'
            if card.value == 'Wild Draw Four':
                return 'Wild Draw Four: choose color and next player draws 4.'
        if card.value == 'Skip':
            return 'Skip: next player is skipped.'
        if card.value == 'Reverse':
            return 'Reverse: reverses play direction.'
        if card.value == 'Draw Two':
            return 'Draw Two: next player draws 2 cards.'
        return f'Number card: {card.value}.'

    def on_click(self, event):
        x, y = event.x, event.y
        # kiểm tra bộ 
        dx, dy = self.deck_pos
        if abs(x - dx) < 60 and abs(y - dy) < 80:
            # clicking deck - animate draw from deck to hand
            self.animate_draw_from_deck()
            return

        # kiểm tra bài trên tay
        # tối ưu hoá vị trí vẽ bài
        margin = 20
        start_x = margin
        hy = self.height - self.card_height/2 - 30
        for i, card in enumerate(self.players[0].hand):
            hx = start_x + i * (self.card_width - 30)
            if hx - self.card_width/2 < x < hx + self.card_width/2 and hy - self.card_height/2 < y < hy + self.card_height/2:
                # select or play
                if self.selected_index == i:
                    # animate playing from hand to center then apply play
                    self.animate_play_from_hand(i)
                else:
                    self.selected_index = i
                    self.draw_table()
                return

        # check rename button
        items = self.canvas.find_withtag('rename_btn')
        for it in items:
            bbox = self.canvas.bbox(it)
            if bbox and bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
                self.open_rename_dialog()
                return

    def ask_color_choice(self):
        # modal dialog to choose a color for Wild cards
        dlg = tk.Toplevel(self.root)
        dlg.title('Choose color')
        dlg.transient(self.root)
        dlg.grab_set()
        choice = {'color': None}

        def pick(c):
            choice['color'] = c
            dlg.destroy()

        tk.Label(dlg, text='Choose color for Wild:', font=('Helvetica', 12)).pack(padx=10, pady=8)
        frm = tk.Frame(dlg)
        frm.pack(padx=10, pady=8)
        for c in COLORS:
            b = tk.Button(frm, text=c, bg=self.tk_color_for(c), command=lambda cc=c: pick(cc), width=10)
            b.pack(side='left', padx=4)

        self.root.wait_window(dlg)
        return choice['color']

    def attempt_play(self, index):
        player = self.players[0]
        card = player.hand[index]
        top = self.discard_pile[-1]
        if (card.color == top.color or card.value == top.value or card.color is None):
            played = player.hand.pop(index)
            # if human plays a wild, ask for color
            if played.color is None and played.value in ('Wild', 'Wild Draw Four') and player.is_human:
                chosen = self.ask_color_choice()
                if chosen:
                    played.color = chosen
            self.discard_pile.append(played)
            self.selected_index = None
            # hiệu ứng
            if played.value == 'Reverse':
                self.direction *= -1
            elif played.value == 'Skip':
                self.next_player()
            elif played.value == 'Draw Two':
                self.next_player()
                self.players[self.current].draw(self.deck, 2)
            elif played.value == 'Wild Draw Four':
                self.next_player()
                self.players[self.current].draw(self.deck, 4)

            if player.has_uno():
                messagebox.showinfo('UNO', f'{player.name} says UNO!')
            if player.is_winner():
                messagebox.showinfo('Winner', f'{player.name} wins!')
                self.root.quit()
            self.next_player()
            self.draw_table()
            self.root.after(400, self.ai_turn_if_needed)
        else:
            messagebox.showinfo('Cannot play', 'This card cannot be played on the top card.')

    def player_draw(self):
        player = self.players[0]
        if self.deck.count() == 0:
            self.reshuffle_discard_into_deck()
        card = self.deck.draw()
        if card:
            # animate deck->hand then add
            self.animate_draw_from_deck(to_hand_index=len(player.hand))
            player.hand.append(card)
            self.selected_index = len(player.hand) - 1
            self.draw_table()
        else:
            messagebox.showinfo('Deck empty', 'No cards to draw.')

    def animate_move(self, src, dst, color='#fff', text='', steps=12, callback=None):
        # src/dst are (x,y) centers. Draw a temporary rect and move it.
        sx, sy = src
        dx, dy = dst
        rect = self.canvas.create_rectangle(sx-20, sy-30, sx+20, sy+30, fill=color, outline='white')
        label = self.canvas.create_text(sx, sy, text=text, fill='white')
        def step(i):
            t = (i+1)/steps
            nx = sx + (dx-sx)*t
            ny = sy + (dy-sy)*t
            self.canvas.coords(rect, nx-20, ny-30, nx+20, ny+30)
            self.canvas.coords(label, nx, ny)
            if i+1 < steps:
                self.root.after(16, lambda: step(i+1))
            else:
                self.canvas.delete(rect)
                self.canvas.delete(label)
                if callback:
                    callback()
        step(0)

    def animate_play_from_hand(self, hand_index):
        # compute hand card pos
        margin = 20
        start_x = margin
        hy = self.height - self.card_height/2 - 30
        sx = start_x + hand_index * (self.card_width - 30)
        sy = hy
        tx, ty = self.center
        player = self.players[0]
        if hand_index < len(player.hand):
            card = player.hand[hand_index]
            text = getattr(card, 'value', str(card))
            color = self.tk_color_for(card.color)
            # after animation, actually play
            def after():
                # ensure index is valid (player may have drawn in meantime)
                if hand_index < len(self.players[0].hand):
                    self.attempt_play(hand_index)
            self.animate_move((sx, sy), (tx, ty), color=color, text=text, callback=after)

    def animate_draw_from_deck(self, to_hand_index=None):
        sx, sy = self.deck_pos
        # destination: approximate end of hand (if to_hand_index given) else center-bottom
        margin = 20
        if to_hand_index is None:
            dx = margin + 0 * (self.card_width - 30)
        else:
            dx = margin + to_hand_index * (self.card_width - 30)
        dy = self.height - self.card_height/2 - 30
        self.animate_move((sx, sy), (dx, dy), color='#222', text='?', callback=None)

    def open_rename_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title('Rename players')
        dlg.transient(self.root)
        dlg.grab_set()
        entries = []
        for i, p in enumerate(self.players):
            tk.Label(dlg, text=f'Player {i+1}:').grid(row=i, column=0, padx=6, pady=6)
            e = tk.Entry(dlg)
            e.insert(0, p.name)
            e.grid(row=i, column=1, padx=6, pady=6)
            entries.append(e)
        def apply_names():
            for i, e in enumerate(entries):
                self.players[i].name = e.get() or self.players[i].name
            dlg.destroy()
            self.draw_table()
        tk.Button(dlg, text='Apply', command=apply_names).grid(row=len(entries), column=0, columnspan=2, pady=8)

    def next_player(self):
        self.current = (self.current + self.direction) % len(self.players)

    def ai_turn_if_needed(self):
        # nếu người chơi hiện tại là AI
        if self.players[self.current].is_human:
            return
        player = self.players[self.current]
        top = self.discard_pile[-1]
        card = player.play(top)
        if card:
            # if AI plays a wild, pick a random color for it
            if card.color is None and card.value in ('Wild', 'Wild Draw Four'):
                card.color = random.choice(COLORS)
            self.discard_pile.append(card)
            # hiệu ứng đơn giản
            if card.value == 'Reverse':
                self.direction *= -1
            elif card.value == 'Skip':
                self.next_player()
            elif card.value == 'Draw Two':
                self.next_player()
                self.players[self.current].draw(self.deck, 2)
            elif card.value == 'Wild Draw Four':
                self.next_player()
                self.players[self.current].draw(self.deck, 4)
            if player.has_uno():
                print(f'{player.name} says UNO!')
            if player.is_winner():
                messagebox.showinfo('Winner', f'{player.name} wins!')
                self.root.quit()
        else:
            if self.deck.count() == 0:
                self.reshuffle_discard_into_deck()
            player.draw(self.deck)
        self.next_player()
        self.draw_table()
        # thiết lập nước đi của AI 
        self.root.after(600, self.ai_turn_if_needed)

    def reshuffle_discard_into_deck(self):
        if len(self.discard_pile) <= 1:
            return
        top = self.discard_pile.pop()
        self.deck.cards = self.discard_pile[:]
        random.shuffle(self.deck.cards)
        self.discard_pile = [top]
