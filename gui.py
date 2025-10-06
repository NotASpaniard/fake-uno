import tkinter as tk
from tkinter import messagebox
import math
import random
from game import Deck, Player


class UnoGUI:
    def __init__(self, root, player_names):
        self.root = root
        self.root.title('UNO - Round Table')
        self.width = 900
        self.height = 700
        self.canvas = tk.Canvas(root, width=self.width, height=self.height, bg='#2b2b2b')
        self.canvas.pack(fill='both', expand=True)

        # Game logic
        self.deck = Deck()
        self.players = [Player(name, is_human=(i == 0)) for i, name in enumerate(player_names)]
        for p in self.players:
            p.draw(self.deck, 7)
        self.discard_pile = [self.deck.draw()]
        self.direction = 1
        self.current = 0

        # UI state
        self.center = (self.width//2, self.height//2)
        self.table_radius = 260
        self.card_width = 80
        self.card_height = 120
        self.deck_pos = (self.center[0], self.center[1] - self.table_radius - 40)
        self.discard_pos = (self.center[0] + 120, self.center[1] - self.table_radius - 40)

        # Bind deck click
        self.canvas.bind('<Button-1>', self.on_click)

        # Selected card for viewing/playing
        self.selected_index = None

        self.draw_table()
        self.root.after(500, self.ai_turn_if_needed)

    def draw_table(self):
        self.canvas.delete('all')
        # draw round table
        x, y = self.center
        self.canvas.create_oval(x - self.table_radius, y - self.table_radius,
                                x + self.table_radius, y + self.table_radius,
                                fill='#1e3b2b', outline='')

        # draw four player areas
        n = len(self.players)
        for i, player in enumerate(self.players):
            angle = (i / n) * 2 * math.pi - math.pi/2
            px = x + math.cos(angle) * (self.table_radius + 70)
            py = y + math.sin(angle) * (self.table_radius + 40)
            # name
            self.canvas.create_text(px, py - 30, text=player.name, fill='white', font=('Helvetica', 12, 'bold'))
            # card backs or count for AI
            if player.is_human:
                # draw hand
                self.draw_hand(player)
            else:
                self.canvas.create_rectangle(px - 30, py - 10, px + 30, py + 10, fill='#444', outline='white')
                self.canvas.create_text(px, py, text=str(len(player.hand)), fill='white')

        # draw deck and discard
        self.draw_deck()
        self.draw_discard()

        # bottom-right: card description
        self.draw_card_description()

    def draw_deck(self):
        x, y = self.deck_pos
        # deck pile (stacked)
        count = self.deck.count()
        for i in range(min(6, count)):
            offset = i * 1.5
            self.canvas.create_rectangle(x - self.card_width/2 + offset, y - self.card_height/2 + offset,
                                         x + self.card_width/2 + offset, y + self.card_height/2 + offset,
                                         fill='#222', outline='white', tags=('deck',))
        self.canvas.create_text(x, y + self.card_height/2 + 10, text=f'Deck: {count}', fill='white')

    def draw_discard(self):
        x, y = self.discard_pos
        top = self.discard_pile[-1]
        color = self.tk_color_for(top.color)
        self.canvas.create_rectangle(x - self.card_width/2, y - self.card_height/2,
                                     x + self.card_width/2, y + self.card_height/2,
                                     fill=color, outline='white')
        self.canvas.create_text(x, y, text=str(top), fill='white')
        self.canvas.create_text(x, y + self.card_height/2 + 10, text='Discard', fill='white')

    def draw_hand(self, player):
        # draw human player's hand at bottom
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
            self.canvas.create_text(x, y, text=str(card), fill='white', tags=(tag,))
            if self.selected_index == i:
                self.canvas.create_rectangle(x - self.card_width/2 - 4, y - self.card_height/2 - 4,
                                             x + self.card_width/2 + 4, y + self.card_height/2 + 4,
                                             outline='yellow', width=3)

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
        # check deck
        dx, dy = self.deck_pos
        if abs(x - dx) < 60 and abs(y - dy) < 80:
            self.player_draw()
            return

        # check hand cards
        # approximate positions used in draw_hand
        margin = 20
        start_x = margin
        hy = self.height - self.card_height/2 - 30
        for i, card in enumerate(self.players[0].hand):
            hx = start_x + i * (self.card_width - 30)
            if hx - self.card_width/2 < x < hx + self.card_width/2 and hy - self.card_height/2 < y < hy + self.card_height/2:
                # select or play
                if self.selected_index == i:
                    self.attempt_play(i)
                else:
                    self.selected_index = i
                    self.draw_table()
                return

    def attempt_play(self, index):
        player = self.players[0]
        card = player.hand[index]
        top = self.discard_pile[-1]
        if (card.color == top.color or card.value == top.value or card.color is None):
            played = player.hand.pop(index)
            self.discard_pile.append(played)
            self.selected_index = None
            # effect handling (simplified)
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
            player.hand.append(card)
            self.selected_index = len(player.hand) - 1
            self.draw_table()
        else:
            messagebox.showinfo('Deck empty', 'No cards to draw.')

    def next_player(self):
        self.current = (self.current + self.direction) % len(self.players)

    def ai_turn_if_needed(self):
        # if current player is AI, make a move
        if self.players[self.current].is_human:
            return
        player = self.players[self.current]
        top = self.discard_pile[-1]
        card = player.play(top)
        if card:
            self.discard_pile.append(card)
            # simple effects
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
        # schedule next AI move if needed
        self.root.after(600, self.ai_turn_if_needed)

    def reshuffle_discard_into_deck(self):
        if len(self.discard_pile) <= 1:
            return
        top = self.discard_pile.pop()
        self.deck.cards = self.discard_pile[:]
        random.shuffle(self.deck.cards)
        self.discard_pile = [top]
