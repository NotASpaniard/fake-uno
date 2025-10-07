import tkinter as tk
from tkinter import messagebox, filedialog
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

        # resize handling
        self.canvas.bind('<Configure>', self.on_resize)

        # Game logic
        self.deck = Deck()
        self.players = [Player(name, is_human=(i == 0)) for i, name in enumerate(player_names)]
        for p in self.players:
            p.draw(self.deck, 7)
        self.discard_pile = [self.deck.draw()]
        self.direction = 1
        self.current = 0
        # UNO state
        self.human_uno_called = False
        self.pending_uno_penalty_index = None

        # UI state defaults (will be recalculated in draw_table)
        self.center = (self.width // 2, self.height // 2)
        self.table_radius = 260
        self.card_width = 80
        self.card_height = 120
        # place deck near the top-left edge of the table circle
        self.deck_pos = (self.center[0] - int(self.table_radius * 0.6), self.center[1] - int(self.table_radius * 0.85))
        # discard sits near top-center of the table
        self.discard_pos = (self.center[0], self.center[1] - self.table_radius - 40)
        # cache player area centers (bottom human, left bot, top bot, right bot)
        self.player_positions = []
        # avatar images (tk.PhotoImage) keyed by player index
        self.avatar_images = {}

        # user interaction bindings
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<Motion>', self.on_mouse_move)
        self.canvas.bind('<Double-Button-1>', self.on_double_click)

        # selection/hover state
        self.selected_index = None
        self.hover_index = None

        # initial draw and AI scheduling
        self.draw_table()
        self.root.after(500, self.ai_turn_if_needed)

    def draw_table(self):
        self.canvas.delete('all')
        # chỉnh cửa sổ
        w = max(self.canvas.winfo_width(), 200)
        h = max(self.canvas.winfo_height(), 200)
        self.width = w
        self.height = h
        # đẩy bàn chơi lên trên để các avatar và tay bài không bị che
        self.center = (w//2, max(140, h//2 - 60))
        # make the table a bit smaller so avatars/labels don't get clipped
        self.table_radius = max(100, min(w, h)//2 - 160)
        self.card_width = max(60, min(110, self.table_radius//3))
        self.card_height = int(self.card_width * 1.6)
        # recompute deck to stick to bottom-right corner of the canvas (inside margin)
        margin = 24
        self.deck_pos = (self.width - margin - self.card_width//2, self.height - margin - self.card_height//2)
        self.discard_pos = (self.center[0], self.center[1] - self.table_radius - 40)

        # bàn
        x, y = self.center
        self.canvas.create_oval(x - self.table_radius, y - self.table_radius,
                                x + self.table_radius, y + self.table_radius,
                                fill='#1e3b2b', outline='')

        # fixed player positions (bottom human, left bot, top bot, right bot)
        # ensure we have four players
        while len(self.players) < 4:
            self.players.append(Player(f'Bot {len(self.players)+1}'))
        pp_bottom = (x, y + self.table_radius + 60)
        pp_left = (x - self.table_radius - 90, y)
        pp_top = (x, y - self.table_radius - 60)
        pp_right = (x + self.table_radius + 90, y)
        self.player_positions = [pp_bottom, pp_left, pp_top, pp_right]
        avatar_w, avatar_h = 110, 48
        for i, player in enumerate(self.players):
            px, py = self.player_positions[i]
            # clamp so avatars stay visible inside canvas
            margin = 12
            px = max(margin + avatar_w//2, min(self.width - margin - avatar_w//2, px))
            py = max(margin + avatar_h//2, min(self.height - margin - avatar_h//2, py))
            # avatar frame (clickable)
            self.canvas.create_rectangle(px - avatar_w//2, py - avatar_h//2, px + avatar_w//2, py + avatar_h//2,
                                         fill='#222', outline='white', tags=(f'avatar_{i}',))
            # draw avatar image if set, otherwise placeholder text
            img = self.avatar_images.get(i)
            if img:
                # image is centered on avatar
                self.canvas.create_image(px, py, image=img, tags=(f'avatar_img_{i}',))
            else:
                # placeholder: small inner rect and 'No Img' label
                self.canvas.create_rectangle(px - 28, py - 14, px + 28, py + 14, fill='#121212', outline='white')
                self.canvas.create_text(px, py, text='No Img', fill='white', font=('Helvetica', 9), tags=(f'avatar_{i}',))
            # name label
            self.canvas.create_text(px, py - avatar_h//2 - 8, text=player.name, fill='white', font=('Helvetica', 11, 'bold'), tags=(f'avatar_{i}',))
            # card count for bots
            if not player.is_human:
                self.canvas.create_text(px, py + avatar_h//2 + 6, text=f'Cards: {len(player.hand)}', fill='white', tags=(f'avatar_{i}',))
            # highlight current player
            if i == self.current:
                self.canvas.create_oval(px - avatar_w//2 - 6, py - avatar_h//2 - 6, px + avatar_w//2 + 6, py + avatar_h//2 + 6,
                                       outline='yellow', width=3)

        # rút lá và huỷ
        self.draw_deck()
        self.draw_discard()

        # mô tả bài
        self.draw_card_description()

        # thông tin lượt và chiều
        try:
            arrow = '↻' if self.direction == 1 else '↺'
            turn_text = f"Turn: {self.players[self.current].name}  {arrow}"
            self.canvas.create_text(self.center[0], self.center[1] + self.table_radius + 28,
                                    text=turn_text, fill='white', font=('Helvetica', 12, 'bold'))
        except Exception:
            pass

        # draw human hand at bottom each frame
        try:
            self.draw_hand(self.players[0])
            # đảm bảo avatar và điều khiển nổi trên tay bài
            for i in range(len(self.players)):
                self.canvas.tag_raise(f'avatar_{i}')
                self.canvas.tag_raise(f'avatar_img_{i}')
            self.canvas.tag_raise('rename_btn')
            self.canvas.tag_raise('uno_btn')
        except Exception:
            pass

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

        # UNO button
        ubx = bx
        uby = by + 30
        uno_fill = '#2d5' if self.human_uno_called else '#333'
        self.canvas.create_rectangle(ubx-2, uby-12, ubx+82, uby+12, fill=uno_fill, outline='white', tags=('uno_btn',))
        self.canvas.create_text(ubx+40, uby, text='UNO!', fill='white', tags=('uno_btn',))

    def draw_discard(self):
        # show the top discarded card in the center of the table
        x, y = self.center
        top = self.discard_pile[-1]
        color = self.tk_color_for(top.color)
        w = int(self.card_width * 1.2)
        h = int(self.card_height * 1.2)
        # card shape with rounded corners look: layered rectangles
        self.canvas.create_rectangle(x - w//2, y - h//2, x + w//2, y + h//2, fill='#111', outline='white', width=1)
        self.canvas.create_rectangle(x - w//2 + 4, y - h//2 + 4, x + w//2 - 4, y + h//2 - 4, fill=color, outline='white', width=2)
        # show only value/function + color label
        display_text = getattr(top, 'value', str(top))
        self.canvas.create_text(x, y, text=display_text, fill='white', font=('Helvetica', 16, 'bold'))
        color_label = 'Any' if getattr(top, 'color', None) is None else top.color
        self.canvas.create_text(x, y + h//2 + 12, text=f'Color: {color_label}', fill='white')

    def draw_hand(self, player):
        # rút bài
        margin = 20
        start_x = margin
        y = self.height - self.card_height/2 - 30
        # compute spacing to center hand if many cards
        total_w = max(0, len(player.hand)-1) * (self.card_width - 30) + self.card_width
        start_x = max(margin, (self.width - total_w)//2)
        top = self.discard_pile[-1]
        is_human_turn = (self.players[self.current].is_human if self.players else False)
        for i, card in enumerate(player.hand):
            # if hovering over an index, slightly separate neighbors
            base_x = start_x + i * (self.card_width - 30)
            x = base_x
            if self.hover_index is not None and self.hover_index == i:
                # bring hovered card slightly up (visual)
                hy_offset = -12
            else:
                hy_offset = 0
            # spread others away a bit when hovering
            if self.hover_index is not None and self.hover_index != i:
                # push card left or right depending on side
                dir_sign = 1 if i > self.hover_index else -1
                x += dir_sign * 8
            color = self.tk_color_for(card.color)
            tag = f'hand_{i}'
            # layered look for each card
            self.canvas.create_rectangle(x - self.card_width/2, y - self.card_height/2,
                                         x + self.card_width/2, y + self.card_height/2,
                                         fill='#111', outline='white', tags=(tag, 'hand'))
            self.canvas.create_rectangle(x - self.card_width/2 + 3, y - self.card_height/2 + 3,
                                         x + self.card_width/2 - 3, y + self.card_height/2 - 3,
                                         fill=color, outline='white', tags=(tag, 'hand'))
            # hiển thị giá trị và nhãn màu
            value_text = getattr(card, 'value', str(card))
            self.canvas.create_text(x, y+hy_offset-8, text=value_text, fill='white', font=('Helvetica', 12, 'bold'), tags=(tag,))
            color_label = 'Wild' if getattr(card, 'color', None) is None else getattr(card, 'color', 'Any')
            self.canvas.create_text(x, y+hy_offset+10, text=color_label, fill='#eeeeee', font=('Helvetica', 9), tags=(tag,))
            # highlight lá hợp lệ nếu là lượt của người chơi
            playable = (card.color == getattr(top, 'color', None) or
                        getattr(card, 'value', None) == getattr(top, 'value', None) or
                        getattr(card, 'color', None) is None)
            if is_human_turn and playable:
                self.canvas.create_rectangle(x - self.card_width/2 - 3, y - self.card_height/2 - 3,
                                             x + self.card_width/2 + 3, y + self.card_height/2 + 3,
                                             outline='#00e0ff', width=2)
            if self.selected_index == i:
                self.canvas.create_rectangle(x - self.card_width/2 - 4, y - self.card_height/2 - 4,
                                             x + self.card_width/2 + 4, y + self.card_height/2 + 4,
                                             outline='yellow', width=3)

    def on_mouse_move(self, event):
        # update hover_index based on mouse x/y near hand area
        margin = 20
        hy = self.height - self.card_height/2 - 30
        if not (hy - self.card_height/2 - 10 <= event.y <= hy + self.card_height/2 + 10):
            if self.hover_index is not None:
                self.hover_index = None
                self.draw_table()
            return
        # compute start_x as in draw_hand
        total_w = max(0, len(self.players[0].hand)-1) * (self.card_width - 30) + self.card_width
        start_x = max(margin, (self.width - total_w)//2)
        # determine index
        idx = None
        for i in range(len(self.players[0].hand)):
            x = start_x + i * (self.card_width - 30)
            if x - self.card_width/2 - 6 <= event.x <= x + self.card_width/2 + 6:
                idx = i
                break
        if idx != self.hover_index:
            self.hover_index = idx
            self.draw_table()

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

    def get_human_card_pos(self, index):
        # compute current human hand card center position for given index
        margin = 20
        total_w = max(0, len(self.players[0].hand)-1) * (self.card_width - 30) + self.card_width
        start_x = max(margin, (self.width - total_w)//2)
        x = start_x + index * (self.card_width - 30)
        y = self.height - self.card_height/2 - 30
        return (x, y)

    def tk_color_for(self, color):
        if color == 'Red':
            return '#d64545'
        if color == 'Yellow':
            return '#e7c000'
        if color == 'Green':
            return '#22bb33'
        if color == 'Blue':
            return '#2472c8'
        # back of card / unknown
        return '#444'

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
        # check avatar clicks (rename individual player)
        for i in range(len(self.players)):
            bbox = self.canvas.bbox(f'avatar_{i}')
            if bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                # set target and open rename dialog for that single player
                self._rename_target = i
                self.open_rename_dialog()
                return
        # check deck
        dx, dy = self.deck_pos
        if abs(x - dx) < 60 and abs(y - dy) < 80:
            # chỉ rút khi đến lượt người chơi
            if self.players[self.current].is_human:
                self.player_draw()
            return

        # kiểm tra bài trên tay
        # tính toán vị trí giống draw_hand để bắt chuẩn xác
        margin = 20
        total_w = max(0, len(self.players[0].hand)-1) * (self.card_width - 30) + self.card_width
        start_x = max(margin, (self.width - total_w)//2)
        hy = self.height - self.card_height/2 - 30
        for i, card in enumerate(self.players[0].hand):
            hx = start_x + i * (self.card_width - 30)
            if hx - self.card_width/2 < x < hx + self.card_width/2 and hy - self.card_height/2 < y < hy + self.card_height/2:
                # select or play
                if self.selected_index == i:
                    # chỉ được đánh khi đến lượt người chơi
                    if self.players[self.current].is_human:
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

        # check UNO button
        items = self.canvas.find_withtag('uno_btn')
        for it in items:
            bbox = self.canvas.bbox(it)
            if bbox and bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
                # người chơi tuyên bố UNO (sẽ có hiệu lực khi còn 1 lá)
                if self.players[self.current].is_human:
                    self.human_uno_called = True
                    self.draw_table()
                    messagebox.showinfo('UNO', 'Bạn đã sẵn sàng hô UNO!')
                return

    def on_double_click(self, event):
        # nháy đúp vào lá bài ở giữa để mở hộp đổi tên
        x, y = event.x, event.y
        cx, cy = self.center
        w = int(self.card_width * 1.2)
        h = int(self.card_height * 1.2)
        if (cx - w//2) <= x <= (cx + w//2) and (cy - h//2) <= y <= (cy + h//2):
            self.open_rename_dialog()

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

            # xử lý UNO: người chơi cần nhấn nút trước khi kết thúc lượt
            if player.has_uno():
                if player.is_human:
                    if self.human_uno_called:
                        messagebox.showinfo('UNO', f'{player.name} says UNO!')
                        self.human_uno_called = False
                        self.pending_uno_penalty_index = None
                    else:
                        # sẽ bị phạt +2 khi tới lượt kế tiếp bắt đầu
                        self.pending_uno_penalty_index = 0
                else:
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
            # nếu lá rút đánh được, tự động chọn để người chơi có thể click chơi ngay
            top = self.discard_pile[-1]
            if (card.color == getattr(top, 'color', None) or
                getattr(card, 'value', None) == getattr(top, 'value', None) or
                getattr(card, 'color', None) is None):
                self.selected_index = len(player.hand) - 1
                # người chơi có thể bấm để đánh; chưa kết thúc lượt
            else:
                self.selected_index = None
                # không đánh được -> kết thúc lượt ngay
                self.draw_table()
                self.next_player()
                self.root.after(600, self.ai_turn_if_needed)
                return
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
        sx, sy = self.get_human_card_pos(hand_index)
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
        # destination: position of the human hand slot
        player = self.players[0]
        if to_hand_index is None:
            to_index = len(player.hand)
        else:
            to_index = to_hand_index
        dx, dy = self.get_human_card_pos(to_index)
        self.animate_move((sx, sy), (dx, dy), color='#222', text='?', callback=None)

    def open_rename_dialog(self):
        # legacy support: if called with player_index, rename single player
        def _open_all():
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

        # allow external callers to pass player_index
        import inspect
        caller_args = inspect.getfullargspec(self.open_rename_dialog).args
        # We'll implement a simpler API: if caller passed player_index via attribute
        if hasattr(self, '_rename_target') and isinstance(self._rename_target, int):
            i = self._rename_target
            dlg = tk.Toplevel(self.root)
            dlg.title(f'Rename {self.players[i].name}')
            dlg.transient(self.root)
            dlg.grab_set()
            tk.Label(dlg, text=f'New name for {self.players[i].name}:').grid(row=0, column=0, padx=6, pady=6)
            e = tk.Entry(dlg)
            e.insert(0, self.players[i].name)
            e.grid(row=0, column=1, padx=6, pady=6)
            def apply_one():
                self.players[i].name = e.get() or self.players[i].name
                dlg.destroy()
                delattr(self, '_rename_target')
                self.draw_table()
            def set_avatar():
                path = filedialog.askopenfilename(title='Select avatar image', filetypes=[('Images','*.png *.gif *.ppm *.pgm')])
                if not path:
                    return
                try:
                    img = tk.PhotoImage(file=path)
                    # subsample large images so they fit avatar area
                    max_w, max_h = 100, 80
                    fw = max(1, img.width() // max_w)
                    fh = max(1, img.height() // max_h)
                    factor = max(fw, fh)
                    if factor > 1:
                        img = img.subsample(factor, factor)
                    self.avatar_images[i] = img
                    self.draw_table()
                except Exception as ex:
                    messagebox.showerror('Image error', f'Could not load image: {ex}')

            tk.Button(dlg, text='Apply', command=apply_one).grid(row=1, column=0, pady=8)
            tk.Button(dlg, text='Set Avatar', command=set_avatar).grid(row=1, column=1, pady=8)
        else:
            _open_all()

    def next_player(self):
        self.current = (self.current + self.direction) % len(self.players)

    def apply_uno_penalty_if_pending(self):
        # áp dụng phạt +2 nếu người chơi quên hô UNO
        if self.pending_uno_penalty_index is None:
            return
        idx = self.pending_uno_penalty_index
        # đảm bảo có đủ bài để rút
        if self.deck.count() < 2:
            self.reshuffle_discard_into_deck()
        # rút 2 lá cho người bị phạt
        self.players[idx].draw(self.deck, 2)
        try:
            messagebox.showinfo('UNO penalty', f"{self.players[idx].name} quên hô UNO: +2")
        except Exception:
            pass
        self.pending_uno_penalty_index = None
        if idx == 0:
            self.human_uno_called = False

    def ai_turn_if_needed(self):
        # áp dụng phạt UNO (nếu có) trước khi người kế tiếp hành động
        self.apply_uno_penalty_if_pending()
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
            # không có lá hợp lệ, rút 1 lá và chơi nếu có thể
            if self.deck.count() == 0:
                self.reshuffle_discard_into_deck()
            drawn = self.deck.draw()
            if drawn is not None:
                # nếu wild, sẽ chọn màu khi chơi
                can_play = (drawn.color == top.color or drawn.value == top.value or drawn.color is None)
                if can_play:
                    if drawn.color is None and drawn.value in ('Wild', 'Wild Draw Four'):
                        drawn.color = random.choice(COLORS)
                    self.discard_pile.append(drawn)
                    if drawn.value == 'Reverse':
                        self.direction *= -1
                    elif drawn.value == 'Skip':
                        self.next_player()
                    elif drawn.value == 'Draw Two':
                        self.next_player()
                        self.players[self.current].draw(self.deck, 2)
                    elif drawn.value == 'Wild Draw Four':
                        self.next_player()
                        self.players[self.current].draw(self.deck, 4)
                    if player.has_uno():
                        print(f'{player.name} says UNO!')
                    if player.is_winner():
                        messagebox.showinfo('Winner', f'{player.name} wins!')
                        self.root.quit()
                else:
                    # không chơi được -> thêm vào tay
                    player.hand.append(drawn)
            else:
                # không còn bài để rút
                pass
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
