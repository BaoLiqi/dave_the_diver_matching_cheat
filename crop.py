import cv2
import os
import numpy as np


def crop_cards_from_screenshot(screenshot_path, card_locations, card_back_h, card_back_w, output_dir="cropped_cards"):
    screenshot = cv2.imread(screenshot_path)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i, (x, y) in enumerate(card_locations):
        card_roi = screenshot[y:y + card_back_h, x:x + card_back_w]
        output_path = os.path.join(output_dir, f"card_{i}.png")
        cv2.imwrite(output_path, card_roi)


class CardMemoryHelper:
    def __init__(self, screenshot_path, card_back_path):
        self.screenshot_path = screenshot_path
        self.card_back_path = card_back_path
        self.screenshot_color = cv2.imread(screenshot_path)
        self.screenshot_gray = cv2.cvtColor(self.screenshot_color, cv2.COLOR_BGR2GRAY)
        self.card_back = cv2.imread(card_back_path, cv2.IMREAD_GRAYSCALE)
        self.card_back_h, self.card_back_w = self.card_back.shape
        self.card_locations = self._find_all_cards()
        self.cheating_image = self.screenshot_color.copy()
        self.known_cards = {}

    def _find_all_cards(self):
        res = cv2.matchTemplate(self.screenshot_gray, self.card_back, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)
        card_locations = list(zip(*loc[::-1]))
        return card_locations


if __name__ == '__main__':
    screenshot_path = "assets/screenshot.png"
    card_back_path = "assets/card_back.png"
    screenshot_to_be_cropped_path = "image.png"

    helper = CardMemoryHelper(screenshot_path, card_back_path)

    card_locations = helper.card_locations
    card_back_h = helper.card_back_h
    card_back_w = helper.card_back_w
    output_dir = "cropped_cards"

    crop_cards_from_screenshot(screenshot_to_be_cropped_path, card_locations, card_back_h, card_back_w, output_dir)
    print('finish')