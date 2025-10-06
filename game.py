import random

COLORS = ['Pink', 'Black', 'Teal', 'Green']
VALUES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'Skip', 'Reverse', 'Draw Two']
SPECIALS = ['Wild', 'Wild Draw Four']


class Card:
    def __init__(self, color, value):
        self.color = color
        self.value = value

    def __str__(self):
        if self.color:
            return f"{self.color} {self.value}"
        else:
            return f"{self.value}"


class Deck:
    def __init__(self):
        self.cards = []
        for color in COLORS:
            self.cards.append(Card(color, '0'))
            for value in VALUES[1:]:
                self.cards.extend([Card(color, value)] * 2)
        for special in SPECIALS:
            self.cards.extend([Card(None, special)] * 4)
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop() if self.cards else None

    def add(self, card):
        self.cards.insert(0, card)

    def count(self):
        return len(self.cards)


class Player:
    def __init__(self, name, is_human=False):
        self.name = name
        self.hand = []
        self.is_human = is_human

    def draw(self, deck, count=1):
        for _ in range(count):
            card = deck.draw()
            if card:
                self.hand.append(card)

    def play(self, top_card):
        # simple AI: play first legal
        for i, card in enumerate(self.hand):
            if (card.color == top_card.color or
                card.value == top_card.value or
                card.color is None):
                return self.hand.pop(i)
        return None

    def has_uno(self):
        return len(self.hand) == 1

    def is_winner(self):
        return len(self.hand) == 0
